from click.testing import CliRunner
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest

from sigma.cli.check import check

TEST_FILES_DIR = Path(__file__).parent / "files"


def skip_if_junitxml_unavailable():
    if "junitxml" not in {param.name for param in check.params}:
        pytest.skip("--junitxml option is not available in this branch")


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
    with open("tests/files/valid/sigma_rule.yml", "rt") as yml_file:
        input = yml_file.read()
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
    assert result.exit_code == 1
    assert "4 issues" in result.stdout


def test_check_with_issues_exclusions():
    cli = CliRunner()
    result = cli.invoke(
        check,
        [
            "--validation-config",
            "tests/files/validation_config.yml",
            "tests/files/issues",
        ],
    )
    assert result.exit_code == 1
    assert "2 issues" in result.stdout


def test_check_fail_on_issues():
    cli = CliRunner()
    result = cli.invoke(check, ["--fail-on-issues", "tests/files/issues"])
    assert result.exit_code == 1
    assert "Validation issue summary" in result.stdout


def test_check_exclude():
    cli = CliRunner()
    result = cli.invoke(
        check,
        [
            "--fail-on-issues",
            "--exclude",
            "Invalid_Related_Type",
            "--exclude",
            "status_existence",
            "-x",
            "date_existence",
            "--exclude",
            "MyValidator",
            "tests/files/issues/sigma_rule_with_bad_references.yml",
        ],
    )
    assert result.exit_code == 1
    assert "Invalid validators name" in result.stdout
    assert "myvalidator" in result.stdout
    assert "Check failure" in result.stdout


def test_check_junitxml_created_and_well_formed(tmp_path):
    runner = CliRunner()
    skip_if_junitxml_unavailable()
    report_path = tmp_path / "check-report.xml"
    result = runner.invoke(
        check,
        [
            "--junitxml",
            str(report_path),
            str(TEST_FILES_DIR / "invalid"),
        ],
    )
    assert result.exit_code == 1
    assert report_path.exists()
    root = ET.parse(report_path).getroot()
    # JUnit XML producers can emit either a single "testsuite" root
    # or a "testsuites" wrapper for multiple suites.
    assert root.tag in {"testsuites", "testsuite"}
    if root.tag == "testsuites":
        assert len(root.findall("testsuite")) > 0


def test_check_junitxml_reports_failures_for_invalid_rules(tmp_path):
    runner = CliRunner()
    skip_if_junitxml_unavailable()
    report_path = tmp_path / "check-report.xml"
    result = runner.invoke(
        check,
        [
            "--junitxml",
            str(report_path),
            str(TEST_FILES_DIR / "invalid"),
        ],
    )
    assert result.exit_code == 1
    root = ET.parse(report_path).getroot()
    failures = root.findall(".//failure")
    assert len(failures) > 0
