"""
Marks provided by plugin.

 * @pytest.mark.print_output_content(Name.*)
    At conclusion of a test, attach every defined output file's content as a report section.
    Accepts zero or more parameters with Name of environment variable to include.
    Default is equivilant to specifying all environment variables of type Path.
"""

from collections.abc import Mapping
from pathlib import Path

import pytest

from pytest_github_actions_toolkit.env import Name


@pytest.mark.print_output_content(Name.GITHUB_STEP_SUMMARY)
def test_mark_one_file(github_resource_paths: Mapping[Name, Path]):
    """A intentionally-failing test which demonstrates mark citing one output."""
    github_resource_paths[Name.GITHUB_STEP_SUMMARY].write_text("words")
    assert 0


@pytest.mark.print_output_content
def test_mark_one_directory(github_resource_paths: Mapping[Name, Path]):
    """A intentionally-failing test which demonstrates mark citing no outputs."""
    (github_resource_paths[Name.GITHUB_WORKSPACE] / "arbitrary").write_text("words")
    assert 0


@pytest.mark.print_output_content
def test_mark_all_files(github_resource_paths: Mapping[Name, Path]):
    """A intentionally-failing test which demonstrates mark citing no outputs."""
    github_resource_paths[Name.GITHUB_STEP_SUMMARY].write_text("words")
    assert 0


@pytest.mark.print_output_content
def test_mark_without_citing_resource_paths():
    """A intentionally-failing test which demonstrates a mark without the github_resource_paths fixture."""
    assert 0


def test_mark_nothing(github_resource_paths: Mapping[Name, Path]):
    """A intentionally-failing test which demonstrates no mark."""
    github_resource_paths[Name.GITHUB_STEP_SUMMARY].write_text("words")
    assert 0
