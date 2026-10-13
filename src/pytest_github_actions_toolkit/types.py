"""
foo
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import NewType

Actor = NewType("Actor", str)
Repo = NewType("Repo", str)


class Directory(Path): ...


class OwnerRepoUnparsableError(ValueError):
    def __repr__(self) -> str:
        return f"Expected format owner/repo: {super().__repr__()!r}"

    def __str__(self) -> str:
        return f"Expected format owner/repo: {super().__str__()!r}"


@dataclass(frozen=True)
class OwnerRepo:
    value: str = field(repr=False)
    owner: Actor = field(init=False)
    repo: str = field(init=False)

    def __post_init__(self) -> None:
        try:
            owner, _slash, repo = self.value.partition("/")
        except AttributeError:
            raise OwnerRepoUnparsableError(self.value)
        if any([not owner, not repo, "/" in repo]):
            raise OwnerRepoUnparsableError(self.value)

        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "repo", repo)


@dataclass
class Description:
    description: str

    def __repr__(self) -> str:
        return f"Description({self.description!r})"


@dataclass
class Example:
    example: str

    def __repr__(self) -> str:
        return f"Example({self.example!r})"

    def __str__(self) -> str:
        return self.example


class _MISSING_TYPE: ...


_MISSING = _MISSING_TYPE()
