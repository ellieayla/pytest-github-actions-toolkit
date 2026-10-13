# Inspired by https://stackoverflow.com/a/59109706 by Aaron Hall.
# Retrieved 2026-10-11, License - CC BY-SA 4.0

from collections.abc import Generator
from itertools import islice
from pathlib import Path

# ascii-art tree lines
# fmt: off
space =  "    "
branch = "│   "
tee =    "├── "
last =   "└── "
# fmt: on


def tree(dir_path: Path, length_limit: int | None = 1000, limit_to_directories: bool = False, include_summary: bool = True) -> Generator[str]:
    """
    Given a directory Path, yield lines of a visual tree structure recursively.

    If a length_limit is provided and reached,
        length_limit of file entries will be yielded,
        plus 1 row stating that the limit was reached,
        plus 1 row of summary if include_summary=True.

    Otherwise, row generation continues until traversal is complete.
    """

    files = 0
    directories = 0

    def inner(dir_path: Path, prefix: str = "") -> Generator[str]:
        nonlocal files, directories  # closure used for aggregating stats

        contents = list(dir_path.iterdir())
        pointers = [tee] * (len(contents) - 1) + [last]

        for pointer, path in zip(pointers, contents):
            if path.is_dir():
                yield prefix + pointer + path.name  # directory heading
                directories += 1
                extension = branch if pointer == tee else space
                yield from inner(path, prefix=prefix + extension)
            elif not limit_to_directories:
                yield prefix + pointer + path.name
                files += 1

    iterator = inner(dir_path)
    yield from islice(iterator, length_limit)

    if next(iterator, None):  # iterator was not exhausted, but we returned from the generator early
        yield (f"... length limit {length_limit} reached.")

    if include_summary:
        summary = [
            f"{directories} directories" if directories else None,
            f"{files} files" if files else None,
            "No files or directories." if not any((directories, files)) else None,
        ]

        yield ", ".join(s for s in summary if s)
