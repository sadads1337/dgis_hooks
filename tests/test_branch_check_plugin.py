from pathlib import Path

import pytest

from dgis.hooks.plugins.packaged.branch_check import BranchCheckPlugin
from dgis.hooks.plugins.plugin import PluginContext, PluginResultStatus, execute_plugin
from dgis.hooks.utility.git import GitRef

from tests.utility import make_test_repo, make_and_commit_test_file

_g_valid_branch_names = [
    "master",
    "main",
    "test-ABC-#-aBc_123",
    "test-ABC-123-aBc_123",
    "release-123.567",
    "stable/release-123.567"
    "stable_release-123"
]

_g_invalid_branch_names = [
    "$",
    "test-ABC-123-aBc123!",
    "release-123.!567",
    "stable/release-123\"567\""
    "stable/release-\'"
]


@pytest.mark.parametrize("branch_name", _g_valid_branch_names)
def test_valid_branch_names(tmp_path, branch_name):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = make_test_repo(git_repo_path)

    git_repo.git.checkout("-b", branch_name)
    make_and_commit_test_file(git_repo, Path("test.txt"))
    make_and_commit_test_file(git_repo, Path("test2.txt"))
    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(BranchCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("branch_name", _g_invalid_branch_names)
def test_invalid_branch_names(tmp_path, branch_name):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = make_test_repo(git_repo_path)

    git_repo.git.checkout("-b", branch_name)
    make_and_commit_test_file(git_repo, Path("test.txt"))
    make_and_commit_test_file(git_repo, Path("test2.txt"))
    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(BranchCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Failed
