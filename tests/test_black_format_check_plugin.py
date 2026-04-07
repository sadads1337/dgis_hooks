import pytest

from git import Repo
from pathlib import Path

from dgis.hooks.plugins.packaged.black_format_check import BlackFormatCheckPlugin
from dgis.hooks.plugins.plugin import PluginContext, PluginResultStatus, execute_plugin
from dgis.hooks.utility.git import GitRef

from tests.utility import make_and_commit_test_file, move_and_commit_test_file

_g_pytoml_content = """
[tool.black]
line-length = 120
target-version = ['py312']
exclude = '''
/(
    \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''
"""

_g_good_py = [
    """def add(a, b):
    return a + b


class C:
    def f(self):
        return 1

""",
]

_g_bad_py = [
    "def add(a,b):\n return a+b\n",
    "def f():\n    x=1\n    return x\n",
]


def test_non_py_files(tmp_path):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("pyproject.toml"), _g_pytoml_content)
    make_and_commit_test_file(git_repo, Path("test.txt"), "test")
    make_and_commit_test_file(git_repo, Path("test2.txt"), "test2")

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo_path, git_repo, None)

    with execute_plugin(BlackFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


def test_py_empty_files(tmp_path):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("pyproject.toml"), _g_pytoml_content)
    make_and_commit_test_file(git_repo, Path("test.py"))
    make_and_commit_test_file(git_repo, Path("test_2.py"))

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo_path, git_repo, None)

    with execute_plugin(BlackFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("py_content", _g_good_py)
def test_py_non_empty_files(tmp_path, py_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("pyproject.toml"), _g_pytoml_content)
    make_and_commit_test_file(git_repo, Path("test.py"))
    make_and_commit_test_file(git_repo, Path("test.py"), py_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo_path, git_repo, None)

    with execute_plugin(BlackFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("py_content", _g_bad_py)
def test_py_non_empty_files_invalid_format(tmp_path, py_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("pyproject.toml"), _g_pytoml_content)
    make_and_commit_test_file(git_repo, Path("test.py"))
    make_and_commit_test_file(git_repo, Path("test.py"), py_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo_path, git_repo, None)

    with execute_plugin(BlackFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Failed


@pytest.mark.parametrize("py_content", _g_good_py)
def test_cpp_non_empty_files_deep_files(tmp_path, py_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("pyproject.toml"), _g_pytoml_content)
    make_and_commit_test_file(git_repo, Path("testdir/other/test.py"))
    make_and_commit_test_file(git_repo, Path("testdir/other/test.py"), py_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo_path, git_repo, None)

    with execute_plugin(BlackFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("py_content", _g_good_py)
def test_py_non_empty_files_moved(tmp_path, py_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("pyproject.toml"), _g_pytoml_content)
    make_and_commit_test_file(git_repo, Path("test.py"), py_content)

    move_and_commit_test_file(git_repo, Path("test.py"), Path("test_2.py"))

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo_path, git_repo, None)

    with execute_plugin(BlackFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok
