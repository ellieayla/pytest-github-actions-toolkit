from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import fields
from pathlib import Path
from typing import Literal
from uuid import uuid4

import pytest

from . import samples
from .env import Name
from .env.as_dataclass import GithubEnvironmentVariables, Metadata
from .git_checkout import CheckoutFixture, GitRepo, checkout_repository, sample_remote_repo
from .git_raw import write_raw_git_repo
from .mark import pytest_configure, pytest_runtest_makereport, register_print_output_content
from .output import OutputFile, numbered_file_contents
from .types import Directory


@pytest.fixture(autouse=True)
def clear_standard_github_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for f in fields(GithubEnvironmentVariables):
        monkeypatch.delenv(f.name, raising=False)


@pytest.fixture(autouse=True)
def github_work_directory(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """
    Provision a work directory, like /__w/ or /Users/runner/work/, but inside tmp_path.

    All other files and directories, if requested via another fixture, will be placed inside.
    """
    location = tmp_path_factory.mktemp("__w")
    return location


# some common files get pretty names relative to the work directory (created by the github_work_directory fixture)
pretty_paths_in_workspace: dict[str, str] = {
    Name.GITHUB_WORKSPACE: samples.OWNER_REPO,
    Name.RUNNER_TEMP: "_temp",
    Name.GITHUB_EVENT_PATH: "_temp/_github_workflow/event.json",
}


@pytest.fixture
def github_resource_paths(github_work_directory: Path) -> Mapping[Name, Path | Directory]:
    """
    Declare paths for all temporary resources normally available in a workflow,
    inside the existing 'github_work_directory'. Does not create the new paths.
    """
    allocated: dict[Name, Path | Directory] = {}

    for f in fields(GithubEnvironmentVariables):
        typ = f.metadata.get(Metadata.validate_as)
        if typ is Directory or typ == Directory | None:
            # allocate a new directory inside the worktree
            default = f"_temp/{f.name}"
            allocated[Name(f.name)] = Directory(github_work_directory / pretty_paths_in_workspace.get(f.name, default))

        elif typ is Path or typ == Path | None:
            # allocate a new file inside the worktree
            default = f"_temp/_runner_file_commands/{f.name.lower()}_{uuid4()!s}.txt"
            allocated[Name(f.name)] = github_work_directory / pretty_paths_in_workspace.get(f.name, default)

        # ignore the rest of the fields
    return allocated


@pytest.fixture
def create_github_resource_paths(github_resource_paths: Mapping[Name, Path | Directory], monkeypatch: pytest.MonkeyPatch) -> Mapping[Name, Path]:
    """Create files and directories inside a work directory. Return the paths as a Mapping of environment variable name to Path"""
    created: dict[Name, Path] = {}

    for name, location in github_resource_paths.items():
        match location:
            case Directory():
                # create a new directory inside the work directory.
                location.mkdir(exist_ok=True, parents=True)
                monkeypatch.setenv(name, str(location))
                created[name] = location

            case Path():
                # create a new file inside the work directory.
                location.parent.mkdir(exist_ok=True, parents=True)
                location.touch()
                monkeypatch.setenv(name, str(location))
                created[name] = location

    return created


@contextmanager
def monkeypatch_envs(monkeypatch: pytest.MonkeyPatch, envs: Mapping[Name, str]) -> Generator[Mapping[str, str]]:
    with monkeypatch.context():
        for name, value in envs.items():
            monkeypatch.setenv(name, value)
        yield dict(envs.items())


@pytest.fixture
def pull_request_triggered_workflow(
    create_github_resource_paths: Mapping[str, Path], monkeypatch: pytest.MonkeyPatch
) -> Generator[Mapping[str, str]]:
    with monkeypatch_envs(monkeypatch, samples.pull_request) as d:
        yield d


@pytest.fixture
def push_triggered_workflow(create_github_resource_paths: Mapping[str, Path], monkeypatch: pytest.MonkeyPatch) -> Generator[Mapping[str, str]]:
    with monkeypatch_envs(monkeypatch, samples.push) as d:
        yield d


class WorkflowTriggerFixture:
    """
    Apply sample workflow-trigger events to environment variables within a context.

    Factory class returned by the 'workflow_trigger' fixture.
    """

    _monkeypatch: pytest.MonkeyPatch

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._monkeypatch = monkeypatch

    @contextmanager
    def __call__(self, sample: Literal["push", "push_tag", "pull_request"]) -> Generator[Mapping[str, str]]:
        preset_envs = {
            "push": samples.push,
            "push_tag": samples.push_tag,
            "pull_request": samples.pull_request,
        }[sample]
        with self._monkeypatch.context() as context:
            with monkeypatch_envs(context, preset_envs) as d:
                yield d


@pytest.fixture
def workflow_trigger(create_github_resource_paths: Mapping[str, Path], monkeypatch: pytest.MonkeyPatch) -> WorkflowTriggerFixture:
    """
    Apply sample workflow-trigger events to environment variables within a context, providing
    more control than the 'pull_request_triggered_workflow' and 'push_triggered_workflow' fixtures.
    """
    return WorkflowTriggerFixture(monkeypatch)


@pytest.fixture
def github_workspace_directory(create_github_resource_paths: dict[Name, Path], monkeypatch: pytest.MonkeyPatch) -> Generator[Path]:
    location = create_github_resource_paths[Name.GITHUB_WORKSPACE]
    monkeypatch.chdir(location)
    yield location


@pytest.fixture
def github_output_file(create_github_resource_paths: Mapping[str, Path]) -> OutputFile:
    """Convenience fixture for reviewing writes made to the $GITHUB_OUTPUT file."""
    return OutputFile(create_github_resource_paths[Name.GITHUB_OUTPUT])


@pytest.fixture
def github_env_file(create_github_resource_paths: Mapping[str, Path]) -> OutputFile:
    """Convenience fixture for reviewing writes made to the $GITHUB_ENV file."""
    return OutputFile(create_github_resource_paths[Name.GITHUB_ENV])


__all__ = [
    "CheckoutFixture",
    "GitRepo",
    "checkout_repository",
    "sample_remote_repo",
    "write_raw_git_repo",
    "pytest_configure",
    "pytest_runtest_makereport",
    "register_print_output_content",
    "OutputFile",
    "numbered_file_contents",
    "Directory",
    "clear_standard_github_environment_variables",
]
