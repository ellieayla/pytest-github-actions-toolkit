"""
Check GithubEnvironmentVariablesTD against https://docs.github.com/en/actions/reference/workflows-and-actions/variables
"""

import argparse
from pathlib import Path
from textwrap import dedent

from pytest_github_actions_toolkit.types import Directory, OwnerRepo

variable_url = "https://docs.github.com/api/article/body?pathname=/en/actions/reference/workflows-and-actions/variables"


import logging
import re

logger = logging.getLogger(__name__)


def extract_name_from_first_column(content: str):
    content = content.strip()
    if content[0] == content[-1] == "`":
        variable_name = content[1:-1]
        return variable_name
    raise ValueError(f"No variable in {content}")


LINK = re.compile(r"\[(.*?)\]\((.*?)\)")


def strip_links(content: str):
    return LINK.sub(r"\1", content)


FOR_MORE_INFORMATION = re.compile(r"For more information[^\.]*\.")

PREFIX_FOR_UNSPECIFIED_PATH = "/home/runner/work/_actions/"

FOR_EXAMPLE = re.compile(r"For example[,:]([a-z ]+,)? `(.+?)`(\. *)?")
ALWAYS_SET = re.compile(r"Always set to `(.+?)`(\. *)?")
HAS_THE_VALUE = re.compile(r", and always has the value of `(.+?)`")
POSSIBLE_VALUES = re.compile(r"values are:? `(.+?)`")
TRUE_IF = re.compile(r"`true` if ")


type VariableMetadata = tuple[str, str, type]


def parse_desc_col(column: str) -> VariableMetadata:
    """extract description and example from column."""

    remaining = strip_links(column.strip())

    if has_example := FOR_EXAMPLE.search(remaining):
        example = has_example.group(2)
        remaining = remaining.replace(has_example.group(), "")

    elif has_always := ALWAYS_SET.search(remaining):
        example = has_always.group(1)
        remaining = remaining.replace(has_always.group(), "")

    elif m := HAS_THE_VALUE.search(remaining):
        example = m.group(1)
        remaining = remaining.replace(m.group(), "")

    elif m := POSSIBLE_VALUES.search(remaining):
        example = m.group(1)
        # don't remove from sentence

    elif m := TRUE_IF.search(remaining):
        example = "true"

    elif remaining.startswith("The commit SHA"):
        example = "ffac537e6cbbf934b08745a378932722df287a53"

    elif remaining.startswith("The username"):
        example = "octocat"

    else:
        example = None

    description = FOR_MORE_INFORMATION.sub("", remaining).strip()

    if "directory" in description.lower():
        t = Directory
    elif "path" in description:
        t = Path
    elif description.startswith("The number "):
        t = int
    elif example in ("true", "false"):
        t = bool
    elif description == "The owner and repository name.":
        t = OwnerRepo
    else:
        t = str

    if t in (Path, Directory) and not example:
        example = f"{PREFIX_FOR_UNSPECIFIED_PATH}/example.txt"

    if not example:
        raise ValueError(f"No example extracted from {description=}")

    return description, example, t


def parse_row(row: str):
    columns = row.split("|")
    name_col = columns[1]
    desc_col = columns[2]

    if not name_col.strip():
        # empty row
        return None

    variable_name = extract_name_from_first_column(name_col)

    description, example, typ = metadata = parse_desc_col(desc_col)

    if not description:
        raise ValueError(f"No description produced for {variable_name=} in row {row=}")
    if not example:
        raise ValueError(f"No example found for {variable_name=} in {description=}")
    if not typ:
        raise TypeError(f"No type determined for {variable_name=}")

    logger.debug(f"{variable_name=} {description=} {example=} {typ=}")

    return variable_name, metadata


def parse_markdown(source: str) -> dict[str, VariableMetadata]:

    in_section = False
    in_table = False

    d: dict[str, VariableMetadata] = {}

    for row in source.splitlines():
        if not in_section:
            if row == "## Default environment variables":
                logger.debug(f"Section started {row=}")
                in_section = True
            continue

        if row.startswith("#"):
            in_section = False
            logger.debug(f"Section ended {row=}")
            continue

        if not in_table and in_section:
            if row.startswith("| ---"):
                logger.debug("Table started.")
                in_table = True
            continue

        if not row.startswith("|") and in_section:
            in_table = False
            logger.debug("Table ended.")
            continue

        if in_table:
            # good stuff
            ret = parse_row(row)
            if ret:
                variable_name, metadata = ret
                d[variable_name] = metadata

    return d


