from __future__ import annotations

import os
import re
import requests

from collections import defaultdict
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

from dgis.hooks.plugins.plugin import PluginResult, PluginResultPayload
from dgis.hooks.utility.git import GitRef


@dataclass
class FileComment:
    file_path: str
    content: str
    position: Tuple[Optional[int], Optional[int]] = (None, None)


# Special key for results without file (like branch checks)
_g_dummy_file = "__general__"

# Invisible marker added to all comments posted by this tool. Useful to identify
# bot's comments among other discussions and avoid duplicates.
_g_comment_marker = "<!-- lint-review -->"


def pick_anchor_line(unified_diff: str) -> Tuple[Optional[int], Optional[int]]:
    hunk_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    for line in unified_diff.splitlines():
        m = hunk_re.match(line)
        if not m:
            continue
        old_start = int(m.group(1))
        old_count = int(m.group(2) or "1")
        new_start = int(m.group(3))
        new_count = int(m.group(4) or "1")

        if new_count > 0:
            return new_start, None
        if old_count > 0:
            return None, old_start
    return None, None


def _group_results_by_file(results: List[PluginResult]) -> Dict[str, List[PluginResultPayload]]:
    grouped: Dict[str, List[PluginResultPayload]] = defaultdict(list)
    for result in results:
        if result.payloads:
            for payload in result.payloads:
                if payload.file:
                    grouped[payload.file].append(payload)
                else:
                    grouped[_g_dummy_file].append(payload)
    return dict(grouped)


def _format_payload_content(payload: PluginResultPayload) -> str:
    content_parts = [f"**Found problems in {payload.file}**\n---\n"] if payload.file else []
    if payload.stdout:
        content_parts.append(f"**stdout:**\n```\n{payload.stdout}\n```")
    if payload.stderr:
        content_parts.append(f"**stderr:**\n```\n{payload.stderr}\n```")
    if payload.diff and payload.diff.strip():
        content_parts.append(f"**diff:**\n```diff\n{payload.diff}\n```")
    # Visible tag for users and invisible marker for programmatic detection.
    content_parts.append(f"\n #lint-review\n{_g_comment_marker}")
    return "\n\n".join(content_parts) if content_parts else "No details available"


def _create_file_comment(file_path: Path, payloads: List[PluginResultPayload]) -> FileComment:
    comment_lines = []
    for i, payload in enumerate(payloads, 1):
        if len(payloads) > 1:
            comment_lines.append(f"**Lint suggestion #{i}:**")
        content = _format_payload_content(payload)
        comment_lines.append(content)
    comment_content = "\n\n".join(comment_lines)

    position = (None, None)
    for payload in payloads:
        if payload.diff:
            position = pick_anchor_line(payload.diff)
            break

    return FileComment(file_path=str(file_path), content=comment_content, position=position)


