from click.testing import CliRunner
import pytest
from sigma.cli.convert import convert
import sigma.backends.test

def test_convert_output_list_of_str():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "test", "-p", "another_test", "--disable-pipeline-check", "tests/files/valid"])
    assert 'EventID=1 and ParentImage endswith "\\httpd.exe" and Image endswith "\\cmd.exe"' in result.stdout

def test_convert_output_list_of_dict():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "test", "-f", "list_of_dict", "tests/files/valid"])
    assert 'ParentImage' in result.stdout

def test_convert_output_list_of_dict_indent():
    cli = CliRunner()
    result_noindent = cli.invoke(convert, ["-t", "test", "-f", "list_of_dict", "tests/files/valid"])
    result_indent = cli.invoke(convert, ["-t", "test", "-f", "list_of_dict", "-j", "2", "tests/files/valid"])
    assert len(result_indent.stdout.split("\n")) > len(result_noindent.stdout.split("\n"))

def test_convert_output_str():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "test", "-f", "str", "tests/files/valid"])
    assert 'ParentImage' in result.stdout

# The following test is hard to implement: in a terminal it behaves as expected, as test it seems to be
# something different. The outcome if this fails is also non-fatal: the user gets some binary output on a tty.
# Therefore, the test is not implemented for now.
""" def test_convert_output_bytes_without_output(monkeypatch):
    monkeypatch.setattr("click._io.IOBase", "isatty", lambda self: True)
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "qradar", "-f", "extension", "tests/files/valid"])
    assert "provide output file" in result.stdout """

def test_convert_output_bytes(tmp_path):
    cli = CliRunner()
    test_file = tmp_path / "test.bin"
    result = cli.invoke(convert, ["-t", "test", "-f", "bytes", "-o", str(test_file), "tests/files/valid"])
    assert result.exit_code == 0
    assert "ParentImage" in open(test_file, "r").read()

def test_convert_unknown_format():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "test", "-f", "foo", "tests/files/valid"])
    assert "Invalid value for format" in result.stdout

def test_convert_missing_input():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "test"])
    assert 'Missing argument' in result.stdout

def test_convert_missing_pipeline():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "test_mandatory", "tests/files/valid"])
    assert result.exit_code > 0 and "pipeline required" in result.stdout

def test_convert_missing_pipeline_ignore():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "test_mandatory", "--without-pipeline", "tests/files/valid"])
    assert 'ParentImage' in result.stdout

def test_convert_wrong_pipeline():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "test", "-p", "another_test", "tests/files/valid"])
    assert result.exit_code > 0 and "pipelines are not intended" in result.stdout

def test_yml_pipeline_doesnt_trigger_wrong_pipeline():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "test", "-p", "test", "-p", "tests/files/custom_pipeline.yml", "tests/files/valid"])
    print(result.stdout)
    assert "some_other_string" in result.stdout