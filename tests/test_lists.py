from typing import Counter
import pytest
from click.testing import CliRunner
from sigma.cli.list import list_group, list_pipelines, list_targets, list_formats, list_validators
from sigma.plugins import InstalledSigmaPlugins

def test_list_help():
    cli = CliRunner()
    result = cli.invoke(list_group, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 20

def test_list_pipelines_help():
    cli = CliRunner()
    result = cli.invoke(list_pipelines, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 5

def test_list_targets_help():
    cli = CliRunner()
    result = cli.invoke(list_targets, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 5

def test_list_formats_help():
    cli = CliRunner()
    result = cli.invoke(list_formats, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 5

def test_list_validators_help():
    cli = CliRunner()
    result = cli.invoke(list_validators, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 5

@pytest.fixture(params=[list_targets, list_pipelines], ids=["targets", "pipelines"])
def cli_list(request):
    cli = CliRunner()
    yield cli.invoke(request.param)

def test_simple_list(cli_list):
    counts = Counter(cli_list.output)
    assert cli_list.exit_code == 0 \
        and len(cli_list.output.split()) >= 5 \
        and counts["|"] >= 6 \
        and counts["-"] >= 40

def test_format_list():
    cli = CliRunner()
    cli_list = cli.invoke(list_formats, ["test"])
    counts = Counter(cli_list.output)
    assert cli_list.exit_code == 0 \
        and len(cli_list.output.split()) >= 5 \
        and counts["|"] >= 6 \
        and counts["-"] >= 40

def test_pipeline_list_with_backend():
    cli = CliRunner()
    list_all = cli.invoke(list_pipelines).stdout.split("\n")
    list_filtered = cli.invoke(list_pipelines, ["test"]).stdout.split("\n")
    assert len(list_all) > len(list_filtered)

def test_validator_list():
    cli = CliRunner()
    plugins = InstalledSigmaPlugins.autodiscover()
    validators = plugins.validators
    result = cli.invoke(list_validators)
    assert len(result.stdout.split()) > 10
    assert all((
        validator_name in result.stdout
        for validator_name in validators.keys()
    ))