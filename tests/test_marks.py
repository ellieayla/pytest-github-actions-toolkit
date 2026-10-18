from collections.abc import Mapping
from pathlib import Path

import pytest

from pytest_github_actions_toolkit.env import Name


def test_mark_print_output_content(pytester: pytest.Pytester, create_github_resource_paths: Mapping[Name, Path]) -> None:
    pytester.copy_example("test_mark_print_output_content.py")
    result = pytester.runpytest("-k", "test_mark_one_file", "-vvv")

    result.stdout.fnmatch_lines(
        [
            f"*Captured*/_temp/_runner_file_commands/{Name.GITHUB_STEP_SUMMARY.lower()}*contents*teardown*",
            "* 1 | words",
        ]
    )
    result.assert_outcomes(failed=1)
