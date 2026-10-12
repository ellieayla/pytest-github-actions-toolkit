from pathlib import Path

from pytest_github_actions_toolkit.checkout import GitRepo
from pytest_github_actions_toolkit.plugin import CheckoutFixture
from pytest_github_actions_toolkit.raw_git import write_raw_git_repo_fixture


def test_remote_git_repo_deterministic(sample_remote_repo: GitRepo) -> None:
    assert sample_remote_repo.log1() == "d7c2169cd2af356a325633261afe5cc6237059a5"


def test_source_git_repository_can_be_cloned(sample_remote_repo: GitRepo, tmp_path: Path) -> None:
    destination = tmp_path / "clone"

    GitRepo.clone(str(sample_remote_repo.root), root=destination)


def test_checkout_fixture_writes_to_workspace_directory(
    workspace_directory: Path, sample_remote_repo: GitRepo, checkout_repository: CheckoutFixture
) -> None:
    sha = checkout_repository(source=sample_remote_repo.root, commit="main")

    repo = GitRepo(workspace_directory)
    assert repo.log1() == sha

    print(sample_remote_repo.git(["ls-tree", "HEAD"]))


def test_generate_repo(tmp_path: Path, sample_remote_repo: GitRepo) -> None:
    simple = tmp_path / "simple"
    write_raw_git_repo_fixture(simple)

    repo = GitRepo.clone(str(simple), tmp_path / "clone")
    repo.git(["cat-file", "commit", "d7c2169cd2af356a325633261afe5cc6237059a5"])
    repo.git(["gc"])
