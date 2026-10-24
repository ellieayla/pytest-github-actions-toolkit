"""Sample collections of environment variables in common configurations."""

from typing import Final

from .env import GithubEnvironmentVariables, Name

example_fields = {Name(k): v for k, v in GithubEnvironmentVariables.examples().items() if v is not None}

example_fields[Name.CI] = "false"

OWNER_NAME: Final[str] = "octocat"
REPO_NAME: Final[str] = "repo"
OWNER_REPO: Final[str] = f"{OWNER_NAME}/{REPO_NAME}"

BRANCH_NAME: Final[str] = "feature-branch-1"
TAG_NAME: Final[str] = "v0.4"

PULL_REQUEST_NUMBER: Final[str] = "4"


push = {
    **example_fields,
    Name.GITHUB_EVENT_NAME: "push",
    Name.GITHUB_REF: f"refs/heads/{BRANCH_NAME}",
    Name.GITHUB_REF_NAME: BRANCH_NAME,
}

push_tag = {
    **push,
    Name.GITHUB_REF_TYPE: "tag",
    Name.GITHUB_REF: f"refs/tags/{TAG_NAME}",
    Name.GITHUB_REF_NAME: TAG_NAME,
}

pull_request = {
    **example_fields,
    Name.GITHUB_EVENT_NAME: "pull_request",
    Name.GITHUB_REF: f"refs/pull/{PULL_REQUEST_NUMBER}/merge",
    Name.GITHUB_REF_NAME: f"{PULL_REQUEST_NUMBER}/merge",
    Name.GITHUB_BASE_REF: "main",  # The name of the base ref or target branch of the pull request in a workflow run.
    Name.GITHUB_HEAD_REF: BRANCH_NAME,
}
