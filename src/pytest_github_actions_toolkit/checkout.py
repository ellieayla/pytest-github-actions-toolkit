import logging
import subprocess
from collections.abc import Generator, Iterator, Mapping, MutableMapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import ItemsView, Self

import pytest

logger = logging.getLogger(__name__)


@contextmanager
def override_home(to: Path) -> Generator[None]:
    """Run a context with the HOME environment variable overridden."""
    with pytest.MonkeyPatch.context() as context:
        context.setenv("HOME", str(to))
        yield


def find_git_binary() -> Path:
    for possibility in ["/usr/bin/git"]:
        location = Path(possibility)
        if location.exists() and location.is_file():
            return location
    raise FileNotFoundError("No git found.")


@dataclass
class GitCommand:
    git_bin: Path = field(default_factory=find_git_binary)

    def run(self, command: Sequence[str], cwd: Path, env: Mapping[str, str] | None = None) -> str:
        logger.info(f"GitCommand: {command}")
        return subprocess.check_output([str(self.git_bin), *command], text=True, cwd=cwd, env=env)


@dataclass
class GitConfig(MutableMapping[str, str]):
    root: Path
    command: GitCommand

    def __setitem__(self, key: str, value: str) -> None:
        self.command.run(["config", "set", "--local", key, value], cwd=self.root)

    def __delitem__(self, key: str) -> None:
        self.command.run(["config", "unset", "--local", key], cwd=self.root)

    def __getitem__(self, key: str) -> str:
        return self.command.run(["config", "get", "--local", key], cwd=self.root).strip()

    def __iter__(self) -> Iterator[str]:
        yield from self.keys()
        # for key, _item in self.items():
        #    self.keys()
        #    yield key

    def __len__(self) -> int:
        return len(self.items())

    def items(self) -> ItemsView[str, str]:
        ret = self.command.run(["config", "list", "--local"], cwd=self.root)

        def kv(row: str) -> tuple[str, str]:
            k, _eq, v = row.partition("=")
            return (k, v)

        return ItemsView(dict([kv(row) for row in ret.splitlines()]))


@dataclass
class GitRepo:
    root: Path
    command: GitCommand = field(default_factory=GitCommand)

    @classmethod
    def init(cls, root: Path, bare: bool = False) -> Self:
        bare_args = ["--bare"] if bare else []

        command = GitCommand()
        command.run(["init", "--initial-branch=main", "--template=", *bare_args, "--", str(root)], cwd=Path.cwd())
        return cls(root, command=command)

    @classmethod
    def clone(cls, source: str, root: Path, branch: str | None = None) -> Self:
        command = GitCommand()

        branch_args = ["--branch", branch] if branch else []
        command.run(["clone", *branch_args, "--", source, str(root)], cwd=Path.cwd())
        return cls(root, command=command)

    def git(self, args: Sequence[str], env: Mapping[str, str] | None = None) -> str:
        return self.command.run(args, cwd=self.root, env=env)

    def add_remote(self, source: str, name: str = "origin") -> None:
        self.git(["remote", "add", name, "--", source])

    def add(self, file_spec: Sequence[str]) -> None:
        self.git(["add", "--", *file_spec])

    def commit(self, message: str, date: datetime | None = None, commit_date: datetime | None = None) -> None:
        date_args = [f"--date={date.isoformat()}"] if date else []
        commit_date_env = {"GIT_COMMITTER_DATE": commit_date.isoformat()} if commit_date else {}
        self.git(["commit", *date_args, "--no-edit", "--message", message], env=commit_date_env)

    def log1(self) -> str:
        """Just the hash of the last commit on the current ref."""
        return self.git(["log", "-1", "--format=%H"]).strip()

    @property
    def config(self) -> GitConfig:
        return GitConfig(self.root, self.command)

    @contextmanager
    def worktree(self, branch: str, path: Path) -> Generator[Self]:
        self.git(["worktree", "add", "-B", branch, "--", str(path)])
        yield self.__class__(path, command=self.command)
        self.git(["worktree", "remove", "--", str(path)])


