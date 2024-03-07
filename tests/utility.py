from pathlib import Path
from typing import Optional
from git import Repo


def make_test_repo(repo_path: Path, *args, **kwargs) -> Repo:
    git_repo = Repo.init(repo_path, *args, **kwargs)
    return git_repo


def make_and_commit_test_file(git_repo: Repo, file_relative_path: Path, file_content: Optional[str] = None,
                              amend: bool = False):
    file_path = git_repo.working_tree_dir / file_relative_path
    file_path.touch()
    if file_content:
        with open(file_path, "w") as file:
            file.write(file_content)
    git_repo.git.add(file_path)
    if amend:
        git_repo.git.commit("--amend", "-m", f"'commit {str(file_path)}'")
    else:
        git_repo.git.commit("-m", f"'commit {str(file_path)}'")
