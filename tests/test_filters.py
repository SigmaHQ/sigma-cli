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
            "-",
        ],
        input=input,
    )
    assert (
            'ParentImage endswith "\\httpd.exe" and Image endswith "\\cmd.exe" and not User startswith "ADM_"\n'
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

    assert 'some_other_string endswith "\\httpd.exe" and Image endswith "\\cmd.exe" and not username startswith "ADM_"\n' in result.stdout



# def test_filter_with_correlation_rules():
#     cli = CliRunner(
#         mix_stderr=True
#     )
#     result = cli.invoke(
#         convert, [
#
#             "-t",
#             "text_query_test",
#             "-p",
#             "tests/files/custom_pipeline.yml",
#             "--filter",
#             "tests/files/sigma_filter.yml",
#             "./tests/files/valid/sigma_correlation_rules.yml"
#         ],
#     )
#
#     assert 'some_other_string endswith "\\httpd.exe" and Image endswith "\\cmd.exe" and not username startswith "ADM_"\n' in result.stdout
