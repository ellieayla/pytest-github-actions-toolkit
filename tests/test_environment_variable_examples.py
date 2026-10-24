from dataclasses import fields, is_dataclass

from pytest_github_actions_toolkit import env


def test_all_dataclass_examples_are_valid() -> None:
    raw_envs = env.GithubEnvironmentVariables.examples()
    assert raw_envs["CI"] == "true"

    non_none = {f: v for f, v in raw_envs.items() if v is not None}

    o = env.GithubEnvironmentVariables.load(non_none)
    assert o.CI is True


def test_empty_mapping_produces_dataclass_of_all_defaults() -> None:
    raw_envs: dict[str, str] = {}
    o = env.GithubEnvironmentVariables.load(raw_envs)

    assert o.CI is None

    assert is_dataclass(env.GithubEnvironmentVariables)
    for f in fields(env.GithubEnvironmentVariables):
        assert hasattr(o, f.name)
        assert getattr(o, f.name) == f.default


def test_construct() -> None:
    raw_envs: dict[str, str] = {"CI": "true"}
    o = env.GithubEnvironmentVariables.load(raw_envs)

    assert o.CI is True
