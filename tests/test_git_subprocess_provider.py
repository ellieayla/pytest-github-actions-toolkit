from pathlib import Path

import pytest

from pytest_github_actions_toolkit._git_subprocess_provider import GitSubprocessRepo
from pytest_github_actions_toolkit.action_checkout_fixture import CheckoutFixture


def test_remote_git_repo_deterministic(sample_remote_repo: Path) -> None:
    r = GitSubprocessRepo(sample_remote_repo)
    assert r.log1() == "d7c2169cd2af356a325633261afe5cc6237059a5"


def test_source_git_repository_can_be_cloned(sample_remote_repo: Path, tmp_path: Path) -> None:
    destination = tmp_path / "clone"

    repo = GitSubprocessRepo.clone(str(sample_remote_repo), root=destination)
    commit_msg = repo.git(["cat-file", "commit", "d7c2169cd2af356a325633261afe5cc6237059a5"])

    matcher = pytest.LineMatcher(commit_msg.splitlines())

    matcher.fnmatch_lines(["tree *", "author pytest <pytest@localhost> *", "committer pytest <pytest@localhost> *", "Initial commit"])


def test_checkout_fixture_writes_to_workspace_directory(
    github_workspace_directory: Path, sample_remote_repo: Path, checkout_repository: CheckoutFixture
) -> None:

    sha = checkout_repository(source=sample_remote_repo, commit="main")

    repo = GitSubprocessRepo(github_workspace_directory)
    assert repo.log1() == sha

    print(repo.git(["ls-tree", "HEAD"]))


def test_list_refs(tmp_path: Path, sample_remote_repo: Path) -> None:
    repo = GitSubprocessRepo(sample_remote_repo)
    assert repo.refs() == {"refs/heads/main": "d7c2169cd2af356a325633261afe5cc6237059a5"}
