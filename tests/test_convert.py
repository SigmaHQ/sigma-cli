from click.testing import CliRunner
import pytest
from sigma.cli.convert import convert
from sigma.cli.backends import backends

def test_convert_output_list_of_str():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "-p", "sysmon", "tests/files/valid"])
    assert 'EventID=1 ParentImage="*\\\\httpd.exe" Image="*\\\\cmd.exe"' in result.stdout

def test_convert_output_list_of_dict():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "elasticsearch", "-p", "sysmon", "-f", "dsl_lucene", "tests/files/valid"])
    assert 'EventID:1' in result.stdout

def test_convert_output_list_of_dict_indent():
    cli = CliRunner()
    result_noindent = cli.invoke(convert, ["-t", "elasticsearch", "-p", "sysmon", "-f", "dsl_lucene", "tests/files/valid"])
    result_indent = cli.invoke(convert, ["-t", "elasticsearch", "-p", "sysmon", "-f", "dsl_lucene", "-j", "2", "tests/files/valid"])
    assert len(result_indent.stdout.split("\n")) > len(result_noindent.stdout.split("\n"))

def test_convert_output_str():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "-p", "sysmon", "-f", "savedsearches", "tests/files/valid"])
    assert 'EventID=1 ParentImage="*\\\\httpd.exe" Image="*\\\\cmd.exe"' in result.stdout

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
    test_file = str(tmp_path) + "/test.zip"
    result = cli.invoke(convert, ["-t", "qradar", "-f", "extension", "-o", test_file, "tests/files/valid"])
    assert open(test_file, "rb").read(2) == b"PK"

def test_convert_unknown_format():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "-p", "sysmon", "-f", "foo", "tests/files/valid"])
    assert "Invalid value for format" in result.stdout

@pytest.mark.parametrize("backend,format", [
    (backend, format)
    for backend, backend_definition in backends.items()
    for format in backend_definition.formats
])
def test_conversion_all_backends_and_formats(backend, format):
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", backend, "-f", format, "--without-pipeline", "tests/files/valid"])
    assert result.exit_code == 0 and len(result.stdout) > 60

def test_convert_missing_input():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "-p", "sysmon"])
    assert 'Missing argument' in result.stdout

def test_convert_missing_pipeline():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "tests/files/valid"])
    assert result.exit_code > 0 and "pipeline required" in result.stdout

def test_convert_missing_pipeline_ignore():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "--without-pipeline", "tests/files/valid"])
    assert 'ParentImage="*\\\\httpd.exe" Image="*\\\\cmd.exe"' in result.stdout

def test_convert_wrong_pipeline():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "-p", "ecs_windows", "tests/files/valid"])
    assert result.exit_code > 0 and "pipelines are not intended" in result.stdout

def test_convert_wrong_pipeline_ignore():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "-p", "ecs_windows", "--disable-pipeline-check", "tests/files/valid"])
    assert "process.executable" in result.stdout