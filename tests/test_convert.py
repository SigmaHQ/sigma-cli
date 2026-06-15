from click.testing import CliRunner
import pytest
from sigma.cli.convert import convert
import sigma.backends.test.backend


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

def test_convert_invalid_rule():
    cli = CliRunner()
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-p",
            "another_test",
            "--disable-pipeline-check",
            "tests/files/sigma_rule_without_condition.yml",
        ],
    )
    assert result.exit_code > 0
    assert "at least one condition" in result.stderr


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
        convert, ["-t", "text_query_test", "-f", "str", "-c", "test", "tests/files/valid"]
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
    assert "Invalid value for" in result.stderr
    assert "--plugin-type backend" in result.stderr


def test_convert_unknown_format():
    cli = CliRunner()
    result = cli.invoke(
        convert, ["-t", "text_query_test", "-f", "nonexisting", "tests/files/valid"]
    )
    assert "Invalid value for format" in result.stderr
    assert "sigma list formats" in result.stderr


def test_convert_unknown_pipeline():
    cli = CliRunner()
    result = cli.invoke(
        convert, ["-t", "text_query_test", "-p", "nonexisting", "tests/files/valid"]
    )
    assert "'nonexisting' was not found" in result.stderr
    assert "--plugin-type pipeline" in result.stderr


def test_convert_missing_input():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "text_query_test"])
    assert "Missing argument" in result.stderr


def test_convert_missing_pipeline():
    cli = CliRunner()
    result = cli.invoke(convert, ["-t", "mandatory_pipeline_test", "tests/files/valid"])
    assert result.exit_code > 0 and "pipeline required" in result.stderr


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
    assert result.exit_code > 0 and "'another_test' is not intended" in result.stderr


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
    assert "not format key=value" in result.stderr


def test_backend_option_invalid_type():
    cli = CliRunner()
    result = cli.invoke(
        convert, ["-t", "text_query_test", "-O", 123, "tests/files/valid"]
    )
    assert result.exit_code != 0
    assert "must be a string" in result.stderr


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
    monkeypatch.setattr(sigma.backends.test.backend.TextQueryTestBackend, "correlation_methods", None)
    cli = CliRunner()
    result = cli.invoke(
        convert, ["-t", "text_query_test", "-f", "str", "-c", "test", "tests/files/valid"]
    )
    assert result.exit_code != 0
    assert "Backend 'text_query_test' does not support correlation" in result.stderr


def test_convert_invalid_correlation_method():
    cli = CliRunner()
    result = cli.invoke(
        convert, ["-t", "text_query_test", "-f", "str", "-c", "invalid", "tests/files/valid"]
    )
    assert result.exit_code != 0
    assert "Correlation method 'invalid' is not supported" in result.stderr


def test_convert_output_dir_basic(tmp_path):
    """Test basic output to separate files in a directory."""
    cli = CliRunner()
    output_dir = tmp_path / "output"
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-p",
            "another_test",
            "--disable-pipeline-check",
            "--output-dir",
            str(output_dir),
            "tests/files/multiple_rules/rule_1.yml",
            "tests/files/multiple_rules/rule_2.yml",
        ],
    )
    assert result.exit_code == 0
    assert "Wrote 2 file(s)" in result.stderr
    
    # Check that output files exist
    assert (output_dir / "rule_1.txt").exists()
    assert (output_dir / "rule_2.txt").exists()
    
    # Check content
    content1 = (output_dir / "rule_1.txt").read_text()
    assert 'Image endswith "\\test1.exe"' in content1


def test_convert_output_dir_with_subdirs(tmp_path):
    """Test output with directory structure preserved."""
    cli = CliRunner()
    output_dir = tmp_path / "output"
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-p",
            "another_test",
            "--disable-pipeline-check",
            "--output-dir",
            str(output_dir),
            "--output-filename-template",
            "{path}/{stem}.esql",
            "tests/files/multiple_rules/",
        ],
    )
    assert result.exit_code == 0
    
    # Check that output files exist with subdirectories
    assert (output_dir / "windows" / "windows_rule.esql").exists()
    assert (output_dir / "linux" / "linux_rule.esql").exists()


def test_convert_output_dir_flat(tmp_path):
    """Test output with flat structure (no subdirs)."""
    cli = CliRunner()
    output_dir = tmp_path / "output"
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-p",
            "another_test",
            "--disable-pipeline-check",
            "--output-dir",
            str(output_dir),
            "--output-filename-template",
            "{stem}.txt",
            "tests/files/multiple_rules/",
        ],
    )
    assert result.exit_code == 0
    
    # Check that all files are in the root output directory
    assert (output_dir / "rule_1.txt").exists()
    assert (output_dir / "rule_2.txt").exists()
    assert (output_dir / "windows_rule.txt").exists()
    assert (output_dir / "linux_rule.txt").exists()


def test_convert_output_dir_mutually_exclusive(tmp_path):
    """Test that --output and --output-dir are mutually exclusive."""
    cli = CliRunner()
    output_file = tmp_path / "output.txt"
    output_dir = tmp_path / "output"
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-p",
            "another_test",
            "--disable-pipeline-check",
            "--output",
            str(output_file),
            "--output-dir",
            str(output_dir),
            "tests/files/valid",
        ],
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.stderr


def test_convert_output_dir_with_index(tmp_path):
    """Test output with index for rules that generate multiple queries."""
    cli = CliRunner()
    output_dir = tmp_path / "output"
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-p",
            "another_test",
            "--disable-pipeline-check",
            "--output-dir",
            str(output_dir),
            "--output-filename-template",
            "{stem}-{index}.txt",
            "tests/files/multiple_rules/multi_condition.yml",
        ],
    )
    assert result.exit_code == 0
    
    # Check that output files with indexes exist
    # The rule has 3 conditions, so it should generate 3 separate queries
    assert (output_dir / "multi_condition-1.txt").exists()
    assert (output_dir / "multi_condition-2.txt").exists()
    assert (output_dir / "multi_condition-3.txt").exists()


def test_convert_output_dir_with_correlation_rules(tmp_path):
    """Test that correlation rules are not supported with --output-dir."""
    cli = CliRunner()
    output_dir = tmp_path / "output"
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-c",
            "test",
            "--output-dir",
            str(output_dir),
            "tests/files/sigma_correlation_rules.yml",
        ],
    )
    # Should fail with a clear error message
    assert result.exit_code != 0
    assert "correlation" in result.stderr.lower() or "collection" in result.stderr.lower()


def test_convert_output_dir_with_filter(tmp_path):
    """Test that filters are applied correctly with --output-dir."""
    cli = CliRunner()
    output_dir = tmp_path / "output"
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "--filter",
            "tests/files/sigma_filter.yml",
            "--output-dir",
            str(output_dir),
            "tests/files/valid/sigma_rule.yml",
        ],
    )
    assert result.exit_code == 0

    # Check that output file exists
    assert (output_dir / "sigma_rule.txt").exists()
    
    # Check that filter was applied
    content = (output_dir / "sigma_rule.txt").read_text()
    assert 'not User startswith "ADM_"' in content

