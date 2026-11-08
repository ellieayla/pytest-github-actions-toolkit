"""
A crude wrapper around the the 'git' cli.
One of GitPython/gix/pygit2/dulwich could be used instead.
"""

import logging
import os
import subprocess
from collections.abc import Generator, ItemsView, Iterator, Mapping, MutableMapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Protocol, Self

import pytest

logger = logging.getLogger(__name__)


class GitRepo(Protocol):
    """Anything that behaves vaguely like a git repository class."""

    def __init__(self, root: Path): ...
    @classmethod
    def init(cls, root: Path) -> Self: ...
    def add_remote(self, source: str, name: str = "origin") -> None: ...
    def git(self, args: Sequence[str], env: Mapping[str, str] | None = None) -> str: ...


@contextmanager
def override_home(to: Path) -> Generator[None]:
    """Run a context with the HOME environment variable overridden."""
    with pytest.MonkeyPatch.context() as context:
        context.setenv("HOME", str(to))
        yield


def find_git_binary() -> Path:
    """Locate the git binary on the OS search path (PATH)."""
    search_path = os.get_exec_path()
    for possibile_dir, possible_file in product(search_path, ("git", "git.exe")):
        location = Path(possibile_dir) / possible_file
        if location.exists() and location.is_file():
            try:
                version = subprocess.check_output([location, "--version"], text=True)  # noqa: S603
                logger.info(f"Using {location}: {version.strip()}")
                return location
            except subprocess.SubprocessError:
                continue

    raise FileNotFoundError(f"No git found in {search_path!r}")


@dataclass
class GitCommand:
    """Where the git binary is, and executing things with it."""

    git_bin: Path = field(default_factory=find_git_binary)

    def __post_init__(self) -> None:
        if not self.git_bin.exists():
            raise FileNotFoundError(self.git_bin)

    def run(self, command: Sequence[str], cwd: Path, env: Mapping[str, str] | None = None) -> str:
        logger.info(f"GitCommand: {command}")
        return subprocess.check_output([str(self.git_bin), *command], text=True, cwd=cwd, env=env)  # noqa: S603


@dataclass
class GitConfig(MutableMapping[str, str]):
    """Modeling of a .git/config file."""

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

    def __len__(self) -> int:
        return len(self.items())

    def items(self) -> ItemsView[str, str]:
        ret = self.command.run(["config", "list", "--local"], cwd=self.root)

        def kv(row: str) -> tuple[str, str]:
            k, _eq, v = row.partition("=")
            return (k, v)

        return ItemsView(dict([kv(row) for row in ret.splitlines()]))


class Commit(str):
    """Value type for a 40-character commit hash."""

    def __new__(cls, object: object) -> Self:
        value = str(object).lower()
        if len(value) != 40:
            raise ValueError(f"Expected 40-character commit hash (not {value!r} len ({len(value)}))")
        return super().__new__(cls, value)


@dataclass
class GitSubprocessRepo(GitRepo):
    """
    A simple wrapper for interacting with a repository using a git executable.

    For anything more complex, consider one of these instead:

    * https://gitpython.readthedocs.io/
    * https://dulwich.readthedocs.io/
    * https://github.com/GitoxideLabs/GixPython/
    """

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

    def refs(self) -> Mapping[str, Commit]:
        def _parse_line(row: str) -> tuple[str, Commit]:
            ref, _nul, sha = row.partition("\0")
            return ref, Commit(sha)

        return dict(_parse_line(row) for row in self.git(["for-each-ref", r"--format=%(refname)%00%(objectname)"]).splitlines())

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
