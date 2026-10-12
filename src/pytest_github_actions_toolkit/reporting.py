from collections.abc import Generator
from contextlib import contextmanager
from difflib import unified_diff
from pathlib import Path

import pytest

from .tree import tree


@contextmanager
def report_directory_changes(request: pytest.FixtureRequest, location: Path, name: str | None = None) -> Generator[Path]:
    """Report the directory content changes during the context manager, as a diff of asciiart.."""
    directory_asciiart_before = list(tree(location, include_summary=True))

    yield location

    if name is None:
        name = location.name

    directory_asciiart_after = list(tree(location, include_summary=True))

    changes = list(
        unified_diff(
            a=directory_asciiart_before,
            b=directory_asciiart_after,
            fromfile=f"{name} contents before",
            tofile=f"{name} contents after",
            n=max(len(directory_asciiart_before), len(directory_asciiart_after)),
        )
    )

    request.node.add_report_section("teardown", f"{name} directory contents at", changes)


def register_report_directory_contents(request: pytest.FixtureRequest, location: Path, name: str | None = None) -> None:
    """Report the directory content as it will exist at the end of the test."""
    if name is None:
        name = location.name

    def _add_report() -> None:
        directory_asciiart = list(tree(location, include_summary=False))
        request.node.add_report_section("teardown", f"{name} directory contents at", directory_asciiart)

    request.addfinalizer(_add_report)
