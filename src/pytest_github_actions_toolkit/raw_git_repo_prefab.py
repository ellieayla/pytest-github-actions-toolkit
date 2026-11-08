"""
Boldly slam a git repo directly onto disk.

Absolute minimum needed to run the equivilant of following, but in a bare repo:

    git init
    git config set user.name pytest
    git config set user.email pytest@localhost
    echo "Example remote repo" > README.md
    git add README.md
    git commit -m "Initial commit"
"""

import logging
import zlib
from pathlib import Path
from textwrap import dedent
from typing import Literal

logger = logging.getLogger(__name__)

type GitType = Literal["commit"] | Literal["tree"] | Literal["blob"] | Literal["tag"]


def write_bytes(at: Path, b: bytes) -> None:
    at.parent.mkdir(exist_ok=True, parents=True)
    at.write_bytes(b)


def write_raw_git_repo(into: Path) -> None:
    """
    Directly write pre-baked bytes into files to create a bare git repo.
    This is faster than launching a git subprocess.
    """

    into.mkdir(parents=True, exist_ok=True)

    config = dedent("""\
        [core]
            repositoryformatversion = 0
            filemode = true
            bare = true
            ignorecase = true
            precomposeunicode = true
    """)
    (into / "config").write_text(config)

    blob = b"blob 19\x00Example remote repo"
    write_bytes(into / "objects/76/cbf7878c36488a4f59684bb5ecb6409d802228", zlib.compress(blob))

    tree = b'tree 37\x00100644 README.md\x00v\xcb\xf7\x87\x8c6H\x8aOYhK\xb5\xec\xb6@\x9d\x80"('
    write_bytes(into / "objects/ce/6cb4c746b5dea5b059c5d69c4f24d08c550f8d", zlib.compress(tree))

    commit = b"commit 163\x00tree ce6cb4c746b5dea5b059c5d69c4f24d08c550f8d\nauthor pytest <pytest@localhost> 631152000 +0000\ncommitter pytest <pytest@localhost> 631152000 +0000\n\nInitial commit\n"
    write_bytes(into / "objects/d7/c2169cd2af356a325633261afe5cc6237059a5", zlib.compress(commit))

    (into / "refs").mkdir()
    (into / "refs/heads").mkdir()
    (into / "refs/heads/main").write_text("d7c2169cd2af356a325633261afe5cc6237059a5")

    write_bytes(into / "refs/heads/main", b"d7c2169cd2af356a325633261afe5cc6237059a5\n")

    write_bytes(into / "HEAD", b"ref: refs/heads/main\n")


def refs(inside: Path) -> dict[str, str]:
    """Produce a map of ref names to commit hashes by directly reading the contents of the git repo's refs/ directory."""
    return {str(location.relative_to(inside)): location.read_text().strip() for location in (inside / "refs").rglob("*") if location.is_file()}
