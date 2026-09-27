from click.testing import CliRunner

from sigma.cli.check import check
import xml.etree.ElementTree as ET
from sigma.cli.check import generate_junit_report
import pathlib


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


def test_generate_junit_report_writes_file(tmp_path):
    # Prepare sample results with one failed and one passed test
    results = [
        {
            "rule_name": "rule_one",
            "file_path": "tests/files/valid/sigma_rule.yml",
            "status": "failed",
            "issue_type": "TestIssue",
            "severity": "high",
            "description": "Something went wrong",
        },
        {
            "rule_name": "rule_two",
            "file_path": "tests/files/valid/sigma_rule.yml",
            "status": "passed",
            "issue_type": "Validation Success",
            "severity": "ok",
            "description": "All good",
        },
    ]

    out = tmp_path / "junit.xml"
    generate_junit_report(results, str(out))

    # Ensure file exists and is valid XML with expected structure
    assert out.exists()
    tree = ET.parse(str(out))
    root = tree.getroot()
    assert root.tag == "testsuites"

    suites = {ts.get("name"): ts for ts in root.findall("testsuite")}
    assert "TestIssue" in suites
    assert "Validation Success" in suites

    test_suite = suites["TestIssue"]
    assert test_suite.get("tests") == "1"
    assert test_suite.get("failures") == "1"

    # Check testcase contains the icon for high severity (🔴)
    testcase = test_suite.find("testcase")
    assert testcase is not None
    assert testcase.get("name").startswith("🔴 ")

    failure = testcase.find("failure")
    assert failure is not None
    assert failure.get("message") == "TestIssue: HIGH"


def test_check_cli_generates_junitxml(tmp_path):
    cli = CliRunner()
    out = tmp_path / "report.xml"
    result = cli.invoke(check, ["--junitxml", str(out), "tests/files/valid"])
    assert result.exit_code == 0
    assert out.exists()
    tree = ET.parse(str(out))
    assert tree.getroot().tag == "testsuites"
