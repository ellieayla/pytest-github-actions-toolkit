import os
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import InitVar, dataclass, field
from enum import StrEnum
from itertools import chain
from pathlib import Path
from typing import Self


@dataclass
class StatResultDiff:
    """Differences between two calls to os.stat(), with a minimal repr including only the changed fields."""

    a: os.stat_result
    b: os.stat_result

    def __bool__(self) -> bool:
        return self.a != self.b

    def zip(self) -> list[tuple[str, float, float]]:
        return [(key, x, y) for key, x, y in zip(self.a.__match_args__, self.a, self.b)]

    def __repr__(self) -> str:
        return ", ".join(f"{key}: {x} => {y}" for key, x, y in self.zip() if x != y)


class Change(StrEnum):
    removed = "removed"
    added = "added"
    modified = "modified"
    unchanged = "unchanged"


_CHANGE_WIDTH = max(len(s) for s in Change) + 2


type PathStatus = tuple[Path, Change, None | StatResultDiff]


class StatusList(list[PathStatus]):
    """A list of PathStatus instances, but with a nicer repr."""

    def __repr__(self) -> str:
        return "\n".join(f"{record[1] + ':':{_CHANGE_WIDTH}}{record[0]}{' ' + repr(record[2]) if record[2] is not None else ''}" for record in self)


@dataclass
class TreeRecording:
    """Record stat() for each item in a directory tree, so it can be compared against another recording later."""

    path: Path
    include_directories: InitVar[bool] = True
    data: Mapping[Path, os.stat_result] = field(init=False)

    def __post_init__(self, include_directories: bool) -> None:
        self.data = {
            location.relative_to(self.path): location.stat() for location in self.path.rglob("*") if location.is_file() or include_directories
        }

    def compare(self, other: Self, include_unchanged: bool = False) -> list[PathStatus]:
        """Compare this recording against another one, producing a list of changes."""
        all_paths = set(chain(self.data.keys(), other.data.keys()))

        result: list[PathStatus] = []
        for path in all_paths:
            if path in self.data and path in other.data:
                # both have this path, compare their metadata
                if stat_differences := StatResultDiff(self.data[path], other.data[path]):
                    result.append((path, Change.modified, stat_differences))
                elif include_unchanged:
                    result.append((path, Change.unchanged, None))

            elif path in self.data:
                # left side only
                result.append((path, Change.removed, None))

            else:
                # right side only
                result.append((path, Change.added, None))

        return result


@contextmanager
def changes(path: Path) -> Generator[StatusList]:
    """Record a directory tree twice, producing a list of changes made during the context manager."""
    a = TreeRecording(path)
    status = StatusList()

    try:
        yield status

    finally:
        b = TreeRecording(path)
        status.extend(a.compare(b))
