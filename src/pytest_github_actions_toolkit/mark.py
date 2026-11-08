import warnings
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from .env import Name
from .output import OutputFile
from .tree import tree
from .types import Directory

if TYPE_CHECKING:
    from _pytest.nodes import Item

from .plugin import github_resource_paths, github_work_directory

_PRINT_OUTPUT_CONTENT_MARKER_NAME = "print_output_content"
_CREATED_WORKFLOW_ENVIRONMENT_PATHS_FIXTURE_NAME = github_resource_paths.name
_CREATED_WORKFLOW_GITHUB_WORK_DIRECTORY_FIXTURE_NAME = github_work_directory.name

output_file_stash_key = pytest.StashKey[dict[Name, OutputFile]]()
output_mark_name_stash_key = pytest.StashKey[set[Name]]()


@pytest.hookimpl()
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", f"{_PRINT_OUTPUT_CONTENT_MARKER_NAME}(envvar): Attach a report with the given file/directory contents.")


def print_output_content_finalizer(node: pytest.Item, output_file: OutputFile) -> None:
    node.add_report_section("teardown", f"{output_file.path} contents at", output_file.read_text())


@pytest.hookimpl
def pytest_runtest_call(item: "Item") -> None:
    """Accumulate Names in a mark."""
    mark: pytest.Mark | None = item.get_closest_marker(_PRINT_OUTPUT_CONTENT_MARKER_NAME)

    if mark:
        if mark.args:  # add named items
            for_files = {Name(v) for v in mark.args}
        else:  # add all items
            for_files = set(Name)

        if output_mark_name_stash_key in item.stash:
            item.stash[output_mark_name_stash_key].update(for_files)
        else:
            item.stash[output_mark_name_stash_key] = for_files


@pytest.hookimpl
def pytest_runtest_makereport(item: pytest.Function, call: pytest.CallInfo[None]) -> None:
    """Communicate content of output files / directories to the failure report for 'print_output_content' marked tests."""

    if call.excinfo is None:  # test passed, so don't report anything
        return

    try:
        requested_names = item.stash[output_mark_name_stash_key]
    except KeyError:  # test was not marked, so don't report anything
        return

    if _CREATED_WORKFLOW_ENVIRONMENT_PATHS_FIXTURE_NAME not in item.fixturenames:  # don't have paths, so warn and don't report anything
        warnings.warn(
            f"Test marked with @pytest.mark.{_PRINT_OUTPUT_CONTENT_MARKER_NAME} doesn't use {_CREATED_WORKFLOW_ENVIRONMENT_PATHS_FIXTURE_NAME}. Remove the mark or add the fixture."
        )
        return

    # Test is marked, uses the fixture, has paths generated, and finished running.
    # What paths should be reported?

    workflow_paths: Mapping[Name, Path] = cast(Mapping[Name, Path], item.funcargs[_CREATED_WORKFLOW_ENVIRONMENT_PATHS_FIXTURE_NAME])
    hide_path_prefix: Path = cast(Path, item.funcargs.get(_CREATED_WORKFLOW_GITHUB_WORK_DIRECTORY_FIXTURE_NAME, Path("/")))

    requested_names = item.stash[output_mark_name_stash_key]

    requested = {a: workflow_paths[a] for a in requested_names if a in workflow_paths}

    # Add a pytest report section for each output Path
    for name, location in requested.items():
        # Attempt to make a nicer Path for display, if the location is inside the 'github_work_directory'.
        try:
            pretty_path = location.relative_to(hide_path_prefix.parent)
        except ValueError:
            pretty_path = location

        if isinstance(location, Directory):
            if directory_listing := "\n".join(tree(location, include_summary=False)):
                item.add_report_section("teardown", f"{name} {pretty_path!r} contents at", directory_listing)

        else:
            if captured := OutputFile(location):
                item.add_report_section("teardown", f"{name} file contents at", repr(captured))
