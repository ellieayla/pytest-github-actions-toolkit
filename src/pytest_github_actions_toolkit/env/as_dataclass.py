import os
from collections.abc import Callable, Mapping
from dataclasses import _MISSING_TYPE, MISSING, Field, dataclass, field, fields, is_dataclass
from enum import StrEnum, auto
from pathlib import Path
from types import NoneType
from typing import Annotated, Any, Self

from ..types import Description, Directory, Example, OwnerRepo
from ..util import truthy_value

type _Constructor[T] = Callable[[str], T]


@dataclass
class ValidateAs[T]:
    """A callback which will construct the needed type."""

    callable: _Constructor[T]


class Metadata(StrEnum):
    example = auto()
    validate_as = auto()


@dataclass(frozen=True)
class GithubEnvironmentVariables:
    """
    Typed list of variables from https://docs.github.com/en/actions/reference/workflows-and-actions/variables
    Examples in annotations are all valid for that field, but should not be considered defaults.
    Whether a given variable is present depends on other context, like whether a workflow is triggered by a pull request.
    """

    CI: Annotated[
        bool | None,
        Description("You can use this variable to differentiate when tests are being run locally or by GitHub Actions."),
        Example("true"),
        ValidateAs(truthy_value),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "true",
            Metadata.validate_as: truthy_value,
        },
    )
    GITHUB_ACTION: Annotated[
        str | None,
        Description(
            "The name of the action currently running, or the `id` of a step. <br><br>GitHub removes special "
            "characters, and uses the name `__run` when the current step runs a script without an `id`. If you "
            "use the same script or action more than once in the same job, the name will include a suffix that "
            "consists of the sequence number preceded by an underscore. For example, the first script you run "
            "will have the name `__run`, and the second script will be named `__run_2`. Similarly, the second "
            "invocation of `actions/checkout` will be `actionscheckout2`."
        ),
        Example("__repo-owner_name-of-action-repo"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "__repo-owner_name-of-action-repo",
            Metadata.validate_as: str,
        },
    )
    GITHUB_ACTION_PATH: Annotated[
        Directory | None,
        Description(
            "The path where an action is located. This property is only supported in composite actions. You can "
            "use this path to change directories to where the action is located and access other files in that "
            "same repository."
        ),
        Example("/home/runner/work/_actions/repo-owner/name-of-action-repo/v1"),
        ValidateAs(Path),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "/home/runner/work/_actions/repo-owner/name-of-action-repo/v1",
            Metadata.validate_as: Path,
        },
    )
    GITHUB_ACTION_REPOSITORY: Annotated[
        str | None,
        Description("For a step executing an action, this is the owner and repository name of the action."),
        Example("actions/checkout"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "actions/checkout",
            Metadata.validate_as: str,
        },
    )
    GITHUB_ACTIONS: Annotated[
        bool | None,
        Description(
            "when GitHub Actions is running the workflow. You can use this variable to differentiate when tests are being run locally or by GitHub Actions."
        ),
        Example("true"),
        ValidateAs(truthy_value),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "true",
            Metadata.validate_as: truthy_value,
        },
    )
    GITHUB_ACTOR: Annotated[
        str | None,
        Description("The name of the person or app that initiated the workflow."),
        Example("octocat"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "octocat",
            Metadata.validate_as: str,
        },
    )
    GITHUB_ACTOR_ID: Annotated[
        str | None,
        Description(
            "The account ID of the person or app that triggered the initial workflow run. Note that this is different from the actor username."
        ),
        Example("1234567"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "1234567",
            Metadata.validate_as: str,
        },
    )
    GITHUB_API_URL: Annotated[
        str | None,
        Description("Returns the API URL."),
        Example("https://api.github.com"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "https://api.github.com",
            Metadata.validate_as: str,
        },
    )
    GITHUB_ARTIFACTS: Annotated[
        Path | None,
        Description(
            "The path on the runner to the file that declares workflow artifacts for the current step. Write one "
            "declaration per line to identify files or OCI digest references as workflow artifacts."
        ),
        Example("/home/runner/work/_actions//example.txt"),
        ValidateAs(Path),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "/home/runner/work/_actions//example.txt",
            Metadata.validate_as: Path,
        },
    )
    GITHUB_ARTIFACTS_LIST: Annotated[
        Path | None,
        Description(
            "The path on the runner to a read-only file that contains aggregated workflow artifact metadata for the current job as a JSON object."
        ),
        Example("/home/runner/work/_actions//example.txt"),
        ValidateAs(Path),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "/home/runner/work/_actions//example.txt",
            Metadata.validate_as: Path,
        },
    )
    GITHUB_BASE_REF: Annotated[
        str | None,
        Description(
            "The name of the base ref or target branch of the pull request in a workflow run. This is only set "
            "when the event that triggers a workflow run is either `pull_request` or `pull_request_target`."
        ),
        Example("main"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "main",
            Metadata.validate_as: str,
        },
    )
    GITHUB_ENV: Annotated[
        Path | None,
        Description(
            "The path on the runner to the file that sets variables from workflow commands. The path to this file"
            " is unique to the current step and changes for each step in a job."
        ),
        Example("/home/runner/work/_temp/_runner_file_commands/set_env_87406d6e-4979-4d42-98e1-3dab1f48b13a"),
        ValidateAs(Path),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "/home/runner/work/_temp/_runner_file_commands/set_env_87406d6e-4979-4d42-98e1-3dab1f48b13a",
            Metadata.validate_as: Path,
        },
    )
    GITHUB_EVENT_NAME: Annotated[
        str | None,
        Description("The name of the event that triggered the workflow."),
        Example("workflow_dispatch"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "workflow_dispatch",
            Metadata.validate_as: str,
        },
    )
    GITHUB_EVENT_PATH: Annotated[
        Path | None,
        Description("The path to the file on the runner that contains the full event webhook payload."),
        Example("/github/workflow/event.json"),
        ValidateAs(Path),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "/github/workflow/event.json",
            Metadata.validate_as: Path,
        },
    )
    GITHUB_GRAPHQL_URL: Annotated[
        str | None,
        Description("Returns the GraphQL API URL."),
        Example("https://api.github.com/graphql"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "https://api.github.com/graphql",
            Metadata.validate_as: str,
        },
    )
    GITHUB_HEAD_REF: Annotated[
        str | None,
        Description(
            "The head ref or source branch of the pull request in a workflow run. This property is only set when "
            "the event that triggers a workflow run is either `pull_request` or `pull_request_target`."
        ),
        Example("feature-branch-1"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "feature-branch-1",
            Metadata.validate_as: str,
        },
    )
    GITHUB_JOB: Annotated[
        str | None,
        Description("The job\\_id of the current job."),
        Example("greeting_job"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "greeting_job",
            Metadata.validate_as: str,
        },
    )
    GITHUB_OUTPUT: Annotated[
        Path | None,
        Description(
            "The path on the runner to the file that sets the current step's outputs from workflow commands. The "
            "path to this file is unique to the current step and changes for each step in a job."
        ),
        Example("/home/runner/work/_temp/_runner_file_commands/set_output_a50ef383-b063-46d9-9157-57953fc9f3f0"),
        ValidateAs(Path),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "/home/runner/work/_temp/_runner_file_commands/set_output_a50ef383-b063-46d9-9157-57953fc9f3f0",
            Metadata.validate_as: Path,
        },
    )
    GITHUB_PATH: Annotated[
        Path | None,
        Description(
            "The path on the runner to the file that sets system `PATH` variables from workflow commands. The "
            "path to this file is unique to the current step and changes for each step in a job."
        ),
        Example("/home/runner/work/_temp/_runner_file_commands/add_path_899b9445-ad4a-400c-aa89-249f18632cf5"),
        ValidateAs(Path),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "/home/runner/work/_temp/_runner_file_commands/add_path_899b9445-ad4a-400c-aa89-249f18632cf5",
            Metadata.validate_as: Path,
        },
    )
    GITHUB_REF: Annotated[
        str | None,
        Description(
            "The fully-formed ref of the branch or tag that triggered the workflow run. For workflows triggered "
            "by `push`, this is the branch or tag ref that was pushed. For workflows triggered by `pull_request` "
            "that were not merged, this is the pull request merge branch. If the pull request was merged, this is"
            " the branch it was merged into. For workflows triggered by `release`, this is the release tag "
            "created. For other triggers, this is the branch or tag ref that triggered the workflow run. This is "
            "only set if a branch or tag is available for the event type. The ref given is fully-formed, meaning "
            "that for branches the format is `refs/heads/<branch_name>`. For pull request events except "
            "`pull_request_target` that were not merged, it is `refs/pull/<pr_number>/merge`. "
            "`pull_request_target` events have the `ref` from the base branch. For tags it is "
            "`refs/tags/<tag_name>`."
        ),
        Example("refs/heads/feature-branch-1"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "refs/heads/feature-branch-1",
            Metadata.validate_as: str,
        },
    )
    GITHUB_REF_NAME: Annotated[
        str | None,
        Description(
            "The short ref name of the branch or tag that triggered the workflow run. This value matches the "
            "branch or tag name shown on GitHub. <br><br>For pull requests that were not merged, the format is "
            "`<pr_number>/merge`."
        ),
        Example("feature-branch-1"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "feature-branch-1",
            Metadata.validate_as: str,
        },
    )
    GITHUB_REF_PROTECTED: Annotated[
        bool | None,
        Description("`true` if branch protections or rulesets are configured for the ref that triggered the workflow run."),
        Example("true"),
        ValidateAs(truthy_value),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "true",
            Metadata.validate_as: truthy_value,
        },
    )
    GITHUB_REF_TYPE: Annotated[
        str | None,
        Description("The type of ref that triggered the workflow run. Valid values are `branch` or `tag`."),
        Example("branch"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "branch",
            Metadata.validate_as: str,
        },
    )
    GITHUB_REPOSITORY: Annotated[
        OwnerRepo | None,
        Description("The owner and repository name."),
        Example("octocat/Hello-World"),
        ValidateAs(OwnerRepo),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "octocat/Hello-World",
            Metadata.validate_as: OwnerRepo,
        },
    )
    GITHUB_REPOSITORY_ID: Annotated[
        str | None,
        Description("The ID of the repository. Note that this is different from the repository name."),
        Example("123456789"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "123456789",
            Metadata.validate_as: str,
        },
    )
    GITHUB_REPOSITORY_OWNER: Annotated[
        str | None,
        Description("The repository owner's name."),
        Example("octocat"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "octocat",
            Metadata.validate_as: str,
        },
    )
    GITHUB_REPOSITORY_OWNER_ID: Annotated[
        str | None,
        Description("The repository owner's account ID. Note that this is different from the owner's name."),
        Example("1234567"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "1234567",
            Metadata.validate_as: str,
        },
    )
    GITHUB_RETENTION_DAYS: Annotated[
        int | None,
        Description("The number of days that workflow run logs and artifacts are kept."),
        Example("90"),
        ValidateAs(int),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "90",
            Metadata.validate_as: int,
        },
    )
    GITHUB_RUN_ATTEMPT: Annotated[
        str | None,
        Description(
            "A unique number for each attempt of a particular workflow run in a repository. This number begins at"
            " 1 for the workflow run's first attempt, and increments with each re-run."
        ),
        Example("3"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "3",
            Metadata.validate_as: str,
        },
    )
    GITHUB_RUN_ID: Annotated[
        str | None,
        Description("A unique number for each workflow run within a repository. This number does not change if you re-run the workflow run."),
        Example("1658821493"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "1658821493",
            Metadata.validate_as: str,
        },
    )
    GITHUB_RUN_NUMBER: Annotated[
        str | None,
        Description(
            "A unique number for each run of a particular workflow in a repository. This number begins at 1 for "
            "the workflow's first run, and increments with each new run. This number does not change if you re-"
            "run the workflow run."
        ),
        Example("3"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "3",
            Metadata.validate_as: str,
        },
    )
    GITHUB_SERVER_URL: Annotated[
        str | None,
        Description("The URL of the GitHub server."),
        Example("https://github.com"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "https://github.com",
            Metadata.validate_as: str,
        },
    )
    GITHUB_SHA: Annotated[
        str | None,
        Description("The commit SHA that triggered the workflow. The value of this commit SHA depends on the event that triggered the workflow."),
        Example("ffac537e6cbbf934b08745a378932722df287a53"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "ffac537e6cbbf934b08745a378932722df287a53",
            Metadata.validate_as: str,
        },
    )
    GITHUB_STEP_SUMMARY: Annotated[
        Path | None,
        Description(
            "The path on the runner to the file that contains job summaries from workflow commands. The path to "
            "this file is unique to the current step and changes for each step in a job."
        ),
        Example("/home/runner/_layout/_work/_temp/_runner_file_commands/step_summary_1cb22d7f-5663-41a8-9ffc-13472605c76c"),
        ValidateAs(Path),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "/home/runner/_layout/_work/_temp/_runner_file_commands/step_summary_1cb22d7f-5663-41a8-9ffc-13472605c76c",
            Metadata.validate_as: Path,
        },
    )
    GITHUB_TRIGGERING_ACTOR: Annotated[
        str | None,
        Description(
            "The username of the user that initiated the workflow run. If the workflow run is a re-run, this "
            "value may differ from `github.actor`. Any workflow re-runs will use the privileges of "
            "`github.actor`, even if the actor initiating the re-run (`github.triggering_actor`) has different "
            "privileges."
        ),
        Example("octocat"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "octocat",
            Metadata.validate_as: str,
        },
    )
    GITHUB_WORKFLOW: Annotated[
        Directory | None,
        Description(
            "The name of the workflow. If the workflow file doesn't specify a `name`, the value of this variable "
            "is the full path of the workflow file in the repository."
        ),
        Example("My test workflow"),
        ValidateAs(Path),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "My test workflow",
            Metadata.validate_as: Path,
        },
    )
    GITHUB_WORKFLOW_REF: Annotated[
        Path | None,
        Description("The ref path to the workflow."),
        Example("octocat/hello-world/.github/workflows/my-workflow.yml@refs/heads/my_branch"),
        ValidateAs(Path),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "octocat/hello-world/.github/workflows/my-workflow.yml@refs/heads/my_branch",
            Metadata.validate_as: Path,
        },
    )
    GITHUB_WORKFLOW_SHA: Annotated[
        str | None,
        Description("The commit SHA for the workflow file."),
        Example("ffac537e6cbbf934b08745a378932722df287a53"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "ffac537e6cbbf934b08745a378932722df287a53",
            Metadata.validate_as: str,
        },
    )
    GITHUB_WORKSPACE: Annotated[
        Directory | None,
        Description(
            "The default working directory on the runner for steps, and the default location of your repository when using the `checkout` action."
        ),
        Example("/home/runner/work/my-repo-name/my-repo-name"),
        ValidateAs(Directory),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "/home/runner/work/my-repo-name/my-repo-name",
            Metadata.validate_as: Directory,
        },
    )
    RUNNER_ARCH: Annotated[
        str | None,
        Description("The architecture of the runner executing the job. Possible values are `X86`, `X64`, `ARM`, or `ARM64`."),
        Example("X86"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "X86",
            Metadata.validate_as: str,
        },
    )
    RUNNER_DEBUG: Annotated[
        str | None,
        Description(
            "This is set only if debug logging is enabled. It can be useful as an indicator to enable additional "
            "debugging or verbose logging in your own job steps."
        ),
        Example("1"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "1",
            Metadata.validate_as: str,
        },
    )
    RUNNER_ENVIRONMENT: Annotated[
        str | None,
        Description(
            "The environment of the runner executing the job. Possible values are: `github-hosted` for GitHub-"
            "hosted runners provided by GitHub, and `self-hosted` for self-hosted runners configured by the "
            "repository owner."
        ),
        Example("github-hosted"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "github-hosted",
            Metadata.validate_as: str,
        },
    )
    RUNNER_NAME: Annotated[
        str | None,
        Description(
            "The name of the runner executing the job. This name may not be unique in a workflow run as runners "
            "at the repository and organization levels could use the same name."
        ),
        Example("Hosted Agent"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "Hosted Agent",
            Metadata.validate_as: str,
        },
    )
    RUNNER_OS: Annotated[
        str | None,
        Description("The operating system of the runner executing the job. Possible values are `Linux`, `Windows`, or `macOS`."),
        Example("Windows"),
        ValidateAs(str),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "Windows",
            Metadata.validate_as: str,
        },
    )
    RUNNER_TEMP: Annotated[
        Directory | None,
        Description(
            "The path to a temporary directory on the runner. This directory is emptied at the beginning and end "
            "of each job. Note that files will not be removed if the runner's user account does not have "
            "permission to delete them."
        ),
        Example("D:\\a\\_temp"),
        ValidateAs(Directory),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "D:\\a\\_temp",
            Metadata.validate_as: Directory,
        },
    )
    RUNNER_TOOL_CACHE: Annotated[
        Directory | None,
        Description("The path to the directory containing preinstalled tools for GitHub-hosted runners."),
        Example("C:\\hostedtoolcache\\windows"),
        ValidateAs(Directory),
    ] = field(
        default=None,
        metadata={
            Metadata.example: "C:\\hostedtoolcache\\windows",
            Metadata.validate_as: Directory,
        },
    )

    @classmethod
    def load(cls, envs: Mapping[str, str] = os.environ) -> Self:
        """
        Load items from 'envs' Mapping into a new instance of a dataclass.

        For each field defined on the dataclass,
        - read raw string value out of mapping, defaulting to field's default.
        - inspect field metadata to determine constructor to call,
        - call type constructor to hydrate field value.

        Create a new dataclass instance with all fields populated.
        """
        if not is_dataclass(cls):
            raise TypeError(f"Must be a dataclass class, got {cls!r}")

        # For every field on the dataclass, read value out of the envs mapping by field name. All values are either strings or field defaults or MISSING.
        raw_values: Mapping[Field[str], str | _MISSING_TYPE | None] = {
            f: envs.get(f.name, str(f.default) if f.default not in (MISSING, None) else f.default) for f in fields(cls)
        }

        values_that_are_set: Mapping[Field[str], str] = {
            f: v
            for f, v in raw_values.items()
            if not isinstance(v, (_MISSING_TYPE, NoneType))  # NOTE: Checking the type of v instead of its value to make mypy happy
        }

        constructors: Mapping[Field[str], _Constructor[str]] = {f: f.metadata.get(Metadata.validate_as, f.type) for f in values_that_are_set}

        loaded_values = {f: constructors[f](v) for f, v in values_that_are_set.items()}

        # Splat dictionary of field names to values into the dataclass's constructor
        splat: Mapping[str, Any] = {f.name: v for f, v in loaded_values.items()}
        return cls(**splat)  # pyright: ignore[reportCallIssue, reportUnknownVariableType]

    @classmethod
    def examples(cls) -> dict[str, str | None]:
        return {f.name: f.metadata.get(Metadata.example) for f in fields(cls)}
