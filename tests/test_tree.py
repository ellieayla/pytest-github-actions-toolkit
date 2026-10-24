from pathlib import Path
from string import ascii_lowercase

import pytest

from pytest_github_actions_toolkit.dir_stat import StatusList, TreeRecording, changes
from pytest_github_actions_toolkit.tree import tree


def letter_directories(depth: int = 4) -> Path:
    """Create a directory structure 'depth' levels deep, made of letters."""
    return Path(*ascii_lowercase[:depth])


def test_empty_tree(tmp_path: Path) -> None:
    # the tmp_path is empty.

    root = tmp_path / "empty"
    root.mkdir()
    r = list(tree(root, include_summary=False))
    assert len(r) == 0

    r = list(tree(root, include_summary=True))
    assert len(r) == 1
    assert r[0] == "No files or directories."


def test_tree_only_directories(tmp_path: Path) -> None:
    root = tmp_path / "empty"

    d = letter_directories()
    (root / d).mkdir(parents=True)
    (root / "a/b/c/e-file").touch()

    assert list(tree(root, limit_to_directories=True)) == [
        "└── a",
        "    └── b",
        "        └── c",
        "            └── d",
        "4 directories",
    ]


def test_tree_recording_compare(tmp_path: Path) -> None:
    """Make a directory tree, record its contents, make a change, record again, diff the recordings."""
    root = tmp_path / "empty"

    d = letter_directories()
    (root / d).mkdir(parents=True)

    a = TreeRecording(root)

    (root / d.parent / "foo").write_text("foo")

    b = TreeRecording(root)

    status = StatusList(a.compare(b))

    matcher = pytest.LineMatcher(sorted(repr(status).splitlines()))

    matcher.fnmatch_lines(
        [
            "added:     a/b/c/foo",
            "modified:  a/b/c *st_nlink*",
        ]
    )


def test_changes_contextmanager(tmp_path: Path) -> None:
    """Make a directory tree, make a change inside context manager, diff the recordings."""
    root = tmp_path / "empty"

    d = letter_directories()
    (root / d).mkdir(parents=True)

    with changes(root) as status:
        (root / d.parent / "foo").write_text("foo")

    matcher = pytest.LineMatcher(sorted(repr(status).splitlines()))

    matcher.fnmatch_lines(
        [
            "added:     a/b/c/foo",
            "modified:  a/b/c *st_nlink*",
        ]
    )
