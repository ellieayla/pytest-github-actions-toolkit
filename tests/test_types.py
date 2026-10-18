import pytest

from pytest_github_actions_toolkit.types import Actor, Description, OwnerRepo, OwnerRepoUnparsableError


def test_actor() -> None:
    a = Actor("")
    assert isinstance(a, str)


def test_owner_repo() -> None:
    a = OwnerRepo("foo/bar")
    assert a.owner == "foo"
    assert a.repo == "bar"

    with pytest.raises(OwnerRepoUnparsableError):
        OwnerRepo(None)  # type: ignore

    with pytest.raises(OwnerRepoUnparsableError):
        OwnerRepo("slug")

    with pytest.raises(OwnerRepoUnparsableError):
        OwnerRepo("slug/with/too/many/slashes")


def test_description() -> None:
    d = Description("dddd")
    assert d.description == "dddd"

    assert "dddd" in repr(d)
