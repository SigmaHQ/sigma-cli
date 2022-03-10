from click.testing import CliRunner
from sigma.cli.convert import convert

def test_convert():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "splunk", "-p", "sysmon", "tests/files"])
    assert 'EventID=1 ParentImage="*\httpd.exe" Image="*\cmd.exe"' in result.stdout