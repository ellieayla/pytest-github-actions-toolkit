from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import fields
from pathlib import Path
from typing import Literal
from uuid import uuid4

import pytest

from . import samples
from .env import GithubEnvironmentVariables, Metadata, Name
from .output import OutputFile, numbered_file_contents
from .types import Directory


@pytest.fixture(autouse=True)
def _clear_standard_github_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Always remove known github environment variables from os.environ before every test.

    Values may be populated in by other fixtures.
    """
    for f in fields(GithubEnvironmentVariables):
        monkeypatch.delenv(f.name, raising=False)


@pytest.fixture
def github_work_directory(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """
    Provision a work directory, like /__w/ or /Users/runner/work/, but inside tmp_path.

    All other files and directories, if requested via another fixture, will be placed inside.

    Not declared autouse=True, but a transitive dependency of many other fixtures.
    """
    location = tmp_path_factory.mktemp("__w")
    return location


# Some common files (declared by the 'allocated_github_resource_paths' fixture) get pretty names
# relative to the work directory (which is itself created by the 'github_work_directory' fixture).
_pretty_paths_in_work_directory: dict[str, str] = {
    Name.GITHUB_WORKSPACE: samples.OWNER_REPO,
    Name.RUNNER_TEMP: "_temp",
    Name.GITHUB_EVENT_PATH: "_temp/_github_workflow/event.json",
}


@pytest.fixture
def allocated_github_resource_paths(github_work_directory: Path) -> Mapping[Name, Path | Directory]:
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
            allocated[Name(f.name)] = Directory(github_work_directory / _pretty_paths_in_work_directory.get(f.name, default))

        elif typ is Path or typ == Path | None:
            # allocate a new file inside the worktree
            default = f"_temp/_runner_file_commands/{f.name.lower()}_{uuid4()!s}.txt"
            allocated[Name(f.name)] = github_work_directory / _pretty_paths_in_work_directory.get(f.name, default)

        # ignore the rest of the fields
    return allocated


@pytest.fixture
def github_resource_paths(allocated_github_resource_paths: Mapping[Name, Path | Directory], monkeypatch: pytest.MonkeyPatch) -> Mapping[Name, Path]:
    """
    Create files and directories inside a work directory.

    Many github environment variables cite ephemeral paths on disk,
    like a working directory or a step summary file.

    This fixture creates the directory or file on disk,
    using the locations previously allocated,
    and stores produced paths in monkeypatched environment variables.

    Returns a Mapping of environment variable name to Path.

    Eg: {"GITHUB_STEP_SUMMARY": Path("__w/_temp/_runner_file_commands/github_step_summary_123456.txt")}
    """
    created: dict[Name, Path] = {}

    for name, location in allocated_github_resource_paths.items():
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
def pull_request_triggered_workflow(github_resource_paths: Mapping[str, Path], monkeypatch: pytest.MonkeyPatch) -> Generator[Mapping[str, str]]:
    with monkeypatch_envs(monkeypatch, samples.pull_request) as d:
        yield d


@pytest.fixture
def push_triggered_workflow(github_resource_paths: Mapping[str, Path], monkeypatch: pytest.MonkeyPatch) -> Generator[Mapping[str, str]]:
    with monkeypatch_envs(monkeypatch, samples.push) as d:
        yield d


class WorkflowTriggerFixture:
    """
    Apply sample workflow-trigger events to environment variables within a context.

    Factory class returned by the 'workflow_trigger' fixture. Call with a sample type to provision.

    TODO: Provision matching event.json.
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
def workflow_trigger(github_resource_paths: Mapping[str, Path], monkeypatch: pytest.MonkeyPatch) -> WorkflowTriggerFixture:
    """
    Apply sample workflow-trigger events to environment variables within a context, providing
    more control than the 'pull_request_triggered_workflow' and 'push_triggered_workflow' fixtures.
    """
    return WorkflowTriggerFixture(monkeypatch)


@pytest.fixture
def github_workspace_directory(github_resource_paths: dict[Name, Path], monkeypatch: pytest.MonkeyPatch) -> Generator[Path]:
    location = github_resource_paths[Name.GITHUB_WORKSPACE]
    monkeypatch.chdir(location)
    yield location


@pytest.fixture
def github_output_file(github_resource_paths: Mapping[str, Path]) -> OutputFile:
    """Convenience fixture for reviewing writes made to the $GITHUB_OUTPUT file."""
    return OutputFile(github_resource_paths[Name.GITHUB_OUTPUT])


@pytest.fixture
def github_env_file(github_resource_paths: Mapping[str, Path]) -> OutputFile:
    """Convenience fixture for reviewing writes made to the $GITHUB_ENV file."""
    return OutputFile(github_resource_paths[Name.GITHUB_ENV])


__all__ = [
    "OutputFile",
    "numbered_file_contents",
    "Directory",
]
