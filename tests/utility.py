import shutil

from pathlib import Path
from typing import Optional
from git import Repo


def make_test_repo(repo_path: Path, *args, **kwargs) -> Repo:
    git_repo = Repo.init(repo_path, *args, **kwargs)
    return git_repo


def make_and_commit_test_file(git_repo: Repo, file_relative_path: Path, file_content: Optional[str] = None,
                              amend: bool = False):
    file_path = git_repo.working_tree_dir / file_relative_path
    if len(file_path.parents) > 0 and not file_path.parent.exists():
        file_path.parent.mkdir(parents=True)
    file_path.touch()
    if file_content:
        with open(file_path, "w") as file:
            file.write(file_content)
    git_repo.git.add(file_path)
    if amend:
        git_repo.git.commit("--amend", "-m", f"'commit {str(file_path)}'")
    else:
        git_repo.git.commit("-m", f"'commit {str(file_path)}'")


def move_and_commit_test_file(git_repo: Repo, src_file_relative_path: Path, dst_file_relative_path: Path,
                              amend: bool = False):
    src_file_path = git_repo.working_tree_dir / src_file_relative_path
    dst_file_path = git_repo.working_tree_dir / dst_file_relative_path

    if len(dst_file_path.parents) > 0 and not dst_file_path.parent.exists():
        dst_file_path.parent.mkdir(parents=True)

    shutil.move(src_file_path, dst_file_path)
    git_repo.git.add(src_file_path)
    git_repo.git.add(dst_file_path)
    if amend:
        git_repo.git.commit("--amend", "-m", f"'commit {str(dst_file_path)}'")
    else:
        git_repo.git.commit("-m", f"'commit {str(dst_file_path)}'")
