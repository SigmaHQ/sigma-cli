from sigma.cli.main import cli as main, version
from click.testing import CliRunner
import re

def test_help():
    cli = CliRunner()
    result = cli.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 10

def test_version():
    cli = CliRunner()
    result = cli.invoke(version)
    assert result.exit_code == 0
    assert re.search("\\d+\\.\\d+\\.\\d+", result.stdout)