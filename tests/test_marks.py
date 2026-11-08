from dataclasses import dataclass

import pytest

from pytest_github_actions_toolkit.env import Name


@dataclass(kw_only=True)
class Expectations:
    step_summary: bool
    warning: bool
    directory_tree: bool


@pytest.mark.parametrize(
    ["expect", "testname"],
    [
        (Expectations(step_summary=True, warning=False, directory_tree=False), "test_mark_one_file"),
        (Expectations(step_summary=False, warning=False, directory_tree=True), "test_mark_one_directory"),
        (Expectations(step_summary=True, warning=False, directory_tree=True), "test_mark_all_files"),
        (Expectations(step_summary=False, warning=True, directory_tree=False), "test_mark_without_citing_resource_paths"),
        (Expectations(step_summary=False, warning=False, directory_tree=False), "test_mark_nothing"),
    ],
)
@pytest.mark.filterwarnings("default")  # one of these cases will emit warnings, isolate from parent pyproject.toml
def test_mark_causes_reports(testname: str, expect: Expectations, pytester: pytest.Pytester) -> None:

    pytester.copy_example("test_mark_print_output_content.py")

    result = pytester.runpytest("-k", testname)

    # Each test will have failed, and maybe warned too
    result.assert_outcomes(failed=1, warnings=1 if expect.warning else 0)

    # But with different report sections
    captured_step_summary_pattern = f"*-- Captured*{Name.GITHUB_STEP_SUMMARY}*contents*teardown*"
    if expect.step_summary:
        result.stdout.fnmatch_lines(
            [
                captured_step_summary_pattern,
                "* 1 | words",
            ]
        )
    else:
        result.stdout.no_fnmatch_line(captured_step_summary_pattern)

    warning_mark_without_fixture_pattern = (
        "*Warning: Test marked with @pytest.mark.print_output_content doesn't use github_resource_paths. Remove the mark or add the fixture."
    )
    if expect.warning:
        result.stdout.fnmatch_lines(
            [
                warning_mark_without_fixture_pattern,
            ]
        )
    else:
        result.stdout.no_fnmatch_line(warning_mark_without_fixture_pattern)

    captured_runner_temp_pattern = "*Captured RUNNER_TEMP * contents at teardown*"
    if expect.directory_tree:
        result.stdout.fnmatch_lines(
            [
                captured_runner_temp_pattern,
                "└── *",
            ]
        )
    else:
        result.stdout.no_fnmatch_line(
            captured_runner_temp_pattern,
        )