def get_checkout_info(ref: str = "", commit: str = "") -> tuple[str, str | None]:
    if not ref and not commit:
        raise ValueError("ref and commit cannot both be empty.")

    result_ref = None
    start_point = None

    upper_ref = ref.upper()

    if not ref:  # SHA only
        result_ref = commit

    elif upper_ref.startswith("REFS/HEADS/"):
        branch = ref[len("REFS/HEADS/") :]
        result_ref = branch
        start_point = f"refs/remotes/origin/{branch}"

    elif upper_ref.startswith("REFS/PULL/"):
        branch = ref[len("REFS/PULL/") :]
        result_ref = f"refs/remotes/pull/{branch}"

    elif upper_ref.startswith("REFS/TAGS/"):
        result_ref = ref

    elif upper_ref.startswith("REFS/"):
        result_ref = commit if commit else ref

    else:  # unqualified ref
        raise ValueError(f"Unqualified ref {ref=}, use refs/heads/{ref} or refs/tags/{ref} instead.")

    return (result_ref, start_point)


def get_refspec(ref: str, commit: str, fetch_tags: bool = False) -> list[str]:
    if not ref and not commit:
        raise ValueError("ref and commit cannot both be empty.")

    result: list[str] = []
    upper_ref = ref.upper()

    if fetch_tags:
        result.append("+refs/tags/*:refs/tags/*")

    if commit:
        if upper_ref.startswith("REFS/HEADS/"):
            branch = ref[len("REFS/HEADS/") :]
            result.append(f"+{commit}:refs/remotes/origin/{branch}")
        elif upper_ref.startswith("REFS/PULL/"):
            branch = ref[len("REFS/PULL/") :]
            result.append(f"+{commit}:refs/remotes/pull/${branch}")

        elif upper_ref.startswith("REFS/TAGS/"):
            if not fetch_tags:
                result.append(f"+{ref}:{ref}")

        else:  # no destination ref
            result.append(commit)

    elif not upper_ref.startswith("REFS/"):  # unqualified ref
        result.append(f"+refs/heads/{ref}*:refs/remotes/origin/{ref}*")
        if not fetch_tags:
            result.append(f"+refs/tags/{ref}*:refs/tags/{ref}*")

    elif upper_ref.startswith("REFS/HEADS/"):
        branch = ref[len("REFS/HEADS/") :]
        result.append(f"+{ref}:refs/remotes/origin/{branch}")

    elif upper_ref.startswith("REFS/PULL/"):
        branch = ref[len("REFS/PULL/") :]
        result.append(f"+{ref}:refs/remotes/pull/${branch}")

    elif upper_ref.startswith("REFS/TAGS/"):
        if not fetch_tags:
            result.append(f"+{ref}:{ref}")
    else:
        result.append(f"+{ref}:{ref}")

    return result


@dataclass
class CheckoutFixture:
    """Behaves similar to a simplified action/checkout"""

    root: Path
    depth: int | None = 1
    default_branch: str = "main"
    fetch_tags: bool = False

    def __call__(self, source: Path | str, ref: str | None = None, commit: str = "") -> str:
        ref = ref or f"refs/heads/{self.default_branch}"

        repo = GitRepo.init(self.root)
        repo.add_remote(str(source))

        refspec = get_refspec(ref, commit, self.fetch_tags)

        fetch_args = ["-c", "protocol.version=2", "fetch", "--no-tags", "--prune", "--no-recurse-submodules"]
        if self.depth is not None:
            fetch_args.append(f"--depth={self.depth}")
        fetch_args.append("origin")

        print(" ".join(fetch_args))
        print(" ".join(refspec))
        repo.git([*fetch_args, *refspec])

        checkout_ref, checkout_start_point = get_checkout_info(ref, commit or "")
        checkout_args = ["checkout", "--progress", "--force"]

        if checkout_start_point:
            checkout_args.extend(["-B", checkout_ref, checkout_start_point])
        else:
            checkout_args.append(checkout_ref)

        repo.git([*checkout_args])

        log1 = repo.git(["log", "-1", "--format=%H"]).strip()

        return log1
