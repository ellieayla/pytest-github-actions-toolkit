"""
Code generator. Produce a dataclass and a StrEnum based on environment variables names and example values in documentation.
Can print new classes to stdout, print a diff vs existing source, or overwrite source files with replacements.
"""

import argparse
import ast
import inspect
import logging
import re
import sys
from abc import abstractmethod
from ast import AnnAssign, Assign, ClassDef
from collections.abc import Iterable
from difflib import unified_diff
from enum import StrEnum
from itertools import chain
from pathlib import Path
from textwrap import wrap
from typing import Literal, Never
from urllib.request import urlopen

# Hardcoded support for specific functionality in pytest_github_actions_toolkit
from pytest_github_actions_toolkit.env import Name, as_dataclass
from pytest_github_actions_toolkit.output import numbered_file_contents
from pytest_github_actions_toolkit.types import Description, Directory, OwnerRepo
from pytest_github_actions_toolkit.util import truthy_value

logger = logging.getLogger(__name__)

type VariableMetadata = tuple[str, str, type]
type Variables = dict[str, VariableMetadata]

variable_url = "https://docs.github.com/api/article/body?pathname=/en/actions/reference/workflows-and-actions/variables"


### Parse Markdown (rudimentary)


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

FOR_EXAMPLE = re.compile(r"For example[,:]([a-z0-9 ]+,)? `(.+?)`(\. *)?")
ALWAYS_SET = re.compile(r"Always set to `(.+?)`(\. *)?")
HAS_THE_VALUE = re.compile(r", and always has the value of `(.+?)`")
POSSIBLE_VALUES = re.compile(r"values are:? `(.+?)`")
TRUE_IF = re.compile(r"`true` if ")
BR = "<br>"


def parse_desc_col(column: str) -> VariableMetadata:
    """Extract an example from the big textual description. Refine the remaining description text."""

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
        # don't remove from sentence, because there's probably several and they should stay together.

    elif m := TRUE_IF.search(remaining):
        example = "true"

    elif "commit SHA" in remaining:
        example = "ffac537e6cbbf934b08745a378932722df287a53"

    elif remaining.startswith("The username"):
        example = "octocat"

    else:
        example = None

    description = FOR_MORE_INFORMATION.sub("", remaining).replace(BR, "").strip()

    t: type
    if "path where an action is located" in description.lower():
        t = Directory
    elif "directory" in description.lower():
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

    if not example:
        if t is Path:
            example = f"{PREFIX_FOR_UNSPECIFIED_PATH}/example.txt"
        elif t is Directory:
            example = f"{PREFIX_FOR_UNSPECIFIED_PATH}/example/"
        else:
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


#### Make new source


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


def double_quote_repr(value: str) -> str:
    """
    Produce a repr of a string wrapped in double-quotes.

    When cpython makes a repr of a string containing only single-quotes,
    it wraps the produced string in double-quotes.
    When making that quoting decision, cpython scans the string only until it finds \0.

    That looks like "'\x00value" - it has unwanted leading characters.

    Remove the first 6 characters and then attach a " back on.

    Ref https://mail.python.org/pipermail/python-list/2003-April/221393.html
    """
    assert len(repr("'\0''")) - len(repr("'")) == 6  # noqa: S101
    return '"' + repr("'\0" + value)[6:]


