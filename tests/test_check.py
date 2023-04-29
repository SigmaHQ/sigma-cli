from click.testing import CliRunner
from sigma.cli.check import check

def test_check_help():
    cli = CliRunner()
    result = cli.invoke(check, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 20

def test_check_valid():
    cli = CliRunner()
    result = cli.invoke(check, ["tests/files/valid"])
    assert result.exit_code == 0
    assert "0 errors" in result.stdout
    assert "0 condition errors" in result.stdout
    assert "0 issues" in result.stdout

def test_check_stdin():
    cli = CliRunner()
    input = open("tests/files/valid/sigma_rule.yml", "rt").read()
    result = cli.invoke(check, ["-"], input=input)
    assert result.exit_code == 0
    assert "0 errors" in result.stdout
    assert "0 condition errors" in result.stdout
    assert "0 issues" in result.stdout

def test_check_invalid():
    cli = CliRunner()
    result = cli.invoke(check, ["tests/files/invalid"])
    assert result.exit_code == 1
    assert "6 errors" in result.stdout
    assert "1 condition errors" in result.stdout
    assert "0 issues" in result.stdout

def test_check_with_issues():
    cli = CliRunner()
    result = cli.invoke(check, ["tests/files/issues"])
    assert result.exit_code == 0
    assert "3 issues" in result.stdout

def test_check_with_issues_exclusions():
    cli = CliRunner()
    result = cli.invoke(check, ["--validation-config", "tests/files/validation_config.yml", "tests/files/issues"])
    assert result.exit_code == 0
    assert "1 issues" in result.stdout

def test_check_fail_on_issues():
    cli = CliRunner()
    result = cli.invoke(check, ["--fail-on-issues", "tests/files/issues"])
    assert result.exit_code == 1
    assert "Validation issue summary" in result.stdout