import importlib
import re
import sys
import types
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
    assert "cancelled" in result.output.lower() or "empty" in result.output.lower() or "nothing to clear" in result.output.lower() or "No cache directory found" in result.output


def test_clear_cache_with_yes_flag():
    """Test clear-cache command with -y flag."""
    cli = CliRunner()
    result = cli.invoke(pysigma_group, ["clear-cache", "-y"])
    assert result.exit_code == 0
    assert "cleared" in result.output.lower() or "empty" in result.output.lower() or "nothing to clear" in result.output.lower() or "No cache directory found" in result.output


def test_update_cache_help():
    """Test update-cache command help."""
    cli = CliRunner()
    result = cli.invoke(pysigma_group, ["update-cache", "--help"])
    assert result.exit_code == 0
    assert "Update cache" in result.output
    assert "--yes" in result.output or "-y" in result.output
    assert "--url" in result.output


def test_update_cache_with_confirmation_cancel():
    """Test update-cache command cancellation."""
    cli = CliRunner()
    result = cli.invoke(pysigma_group, ["update-cache"], input="n\n")
    assert result.exit_code == 0
    assert "cancelled" in result.output.lower()


class FakeCache:
    def __init__(self, directory):
        self.directory = str(directory)
        self._keys = []
        self._size = 0

    def iterkeys(self):
        return iter(self._keys)

    def volume(self):
        return self._size

    def seed(self, keys, size):
        self._keys = list(keys)
        self._size = size


class FakeDataset:
    def __init__(self, directory, trigger_attr):
        self.cache = FakeCache(directory)
        self.trigger_attr = trigger_attr
        self.urls = []
        self.clear_count = 0

    def _get_cache(self):
        return self.cache

    def clear_cache(self):
        self.clear_count += 1
        self.cache.seed([], 0)

    def set_url(self, url):
        self.urls.append(url)

    def __getattr__(self, name):
        if name == self.trigger_attr:
            self.cache.seed(["index"], 42)
            return {"loaded": True}
        raise AttributeError(name)


def install_fake_sigma_data(monkeypatch, tmp_path):
    attack_dataset = FakeDataset(tmp_path / "attack-cache", "mitre_attack_techniques_tactics_mapping")
    d3fend_dataset = FakeDataset(tmp_path / "d3fend-cache", "mitre_d3fend_techniques")
    fake_sigma_data = types.ModuleType("sigma.data")
    fake_sigma_data.mitre_attack = attack_dataset
    fake_sigma_data.mitre_d3fend = d3fend_dataset
    monkeypatch.setitem(sys.modules, "sigma.data", fake_sigma_data)
    return attack_dataset, d3fend_dataset


def test_update_cache_with_url_overrides(monkeypatch, tmp_path):
    cli = CliRunner()
    attack_dataset, d3fend_dataset = install_fake_sigma_data(monkeypatch, tmp_path)
    attack_path = str(tmp_path / "attack.json")
    d3fend_path = str(tmp_path / "d3fend.json")

    result = cli.invoke(
        pysigma_group,
        [
            "update-cache",
            "-y",
            "--url",
            f"mitre_attack:{attack_path}",
            "--url",
            f"mitre_d3fend:{d3fend_path}",
        ],
    )

    assert result.exit_code == 0
    assert attack_dataset.urls == [attack_path]
    assert d3fend_dataset.urls == [d3fend_path]
    assert attack_dataset.clear_count == 1
    assert d3fend_dataset.clear_count == 1
    assert "Cache updated successfully" in result.output


def test_update_cache_rejects_invalid_url_format(monkeypatch, tmp_path):
    cli = CliRunner()
    install_fake_sigma_data(monkeypatch, tmp_path)

    result = cli.invoke(
        pysigma_group,
        ["update-cache", "-y", "--url", "mitre_attack"],
    )

    assert result.exit_code != 0
    assert "dataset:url" in result.output


def test_update_cache_rejects_unknown_dataset(monkeypatch, tmp_path):
    cli = CliRunner()
    install_fake_sigma_data(monkeypatch, tmp_path)

    result = cli.invoke(
        pysigma_group,
        ["update-cache", "-y", "--url", "unknown:/tmp/dataset.json"],
    )

    assert result.exit_code != 0
    assert "unknown dataset 'unknown'" in result.output