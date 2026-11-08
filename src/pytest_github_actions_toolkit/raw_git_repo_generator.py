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
from binascii import hexlify
from hashlib import sha1
from pathlib import Path
from textwrap import dedent
from typing import Literal

logger = logging.getLogger(__name__)

type GitType = Literal["commit"] | Literal["tree"] | Literal["blob"] | Literal["tag"]


def encode_object(content: str, t: GitType) -> bytes:
    header = f"{t} {len(content)}".encode()
    payload = header + b"\0" + content.encode()
    return payload


def git_hash_object(payload: bytes) -> bytes:
    h = sha1(payload, usedforsecurity=False)
    return h.digest()


def object_location(hash: bytes) -> Path:
    return Path(hexlify(hash[0:1]).decode(), hexlify(hash[1:]).decode())


def store_object(git_dir: Path, content: str, t: GitType) -> bytes:
    payload = encode_object(content, t)
    h = git_hash_object(payload)
    location = object_location(h)
    (git_dir / "objects" / location).parent.mkdir(exist_ok=True, parents=True)
    (git_dir / "objects" / location).write_bytes(zlib.compress(payload, level=1))
    logger.warning(f"Write object {h!r} at {location}: {payload=}")
    return h


def store_tree(git_dir: Path, payload: bytes) -> bytes:
    h = git_hash_object(payload)
    location = object_location(h)
    (git_dir / "objects" / location).parent.mkdir(exist_ok=True, parents=True)
    (git_dir / "objects" / location).write_bytes(zlib.compress(payload, level=1))
    logger.warning(f"Write object {h!r} at {location}: {payload=}")
    return h


def generate_simple_repository(into: Path) -> None:
    """Make a git repository composed of 1 commit, 1 tree, and 1 blob."""
    into.mkdir(exist_ok=True, parents=True)

    config = dedent("""\
        [core]
            repositoryformatversion = 0
            filemode = true
            bare = true
            ignorecase = true
            precomposeunicode = true
    """)
    (into / "config").write_text(config)

    (into / "HEAD").write_text("ref: refs/heads/main")

    (into / "refs").mkdir()
    (into / "refs/heads").mkdir()
    (into / "refs/heads/main").write_text("d7c2169cd2af356a325633261afe5cc6237059a5")

    commit = dedent("""\
        tree ce6cb4c746b5dea5b059c5d69c4f24d08c550f8d
        author pytest <pytest@localhost> 631152000 +0000
        committer pytest <pytest@localhost> 631152000 +0000

        Initial commit
        """)

    store_object(into, commit, "commit")

    blob = "Example remote repo"

    blob_hash = store_object(into, blob, "blob")

    tree_items = [b"100644 README.md\0" + blob_hash]
    tree_content = b"".join(tree_items)
    tree = b"tree " + str(len(tree_content)).encode() + b"\0" + tree_content

    print(f"writing {tree=}")
    tree_hash = store_tree(into, tree)
    print(f"Write tree {tree_hash=}")


def write_bytes(at: Path, b: bytes) -> None:
    at.parent.mkdir(exist_ok=True, parents=True)
    at.write_bytes(b)
