from click.testing import CliRunner
import pytest
from sigma.cli.convert import convert
from sigma.cli.backends import backends

def test_convert_output_list():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "-p", "sysmon", "tests/files"])
    assert 'EventID=1 ParentImage="*\\\\httpd.exe" Image="*\\\\cmd.exe"' in result.stdout

def test_convert_output_str():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "-p", "sysmon", "-f", "savedsearches", "tests/files"])
    assert 'EventID=1 ParentImage="*\\\\httpd.exe" Image="*\\\\cmd.exe"' in result.stdout

def test_convert_unknown_format():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "-p", "sysmon", "-f", "foo", "tests/files"])
    assert "Invalid value for format" in result.stdout

@pytest.mark.parametrize("backend,format", [
    (backend, format)
    for backend, backend_definition in backends.items()
    for format in backend_definition.formats
])
def test_conversion_all_backends_and_formats(backend, format):
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", backend, "-f", format, "tests/files"])
    assert result.exit_code == 0