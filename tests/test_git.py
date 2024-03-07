import pytest

from git import Repo

from dgis.hooks.utility.git import parse_ref, RefStatus, GitRef


@pytest.mark.parametrize("line", ["", "123", "123 456", "123 456 789 111213"])
def test_parse_ref_invalid_string(tmp_path, line):
    with pytest.raises(Exception):
        parse_ref(line)


@pytest.mark.parametrize("line", ["123 456 789"])
def test_parse_ref_valid_string(tmp_path, line):
    ref = parse_ref(line)
    assert ref.old_rev == "123"
    assert ref.new_rev == "456"
    assert ref.ref == "789"


@pytest.mark.parametrize("line, expected", [(f"{'0' * 40} 456 789", RefStatus.Created),
                                            (f"123 {'0' * 40} 789", RefStatus.Deleted)])
def test_ref_status_created_deleted(tmp_path, line, expected):
    ref = parse_ref(line)
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)
    status = ref.status(git_repo)
    assert status == expected


def test_ref_status_exists(tmp_path):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    tmp_file_path = git_repo_path / f"test.txt"
    tmp_file_path.touch()
    git_repo.git.add(tmp_file_path)
    git_repo.git.commit("-m", f"'commit {str(tmp_file_path)}'")

    commit = git_repo.commit("HEAD")
    old_rev = commit.hexsha

    tmp_file_path = git_repo_path / f"other_test.txt"
    tmp_file_path.touch()
    git_repo.git.add(tmp_file_path)
    git_repo.git.commit("-m", f"commit {str(tmp_file_path)}")

    commit = git_repo.commit("HEAD")
    new_rev = commit.hexsha

    ref = GitRef(old_rev, new_rev, "123")
    status = ref.status(git_repo)
    assert status == RefStatus.Updated


def test_ref_status_force_update(tmp_path):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    tmp_file_path = git_repo_path / f"test.txt"
    tmp_file_path.touch()
    git_repo.git.add(tmp_file_path)
    git_repo.git.commit("-m", f"'commit {str(tmp_file_path)}'")

    tmp_file_path = git_repo_path / f"other_test.txt"
    tmp_file_path.touch()
    git_repo.git.add(tmp_file_path)
    git_repo.git.commit("-m", f"commit {str(tmp_file_path)}")

    commit = git_repo.commit("HEAD")
    old_rev = commit.hexsha

    git_repo.git.reset("--hard", "HEAD~1")

    commit = git_repo.commit("HEAD")
    new_rev = commit.hexsha

    ref = GitRef(old_rev, new_rev, "123")
    status = ref.status(git_repo)
    assert status == RefStatus.ForceUpdated


def test_diff_is_not_empty(tmp_path):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    tmp_file_path = git_repo_path / f"test.txt"
    tmp_file_path.touch()
    git_repo.git.add(tmp_file_path)
    git_repo.git.commit("-m", f"'commit {str(tmp_file_path)}'")

    old_commit = git_repo.commit("HEAD")
    old_rev = old_commit.hexsha

    tmp_file_path = git_repo_path / f"other_test.txt"
    tmp_file_path.touch()
    git_repo.git.add(tmp_file_path)
    git_repo.git.commit("-m", f"commit {str(tmp_file_path)}")

    new_commit = git_repo.commit("HEAD")
    new_rev = new_commit.hexsha

    ref = GitRef(old_rev, new_rev, "123")
    diff = ref.diff(git_repo)
    assert len(diff) > 0


def test_diff_is_empty(tmp_path):
    git_repo_path = tmp_path / "tmp-rep"
    git_repo = Repo.init(git_repo_path)

    tmp_file_path = git_repo_path / f"test.txt"
    tmp_file_path.touch()
    git_repo.git.add(tmp_file_path)
    git_repo.git.commit("-m", f"'commit {str(tmp_file_path)}'")

    old_commit = git_repo.commit("HEAD")
    old_rev = old_commit.hexsha

    new_rev = old_rev

    ref = GitRef(old_rev, new_rev, "123")
    diff = ref.diff(git_repo)
    assert len(diff) == 0
