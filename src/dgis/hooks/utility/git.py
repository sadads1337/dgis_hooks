from dataclasses import dataclass
from enum import Enum

from git import Repo, NULL_TREE


class RefStatus(Enum):
    Deleted = 0
    ForceUpdated = 1
    Created = 2
    Updated = 3


# https://git-scm.com/docs/git-receive-pack#_pre_receive_hook
# Refs to be created will have sha1-old equal to 0{40},
# while refs to be deleted will have sha1-new equal to 0{40},
# otherwise sha1-old and sha1-new should be valid objects in the repository.
g_zero_rev = "0" * 40


@dataclass
class GitRef:
    old_rev: str
    new_rev: str
    ref: str

    def __str__(self):
        return f"old_rev: {self.old_rev} new_rev: {self.new_rev} ref: {self.ref}"

    def status(self, git_repo: Repo) -> RefStatus:
        zero_rev = g_zero_rev

        if self.new_rev == zero_rev:
            return RefStatus.Deleted
        elif self.old_rev != zero_rev and git_repo.git.rev_list(self.old_rev, f"^{self.new_rev}"):
            # https://git-scm.com/docs/git-rev-list
            # git rev-list oldrev ^newrev
            # Shows the commits reachable from oldrev but not reachable from newrev.
            # This shows the commits existed only old tree.
            # If this command show any commits, old tree was replaced with new tree, so forced update was occured.
            return RefStatus.ForceUpdated
        elif self.old_rev == zero_rev:
            return RefStatus.Created
        else:
            return RefStatus.Updated

    def diff(self, git_repo: Repo):
        status = self.status(git_repo)
        if status == RefStatus.Deleted:
            return []
        elif self.status(git_repo) in (RefStatus.ForceUpdated, RefStatus.Created):
            rev_list = git_repo.git.rev_list(self.new_rev, "--not", "--all")
            if rev_list:
                # Commit objects are in reverse chronological order.
                rev_list = rev_list.split('\n')
                commit = git_repo.commit(f"{rev_list[-1]}~1")
                return commit.diff(self.new_rev, create_patch=True, unified=0)
            else:
                commit = git_repo.commit(self.new_rev)
                return commit.diff(NULL_TREE, create_patch=True, unified=0)
        else:
            commit = git_repo.commit(self.old_rev)
            return commit.diff(self.new_rev, create_patch=True, unified=0)


def parse_ref(line: str) -> GitRef:
    old_rev, new_rev, ref = line.split()
    return GitRef(old_rev, new_rev, ref)