class GitLabReporter:
    def __init__(self, git_repo_path: Path, git_ref: GitRef, log: Optional[Logger] = None):
        self._repo_path = git_repo_path
        self._ref = git_ref
        self._log = log

        self._gitlab_api_url = os.getenv("CI_API_V4_URL")
        self._project_id = os.getenv("CI_PROJECT_ID")
        self._merge_request_iid = os.getenv("CI_MERGE_REQUEST_IID")
        self._gitlab_token = os.getenv("LINT_REVIEW_PERSONAL_ACCESS_TOKEN")

    def _log_func(self, message: str, level: str = "info"):
        if self._log:
            log_func = getattr(self._log, level)
            log_func(message)

    def _group_and_prepare_comments(self, results: List[PluginResult]) -> List[FileComment]:
        grouped = _group_results_by_file(results)
        comments = []
        for file_path, payloads in grouped.items():
            if file_path == _g_dummy_file:
                # For general comments (without file association), skip file-specific posting
                self._log_func(f"General comment found (no file association) with {len(payloads)} payload(s)")
                continue
            comment = _create_file_comment(file_path, payloads)
            comments.append(comment)
        return comments

    def _fetch_existing_comments(self) -> Tuple[Set[str], Dict[str, set]]:
        existing: Set[str] = set()
        existing_positional: Dict[str, set] = dict()
        if not self._gitlab_api_url or not self._project_id or not self._merge_request_iid:
            return existing, existing_positional

        headers = {
            "PRIVATE-TOKEN": self._gitlab_token,
            "Content-Type": "application/json",
        }

        page = 1
        per_page = 100
        try:
            while True:
                url = (
                    f"{self._gitlab_api_url}/projects/{self._project_id}/merge_requests/"
                    f"{self._merge_request_iid}/discussions?page={page}&per_page={per_page}"
                )
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code != 200:
                    # unable to fetch discussions; bail out returning what we have
                    self._log_func(f"Failed to fetch existing discussions: {resp.status_code}", "warning")
                    return existing, existing_positional

                discussions = resp.json()
                if not discussions:
                    break

                for disc in discussions:
                    notes = disc.get("notes") or []
                    for note in notes:
                        body = note.get("body") or ""
                        pos = note.get("position") or {}
                        if pos:
                            old_path = pos.get("old_path")
                            new_path = pos.get("new_path")
                            file_path = old_path or new_path
                            if file_path:
                                existing_positional.setdefault(file_path, set()).add(body.strip())
                        else:
                            existing.add(body.strip())

                # Pagination: GitLab may use X-Next-Page header
                next_page = resp.headers.get("X-Next-Page")
                if not next_page:
                    break
                try:
                    page = int(next_page)
                except Exception:
                    break
        except requests.exceptions.RequestException as e:
            self._log_func(f"Exception while fetching discussions: {e}", "warning")
            return existing, existing_positional

        return existing, existing_positional

    def _get_versions(self) -> Optional[List[Dict]]:
        if not self._gitlab_api_url or not self._project_id or not self._merge_request_iid:
            return None

        headers = {
            "PRIVATE-TOKEN": self._gitlab_token,
        }

        try:
            url = (
                f"{self._gitlab_api_url}/projects/{self._project_id}/merge_requests/"
                f"{self._merge_request_iid}/versions"
            )
            resp = requests.get(url=url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            else:
                self._log_func(f"Failed to fetch merge request versions: {resp.status_code}", "error")
                return None
        except requests.exceptions.RequestException as error:
            self._log_func(f"Exception while fetching merge request versions: {error}", "error")
            return None

    def _post_comments(self, comments: List[FileComment]) -> bool:
        if not self._gitlab_api_url or not self._project_id or not self._merge_request_iid:
            self._log_func(
                "GitLab API credentials not available. Skipping comment posting. "
                "Make sure CI_API_V4_URL, CI_PROJECT_ID, and CI_MERGE_REQUEST_IID are set.",
                "warning",
            )
            return True
        if not comments:
            self._log_func("No comments to post", "info")
            return True

        versions = self._get_versions()
        if not versions:
            return True
        # Take last revision to add comments to the latest version of the MR.
        # This is important to avoid "position not found" errors.
        version = versions[0]

        headers = {
            "PRIVATE-TOKEN": self._gitlab_token,
            "Content-Type": "application/json",
        }

        all_posted = True

        # Fetch existing comments once and avoid duplicates.
        existing, existing_by_file = self._fetch_existing_comments()

        for comment in comments:
            old_line, new_line = comment.position
            positional = not old_line and not new_line

            # Skip posting if identical comment body already exists for the same file.
            if positional and comment.content.strip() in existing:
                self._log_func(f"Skipping duplicate comment for {comment.file_path}", "debug")
            if comment.content.strip() in existing_by_file.get(comment.file_path, set()):
                self._log_func(f"Skipping duplicate comment for {comment.file_path}", "debug")
                continue

            try:
                url = (
                    f"{self._gitlab_api_url}/projects/{self._project_id}/merge_requests/"
                    f"{self._merge_request_iid}/discussions"
                )

                old_line, new_line = comment.position
                if positional:
                    # No positions find, so writing simple comment without position.
                    # This can happen for example for comments generated by branch-level checks without file association.
                    body = {"body": comment.content}
                else:
                    position = {
                        "base_sha": version["base_commit_sha"],
                        "start_sha": version["start_commit_sha"],
                        "head_sha": version["head_commit_sha"],
                        "old_path": str(comment.file_path),
                        "new_path": str(comment.file_path),
                        "position_type": "text",
                    }
                    if new_line:
                        position["new_line"] = new_line
                    else:
                        position["old_line"] = old_line

                    body = {
                        "body": comment.content,
                        "position": position,
                    }

                response = requests.post(url, json=body, headers=headers, timeout=10)

                if response.status_code in (201, 200):
                    self._log_func(f"Successfully posted comment for file: {comment.file_path}", "debug")
                    # Update local cache so subsequent comments in this run will be deduped too.
                    if positional:
                        existing.add(comment.content.strip())
                    else:
                        existing_by_file.setdefault(comment.file_path, set()).add(comment.content.strip())
                else:
                    self._log_func(
                        f"Failed to post comment for {comment.file_path}. "
                        f"Status: {response.status_code}, Response: {response.text}",
                        "error",
                    )
                    all_posted = False

            except requests.exceptions.RequestException as e:
                self._log_func(f"Exception while posting comment for {comment.file_path}: {e}", "error")
                all_posted = False

        return all_posted

    def process_and_post(self, results: List[PluginResult]) -> bool:
        self._log_func("Starting to process plugin results for GitLab posting", "debug")

        comments = self._group_and_prepare_comments(results)
        result = self._post_comments(comments)

        if result:
            self._log_func("Successfully processed and posted all results", "info")
        else:
            self._log_func("Some comments failed to post", "warning")
        return result