def field_to_source(field_name: str, annotation: str):
    return f"{field_name}: {annotation}"


def compute_expected_source(v: dict[str, VariableMetadata]):
    """
    Compute what the source of GithubEnvironmentVariables should look like, given v.
    """
    # first few lines
    # source = inspect.getsource(GithubEnvironmentVariables)
    source = dedent('''\
        class GithubEnvironmentVariables(TypedDict, total=False):
            """
            Typed list of variables from https://docs.github.com/en/actions/reference/workflows-and-actions/variables
            Examples in annotations are all valid for that field, but should not be considered defaults.
            Whether a given variable is present depends on other context, like whether a workflow is triggered by a pull request.
            """

    ''')
    expected: list[str] = source.splitlines()

    indent = "    "
    if not expected[2].startswith(indent):
        raise IndentationError()

    for field_name, metadata in v.items():
        desc, example, typ = metadata

        expected.append(f"{indent}{field_name}: Annotated[")

        for aa in [
            f"{typ.__name__},",
            f"Description({desc!r}),",
            f"Example({example!r}),",
        ]:
            expected.append(f"{indent * 2}{aa}")

        expected.append(f"{indent}]")

    return "\n".join(expected)


def compute_expected_source_enum(v: dict[str, VariableMetadata]) -> str:
    """Compute what the source of GithubEnvironmentVariableNames should look like, given v."""
    # source = inspect.getsource(GithubEnvironmentVariableNames)
    source = dedent('''\
        class GithubEnvironmentVariableNames(StrEnum):
            """
            Names of standard github environment variables from https://docs.github.com/en/actions/reference/workflows-and-actions/variables.
            Matches keys of GithubEnvironmentVariables.
            """

    ''')
    expected: list[str] = source.splitlines()
    indent = "    "
    if not expected[2].startswith(indent):
        raise IndentationError()

    for field_name in v:
        expected.append(f"{indent}{field_name} = {field_name!r}")

    return "\n".join(expected)


def compute_expected_source_dataclass(v: dict[str, VariableMetadata]) -> str:
    """Compute what the source of GithubEnvironmentVariableNamesDC should look like, given v."""

    e = dedent('''\
        @dataclass
        class GithubEnvironmentVariablesDC:
            """
            Typed list of variables from https://docs.github.com/en/actions/reference/workflows-and-actions/variables
            Examples in annotations are all valid for that field, but should not be considered defaults.
            Whether a given variable is present depends on other context, like whether a workflow is triggered by a pull request.
            """

    ''')
    expected: list[str] = e.splitlines()
    indent = "    "

    for field_name, metadata in v.items():
        desc, example, typ = metadata

        expected.append(f"{indent}{field_name}: Annotated[")

        if typ is bool:
            constructor = "truthy_value"
        else:
            constructor = typ.__name__

        for aa in [f"{typ.__name__} | None,", f"Description({desc!r}),", f"Example({example!r}),", f"ValidateAs({constructor}),"]:
            expected.append(f"{indent * 2}{aa}")

        expected.append(f"{indent}] = None")

    return "\n".join(expected)


def main() -> int:
    """Inspect GithubEnvironmentVariables."""
    p = argparse.ArgumentParser()
    p.add_argument("--cache")

    a = p.parse_args()

    logging.basicConfig(level=logging.INFO)
    markdown = None
    if a.cache:
        markdown = Path(a.cache).read_text()

    if not markdown:
        p.error("Need markdown source.")

    variables: dict[str, VariableMetadata] = parse_markdown(markdown)

    expected = compute_expected_source(variables)

    expected += "\n\n"

    expected += compute_expected_source_enum(variables)

    expected += "\n\n"
    expected += compute_expected_source_dataclass(variables)

    produced_source = compile(source=expected, filename="<string>", mode="exec")

    print(expected)


if __name__ == "__main__":
    raise SystemExit(main())
