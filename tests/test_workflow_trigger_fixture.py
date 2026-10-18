import os

import pytest

from pytest_github_actions_toolkit.env import Name
from pytest_github_actions_toolkit.plugin import WorkflowTriggerFixture
from pytest_github_actions_toolkit.samples import example_fields


def test_workflow_trigger_fixture(monkeypatch: pytest.MonkeyPatch, workflow_trigger: WorkflowTriggerFixture) -> None:
    """Use the 'workflow_trigger' fixture as a context manager to alter the set environment variables temporarily."""
    assert os.environ.get(Name.CI) is None

    with workflow_trigger("pull_request") as context:
        assert context[Name.CI] == example_fields[Name.CI]
        assert os.environ.get(Name.CI) == example_fields[Name.CI]

    assert os.environ.get(Name.CI) is None
