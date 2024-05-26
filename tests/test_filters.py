from click.testing import CliRunner
import pytest
from sigma.cli.convert import convert
import sigma.backends.test.backend


def test_filter_basic_operation():
    cli = CliRunner(
        mix_stderr=True
    )
    result = cli.invoke(
        convert, ["-t", "text_query_test", "-e", "tests/files/valid/sigma_filter.yml", "tests/files/valid/sigma_rule.yml"],
    )
    assert "Correlation method 'invalid' is not supported" in result.stdout