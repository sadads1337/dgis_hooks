from __future__ import annotations

import os
import requests

from collections import defaultdict
from dataclasses import dataclass
from logging import Logger
from typing import Dict, List, Optional

from dgis.hooks.plugins.plugin import PluginResult, PluginResultPayload
from dgis.hooks.utility.git import GitRef


@dataclass
class FileComment:
    file_path: str
    content: str


# Special key for results without file (like branch checks)
_g_dummy_file = "__general__"

# Invisible marker added to all comments posted by this tool. Useful to identify
# bot's comments among other discussions and avoid duplicates.
_g_comment_marker = "<!-- lint-review -->"


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
    content_parts = []
    if payload.stdout:
        content_parts.append(f"**stdout:**\n```\n{payload.stdout}\n```")
    if payload.stderr:
        content_parts.append(f"**stderr:**\n```\n{payload.stderr}\n```")
    if payload.diff and payload.diff.strip():
        content_parts.append(f"**diff:**\n```diff\n{payload.diff}\n```")
    # Visible tag for users and invisible marker for programmatic detection.
    content_parts.append(f"\n #lint-review\n{_g_comment_marker}")
    return "\n\n".join(content_parts) if content_parts else "No details available"


def _create_file_comment(file_path: str, payloads: List[PluginResultPayload]) -> FileComment:
    comment_lines = []
    for i, payload in enumerate(payloads, 1):
        if len(payloads) > 1:
            comment_lines.append(f"**Lint suggestion #{i}:**")
        content = _format_payload_content(payload)
        comment_lines.append(content)
    comment_content = "\n\n".join(comment_lines)
    return FileComment(file_path=file_path, content=comment_content)


class GitLabReporter:
    def __init__(self, git_ref: GitRef, log: Optional[Logger] = None):
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

    def _fetch_existing_comments(self) -> Dict[str, set]:
        existing: Dict[str, set] = {}
        if not self._gitlab_api_url or not self._project_id or not self._merge_request_iid:
            return existing

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
                    return existing

                discussions = resp.json()
                if not discussions:
                    break

                for disc in discussions:
                    notes = disc.get("notes") or []
                    for note in notes:
                        body = note.get("body") or ""
                        pos = note.get("position") or {}
                        old_path = pos.get("old_path")
                        new_path = pos.get("new_path")
                        file_path = old_path or new_path
                        if file_path:
                            existing.setdefault(file_path, set()).add(body.strip())

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
            return existing

        return existing

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

        headers = {
            "PRIVATE-TOKEN": self._gitlab_token,
            "Content-Type": "application/json",
        }

        all_posted = True

        # Fetch existing comments once and avoid duplicates.
        existing_by_file = self._fetch_existing_comments()

        for comment in comments:
            # Skip posting if identical comment body already exists for the same file.
            bodies_for_file = existing_by_file.get(comment.file_path, set())
            if comment.content.strip() in bodies_for_file:
                self._log_func(f"Skipping duplicate comment for {comment.file_path}", "debug")
                continue
            try:
                url = (
                    f"{self._gitlab_api_url}/projects/{self._project_id}/merge_requests/"
                    f"{self._merge_request_iid}/discussions"
                )

                body = {
                    "body": comment.content,
                    "position": {
                        "base_sha": self._ref.old_rev,
                        "start_sha": self._ref.old_rev,
                        "head_sha": self._ref.new_rev,
                        "old_path": comment.file_path,
                        "new_path": comment.file_path,
                        "position_type": "text",
                    },
                }

                response = requests.post(url, json=body, headers=headers, timeout=10)

                if response.status_code in (201, 200):
                    self._log_func(f"Successfully posted comment for file: {comment.file_path}", "debug")
                    # Update local cache so subsequent comments in this run will be deduped too.
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
