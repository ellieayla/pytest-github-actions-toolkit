from pathlib import Path
from string import ascii_lowercase

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
    (root / d / "e-file").touch()

    assert list(tree(root, limit_to_directories=True)) == [
        "└── a",
        "    └── b",
        "        └── c",
        "            └── d",
        "4 directories",
    ]
