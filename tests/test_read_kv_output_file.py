from pathlib import Path
from textwrap import dedent

import pytest

from pytest_github_actions_toolkit.output import OutputFile, parse_command_file

INVALID_FILES = [
    # Heredoc with posix assignment not supported by github actions
    dedent("""\
        equals=<<EOF
        posix
        EOF
    """),
    # A bare word is an error
    "foo",
    # Missing terminator is an error
    dedent("""\
        foo<<EOF
        1
    """),
    # Heredoc with quote characters around delimiter is not supported by github actions (but expansion never happened anyway)
    dedent("""\
        quote=<<'EOF'
        pwd is $PWD
        EOF
    """),
    # Minus: <<-EOF to support leading tabs inside doc does not work
    dedent("""\
        minus<<-EOF
        \ta line starting with tab and containing EOF but that's fine
        \tEOF
    """),
    # Quotes: Quotes for escaping of contents does not work
    dedent("""\
        quote<<'EOF'
        pwd is $PWD
        pwdcmd is `pwd`
        EOF
    """),
    # Heredoc starting with space between << and delimiter is not supported by github actions
    dedent("""\
        space=<< EOF
        value
        EOF
    """),
    # Bash array of values unsupported
    dedent("""\
        arr=(
        1
        2
        )
    """),
]


VALID_FILES = {
    # Basic heredoc
    dedent("""\
        foo<<EOF
        text
        EOF
    """): {"foo": "text"},
    # Multiple assignments is OK
    dedent("""\
        foo<<EOF
        1
        EOF
        bar<<EOF
        2
        EOF
    """): {"foo": "1", "bar": "2"},
    # Minus: <<-EOF is treated as a literal delimiter
    dedent("""\
        minus<<-EOF
        some text
        -EOF
    """): {"minus": "some text"},
    # Expansion: Shell-like variable expansion is ignored.
    dedent("""\
        exp<<EOF
        pwd is $PWD
        EOF
    """): {"exp": "pwd is $PWD"},
    # Extra space at the end of a key is valid.
    dedent("""\
        foo <<EOF
        text
        EOF
    """): {"foo ": "text"},
    # Assigning multiple variables on one line like a shell does nothing, rest of line attached to first
    dedent("""\
        foo=1 bar=2
    """): {"foo": "1 bar=2"},
    # Semicolon is ignored, rest of line attached to first
    dedent("""\
        foo=1;bar=2
    """): {"foo": "1;bar=2"},
    # Starting a line with # is not a comment (though it might be hard to refer to elsewhere unless using toJSON())
    dedent("""\
        foo=1
        #comment=2
        bar=3
    """): {"foo": "1", "#comment": "2", "bar": "3"},
    # Blank lines are ignored
    dedent("""\
        foo=1

        bar=2
    """): {"foo": "1", "bar": "2"},
    # Starting a line inside a DOC is not a comment
    dedent("""\
        foo<<DOC
        value
        #comment=2
        DOC
    """): {"foo": "value\n#comment=2"},
    # << inside a value, after =
    dedent("""\
        foo=value<<with<arrows
    """): {"foo": "value<<with<arrows"},
    # = inside a delimiter, after <<
    dedent("""\
        foo<<EOF=DOC
        value
        EOF=DOC
    """): {"foo": "value"},
    # various combinations of < and =
    "foo<=bar": {"foo<": "bar"},
    " foo=bar": {" foo": "bar"},
    "foo =bar": {"foo ": "bar"},
    "foo bar=1": {"foo bar": "1"},
    "foo= bar": {"foo": " bar"},
    "foo=bar ": {"foo": "bar "},
    "foo==bar": {"foo": "=bar"},
}


@pytest.mark.parametrize(
    "content",
    INVALID_FILES,
)
def test_ensure_invalid_content_produces_error(content: str) -> None:
    with pytest.raises(ValueError):
        parse_command_file(content)


@pytest.mark.parametrize(
    ("content", "expected"),
    VALID_FILES.items(),
    ids=repr,
)
def test_valid_content(tmp_path: Path, content: str, expected: dict[str, str]) -> None:
    assert parse_command_file(content) == expected

    location = tmp_path / "f.txt"
    location.write_text(content)

    o = OutputFile(location)

    assert o.read_text() == content
    assert o.as_dict() == expected


@pytest.mark.parametrize(
    ("content"),
    (
        *VALID_FILES.keys(),
        *INVALID_FILES,
    ),
    ids=repr,
)
def test_any_content_repr(tmp_path: Path, content: str) -> None:
    location = tmp_path / "f.txt"
    location.write_text(content)

    o = OutputFile(location)

    print(repr(o))
