from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, get_type_hints
from uuid import uuid4

import pytest

from . import samples
from .checkout import CheckoutFixture, GitRepo
from .env.as_typeddict import GithubEnvironmentVariables, names
from .raw_git import write_raw_git_repo_fixture
from .types import Directory


@pytest.fixture(autouse=True)
def clear_standard_github_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in names(GithubEnvironmentVariables):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def github_work_directory(tmp_path: Path) -> Path:
    """
    Provision a work directory, like /__w/ or /Users/runner/work/, but inside tmp_path.

    If requested, all other generated files and directories will be placed inside.
    """
    location = tmp_path / "__w"
    location.mkdir()
    return location


EXAMPLE_REPO_OWNER_NAME: Final[str] = "octocat"
EXAMPLE_REPO_NAME: Final[str] = "repo"


# some common files get pretty names relative to the work directory (created by the github_work_directory fixture)
pretty_paths_in_workspace: dict[str, str] = {
    "GITHUB_WORKSPACE": f"{EXAMPLE_REPO_OWNER_NAME}/{EXAMPLE_REPO_NAME}",
    "RUNNER_WORKSPACE": EXAMPLE_REPO_OWNER_NAME,
    "GITHUB_EVENT_PATH": "_temp/_github_workflow/event.json",
}


@pytest.fixture
def workflow_paths(github_work_directory: Path) -> Mapping[str, Path | Directory]:
    """Declare paths for all temporary resources normally available in a workflow. Does not create the paths."""
    allocated: dict[str, Path | Directory] = {}

    fields = get_type_hints(GithubEnvironmentVariables)
    for name, typ in fields.items():
        if typ is Directory:
            default = f"_temp/{name}"
            allocated[name] = Directory(github_work_directory / pretty_paths_in_workspace.get(name, default))

        elif typ is Path:
            # create a new file inside the worktree
            default = f"_temp/_runner_file_commands/{name.lower()}_{uuid4()!s}.txt"
            allocated[name] = github_work_directory / pretty_paths_in_workspace.get(name, default)

    return allocated


@pytest.fixture
def created_workflow_environment_paths(
    github_work_directory: Path, workflow_paths: Mapping[str, Path | Directory], monkeypatch: pytest.MonkeyPatch
) -> Mapping[str, Path]:
    """Create files and directories inside a work directory. Return the paths as a Mapping of environment variable name to Path"""
    created: dict[str, Path] = {}

    for name, location in workflow_paths.items():
        match location:
            case Directory():
                # create a new directory inside the work directory.
                location.mkdir(parents=True)
                monkeypatch.setenv(name, str(location))
                created[name] = location

            case Path():
                # create a new file inside the work directory.
                location.parent.mkdir(exist_ok=True, parents=True)
                location.touch()
                monkeypatch.setenv(name, str(location))
                created[name] = location

    return created


def monkeypatch_envs(monkeypatch: pytest.MonkeyPatch, envs: Mapping[str, str]) -> None:
    for name, value in envs.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def pull_request_workflow(github_work_directory: Path, monkeypatch: pytest.MonkeyPatch) -> Mapping[str, str]:
    monkeypatch_envs(monkeypatch, samples.pull_request)
    return samples.pull_request


@pytest.fixture
def push_triggered_workflow(github_work_directory: Path, monkeypatch: pytest.MonkeyPatch) -> Mapping[str, str]:
    monkeypatch_envs(monkeypatch, samples.push)
    return samples.push


@pytest.fixture
def workspace_directory(created_workflow_environment_paths: dict[str, Path]) -> Path:
    return created_workflow_environment_paths["GITHUB_WORKSPACE"]


@pytest.fixture
def checkout_repository(workspace_directory: Path) -> CheckoutFixture:
    return CheckoutFixture(workspace_directory)


@pytest.fixture
def sample_remote_repo(tmp_path: Path, tmp_path_factory: pytest.TempPathFactory) -> GitRepo:
    """A git repository in a local temp directory which can be cloned and pushed to.
    Contains one commit (probably d7c2169cd2af356a325633261afe5cc6237059a5)."""
    bare_repo = tmp_path / "__remote_repo"

    write_raw_git_repo_fixture(bare_repo)

    repo = GitRepo(bare_repo)
    return repo

    bare_repo_worktree = tmp_path / "__remote_repo_worktree"

    with repo.worktree("main", bare_repo_worktree) as worktree:
        readme = bare_repo_worktree / "README.md"
        assert not readme.exists()

        readme.write_text("Example remote repo")

        worktree.config["user.name"] = "pytest"
        worktree.config["user.email"] = "pytest@localhost"
        worktree.add(["README.md"])
        PAST = datetime(1990, 1, 1, 0, 0, 0, 0, UTC)
        worktree.commit("Initial commit", date=PAST, commit_date=PAST)

    return repo
