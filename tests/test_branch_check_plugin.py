import pytest

from dgis.hooks.plugins.packaged.branch_check import BranchCheckPlugin
from dgis.hooks.plugins.plugin import PluginContext, PluginResultStatus, execute_plugin
from dgis.hooks.utility.git import GitRef

from tests.utility import make_test_repo

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
    "test-ABC-#-aBc123*",
    "test-ABC-123-aBc123!",
    "release-123.!567",
    "stable/release-123\"567\""
    "stable/release-\'"
]


@pytest.mark.parametrize("branch_name", _g_valid_branch_names)
def test_valid_branch_names(tmp_path, branch_name):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = make_test_repo(git_repo_path, bare=True)

    ref = GitRef("unimportant", "unimportant2", branch_name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(BranchCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("branch_name", _g_invalid_branch_names)
def test_invalid_branch_names(tmp_path, branch_name):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = make_test_repo(git_repo_path, bare=True)

    ref = GitRef("unimportant", "unimportant2", branch_name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(BranchCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Failed
