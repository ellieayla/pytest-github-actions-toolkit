"""
The idea of a key=value output file, like GITHUB_OUTPUT or GITHUB_ENV. And the verification thereof.

It supports a heredoc-like syntax for multi-line values.

References:
 * https://jstrieb.github.io/posts/github-actions-multiline-outputs/
 * https://github.com/orgs/community/discussions/106666
 * https://github.com/orgs/community/discussions/116619
 * https://github.com/github/docs/issues/21529
 * https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#multiline-strings
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OutputFile:
    path: Path

    def exists(self) -> bool:
        return self.path.exists()

    def content(self) -> str:
        return self.path.read_text()

    def __str__(self) -> str:
        return self.content()

    def as_dict(self) -> Mapping[str, str]:
        return parse_file_command(self.content())

    @property
    def _mapping(self):
        return self.as_dict()

    def __eq__(self, value: object) -> bool:
        return self.as_dict() == value

    def __get_item__(self, item: str) -> str:
        return self.as_dict()[item]

    def __contains__(self, item: str) -> bool:
        return item in self.as_dict()

    def items(self):
        return self.as_dict().items()


def parse_file_command(content: str) -> Mapping[str, str]:
    """
    Read a env-file format file from a string and return it as a Mapping.

    Supports Github's HEREDOC-like syntax for multi-line values.
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
