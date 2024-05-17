import pytest

from git import Repo
from pathlib import Path

from dgis.hooks.utility.git import GitRef
from dgis.hooks.plugins.plugin import PluginContext, PluginResultStatus, execute_plugin
from dgis.hooks.plugins.packaged.clang_format_check import ClangFormatCheckPlugin

from utility import make_and_commit_test_file, move_and_commit_test_file

g_clang_format_content = """
---
BasedOnStyle: LLVM
IndentWidth: 4
AllowShortFunctionsOnASingleLine: None
"""

_g_cpp_files = ["""
int main() {
    return 0;
}
""", """
struct S {
    int f() {
        const auto l = []() { return 0; };
        return l();
    }
}

int main() {
    S s;
    s.f();
}
""",
]

_g_cpp_files_ivalid_format = ["""int main() { return 0; }"""]


def test_non_cpp_files(tmp_path):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path(".clang-format"), g_clang_format_content)
    make_and_commit_test_file(git_repo, Path("test.txt"), "test")
    make_and_commit_test_file(git_repo, Path("test_2.txt"), "test2")

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(ClangFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


def test_non_cpp_empty_files(tmp_path):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path(".clang-format"), g_clang_format_content)
    make_and_commit_test_file(git_repo, Path("test.txt"))
    make_and_commit_test_file(git_repo, Path("test_2.txt"))

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(ClangFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


def test_cpp_empty_files(tmp_path):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path(".clang-format"), g_clang_format_content)
    make_and_commit_test_file(git_repo, Path("test.cpp"))
    make_and_commit_test_file(git_repo, Path("test_2.cpp"))

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(ClangFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("cpp_content", _g_cpp_files)
def test_cpp_non_empty_files(tmp_path, cpp_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path(".clang-format"), g_clang_format_content)
    make_and_commit_test_file(git_repo, Path("test.cpp"))
    make_and_commit_test_file(git_repo, Path("test.cpp"), cpp_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(ClangFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("cpp_content", _g_cpp_files)
def test_cpp_non_empty_files_deep_files(tmp_path, cpp_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path(".clang-format"), g_clang_format_content)
    make_and_commit_test_file(git_repo, Path("testdir/other/test.cpp"))
    make_and_commit_test_file(git_repo, Path("testdir/other/test.cpp"), cpp_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(ClangFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("cpp_content", _g_cpp_files)
def test_cpp_non_empty_files_no_format(tmp_path, cpp_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.cpp"))
    make_and_commit_test_file(git_repo, Path("test.cpp"), cpp_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(ClangFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("cpp_content", _g_cpp_files_ivalid_format)
def test_cpp_non_empty_files_invalid_format(tmp_path, cpp_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path(".clang-format"), g_clang_format_content)
    make_and_commit_test_file(git_repo, Path("test.cpp"))
    make_and_commit_test_file(git_repo, Path("test.cpp"), cpp_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(ClangFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Failed


@pytest.mark.parametrize("cpp_content", _g_cpp_files)
def test_cpp_non_empty_files_moved(tmp_path, cpp_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path(".clang-format"), g_clang_format_content)
    make_and_commit_test_file(git_repo, Path("test.cpp"), cpp_content)

    move_and_commit_test_file(git_repo, Path("test.cpp"), Path("test_2.cpp"))

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(ClangFormatCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok
