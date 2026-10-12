from dataclasses import fields, is_dataclass

from pytest_github_actions_toolkit.env import as_dataclass, as_typeddict


def test_basic_constructor_works() -> None:
    as_typeddict.GithubEnvironmentVariables()


def test_load_empty_mapping() -> None:
    as_typeddict.load(as_typeddict.GithubEnvironmentVariables, {})


def test_all_examples_are_valid() -> None:

    raw_envs = as_typeddict.examples(as_typeddict.GithubEnvironmentVariables)

    assert raw_envs["CI"] == "true"

    o = as_typeddict.load(as_typeddict.GithubEnvironmentVariables, raw_envs)

    # appears with typed value
    assert "CI" in o
    assert o["CI"] is True


def test_all_dataclass_examples_are_valid() -> None:
    raw_envs = as_dataclass.examples(as_dataclass.GithubEnvironmentVariables)
    assert raw_envs["CI"] == "true"

    o = as_dataclass.load(as_dataclass.GithubEnvironmentVariables, raw_envs)
    assert o.CI is True


def test_empty_mapping_produces_dataclass_of_all_defaults() -> None:
    raw_envs: dict[str, str] = {}
    o = as_dataclass.load(as_dataclass.GithubEnvironmentVariables, raw_envs)

    assert is_dataclass(as_dataclass.GithubEnvironmentVariables)
    for f in fields(as_dataclass.GithubEnvironmentVariables):
        assert hasattr(o, f.name)
        assert getattr(o, f.name) == f.default
