"""
Code generation. Produce a dataclass and a StrEnum based on environment variables names and example values in documentation.
"""

import argparse
import ast
import inspect
import logging
import re
import sys
from ast import AnnAssign, Assign, ClassDef
from collections.abc import Iterable
from difflib import unified_diff
from enum import StrEnum
from itertools import chain
from pathlib import Path
from textwrap import wrap
from typing import Literal, Never

from pytest_github_actions_toolkit.env import Name, as_dataclass
from pytest_github_actions_toolkit.types import Description, Directory, OwnerRepo
from pytest_github_actions_toolkit.util import truthy_value

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
BR = "<br>"

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

    description = FOR_MORE_INFORMATION.sub("", remaining).replace(BR, "").strip()

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


def compute_expected_source_enum(v: dict[str, VariableMetadata], indent: int) -> str:
    """Compute what the source of env.Name should look like, given v."""
    expected: list[str] = [
        "",
        *indented([f"{field_name} = {double_quote_repr(field_name)}" for field_name in v], indent),
        "",
    ]

    return "\n".join(expected)


def indented(src: Iterable[str], indent: int) -> list[str]:
    """Return the same list of strings, but with 'indent' qty spaces on the front of each string."""
    return [(" " * indent + row) for row in src]


def annotated_arg(desc: str, typ: type, indent: int) -> list[str]:
    """Construct lines of an Annotated[] attribute list. Caller is responsible for joining and indenting them."""

    description = "\n".join(repr_long_strings(desc, indent))

    return [f"{typ.__name__} | None,", *f"{Description.__name__}({description}),".splitlines()]


def field_arg(constructor: str, example: str, indent: int):
    """Construct lines of a field() constructor's arguments. Caller is responsible for joining and indenting them."""
    MetadataKeysEnum = as_dataclass.Metadata

    if len(example) > 110:
        raise ValueError(f"Unexpectedly long example. Need to consider wrapping it like Description (len={len(example)}): {example!r}")
    field_metadata_lines = [
        f"{MetadataKeysEnum.__name__}.{MetadataKeysEnum.example.name}: {double_quote_repr(example)},",
        f"{MetadataKeysEnum.__name__}.{MetadataKeysEnum.validate_as.name}: {constructor},",
    ]

    return [
        "default=None,",
        "metadata={",
        *indented(field_metadata_lines, indent),
        "},",
    ]


def class_attribute(name: str, meta: VariableMetadata, indent: int) -> list[str]:
    """Construct lines of one class attribute. Caller is responsible for joining and indenting them.

    foo = Annotated[
        ...
    ] = field(
        ...
    )
    """
    desc, example, typ = meta

    if typ is bool:
        constructor = truthy_value.__name__
    else:
        constructor = typ.__name__

    return [
        f"{name}: Annotated[",
        *indented(annotated_arg(desc, typ, indent), indent),
        "] = field(",
        *indented(field_arg(constructor, example, indent), indent),
        ")",
    ]


def compute_expected_source_dataclass(v: dict[str, VariableMetadata], indent: int) -> str:
    """Compute what the source of GithubEnvironmentVariables should look like, given v.
    Indent it to match the parent class body."""

    expected: list[str] = [
        "",
        *indented(chain.from_iterable(class_attribute(field_name, metadata, indent) for field_name, metadata in v.items()), indent),
        "",
    ]

    return "\n".join(expected)


def double_quote_repr(value: str) -> str:
    """Produce a repr of a string wrapped in doublequotes.
    Works by creating a repr with '\0 (singlequote+nul) in it, tricking cpython into using doublequotes.
    Then strip off the extra characters from the rendered repr.
    Ref https://mail.python.org/pipermail/python-list/2003-April/221393.html"""
    return '"' + repr("'\0" + value)[6:]


def repr_long_string_candidate(src: str, width: int, indent: int) -> list[str]:
    """Create a stack of strings wrapped in doublequotes."""
    lines = wrap(src, drop_whitespace=False, width=100)

    return [
        "",
        *indented(map(double_quote_repr, lines), indent=indent),
        "",
    ]


def compute_boxyness(chunk: list[str]) -> float:
    """How close is the length of the shortest line vs the longest line, ignoring the first and last?"""
    lengths = [len(line.strip()) for line in chunk[1:-1]]
    return min(lengths) / max(lengths)


def repr_long_strings(src: str, indent: int) -> list[str]:
    """
    Given a long string, make a multiline thing.

    Like: ("aaaaaa bbbb")
    becomes: (
        "aaaaaa"
        "bbbb"
    )

    Caller is responsible for splicing it in with correct indentation.
    """

    candidates: list[tuple[float | int, list[str]]] = []

    if len(src) < 150 - (indent * 3):
        candidates.append((1, [double_quote_repr(src)]))

    for width in (90, 100, 110):
        candidate = repr_long_string_candidate(src, width=width, indent=indent)
        boxyness = compute_boxyness(candidate)
        candidates.append((boxyness, candidate))

    return sorted(candidates, key=lambda x: x[0]).pop()[1]  # idx=1 is the body, idx=0 is the score


def print_source_pretty(source: str, start: int = 1) -> None:
    for idx, row in enumerate(source.splitlines(), start=start):
        print(f"{idx:>5} | {row}")


