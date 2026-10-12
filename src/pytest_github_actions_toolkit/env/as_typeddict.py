import os
from collections.abc import Mapping
from pathlib import Path
from types import NoneType
from typing import Annotated, TypedDict, get_args, get_type_hints

from ..environment_variables import Description, Directory, Example, OwnerRepo
from ..util import truthy_value


class GithubEnvironmentVariables(TypedDict, total=False):
    """
    Typed list of variables from https://docs.github.com/en/actions/reference/workflows-and-actions/variables
    Examples in annotations are all valid for that field, but should not be considered defaults.
    Whether a given variable is present depends on other context, like whether a workflow is triggered by a pull request.
    """

    CI: Annotated[
        bool,
        Description("You can use this variable to differentiate when tests are being run locally or by GitHub Actions."),
        Example("true"),
    ]
    GITHUB_ACTION: Annotated[
        str,
        Description(
            "The name of the action currently running, or the `id` of a step. <br><br>GitHub removes special characters, and uses the name `__run` when the current step runs a script without an `id`. If you use the same script or action more than once in the same job, the name will include a suffix that consists of the sequence number preceded by an underscore. For example, the first script you run will have the name `__run`, and the second script will be named `__run_2`. Similarly, the second invocation of `actions/checkout` will be `actionscheckout2`."
        ),
        Example("__repo-owner_name-of-action-repo"),
    ]
    GITHUB_ACTION_PATH: Annotated[
        Path,
        Description(
            "The path where an action is located. This property is only supported in composite actions. You can use this path to change directories to where the action is located and access other files in that same repository."
        ),
        Example("/home/runner/work/_actions/repo-owner/name-of-action-repo/v1"),
    ]
    GITHUB_ACTION_REPOSITORY: Annotated[
        str,
        Description("For a step executing an action, this is the owner and repository name of the action."),
        Example("actions/checkout"),
    ]
    GITHUB_ACTIONS: Annotated[
        bool,
        Description(
            "when GitHub Actions is running the workflow. You can use this variable to differentiate when tests are being run locally or by GitHub Actions."
        ),
        Example("true"),
    ]
    GITHUB_ACTOR: Annotated[
        str,
        Description("The name of the person or app that initiated the workflow."),
        Example("octocat"),
    ]
    GITHUB_ACTOR_ID: Annotated[
        str,
        Description(
            "The account ID of the person or app that triggered the initial workflow run. Note that this is different from the actor username."
        ),
        Example("1234567"),
    ]
    GITHUB_API_URL: Annotated[
        str,
        Description("Returns the API URL."),
        Example("https://api.github.com"),
    ]
    GITHUB_ARTIFACTS: Annotated[
        Path,
        Description(
            "The path on the runner to the file that declares workflow artifacts for the current step. Write one declaration per line to identify files or OCI digest references as workflow artifacts."
        ),
        Example("/home/runner/work/_actions//example.txt"),
    ]
    GITHUB_ARTIFACTS_LIST: Annotated[
        Path,
        Description(
            "The path on the runner to a read-only file that contains aggregated workflow artifact metadata for the current job as a JSON object."
        ),
        Example("/home/runner/work/_actions//example.txt"),
    ]
    GITHUB_BASE_REF: Annotated[
        str,
        Description(
            "The name of the base ref or target branch of the pull request in a workflow run. This is only set when the event that triggers a workflow run is either `pull_request` or `pull_request_target`."
        ),
        Example("main"),
    ]
    GITHUB_ENV: Annotated[
        Path,
        Description(
            "The path on the runner to the file that sets variables from workflow commands. The path to this file is unique to the current step and changes for each step in a job."
        ),
        Example("/home/runner/work/_temp/_runner_file_commands/set_env_87406d6e-4979-4d42-98e1-3dab1f48b13a"),
    ]
    GITHUB_EVENT_NAME: Annotated[
        str,
        Description("The name of the event that triggered the workflow."),
        Example("workflow_dispatch"),
    ]
    GITHUB_EVENT_PATH: Annotated[
        Path,
        Description("The path to the file on the runner that contains the full event webhook payload."),
        Example("/github/workflow/event.json"),
    ]
    GITHUB_GRAPHQL_URL: Annotated[
        str,
        Description("Returns the GraphQL API URL."),
        Example("https://api.github.com/graphql"),
    ]
    GITHUB_HEAD_REF: Annotated[
        str,
        Description(
            "The head ref or source branch of the pull request in a workflow run. This property is only set when the event that triggers a workflow run is either `pull_request` or `pull_request_target`."
        ),
        Example("feature-branch-1"),
    ]
    GITHUB_JOB: Annotated[
        str,
        Description("The job\\_id of the current job."),
        Example("greeting_job"),
    ]
    GITHUB_OUTPUT: Annotated[
        Path,
        Description(
            "The path on the runner to the file that sets the current step's outputs from workflow commands. The path to this file is unique to the current step and changes for each step in a job."
        ),
        Example("/home/runner/work/_temp/_runner_file_commands/set_output_a50ef383-b063-46d9-9157-57953fc9f3f0"),
    ]
    GITHUB_PATH: Annotated[
        Path,
        Description(
            "The path on the runner to the file that sets system `PATH` variables from workflow commands. The path to this file is unique to the current step and changes for each step in a job."
        ),
        Example("/home/runner/work/_temp/_runner_file_commands/add_path_899b9445-ad4a-400c-aa89-249f18632cf5"),
    ]
    GITHUB_REF: Annotated[
        str,
        Description(
            "The fully-formed ref of the branch or tag that triggered the workflow run. For workflows triggered by `push`, this is the branch or tag ref that was pushed. For workflows triggered by `pull_request` that were not merged, this is the pull request merge branch. If the pull request was merged, this is the branch it was merged into. For workflows triggered by `release`, this is the release tag created. For other triggers, this is the branch or tag ref that triggered the workflow run. This is only set if a branch or tag is available for the event type. The ref given is fully-formed, meaning that for branches the format is `refs/heads/<branch_name>`. For pull request events except `pull_request_target` that were not merged, it is `refs/pull/<pr_number>/merge`. `pull_request_target` events have the `ref` from the base branch. For tags it is `refs/tags/<tag_name>`."
        ),
        Example("refs/heads/feature-branch-1"),
    ]
    GITHUB_REF_NAME: Annotated[
        str,
        Description(
            "The short ref name of the branch or tag that triggered the workflow run. This value matches the branch or tag name shown on GitHub. <br><br>For pull requests that were not merged, the format is `<pr_number>/merge`."
        ),
        Example("feature-branch-1"),
    ]
    GITHUB_REF_PROTECTED: Annotated[
        bool,
        Description("`true` if branch protections or rulesets are configured for the ref that triggered the workflow run."),
        Example("true"),
    ]
    GITHUB_REF_TYPE: Annotated[
        str,
        Description("The type of ref that triggered the workflow run. Valid values are `branch` or `tag`."),
        Example("branch"),
    ]
    GITHUB_REPOSITORY: Annotated[
        OwnerRepo,
        Description("The owner and repository name."),
        Example("octocat/Hello-World"),
    ]
    GITHUB_REPOSITORY_ID: Annotated[
        str,
        Description("The ID of the repository. Note that this is different from the repository name."),
        Example("123456789"),
    ]
    GITHUB_REPOSITORY_OWNER: Annotated[
        str,
        Description("The repository owner's name."),
        Example("octocat"),
    ]
    GITHUB_REPOSITORY_OWNER_ID: Annotated[
        str,
        Description("The repository owner's account ID. Note that this is different from the owner's name."),
        Example("1234567"),
    ]
    GITHUB_RETENTION_DAYS: Annotated[
        int,
        Description("The number of days that workflow run logs and artifacts are kept."),
        Example("90"),
    ]
    GITHUB_RUN_ATTEMPT: Annotated[
        str,
        Description(
            "A unique number for each attempt of a particular workflow run in a repository. This number begins at 1 for the workflow run's first attempt, and increments with each re-run."
        ),
        Example("3"),
    ]
    GITHUB_RUN_ID: Annotated[
        str,
        Description("A unique number for each workflow run within a repository. This number does not change if you re-run the workflow run."),
        Example("1658821493"),
    ]
    GITHUB_RUN_NUMBER: Annotated[
        str,
        Description(
            "A unique number for each run of a particular workflow in a repository. This number begins at 1 for the workflow's first run, and increments with each new run. This number does not change if you re-run the workflow run."
        ),
        Example("3"),
    ]
    GITHUB_SERVER_URL: Annotated[
        str,
        Description("The URL of the GitHub server."),
        Example("https://github.com"),
    ]
    GITHUB_SHA: Annotated[
        str,
        Description("The commit SHA that triggered the workflow. The value of this commit SHA depends on the event that triggered the workflow."),
        Example("ffac537e6cbbf934b08745a378932722df287a53"),
    ]
    GITHUB_STEP_SUMMARY: Annotated[
        Path,
        Description(
            "The path on the runner to the file that contains job summaries from workflow commands. The path to this file is unique to the current step and changes for each step in a job."
        ),
        Example("/home/runner/_layout/_work/_temp/_runner_file_commands/step_summary_1cb22d7f-5663-41a8-9ffc-13472605c76c"),
    ]
    GITHUB_TRIGGERING_ACTOR: Annotated[
        str,
        Description(
            "The username of the user that initiated the workflow run. If the workflow run is a re-run, this value may differ from `github.actor`. Any workflow re-runs will use the privileges of `github.actor`, even if the actor initiating the re-run (`github.triggering_actor`) has different privileges."
        ),
        Example("octocat"),
    ]
    GITHUB_WORKFLOW: Annotated[
        Path,
        Description(
            "The name of the workflow. If the workflow file doesn't specify a `name`, the value of this variable is the full path of the workflow file in the repository."
        ),
        Example("My test workflow"),
    ]
    GITHUB_WORKFLOW_REF: Annotated[
        Path,
        Description("The ref path to the workflow."),
        Example("octocat/hello-world/.github/workflows/my-workflow.yml@refs/heads/my_branch"),
    ]
    GITHUB_WORKFLOW_SHA: Annotated[
        str,
        Description("The commit SHA for the workflow file."),
        Example("ffac537e6cbbf934b08745a378932722df287a53"),
    ]
    GITHUB_WORKSPACE: Annotated[
        Directory,
        Description(
            "The default working directory on the runner for steps, and the default location of your repository when using the `checkout` action."
        ),
        Example("/home/runner/work/my-repo-name/my-repo-name"),
    ]
    RUNNER_ARCH: Annotated[
        str,
        Description("The architecture of the runner executing the job. Possible values are `X86`, `X64`, `ARM`, or `ARM64`."),
        Example("X86"),
    ]
    RUNNER_DEBUG: Annotated[
        str,
        Description(
            "This is set only if debug logging is enabled. It can be useful as an indicator to enable additional debugging or verbose logging in your own job steps."
        ),
        Example("1"),
    ]
    RUNNER_ENVIRONMENT: Annotated[
        str,
        Description(
            "The environment of the runner executing the job. Possible values are: `github-hosted` for GitHub-hosted runners provided by GitHub, and `self-hosted` for self-hosted runners configured by the repository owner."
        ),
        Example("github-hosted"),
    ]
    RUNNER_NAME: Annotated[
        str,
        Description(
            "The name of the runner executing the job. This name may not be unique in a workflow run as runners at the repository and organization levels could use the same name."
        ),
        Example("Hosted Agent"),
    ]
    RUNNER_OS: Annotated[
        str,
        Description("The operating system of the runner executing the job. Possible values are `Linux`, `Windows`, or `macOS`."),
        Example("Windows"),
    ]
    RUNNER_TEMP: Annotated[
        Path,
        Description(
            "The path to a temporary directory on the runner. This directory is emptied at the beginning and end of each job. Note that files will not be removed if the runner's user account does not have permission to delete them."
        ),
        Example("D:\\a\\_temp"),
    ]
    RUNNER_TOOL_CACHE: Annotated[
        Path,
        Description("The path to the directory containing preinstalled tools for GitHub-hosted runners."),
        Example("C:\\hostedtoolcache\\windows"),
    ]


