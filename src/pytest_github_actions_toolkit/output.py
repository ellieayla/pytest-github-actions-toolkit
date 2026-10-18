"""
Load and parse a key=value output file, like GITHUB_OUTPUT or GITHUB_ENV.

References:
 * https://jstrieb.github.io/posts/github-actions-multiline-outputs/
 * https://github.com/orgs/community/discussions/106666
 * https://github.com/orgs/community/discussions/116619
 * https://github.com/github/docs/issues/21529
 * https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#multiline-strings
"""

import reprlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass(frozen=True)
class OutputFile:
    """
    A structured file produced an action inside a workflow step, intended to be read by a subsequent step.

    Dyanamically behaves like a mapping or a sequence when comparing to other objects.

    Provided by various fixtures to write assertions about the written content.

    Re-reads file content on each access.
    """

    path: Path

    def __len__(self) -> int:
        """Length of the file in bytes. If missing, returns 0."""
        try:
            return self.path.stat().st_size
        except FileNotFoundError:
            return 0

    def __bool__(self) -> bool:
        """Whether the file contains information. If missing or 0 bytes in length, returns False."""
        return len(self) > 0

    def exists(self) -> bool:
        """Whether the fiel exists."""
        return self.path.exists()

    def read_text(self) -> str:
        """
        Read the file content as a text string.

        Caller is responsible for parsing or passing it on to another library for further processing.
        Useful for markdown or json or other information.
        """
        return self.path.read_text()

    def matcher(self) -> pytest.LineMatcher:
        """Read the file content as a sequence of lines, and expose them using a pytest LineMatcher instance."""
        return pytest.LineMatcher(self.read_text().splitlines())

    def as_dict(self) -> Mapping[str, str]:
        """
        Interpret the file content as a key=value mapping.

        Useful for GITHUB_OUTPUT or GITHUB_ENV.
        """
        return parse_command_file(self.read_text())

    def __repr__(self) -> str:
        custom_repr = reprlib.Repr(maxdict=30, maxstring=300, indent=" " * 4)
        location = self.path
        try:
            content = self.read_text()
        except FileNotFoundError:
            return f"{location}: Does not exist."
        try:
            d = parse_command_file(content)
            return f"{location}: Valid key=value mapping, {len(d)} items: {custom_repr.repr(d)}"
        except ValueError:
            seq = [f"{location}: Raw file, {len(content.splitlines())} lines:", *numbered_file_contents(content)]
            return "\n".join(seq)


def parse_command_file(content: str) -> Mapping[str, str]:
    """
    Read a env-file format command file (like GITHUB_OUTPUT) from a content string and return a Mapping of key=value pairs.

    Supports Github's HEREDOC-like syntax for multi-line values.

    foo=value1
    bar<<EOF
    value2
    EOF

    If duplicate items are found, last wins.
    """
    iterator = iter(content.splitlines())

    result: dict[str, str] = {}

    for line in iterator:
        if not line:  # skip blank lines
            continue

        # Which of these two supported operators is this?
        key_before_delimiter, arrows, delimiter = line.partition("<<")
        key_before_equals, equals, value = line.partition("=")

        # Neither matched this line, that's an error
        if arrows == equals == "":
            raise ValueError(f"Invalid format {value!r}")

        # If both operators are present on the same line, the first one (so shorter key) wins.
        if len(key_before_equals) < len(key_before_delimiter):
            key = key_before_equals

        else:
            key = key_before_delimiter

            partial_value: list[str] = []

            # consume more lines until we reach the delimiter.
            for inner_line in iterator:
                if inner_line == delimiter:
                    value = "\n".join(partial_value)
                    break
                partial_value.append(inner_line)
            else:
                # no delimiter was matched but exhausted the iterator
                raise ValueError(f"Invalid value. Matching delimiter not found {delimiter!r}")

        # Add this item to the result dict. Potentially overwriting a previously-set item (last one wins).
        result[key] = value

    return result


def numbered_file_contents(source: str, *, start: int = 1, around: int | None = None, context: int = 4) -> list[str]:
    ret: list[str] = []
    if around is None:
        for idx, row in enumerate(source.splitlines(), start=start):
            ret.append(f"{idx:>5} | {row}")

    else:
        for idx, row in enumerate(source.splitlines(), start=start):
            if around - context < idx < around + context:
                mark = ">" if idx == around else "|"
                ret.append(f"{idx:>5} {mark} {row}")

    return ret
