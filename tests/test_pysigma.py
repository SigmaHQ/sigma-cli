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