"""
Check GithubEnvironmentVariablesTD against https://docs.github.com/en/actions/reference/workflows-and-actions/variables
"""

import argparse
import inspect
import itertools
import logging
import re
from ast import AnnAssign, FunctionDef
from difflib import unified_diff
from pathlib import Path
from textwrap import dedent, wrap
from typing import Any

from pytest_github_actions_toolkit.env import as_dataclass
from pytest_github_actions_toolkit.types import Directory, OwnerRepo

variable_url = "https://docs.github.com/api/article/body?pathname=/en/actions/reference/workflows-and-actions/variables"


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

    t: type
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


def compute_expected_source_of_typed_dict(v: dict[str, VariableMetadata]):
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

    expected: list[str] = [""]
    indent = "    "

    for field_name, metadata in v.items():
        desc, example, typ = metadata

        expected.append(f"{indent}{field_name}: Annotated[")

        if typ is bool:
            constructor = "truthy_value"
        else:
            constructor = typ.__name__

        for aa in [
            f"{typ.__name__} | None,",
            f"Description({f'\n{indent * 2}'.join(repr_long_strings(desc))}),",
            # f"Example({double_quote_repr(example)}),",
            # f"ValidateAs({constructor}),"
        ]:
            expected.append(f"{indent * 2}{aa}")

        expected.append(f"{indent}] = field(")
        expected.append(f"{indent * 2}default=None,")
        expected.append(f"{indent * 2}metadata={{")
        for bb in [
            f"Metadata.example: {double_quote_repr(example)},",
            f"Metadata.validate_as: {constructor},",
        ]:
            expected.append(f"{indent * 3}{bb}")
        expected.append(f"{indent * 2}}},")
        expected.append(f"{indent})")

    expected.append("")

    return "\n".join(expected)


def double_quote_repr(value: str) -> str:
    """Produce a repr of a string wrapped in doublequotes.
    Works by creating a repr with '\0 (singlequote+nul) in it, tricking cpython into using doublequotes.
    Then strip off the extra characters from the rendered repr.
    Ref https://mail.python.org/pipermail/python-list/2003-April/221393.html"""
    return '"' + repr("'\0" + value)[6:]


def repr_long_string_candidate(src: str, width: int) -> list[str]:

    indent_more = "    "
    lines = wrap(src, drop_whitespace=False, width=100)

    output = [
        "",
        *[indent_more + double_quote_repr(line) for line in lines],
        "",
    ]
    return output


def compute_boxyness(chunk: list[str]) -> float:
    """How close is the length of the shortest line vs the longest line, ignoring the first and last?"""
    lengths = [len(line.strip()) for line in chunk[1:-1]]
    return min(lengths) / max(lengths)


def repr_long_strings(src: str) -> list[str]:
    """
    Given a long string, make a multiline thing.

    Like "aaaaaa bbbb"
    becomes
    ("aaaaaa"
     "bbbb)

    Caller is responsible for splicing it in with correct indentation.
    """

    candidates: list[tuple[float | int, list[str]]] = []

    if len(src) < 150:
        candidates.append((1, [double_quote_repr(src)]))

    for width in (90, 100, 110):
        candidate = repr_long_string_candidate(src, width=width)
        boxyness = compute_boxyness(candidate)
        candidates.append((boxyness, candidate))

    return sorted(candidates, key=lambda x: x[0]).pop()[1]


def diff_source(existing_object: type, generated: str) -> bool:
    existing_source = inspect.getsource(existing_object).splitlines()
    generated_source = generated.splitlines()

    u = unified_diff(existing_source, generated_source)

    has_diff = False
    for row in u:
        print(row)
        has_diff = True

    return has_diff


def extract_keepsake_from_existing_code(existing_object: type) -> tuple[str, str]:
    """There's a pile of AnnAssign's in the middle of the class body. Remove them. Keep everything on each side."""
    import ast

    existing_source = inspect.getsource(existing_object)

    # for row, body in enumerate(existing_source.splitlines(), start=1):
    #    print(f"{row:>5} | {body}")

    tree = ast.parse(existing_source)

    lines_to_remove_set: set[int] = set()

    class IdentifyAnnAssign(ast.NodeVisitor):
        def visit_AnnAssign(self, node: AnnAssign) -> Any:
            for line_no in range(node.lineno, node.end_lineno + 1):
                lines_to_remove_set.add(line_no)
            return None

        def visit_FunctionDef(self, node: FunctionDef) -> Any:
            return None

    tree = IdentifyAnnAssign().visit(tree)

    # Now we have a set of line numbers to remove from existing_source. They should be contiguous. Check.
    lines_to_remove = sorted(lines_to_remove_set)

    if not all(b - a == 1 for a, b in itertools.pairwise(sorted(lines_to_remove))):
        print([b - a == 1 for a, b in itertools.pairwise(sorted(lines_to_remove))])
        raise ValueError("Gaps in source, aborting!", lines_to_remove)

    source_lines = existing_source.splitlines()

    prelude = "\n".join(source_lines[: min(lines_to_remove) - 1])
    postlude = "\n".join(source_lines[max(lines_to_remove) :])
    return prelude, postlude


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

    x, y = extract_keepsake_from_existing_code(as_dataclass.GithubEnvironmentVariables)

    new_dataclass_source = x + compute_expected_source_dataclass(variables) + y
    # ensure_compiles(new_dataclass_source)
    print(new_dataclass_source)

    # diff_source(as_dataclass.GithubEnvironmentVariables, new_dataclass_source)
    return 0


def ensure_compiles(generated: str, context: int = 60):
    try:
        _produced_source = compile(source=generated, filename="<string>", mode="exec")
    except SyntaxError as e:
        source = generated.splitlines()
        if e.lineno:
            for line, body in enumerate(source[e.lineno - context : e.lineno + context], start=e.lineno - context):
                print(f"{line:>4} | {body}")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
