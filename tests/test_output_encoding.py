import pytest
from click.testing import CliRunner

from sigma.backends.test.backend import TextQueryTestBackend
from sigma.cli.convert import convert


ENCODINGS = [
    "utf-8",
    "ascii",
    "utf-16",
    "utf-16-le",
    "utf-16-be",
    "utf-32",
    "utf-32-le",
    "utf-32-be",
]


@pytest.fixture
def convert_result(monkeypatch):
    def invoke(value, encoding, output_path=None, indent=None):
        monkeypatch.setattr(
            TextQueryTestBackend,
            "convert",
            lambda self, *args, **kwargs: value,
        )
        args = ["-t", "text_query_test", "--encoding", encoding]
        if output_path is not None:
            args.extend(["-o", str(output_path)])
        if indent is not None:
            args.extend(["--json-indent", str(indent)])
        args.append("tests/files/valid/sigma_rule.yml")
        result = CliRunner().invoke(convert, args)
        assert result.exit_code == 0, result.exception
        if output_path is None:
            return result.stdout_bytes
        assert result.stdout_bytes == b""
        return output_path.read_bytes()

    return invoke


@pytest.mark.parametrize("encoding", ENCODINGS)
@pytest.mark.parametrize("to_file", [False, True], ids=["stdout", "file"])
@pytest.mark.parametrize(
    "value, expected, indent",
    [
        pytest.param("first\nsecond", "first\nsecond\n", None, id="string"),
        pytest.param("", "\n", None, id="empty-string"),
        pytest.param(["first", "second"], "first\n\nsecond\n", None, id="strings"),
        pytest.param([], "\n", None, id="empty-list"),
        pytest.param(
            [{"query": "one"}, {"query": "two"}],
            '{"query": "one"}\n{"query": "two"}\n',
            None,
            id="dictionaries",
        ),
        pytest.param(
            [{"query": "one"}, {"query": "two"}],
            '{\n  "query": "one"\n}\n{\n  "query": "two"\n}\n',
            2,
            id="indented-dictionaries",
        ),
    ],
)
def test_convert_output_text_encoding(
    convert_result, tmp_path, encoding, to_file, value, expected, indent
):
    output_path = tmp_path / "output.txt" if to_file else None
    data = convert_result(value, encoding, output_path, indent)
    assert data == expected.encode(encoding)
    assert data.decode(encoding) == expected


@pytest.mark.parametrize("encoding", ENCODINGS)
@pytest.mark.parametrize(
    "value, expected, indent",
    [
        pytest.param({"query": "one"}, '{"query": "one"}\n', None, id="dictionary"),
        pytest.param({}, "{}\n", None, id="empty-dictionary"),
        pytest.param(
            {"query": "one"},
            '{\n  "query": "one"\n}\n',
            2,
            id="indented-dictionary",
        ),
    ],
)
def test_convert_output_dictionary_encoding(
    convert_result, encoding, value, expected, indent
):
    data = convert_result(value, encoding, indent=indent)
    assert data == expected.encode(encoding)
    assert data.decode(encoding) == expected


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-32"])
@pytest.mark.parametrize("to_file", [False, True], ids=["stdout", "file"])
def test_convert_output_unicode_encoding(convert_result, tmp_path, encoding, to_file):
    output_path = tmp_path / "output.txt" if to_file else None
    data = convert_result("caf\u00e9", encoding, output_path)
    assert data == "caf\u00e9\n".encode(encoding)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
@pytest.mark.parametrize("to_file", [False, True], ids=["stdout", "file"])
@pytest.mark.parametrize("value", [b"\x00\xffdata", b""])
def test_convert_output_bytes_ignores_encoding(
    convert_result, tmp_path, encoding, to_file, value
):
    output_path = tmp_path / "output.bin" if to_file else None
    data = convert_result(value, encoding, output_path)
    assert data == value + b"\n"
