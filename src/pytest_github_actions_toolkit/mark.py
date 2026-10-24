import warnings
from collections.abc import Generator, Mapping
from pathlib import Path
from typing import cast

import pytest
from pluggy import Result

from .env import Name
from .output import OutputFile, numbered_file_contents
from .tree import tree
from .types import Directory

_PRINT_OUTPUT_CONTENT_MARKER_NAME = "print_output_content"
_CREATED_WORKFLOW_ENVIRONMENT_PATHS_FIXTURE_NAME = "create_github_resource_paths"


@pytest.hookimpl()
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", f"{_PRINT_OUTPUT_CONTENT_MARKER_NAME}(envvar): Attach a report with the given file contents.")


def print_output_content_finalizer(node: pytest.Item, output_file: OutputFile) -> None:
    node.add_report_section("teardown", f"{output_file.path} contents at", output_file.read_text())


@pytest.fixture(autouse=True, scope="function")
def register_print_output_content(
    github_work_directory: Path, github_resource_paths: Mapping[Name, Path | Directory], request: pytest.FixtureRequest
) -> Generator[None]:
    for_files: list[Name] = []

    node: pytest.Function = cast(pytest.Function, getattr(request, "node"))  # note matches scope on this fixture
    mark: pytest.Mark | None = node.get_closest_marker("print_output_content")

    # The test function is marked.
    if mark:
        if mark.args:
            for_files = [Name(v) for v in mark.args]
        else:
            for_files = [Name(k) for k, v in github_resource_paths.items() if not isinstance(v, Directory)]

        print(f"{node=} registered to print content of output {for_files=}")

        for arg in for_files:
            if arg not in github_resource_paths:
                pytest.fail(f"Unknown output file {arg!r} ({type(arg)=})")

    yield

    for arg in for_files:
        output_file = OutputFile(github_resource_paths[arg])
        relative_location = output_file.path.relative_to(github_work_directory.parent)
        node.add_report_section(
            "teardown", f"{str(relative_location)!r} contents at placeholder", "\n".join(numbered_file_contents(output_file.read_text()))
        )


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Function, call: pytest.CallInfo[None]) -> Generator[None, Result[pytest.TestReport]]:
    """Communicate content of output files / directories to the failure report for 'print_output_content' marked tests."""
    outcome: Result[pytest.TestReport] = yield

    report: pytest.TestReport = outcome.get_result()
    if report.when != "call" or report.passed:
        return
    mark: None | pytest.Mark = item.get_closest_marker(_PRINT_OUTPUT_CONTENT_MARKER_NAME)
    if mark is None:
        return
    funcargs: dict[str, object] | None = getattr(item, "funcargs", None)
    if funcargs is None:
        return  # doesn't make sense

    workflow_paths = cast(Mapping[Name, Directory | Path], funcargs.get(_CREATED_WORKFLOW_ENVIRONMENT_PATHS_FIXTURE_NAME, {}))
    if not workflow_paths:
        warnings.warn(
            f"Test marked with @pytest.mark.{_PRINT_OUTPUT_CONTENT_MARKER_NAME} doesn't use {_CREATED_WORKFLOW_ENVIRONMENT_PATHS_FIXTURE_NAME}. Remove the mark or add the fixture."
        )
        return

    hide_path_prefix: Path = cast(Path, funcargs.get("github_work_directory", Path("/")))

    # Test is marked, uses the fixture, has paths generated, and finished running.

    # What paths should be reported?
    if mark.args:
        requested: Mapping[Name, Directory | Path] = {Name(a): workflow_paths[a] for a in mark.args}
    else:
        requested = workflow_paths

    # Add a pytest report section for each output Path
    for name, location in requested.items():
        try:
            pretty_path = location.relative_to(hide_path_prefix.parent)
        except ValueError:
            pretty_path = location

        if isinstance(location, Directory):
            if directory_listing := "\n".join(tree(location, include_summary=False)):
                report.sections.append((f"Content of directory ${name} = {pretty_path!r}", directory_listing))

        else:
            if captured := OutputFile(location):
                report.sections.append(
                    (f"Content of {name}", repr(captured)),
                )
