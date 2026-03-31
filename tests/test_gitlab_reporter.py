import requests

from pathlib import Path

from dgis.hooks.scripts_gitlab_ci.gitlab_reporter import (
    _group_results_by_file,
    _format_payload_content,
    _create_file_comment,
    GitLabReporter,
    FileComment,
    _g_dummy_file,
)
from dgis.hooks.plugins.plugin import PluginResult, PluginResultPayload, PluginResultStatus
from dgis.hooks.utility.git import GitRef


def make_payload(file=None, stdout=None, stderr=None, diff=None):
    return PluginResultPayload(stdout=stdout, stderr=stderr, diff=diff, file=file)


def make_result(*payloads):
    return PluginResult(status=PluginResultStatus.Failed, payloads=list(payloads))


def test_format_payload_content_stdout_only():
    payload = make_payload(stdout="hello")
    content = _format_payload_content(payload)
    assert "**stdout:**" in content
    assert "hello" in content


def test_format_payload_content_with_stderr_and_diff():
    payload = make_payload(stderr="err", diff="-old\n+new")
    content = _format_payload_content(payload)
    assert "**stderr:**" in content
    assert "**diff:**" in content
    assert "-old" in content and "+new" in content


def test_create_file_comment_multiple_payloads():
    p1 = make_payload(stdout="a")
    p2 = make_payload(stderr="b")
    comment = _create_file_comment("src/file.py", [p1, p2])
    assert isinstance(comment, FileComment)
    assert "Lint suggestion #1" in comment.content or "Lint suggestion #1:" in comment.content
    assert "a" in comment.content and "b" in comment.content


def test_group_results_by_file_and_group_and_prepare_comments(monkeypatch):
    r1 = make_result(make_payload(file="a.py", stdout="o1"))
    r2 = make_result(make_payload(file="a.py", stderr="e1"))
    r3 = make_result(make_payload(file=None, stdout="general"))

    grouped = _group_results_by_file([r1, r2, r3])
    assert "a.py" in grouped
    assert _g_dummy_file in grouped
    assert len(grouped["a.py"]) == 2
    assert len(grouped[_g_dummy_file]) == 1

    reporter = GitLabReporter(Path(""), GitRef("oldsha", "newsha", "refs/heads/x"))
    comments = reporter._group_and_prepare_comments([r1, r2, r3])

    assert all(isinstance(c, FileComment) for c in comments)
    assert any(c.file_path == "a.py" for c in comments)


def test_post_comments_env_missing_no_network(monkeypatch):
    reporter = GitLabReporter(Path(""), GitRef("old", "new", "ref"))

    monkeypatch.delenv("CI_API_V4_URL", raising=False)
    monkeypatch.delenv("CI_PROJECT_ID", raising=False)
    monkeypatch.delenv("CI_MERGE_REQUEST_IID", raising=False)
    monkeypatch.delenv("LINT_REVIEW_PERSONAL_ACCESS_TOKEN", raising=False)

    comments = [FileComment(file_path="a.py", content="c")]

    result = reporter._post_comments(comments)
    assert result is True


def test_post_comments_skips_existing(monkeypatch):
    monkeypatch.setenv("CI_API_V4_URL", "https://gitlab.example/api/v4")
    monkeypatch.setenv("CI_PROJECT_ID", "123")
    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "10")
    monkeypatch.setenv("LINT_REVIEW_PERSONAL_ACCESS_TOKEN", "secrettoken")

    repo_path = Path("")
    ref = GitRef("oldrev", "newrev", "refs/heads/x")
    reporter = GitLabReporter(repo_path, ref)

    existing_body = "**stdout:**\n```\nhello\n```\n\n #lint-review\n"

    def fake_get(url, headers, timeout):
        class R:
            status_code = 200

            def json(self):
                return [
                    {"notes": [{"body": existing_body, "position": {"old_path": "src/a.py", "new_path": "src/a.py"}}]}
                ]

            headers = {}

        return R()

    monkeypatch.setattr(requests, "get", fake_get)

    def fake_post_should_not_be_called(url, json, headers, timeout):
        raise AssertionError("requests.post should not be called for duplicate comment")

    monkeypatch.setattr(requests, "post", fake_post_should_not_be_called)

    comment = FileComment(file_path="src/a.py", content=existing_body)
    ok = reporter._post_comments([comment])
    assert ok is True
