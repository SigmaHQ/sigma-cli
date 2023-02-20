from sigma.cli.main import cli as main
from click.testing import CliRunner

def test_help():
    cli = CliRunner()
    result = cli.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 10