def repr_long_string_candidate(src: str, width: int, indent: int) -> list[str]:
    """Create a stack of strings wrapped in doublequotes."""
    lines = wrap(src, drop_whitespace=False, width=100)

    return [
        "",  # insert a newline at the end of the first line, where caller has put an opening brace
        *indented(map(double_quote_repr, lines), indent=indent),
        "",  # let the caller finish the last line, probably with a closing brace
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

    # XXX: Hardcoded hack. We only use this for a Description right now, at a known indentation, with a configured ruff line-length
    DESIRED_WIDTH = 150  # ruff line-length
    extra_chars_if_one_line = (" " * indent * 2) + Description.__name__ + "(" + "),"
    extra_chars_if_two_line = " " * indent * 3

    candidates: list[tuple[float | int, list[str]]] = []

    if len(src + extra_chars_if_one_line) < DESIRED_WIDTH:
        # candidates.append((2, [double_quote_repr(src)]))
        return [double_quote_repr(src)]  # just pick it

    if len(src + extra_chars_if_two_line) < DESIRED_WIDTH:
        # candidates.append((2, [double_quote_repr(src)]))
        return ["", *indented([double_quote_repr(src)], indent), ""]  # just pick it

    for width in (90, 100, 110, 120, 130, 140):  # try different wrap widths to find the "most boxy" one.
        candidate = repr_long_string_candidate(src, width=width, indent=indent)
        boxyness = compute_boxyness(candidate)
        candidates.append((boxyness, candidate))

    return sorted(candidates, key=lambda x: x[0]).pop()[1]  # idx=1 is the body, idx=0 is the score


class BodyReplacer[T]:
    """There's a pile of something's in the middle of the class body. Remove them. Keep everything on each side."""

    data: T

    def __init__(self, data: T) -> None:
        self.data = data

    @abstractmethod
    def mark_for_removal(self, class_definition: ClassDef) -> set[int]:
        """Decide which parts of the AST to remove, by line number. Subclass must return a set[node.lineno]"""
        ...

    @abstractmethod
    def make_replacement(self, indent: int) -> list[str]:
        """Construct replacement for the body, replacing the removed parts. Subclass must return a list of strings."""
        ...


class ReplaceNames(BodyReplacer[Variables]):
    def mark_for_removal(self, class_definition: ClassDef) -> set[int]:
        ret: set[int] = set()
        for node in class_definition.body:
            if isinstance(node, Assign):
                # add lines from start to end of this node.
                for line_no in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                    ret.add(line_no)

        return ret

    def make_replacement(self, indent: int) -> list[str]:
        return indented([f"{field_name} = {double_quote_repr(field_name)}" for field_name in self.data], indent)


class ReplaceDataclass(BodyReplacer[Variables]):
    def mark_for_removal(self, class_definition: ClassDef) -> set[int]:
        ret: set[int] = set()
        for node in class_definition.body:
            if isinstance(node, AnnAssign):
                for line_no in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                    ret.add(line_no)
        return ret

    def make_replacement(self, indent: int) -> list[str]:
        return indented(chain.from_iterable(class_attribute(field_name, metadata, indent) for field_name, metadata in self.data.items()), indent)


class ClassNotFoundError(ValueError): ...


def replace_body_of[T](
    existing_source: str,
    existing_class_name: str,
    using: BodyReplacer[T],
    body_indentation: int = 4,  # default,
):
    """
    Using a subclass of BodyReplacer, find pieces of some module-level class to remove and make new ones.
    If some class is not found at the module-level, raises a ClassNotFoundError.
    """
    tree = ast.parse(existing_source)

    for found_class in tree.body:  # TODO: This is module-level right now. Should we search deeper?
        if isinstance(found_class, ClassDef) and found_class.name == existing_class_name:
            break
    else:
        raise ClassNotFoundError(existing_class_name)

    for node in found_class.body:
        body_indentation = node.col_offset  # update assumption based on class' real indentation
        break

    source_lines = existing_source.splitlines()
    lines_to_remove_set = using.mark_for_removal(found_class)

    # Filter the source lines
    retained_source = [line for idx, line in enumerate(source_lines, start=1) if idx not in lines_to_remove_set]

    # Make a replacement
    replacement_body = using.make_replacement(indent=body_indentation)

    insert_point = min(lines_to_remove_set)
    new_source = "\n".join(retained_source[: insert_point - 1] + replacement_body + retained_source[insert_point - 1 :])

    if not new_source.endswith("\n"):
        new_source += "\n"

    return new_source


def handle_resource[T](
    original_class: type,
    mode: Literal["print", "diff", "write"],
    using: BodyReplacer[T],
) -> bool:
    """Handle printing or updating a source file. Return true if changes were needed."""

    # Find the file which provides the original_class source.
    source_filename = inspect.getsourcefile(original_class)
    if not source_filename:
        raise FileNotFoundError(f"Cannot locate file for {original_class=}")
    existing_source = Path(source_filename).read_text()

    # Rip the class apart and put together a replacement
    new_source = replace_body_of(
        existing_source=existing_source,
        existing_class_name=original_class.__name__,
        using=using,
    )

    ensure_compiles(new_source)

    has_differences: bool = new_source != existing_source

    if mode == "write":
        Path(source_filename).write_text(new_source)
        logger.info(f"Wrote {source_filename!r}")

    elif mode == "print":
        # always print, even if nothing changed
        print(new_source)

    elif mode == "diff":
        u = unified_diff(
            existing_source.splitlines(), new_source.splitlines(), fromfile=f"old/{source_filename}", tofile=f"new/{source_filename}", lineterm=""
        )
        for d in u:
            print(d)

    else:
        raise Never()

    return has_differences


class What(StrEnum):
    dataclass = "dataclass"
    enum = "enum"


class Mode(StrEnum):
    print = "print"
    diff = "diff"
    write = "write"


def main() -> int:
    """Inspect classes GithubEnvironmentVariables and Name for differences with upstream documentation."""

    p = argparse.ArgumentParser(
        epilog="Exits with 0 if up-to-date, 1 if changes needed.",
        description=__doc__,
    )
    p.add_argument("mode", nargs="?", choices=Mode, default=Mode.diff, help="Output mode. Default '%(default)s'")
    p.add_argument("--what", action="append", choices=What, default=None, help="What datastructure to update. Default all.")

    # title=f"Markdown documentation, eg {variable_url!r}"
    doc = p.add_argument_group(title="Markdown documentation to extract a list of environment variables from.")
    reference_group = doc.add_mutually_exclusive_group(required=True)
    reference_group.add_argument("--file", type=Path, help="File containing documentation retrieved earlier (eg with curl or git).")
    reference_group.add_argument("--url", nargs="?", type=str, help="Url to fetch, (default %(default)r)", default=variable_url)
    a = p.parse_args()

    logging.basicConfig(format="%(message)s", level=logging.INFO, stream=sys.stderr)

    markdown: str
    if a.file:
        markdown = a.file.read_text()

    else:
        if not a.url:
            a.url = variable_url

        logger.info(f"Fetching {a.url!r}")
        with urlopen(a.url) as f:  # noqa: S310 [https://github.com/astral-sh/ruff/issues/7918]
            markdown = f.read().decode("utf-8")

    variables: dict[str, VariableMetadata] = parse_markdown(markdown)

    changes = False

    if a.what is None:
        a.what = list(What)

    if What.dataclass in a.what:
        changes |= handle_resource(as_dataclass.GithubEnvironmentVariables, mode=a.mode, using=ReplaceDataclass(variables))
    if What.enum in a.what:
        changes |= handle_resource(Name, mode=a.mode, using=ReplaceNames(variables))

    if not changes:
        logger.info("OK")

    return 1 if changes else 0


def ensure_compiles(generated: str):
    """Try to compile the generated source. If it fails, print the source around the erroneous lines."""
    try:
        _produced_source = compile(source=generated, filename="<generated-string>", mode="exec")
    except SyntaxError as e:
        if e.lineno:
            start = e.lineno
            end = e.end_lineno or e.lineno
            print("\n".join(numbered_file_contents(generated, around=(start, end), context=6)))

        raise


if __name__ == "__main__":
    raise SystemExit(main())
