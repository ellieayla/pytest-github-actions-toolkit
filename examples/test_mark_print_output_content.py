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
def test_mark_one_file(create_github_resource_paths: Mapping[Name, Path]):
    """A intentionally-failing test which demonstrates mark citing one output."""
    create_github_resource_paths[Name.GITHUB_STEP_SUMMARY].write_text("words")
    assert 0


@pytest.mark.print_output_content
def test_mark_all_files(create_github_resource_paths: Mapping[Name, Path]):
    """A intentionally-failing test which demonstrates mark citing no outputs."""
    create_github_resource_paths[Name.GITHUB_STEP_SUMMARY].write_text("words")
    assert 0
