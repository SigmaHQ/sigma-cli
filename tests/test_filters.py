from click.testing import CliRunner

from sigma.cli.convert import convert


def test_filter_basic_operation():
    cli = CliRunner(
        mix_stderr=True
    )
    result = cli.invoke(
        convert, ["-t", "text_query_test", "--filter", "tests/files/sigma_filter.yml", "tests/files/valid/sigma_rule.yml"],
    )
    assert 'ParentImage endswith "\\httpd.exe" and Image endswith "\\cmd.exe" and not User startswith "ADM_"\n' in result.stdout


def test_filter_basic_from_stdin():
    cli = CliRunner()
    with open("tests/files/valid/sigma_rule.yml", "rt") as yml_file:
        input = yml_file.read()
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "--filter",
            "tests/files/sigma_filter.yml",
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


def test_filter_with_pipeline_mapping():
    cli = CliRunner(
        mix_stderr=True
    )
    result = cli.invoke(
        convert, [
            "-t",
            "text_query_test",
            "-p",
            "tests/files/custom_pipeline.yml",
            "--filter",
            "tests/files/sigma_filter.yml",
            "tests/files/valid/sigma_rule.yml"
        ],
    )

    assert 'some_other_string endswith "\\httpd.exe" and Image endswith "\\cmd.exe" and not User="Admin"\n' in result.stdout
