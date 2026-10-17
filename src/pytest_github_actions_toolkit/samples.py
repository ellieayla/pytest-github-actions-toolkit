"""Sample collections of environment variables in common configurations."""

from typing import Final

from .env.as_dataclass import GithubEnvironmentVariables

example_fields = {k: v for k, v in GithubEnvironmentVariables.examples().items() if v is not None}

OWNER_NAME: Final[str] = "octocat"
REPO_NAME: Final[str] = "repo"
OWNER_REPO: Final[str] = f"{OWNER_NAME}/{REPO_NAME}"

BRANCH_NAME: Final[str] = "feature-branch-1"
TAG_NAME: Final[str] = "v0.4"

PULL_REQUEST_NUMBER: Final[str] = "4"


push = {
    **example_fields,
    "GITHUB_ACTION": "__run",
    "GITHUB_EVENT_NAME": "push",
    "GITHUB_REF": f"refs/heads/{BRANCH_NAME}",
    "GITHUB_REF_NAME": BRANCH_NAME,
}

push_tag = {
    **push,
    "GITHUB_REF": f"refs/tags/{TAG_NAME}",
    "GITHUB_REF_NAME": TAG_NAME,
    "GITHUB_REF_TYPE": "tag",
}

pull_request = {
    **example_fields,
    "GITHUB_ACTION": "__run",
    "GITHUB_ACTIONS": "pull_request",
    "GITHUB_REF": f"refs/pull/{PULL_REQUEST_NUMBER}/merge",
    "GITHUB_REF_NAME": f"{PULL_REQUEST_NUMBER}/merge",
    "GITHUB_BASE_REF": "main",  # The name of the base ref or target branch of the pull request in a workflow run.
    "GITHUB_HEAD_REF": BRANCH_NAME,
}
