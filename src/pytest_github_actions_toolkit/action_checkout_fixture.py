"""
A crude implementation of action/checkout, using the 'git' cli.
Completely optional fixture. One of GitPython/gix/pygit2/dulwich could be used instead.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from ._git_subprocess_provider import GitRepo, GitSubprocessRepo

logger = logging.getLogger(__name__)


def _get_checkout_info(ref: str = "", commit: str = "") -> tuple[str, str | None]:
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


def _get_refspec(ref: str, commit: str, fetch_tags: bool = False) -> list[str]:
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
    """
    Clone a repository, similar to a simplified action/checkout. Reads from 'source' and writes into 'root'.

    Internally uses the 'git' command line from _git_subprocess_provider.GitSubprocessRepo
    """

    root: Path
    depth: int | None = 1
    default_branch: str = "main"
    fetch_tags: bool = False
    provider: type[GitRepo] = field(default=GitSubprocessRepo)

    def __post_init__(self) -> None: ...

    def __call__(self, source: Path | str, ref: str | None = None, commit: str = "") -> str:
        ref = ref or f"refs/heads/{self.default_branch}"

        repo = self.provider.init(self.root)
        repo.add_remote(str(source))

        refspec = _get_refspec(ref, commit, self.fetch_tags)

        fetch_args = ["-c", "protocol.version=2", "fetch", "--no-tags", "--prune", "--no-recurse-submodules"]
        if self.depth is not None:
            fetch_args.extend(["--depth", str(self.depth)])
        fetch_args.append("origin")

        print(" ".join(fetch_args))
        print(" ".join(refspec))
        repo.git([*fetch_args, *refspec])

        checkout_ref, checkout_start_point = _get_checkout_info(ref, commit or "")
        checkout_args = ["checkout", "--progress", "--force"]

        if checkout_start_point:
            checkout_args.extend(["-B", checkout_ref, checkout_start_point])
        else:
            checkout_args.append(checkout_ref)

        repo.git([*checkout_args])

        log1 = repo.git(["log", "-1", "--format=%H"]).strip()

        return log1


@pytest.fixture
def checkout_repository(github_workspace_directory: Path, pytestconfig: pytest.Config) -> CheckoutFixture:
    return CheckoutFixture(github_workspace_directory)
