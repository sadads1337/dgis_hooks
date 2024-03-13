import pytest

from git import Repo

from dgis.hooks.plugins.packaged.utf8_check import UTF8CheckPlugin
from dgis.hooks.plugins.plugin import PluginContext, PluginResultStatus, execute_plugin
from dgis.hooks.utility.git import GitRef


_g_strings = [
    "",
    "such a long normal string",
    "such a long \n normal string \n with line breaks",
    "utf emoji list 😀😅🤣🙃😇"
]


@pytest.mark.parametrize("file_content", _g_strings)
def test_valid_file(tmp_path, file_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    tmp_file_path = git_repo_path / "unimportant.txt"
    tmp_file_path.touch()
    git_repo.git.add(tmp_file_path)
    git_repo.git.commit("-m", f"commit {str(tmp_file_path)}")

    tmp_file_path = git_repo_path / "utf8.txt"
    with open(tmp_file_path, mode="w", encoding="utf-8", errors="strict") as file:
        file.write(file_content)
    git_repo.git.add(tmp_file_path)
    git_repo.git.commit("-m", f"commit {str(tmp_file_path)}")

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(UTF8CheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok
