import shutil
from click.testing import CliRunner
import pytest
from sigma.cli.convert import convert
import sigma.backends.test.backend
import os
import pathlib

def test_convert_help():
    cli = CliRunner()
    result = cli.invoke(convert, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 20


def test_convert_output_list_of_str():
    cli = CliRunner()
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-p",
            "another_test",
            "--disable-pipeline-check",
            "tests/files/valid",
        ],
    )
    assert (
        'EventID=1 and ParentImage endswith "\\httpd.exe" and Image endswith "\\cmd.exe"'
        in result.stdout
    )


def test_convert_stdin():
    cli = CliRunner()
    with open("tests/files/valid/sigma_rule.yml", "rt") as yml_file:
        input = yml_file.read()
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-p",
            "another_test",
            "--disable-pipeline-check",
            "-",
        ],
        input=input,
    )
    assert (
        'EventID=1 and ParentImage endswith "\\httpd.exe" and Image endswith "\\cmd.exe"'
        in result.stdout
    )


def test_convert_output_list_of_dict():
    cli = CliRunner()
    result = cli.invoke(
        convert, ["-t", "text_query_test", "-f", "list_of_dict", "tests/files/valid"]
    )
    assert "ParentImage" in result.stdout


def test_convert_output_list_of_dict_indent():
    cli = CliRunner()
    result_noindent = cli.invoke(
        convert, ["-t", "text_query_test", "-f", "list_of_dict", "tests/files/valid"]
    )
    result_indent = cli.invoke(
        convert,
        ["-t", "text_query_test", "-f", "list_of_dict", "-j", "2", "tests/files/valid"],
    )
    assert len(result_indent.stdout.split("\n")) > len(
        result_noindent.stdout.split("\n")
    )


def test_convert_output_str():
    cli = CliRunner()
    result = cli.invoke(
        convert,
        ["-t", "text_query_test", "-f", "str", "-c", "test", "tests/files/valid"],
    )
    assert "ParentImage" in result.stdout


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
    test_file = tmp_path / "test.bin"
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-f",
            "bytes",
            "-o",
            str(test_file),
            "tests/files/valid",
        ],
    )
    assert result.exit_code == 0
    assert "ParentImage" in open(test_file, "r").read()


def test_convert_unknown_backend():
    cli = CliRunner()
    result = cli.invoke(
        convert, ["-t", "notexisting", "-f", "foo", "tests/files/valid"]
    )
    assert "Invalid value for" in result.stdout
    assert "--plugin-type backend" in result.stdout


def test_convert_unknown_format():
    cli = CliRunner()
    result = cli.invoke(
        convert, ["-t", "text_query_test", "-f", "nonexisting", "tests/files/valid"]
    )
    assert "Invalid value for format" in result.stdout
    assert "sigma list formats" in result.stdout


def test_convert_unknown_pipeline():
    cli = CliRunner()
    result = cli.invoke(
        convert, ["-t", "text_query_test", "-p", "nonexisting", "tests/files/valid"]
    )
    assert "'nonexisting' was not found" in result.stdout
    assert "--plugin-type pipeline" in result.stdout


def test_convert_missing_input():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "text_query_test"])
    assert "Missing argument" in result.stdout


def test_convert_missing_pipeline():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "mandatory_pipeline_test", "tests/files/valid"])
    assert result.exit_code > 0 and "pipeline required" in result.stdout


def test_convert_missing_pipeline_ignore():
    cli = CliRunner()
    result = cli.invoke(
        convert,
        ["-t", "mandatory_pipeline_test", "--without-pipeline", "tests/files/valid"],
    )
    assert "ParentImage" in result.stdout


def test_convert_wrong_pipeline():
    cli = CliRunner()
    result = cli.invoke(
        convert, ["-t", "text_query_test", "-p", "another_test", "tests/files/valid"]
    )
    assert result.exit_code > 0 and "'another_test' is not intended" in result.stdout


def test_yml_pipeline_doesnt_trigger_wrong_pipeline():
    cli = CliRunner()
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-p",
            "dummy_test",
            "-p",
            "tests/files/custom_pipeline.yml",
            "tests/files/valid",
        ],
    )
    assert "some_other_string" in result.stdout


def test_backend_option_invalid_format():
    cli = CliRunner()
    result = cli.invoke(
        convert, ["-t", "text_query_test", "-O", "invalid", "tests/files/valid"]
    )
    assert result.exit_code != 0
    assert "not format key=value" in result.stdout


def test_backend_option_invalid_type():
    cli = CliRunner()
    result = cli.invoke(
        convert, ["-t", "text_query_test", "-O", 123, "tests/files/valid"]
    )
    assert result.exit_code != 0
    assert "must be a string" in result.stdout


def test_convert_output_backend_option():
    cli = CliRunner()
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-f",
            "list_of_dict",
            "-O",
            "testparam=testvalue",
            "tests/files/valid",
        ],
    )
    assert "testvalue" in result.stdout


def test_convert_output_backend_option_list():
    cli = CliRunner()
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-f",
            "list_of_dict",
            "-O",
            "testparam=123",
            "-O",
            "testparam=test",
            "tests/files/valid",
        ],
    )
    assert '[123, "test"]' in result.stdout


def test_convert_correlation_method_without_backend_correlation_support(monkeypatch):
    monkeypatch.setattr(
        sigma.backends.test.backend.TextQueryTestBackend, "correlation_methods", None
    )
    cli = CliRunner()
    result = cli.invoke(
        convert,
        ["-t", "text_query_test", "-f", "str", "-c", "test", "tests/files/valid"],
    )
    assert result.exit_code != 0
    assert "Backend 'text_query_test' does not support correlation" in result.stdout


def test_convert_invalid_correlation_method():
    cli = CliRunner()
    result = cli.invoke(
        convert,
        ["-t", "text_query_test", "-f", "str", "-c", "invalid", "tests/files/valid"],
    )
    assert result.exit_code != 0
    assert "Correlation method 'invalid' is not supported" in result.stdout


def test_convert_correlation_rule_to_output_dir(tmp_path: pathlib.Path):
    """Tests if the correct output directory is created and that multiple translated rules are stored in individual files within one single directory."""
    cli = CliRunner()

    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "tests/files/valid/correlation_rule.yml",
            "--output-dir",
            tmp_path,
        ],
    )
    assert result.exit_code == 0
    assert tmp_path.exists(), f"{tmp_path} was not created"
    assert tmp_path.is_dir(), f"{tmp_path} is no directory"
    assert (tmp_path / "correlation_rule.yml").exists(), "rule file was not created"


def test_convert_write_to_output_dir(tmp_path: pathlib.Path):
    """Tests if the correct output directory is created and that multiple translated rules are stored in individual files within one single directory."""
    cli = CliRunner()

    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "tests/files/valid/",
            "--output-dir",
            tmp_path,
        ],
    )
    assert result.exit_code == 0
    assert tmp_path.exists(), f"{tmp_path} was not created"
    assert tmp_path.is_dir(), f"{tmp_path} is no directory"
    assert (tmp_path / "sigma_rule.yml").exists(), "rule file was not created"


def test_convert_write_to_output_dir_two_nesting_level(tmp_path: pathlib.Path):
    """Tests if the correct output directory is created and that multiple translated rules are stored in individual files, keeping the original directory structure.
    (e.g. group_one/sigma_rule.yml, group_two/another_sigma_rule.yml)
    """
    cli = CliRunner()

    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "tests/files/nested_rules",
            "--output-dir",
            tmp_path,
            "--nesting-level",
            "2",
        ],
    )
    assert result.exit_code == 0
    assert tmp_path.exists(), f"general output directory {tmp_path} was not created"
    dir_rule_files_group_one = tmp_path / "group_one"
    dir_rule_files_group_two = tmp_path / "group_two"
    assert (
        dir_rule_files_group_one.exists()
    ), f"sub-directory {dir_rule_files_group_one} was not created"
    assert (
        dir_rule_files_group_two.exists()
    ), f"sub-directory {dir_rule_files_group_two} was not created"

    path_rule_file_one = dir_rule_files_group_one / "sigma_rule.yml"
    path_rule_file_two = dir_rule_files_group_two / "another_sigma_rule.yml"

    assert (
        path_rule_file_one.exists()
    ), f"rule file {path_rule_file_one} was not created"
    assert (
        path_rule_file_two.exists()
    ), f"rule file {path_rule_file_two} was not created"