def replace_dataclass_in_source_file(existing_source: str, existing_class_name: str, new_variables: dict[str, VariableMetadata]) -> str:
    """There's a pile of AnnAssign's in the middle of the class body. Remove them. Keep everything on each side."""

    tree = ast.parse(existing_source)
    body_indentation: int = 4  # default, let it be over-ridden if there's other contents
    found_class: ClassDef | None = None

    for node in tree.body:
        if isinstance(node, ClassDef) and node.name == existing_class_name:
            found_class = node
            break
    else:
        raise SyntaxError("Didn't find a ClassDef at all!.")

    source_lines = existing_source.splitlines()
    lines_to_remove_set: set[int] = set()

    # Make a list of all lines comprising the Annotated assignment at the class body.
    for node in found_class.body:
        if isinstance(node, AnnAssign):
            # assert isinstance(node.col_offset, int)
            body_indentation = node.col_offset

            for line_no in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                lines_to_remove_set.add(line_no)
            continue

    # Filter the source lines
    retained_source = [line for idx, line in enumerate(source_lines, start=1) if idx not in lines_to_remove_set]

    # Make a replacement
    replacement_body = compute_expected_source_dataclass(new_variables, indent=body_indentation)

    insert_point = min(lines_to_remove_set)
    new_source = "\n".join(retained_source[: insert_point - 1]) + replacement_body + "\n".join(retained_source[insert_point - 1 :])
    return new_source


def handle_dataclass(
    original_class: type, variables: dict[str, VariableMetadata], mode: Literal["print"] | Literal["diff"] | Literal["write"]
) -> bool:
    """Handle printing or updating the dataclass file. Return true if changes were needed."""

    source_filename = inspect.getsourcefile(original_class)
    if not source_filename:
        raise FileNotFoundError(f"Cannot locate file for {original_class=}")
    existing_source = Path(source_filename).read_text()

    new_source = replace_dataclass_in_source_file(existing_source, original_class.__name__, variables)

    ensure_compiles(new_source)

    has_differences = new_source != existing_source
    if mode == "write":
        Path(source_filename).write_text(new_source)
        return has_differences

    if mode == "print":
        # always print, even if nothing changed
        print(new_source)
        return has_differences

    if mode == "diff":
        u = unified_diff(
            existing_source.splitlines(), new_source.splitlines(), fromfile=f"old/{source_filename}", tofile=f"new/{source_filename}", lineterm=""
        )
        for d in u:
            print(d)
        return has_differences

    raise Never()


def replace_strenum_in_source_file(existing_source: str, existing_class_name: str, new_variables: dict[str, VariableMetadata]) -> str:
    """There's a pile of something's in the middle of the class body. Remove them. Keep everything on each side."""

    tree = ast.parse(existing_source)
    body_indentation: int = 4  # default, let it be over-ridden if there's other contents
    found_class: ClassDef | None = None

    for node in tree.body:
        if isinstance(node, ClassDef) and node.name == existing_class_name:
            found_class = node
            break
    else:
        raise SyntaxError("Didn't find a ClassDef at all!.")

    source_lines = existing_source.splitlines()
    lines_to_remove_set: set[int] = set()

    # Make a list of all lines comprising the assignments at the class body.
    for node in found_class.body:
        if isinstance(node, Assign):
            body_indentation = node.col_offset

            for line_no in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                lines_to_remove_set.add(line_no)
            continue

    # Filter the source lines
    retained_source = [line for idx, line in enumerate(source_lines, start=1) if idx not in lines_to_remove_set]

    # Make a replacement
    replacement_body = compute_expected_source_enum(new_variables, indent=body_indentation)

    insert_point = min(lines_to_remove_set)
    new_source = "\n".join(retained_source[: insert_point - 1]) + replacement_body + "\n".join(retained_source[insert_point - 1 :])
    return new_source


def handle_strenum(original_class: type, variables: dict[str, VariableMetadata], mode: Literal["print"] | Literal["diff"] | Literal["write"]) -> bool:
    """Handle printing or updating the strenum file. Return true if changes were needed."""

    source_filename = inspect.getsourcefile(original_class)
    if not source_filename:
        raise FileNotFoundError(f"Cannot locate file for {original_class=}")
    existing_source = Path(source_filename).read_text()

    new_source = replace_strenum_in_source_file(existing_source, original_class.__name__, variables)

    ensure_compiles(new_source)

    has_differences = new_source != existing_source
    if mode == "write":
        Path(source_filename).write_text(new_source)
        return has_differences

    if mode == "print":
        # always print, even if nothing changed
        print(new_source)
        return has_differences

    if mode == "diff":
        u = unified_diff(
            existing_source.splitlines(), new_source.splitlines(), fromfile=f"old/{source_filename}", tofile=f"new/{source_filename}", lineterm=""
        )
        for d in u:
            print(d)
        return has_differences

    raise Never()


class What(StrEnum):
    dataclass = "dataclass"
    enum = "enum"


class Mode(StrEnum):
    print = "print"
    diff = "diff"
    write = "write"


def main() -> int:
    """Inspect GithubEnvironmentVariables."""

    p = argparse.ArgumentParser(epilog="Exits with 0 if up-to-date, 1 if changes needed.")
    p.add_argument("mode", nargs="?", choices=Mode, default=Mode.diff, help="Output mode. Default '%(default)s'")
    p.add_argument("--what", nargs="+", choices=What, default=None, help="What datastructure to update. Default all.")
    p.add_argument("--cache")

    a = p.parse_args()

    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    markdown = None
    if a.cache:
        markdown = Path(a.cache).read_text()

    if not markdown:
        p.error(f"Need markdown source. Download {variable_url!r} and pass file to --cache")

    variables: dict[str, VariableMetadata] = parse_markdown(markdown)

    changes = False

    if a.what is None:
        a.what = list(What)

    if What.dataclass in a.what:
        changes |= handle_dataclass(as_dataclass.GithubEnvironmentVariables, variables, mode=a.mode)
    if What.enum in a.what:
        changes |= handle_strenum(Name, variables, mode=a.mode)

    return 1 if changes else 0


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
