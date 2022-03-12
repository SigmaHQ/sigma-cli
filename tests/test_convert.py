from click.testing import CliRunner
from sigma.cli.convert import convert

def test_convert_output_list():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "-p", "sysmon", "tests/files"])
    assert 'EventID=1 ParentImage="*\httpd.exe" Image="*\cmd.exe"' in result.stdout

def test_convert_output_str():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "-p", "sysmon", "-f", "savedsearches", "tests/files"])
    assert 'EventID=1 ParentImage="*\httpd.exe" Image="*\cmd.exe"' in result.stdout

def test_convert_unknown_format():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "-p", "sysmon", "-f", "foo", "tests/files"])
    assert "Invalid value for format" in result.stdout