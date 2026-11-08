"""A crude implementation of action/checkout, using the 'git' cli."""

import logging
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from . import raw_git_repo_prefab

if TYPE_CHECKING:
    from _pytest.fixtures import SubRequest
    from _pytest.nodes import Item

logger = logging.getLogger(__name__)


remote_repo_refs_stash_key = pytest.StashKey[dict[str, str]]()


class RemoteRepository(Path):
    def write_raw_git_repo(self) -> None:
        raw_git_repo_prefab.write_raw_git_repo(self)

    def refs(self) -> dict[str, str]:
        return raw_git_repo_prefab.refs(self)


@pytest.fixture
def sample_remote_repo(tmp_path_factory: pytest.TempPathFactory, request: "SubRequest") -> Generator[Path]:
    """
    A bare git repository in a local temp directory which can be cloned and pushed to.

    Path can be added as a remote (git remote add ...).

    Contains one commit (d7c2169cd2af356a325633261afe5cc6237059a5).

    At teardown, a summary of refs in the remote will be stashed on the test node/item,
    and added as a report section.
    """

    location = tmp_path_factory.mktemp("__remote_repo-")

    raw_git_repo_prefab.write_raw_git_repo(location)

    yield location

    # During teardown of the fixture, take a snapshot of the repository's refs
    request.node.stash[remote_repo_refs_stash_key] = raw_git_repo_prefab.refs(location)


@dataclass(frozen=True)
class RemotePlugin:
    """Report refs in the remote."""

    config: pytest.Config

    @pytest.hookimpl(wrapper=True, trylast=True)
    def pytest_runtest_teardown(self, item: "Item") -> Generator[None]:
        """If a summary of the remote repository's refs was stashed on this test node/item, add it to the report."""
        yield

        try:
            refs = item.stash[remote_repo_refs_stash_key]
            summary = "\n".join([f"{commit_hash} {ref}" for ref, commit_hash in refs.items()])

            item.add_report_section("teardown", "remote repository refs at", summary)
        except KeyError:
            pass


@pytest.hookimpl
def pytest_configure(config: pytest.Config) -> None:
    config.pluginmanager.register(RemotePlugin(config), __name__)
