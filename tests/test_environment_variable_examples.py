from dataclasses import fields, is_dataclass

from pytest_github_actions_toolkit.env import as_dataclass


def test_all_dataclass_examples_are_valid() -> None:
    raw_envs = as_dataclass.GithubEnvironmentVariables.examples()
    assert raw_envs["CI"] == "true"

    non_none = {f: v for f, v in raw_envs.items() if v is not None}

    o = as_dataclass.GithubEnvironmentVariables.load(non_none)
    assert o.CI is True


def test_empty_mapping_produces_dataclass_of_all_defaults() -> None:
    raw_envs: dict[str, str] = {}
    o = as_dataclass.GithubEnvironmentVariables.load(raw_envs)

    assert o.CI is None

    assert is_dataclass(as_dataclass.GithubEnvironmentVariables)
    for f in fields(as_dataclass.GithubEnvironmentVariables):
        assert hasattr(o, f.name)
        assert getattr(o, f.name) == f.default


def test_construct() -> None:
    raw_envs: dict[str, str] = {"CI": "true"}
    o = as_dataclass.GithubEnvironmentVariables.load(raw_envs)

    assert o.CI is True
