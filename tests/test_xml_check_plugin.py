import pytest
import os

from git import Repo
from pathlib import Path

from dgis.hooks.plugins.packaged.xml_check import XmlCheckPlugin
from dgis.hooks.plugins.plugin import PluginContext, PluginResult, PluginResultStatus, execute_plugin
from dgis.hooks.utility.git import GitRef

from tests.utility import make_and_commit_test_file


_g_valid_xml = [
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag/>",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag></tag>",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag><inner_tag/></tag>",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag><inner_tag attr=\"str\"/></tag>",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag><inner_tag>value</inner_tag></tag>",
]

_g_invalid_xml = [
    "<",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag>",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag><tag>",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag>",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag><inner_tag/><tag/>",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag><inner_tag<tag/>",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag><inner_tag></tag>",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag><inner_tag attr/></tag>",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag><inner_tag attrstr/></tag>",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag><inner_tag attr=str/></tag>",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><tag><inner_tag>value<inner_tag></tag>",
]


@pytest.mark.parametrize("xml_content", _g_valid_xml)
def test_valid_xml_created_file(tmp_path, xml_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.txt"))
    make_and_commit_test_file(git_repo, Path("test.xml"), xml_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(XmlCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("xml_content", _g_invalid_xml)
def test_invalid_xml_created_file(tmp_path, xml_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.txt"))
    make_and_commit_test_file(git_repo, Path("test.xml"), xml_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(XmlCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Failed


@pytest.mark.parametrize("xml_content", _g_valid_xml)
def test_valid_xml_modified_file(tmp_path, xml_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.xml"))
    make_and_commit_test_file(git_repo, Path("test.xml"), xml_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(XmlCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("xml_content", _g_invalid_xml)
def test_invalid_xml_modified_file(tmp_path, xml_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.xml"))
    make_and_commit_test_file(git_repo, Path("test.xml"), xml_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(XmlCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Failed


@pytest.mark.parametrize("xml_content", _g_valid_xml + _g_invalid_xml)
def test_valid_invalid_xml_deleted_file(tmp_path, xml_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.xml"), xml_content)

    test_file_path = git_repo_path / Path("test.xml")
    os.remove(test_file_path)
    git_repo.git.add(test_file_path)
    git_repo.git.commit("-m", f"'commit {str(test_file_path)}'")

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(XmlCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("xml_content", _g_valid_xml + _g_invalid_xml)
def test_ignore_created_non_xml_files(tmp_path, xml_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.txt"))
    make_and_commit_test_file(git_repo, Path("test2.txt"), xml_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(XmlCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("xml_content", _g_valid_xml + _g_invalid_xml)
def test_ignore_modified_non_xml_files(tmp_path, xml_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.txt"))
    make_and_commit_test_file(git_repo, Path("test2.txt"), xml_content)

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(XmlCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("xml_content", _g_valid_xml + _g_invalid_xml)
def test_ignore_deleted_non_xml_files(tmp_path, xml_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.txt"), xml_content)

    test_file_path = git_repo_path / Path("test.txt")
    os.remove(test_file_path)
    git_repo.git.add(test_file_path)
    git_repo.git.commit("-m", f"'commit {str(test_file_path)}'")

    ref = GitRef(git_repo.commit("HEAD~1").hexsha, git_repo.commit("HEAD").hexsha, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(XmlCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("xml_content", _g_valid_xml)
def test_valid_xml_force_updated_file(tmp_path, xml_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.xml"), xml_content)
    make_and_commit_test_file(git_repo, Path("test.xml"), "abc")

    commit = git_repo.commit("HEAD")
    old_rev = commit.hexsha

    git_repo.git.reset("--hard", "HEAD~1")

    commit = git_repo.commit("HEAD")
    new_rev = commit.hexsha

    ref = GitRef(old_rev, new_rev, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(XmlCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Ok


@pytest.mark.parametrize("xml_content", _g_invalid_xml)
def test_invalid_xml_force_updated_file(tmp_path, xml_content):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    make_and_commit_test_file(git_repo, Path("test.xml"), xml_content)
    make_and_commit_test_file(git_repo, Path("test.xml"), "abc")

    commit = git_repo.commit("HEAD")
    old_rev = commit.hexsha

    git_repo.git.reset("--hard", "HEAD~1")

    commit = git_repo.commit("HEAD")
    new_rev = commit.hexsha

    ref = GitRef(old_rev, new_rev, git_repo.head.ref.name)
    context = PluginContext(ref, git_repo, None)

    with execute_plugin(XmlCheckPlugin, context) as result:
        assert result.status == PluginResultStatus.Failed
