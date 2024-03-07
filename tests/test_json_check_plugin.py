import pytest
import os

from git import Repo
from pathlib import Path

from dgis.hooks.plugins.packaged.json_check import JsonCheckPlugin
from dgis.hooks.plugins.plugin import PluginContext, PluginResult, PluginResultStatus, execute_plugin
from dgis.hooks.utility.git import GitRef

from tests.utility import make_and_commit_test_file


_g_valid_json = [
    "{}",
    "{\"attr\": \"str_value\"}",
    "{\"attr\": 1}",
    "{\"attr\": 1.0}",
    "{\"attr\": []}",
    "{\"attr\": [\"str\", \"other_str\"]}",
    "{\"attr\": [1, 2, 3]}",
    "{\"attr\": { \"other_attr\": [], \"another_attr\": 1.0 }}",
]

_g_invalid_json = [
    ""
    "}",
    "{{}",
    "{\"attr: \"str_value\"}",
    "{\"attr\" \"str_value\"}",
    "{\"attr\": str_value}",
    "{\"attr\": 1abc}",
    "{\"attr\": [[]}",
    "{\"attr\": [}",
    "{\"attr\": { abc }}",
]


@pytest.mark.parametrize("json_content", _g_valid_json)
def test_valid_json_created_file(tmp_path, json_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.txt"))
    make_and_commit_test_file(git_repo, Path("test.json"), json_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(JsonCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("json_content", _g_invalid_json)
def test_invalid_json_created_file(tmp_path, json_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.txt"))
    make_and_commit_test_file(git_repo, Path("test.json"), json_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(JsonCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Failed


@pytest.mark.parametrize("json_content", _g_valid_json)
def test_valid_json_modified_file(tmp_path, json_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.json"))
    make_and_commit_test_file(git_repo, Path("test.json"), json_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(JsonCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("json_content", _g_invalid_json)
def test_invalid_json_modified_file(tmp_path, json_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.json"))
    make_and_commit_test_file(git_repo, Path("test.json"), json_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(JsonCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Failed


@pytest.mark.parametrize("json_content", _g_valid_json + _g_invalid_json)
def test_valid_invalid_json_deleted_file(tmp_path, json_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.json"), json_content)

    test_file_path = git_repo_path / Path("test.json")
    os.remove(test_file_path)
    git_repo.git.add(test_file_path)
    git_repo.git.commit("-m", f"'commit {str(test_file_path)}'")

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(JsonCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("json_content", _g_valid_json + _g_invalid_json)
def test_ignore_created_non_json_files(tmp_path, json_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.txt"))
    make_and_commit_test_file(git_repo, Path("test2.txt"), json_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(JsonCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("json_content", _g_valid_json + _g_invalid_json)
def test_ignore_modified_non_json_files(tmp_path, json_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.txt"))
    make_and_commit_test_file(git_repo, Path("test2.txt"), json_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(JsonCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("json_content", _g_valid_json + _g_invalid_json)
def test_ignore_deleted_non_json_files(tmp_path, json_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.txt"), json_content)

    test_file_path = git_repo_path / Path("test.txt")
    os.remove(test_file_path)
    git_repo.git.add(test_file_path)
    git_repo.git.commit("-m", f"'commit {str(test_file_path)}'")

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(JsonCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("json_content", _g_valid_json)
def test_valid_json_force_updated_file(tmp_path, json_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.json"), json_content)
    make_and_commit_test_file(git_repo, Path("test.json"), "abc")

    commit = git_repo.commit("HEAD")
    old_rev = commit.hexsha

    git_repo.git.reset("--hard", "HEAD~1")

    commit = git_repo.commit("HEAD")
    new_rev = commit.hexsha

    ref = GitRef(old_rev, new_rev, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(JsonCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("json_content", _g_invalid_json)
def test_invalid_json_force_updated_file(tmp_path, json_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.json"), json_content)
    make_and_commit_test_file(git_repo, Path("test.json"), "abc")

    commit = git_repo.commit("HEAD")
    old_rev = commit.hexsha

    git_repo.git.reset("--hard", "HEAD~1")

    commit = git_repo.commit("HEAD")
    new_rev = commit.hexsha

    ref = GitRef(old_rev, new_rev, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(JsonCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Failed
