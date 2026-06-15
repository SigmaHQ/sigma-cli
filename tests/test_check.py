import xml.etree.ElementTree as ET
from pathlib import Path

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


def test_check_junitxml_creates_file(tmp_path):
    """JUnit XML file is created and well-formed when --junitxml is specified."""
    cli = CliRunner()
    output_xml = tmp_path / "results.xml"
    # Use --pass-on-error so exit code is 0; invalid rules don't reach the network
    # validator, which avoids the pre-existing MITRE D3FEND network dependency.
    result = cli.invoke(
        check, ["--pass-on-error", "--junitxml", str(output_xml), "tests/files/invalid"]
    )
    assert result.exit_code == 0
    assert output_xml.exists(), "JUnit XML file was not created"
    assert f"JUnit report saved to: {output_xml}" in result.stdout

    # Verify the XML is well-formed and has the expected root element
    tree = ET.parse(output_xml)
    root = tree.getroot()
    assert root.tag == "testsuites"


def test_check_junitxml_invalid(tmp_path):
    """JUnit XML file contains failure entries when rules have errors."""
    cli = CliRunner()
    output_xml = tmp_path / "results.xml"
    result = cli.invoke(
        check, ["--pass-on-error", "--junitxml", str(output_xml), "tests/files/invalid"]
    )
    assert result.exit_code == 0
    assert output_xml.exists(), "JUnit XML file was not created"

    tree = ET.parse(output_xml)
    root = tree.getroot()
    assert root.tag == "testsuites"

    # At least one testsuite should have failures > 0
    failures = sum(
        int(suite.get("failures", "0")) for suite in root.findall("testsuite")
    )
    assert failures > 0, "Expected failure entries in JUnit XML for invalid rules"

    # The number of <failure> elements across all testcases must match
    # the reported failure counts in the testsuite attributes.
    for suite in root.findall("testsuite"):
        reported_failures = int(suite.get("failures", "0"))
        actual_failures = sum(
            1 for testcase in suite.findall("testcase")
            if testcase.find("failure") is not None
        )
        assert actual_failures == reported_failures
