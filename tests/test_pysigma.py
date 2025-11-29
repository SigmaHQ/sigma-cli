import importlib
import re
from sigma.cli.pysigma import pysigma_group, check_pysigma_version
from click.testing import CliRunner
import pytest

@pytest.mark.xfail(
    condition=re.match(r"^\d+\.\d+\.\d+\w+\d+$", importlib.metadata.version("pysigma")),
    reason="pysigma version is release candidate or other special version.",
)
def test_check_pysigma_version():
    assert check_pysigma_version() == True

@pytest.mark.parametrize(
        "pysigma_expected_version,pysigma_installed_version,expected_result",
        [
            ("<0.11.0,>=0.10.4", "0.10.4", True),
            ("<0.11.0,>=0.10.4", "0.11.0", False),
            ("<0.11.0,>=0.10.4", "0.10.3", False),
        ]
)
def test_check_pysigma_version_incompatible(monkeypatch, pysigma_expected_version, pysigma_installed_version, expected_result):
    monkeypatch.setattr('importlib.metadata.requires', lambda x: [f'pysigma ({pysigma_expected_version})'])
    monkeypatch.setattr('importlib.metadata.version', lambda x: pysigma_installed_version)
    assert check_pysigma_version() == expected_result

@pytest.mark.xfail(
    condition=re.match(r"^\d+\.\d+\.\d+\w+\d+$", importlib.metadata.version("pysigma")),
    reason="pysigma version is release candidate or other special version.",
)
def test_check_pysigma():
    cli = CliRunner()
    result = cli.invoke(pysigma_group, ["check-version"])
    assert "pySigma version is compatible with sigma-cli" in result.output

@pytest.mark.skip(reason="This test is not working")
def test_check_pysigma_incompatible(monkeypatch):
    monkeypatch.setattr('importlib.metadata.version', lambda x: "0.0.1")
    cli = CliRunner()
    result = cli.invoke(pysigma_group, ["check-version"], input="y\n")
    assert "pySigma version is not compatible" in result.output
    assert "pySigma successfully reinstalled" in result.output


def test_list_cache():
    """Test list-cache command shows cache information."""
    cli = CliRunner()
    result = cli.invoke(pysigma_group, ["list-cache"])
    assert result.exit_code == 0
    # Check that the output contains the expected table headers and dataset names
    assert "Dataset" in result.output
    assert "Version" in result.output
    assert "Cached Date" in result.output
    assert ("MITRE ATT&CK" in result.output or "Not cached" in result.output)


def test_clear_cache_help():
    """Test clear-cache command help."""
    cli = CliRunner()
    result = cli.invoke(pysigma_group, ["clear-cache", "--help"])
    assert result.exit_code == 0
    assert "Delete all cached data" in result.output
    assert "--yes" in result.output or "-y" in result.output


def test_clear_cache_with_confirmation_cancel():
    """Test clear-cache command cancellation."""
    cli = CliRunner()
    result = cli.invoke(pysigma_group, ["clear-cache"], input="n\n")
    assert result.exit_code == 0
    assert "cancelled" in result.output.lower() or "empty" in result.output.lower() or "No cache directory found" in result.output


def test_clear_cache_with_yes_flag():
    """Test clear-cache command with -y flag."""
    cli = CliRunner()
    result = cli.invoke(pysigma_group, ["clear-cache", "-y"])
    assert result.exit_code == 0
    assert "cleared" in result.output.lower() or "empty" in result.output.lower() or "No cache directory found" in result.output


def test_update_cache_help():
    """Test update-cache command help."""
    cli = CliRunner()
    result = cli.invoke(pysigma_group, ["update-cache", "--help"])
    assert result.exit_code == 0
    assert "Update cache" in result.output
    assert "--yes" in result.output or "-y" in result.output


def test_update_cache_with_confirmation_cancel():
    """Test update-cache command cancellation."""
    cli = CliRunner()
    result = cli.invoke(pysigma_group, ["update-cache"], input="n\n")
    assert result.exit_code == 0
    assert "cancelled" in result.output.lower()