def load[T](cls: type[T] = GithubEnvironmentVariables, envs: Mapping[str, str] = os.environ) -> T:
    """Create a cls=GithubEnvironmentVariables using the contents of 'envs', using defined types."""

    field_names_to_types = get_type_hints(cls)
    annotations = get_type_hints(cls, include_extras=True)
    if not annotations:
        raise TypeError(f"Must be a TypedDict class with annotations, got {cls!r}")

    # Read values out of the envs mapping
    raw_values = {name: envs.get(name, None) for name in field_names_to_types}

    # All the raw values run through type constructors
    loaded_values = {
        name: (
            truthy_value(v)
            if field_names_to_types[name] is bool
            else field_names_to_types[name](v)
            if isinstance(field_names_to_types[name], type)
            else v
        )
        for name, v in raw_values.items()
        if not isinstance(v, NoneType)
    }

    # Splat dictionary of field names to values into TypedDict's constructor
    return cls(**loaded_values)


def names(cls: type = GithubEnvironmentVariables) -> frozenset[str]:
    """Names of all environment variables normally available in a Github Actions workflow."""
    field_names_to_types = get_type_hints(cls)
    return frozenset(field_names_to_types.keys())


def examples(cls: type[GithubEnvironmentVariables] = GithubEnvironmentVariables) -> dict[str, str]:
    """Extract the first Example annotation for each field in a TypedDict."""
    annotations = get_type_hints(cls, include_extras=True)

    if not annotations:
        raise TypeError(f"Must be a TypedDict class with annotations, got {cls!r}")

    return {field_name: [str(ex) for ex in get_args(annotation) if isinstance(ex, Example)][0] for field_name, annotation in annotations.items()}
