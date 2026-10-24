from dataclasses import fields
from pathlib import Path

from pytest_github_actions_toolkit.env import GithubEnvironmentVariables, Name


def test_dataclass_and_enum_match() -> None:
    """The enum of environment variable names and the dataclass for loading them have the same field names defined."""
    fields_in_dataclass = [f.name for f in fields(GithubEnvironmentVariables)]
    assert list(Name) == fields_in_dataclass


def test_default_cwd_is_workspace_dir(github_workspace_directory: Path) -> None:
    assert Path.cwd() == github_workspace_directory
