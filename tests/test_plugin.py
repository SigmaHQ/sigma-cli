import pytest
from click.testing import CliRunner

import sigma.cli.plugin
import sigma.plugins
from sigma.cli.plugin import (
    plugin_group,
    list_plugins,
    install_plugin,
    uninstall_plugin,
    upgrade_plugin,
)
from sigma.plugins import SigmaPlugin, SigmaPluginDirectory


def test_plugin_help():
    cli = CliRunner()
    result = cli.invoke(plugin_group, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 20


def test_plugin_list_help():
    cli = CliRunner()
    result = cli.invoke(list_plugins, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 20


def test_plugin_install_help():
    cli = CliRunner()
    result = cli.invoke(install_plugin, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 20


def test_plugin_uninstall_help():
    cli = CliRunner()
    result = cli.invoke(uninstall_plugin, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 20


def test_plugin_list():
    cli = CliRunner()
    plugin_list = cli.invoke(list_plugins)
    assert plugin_list.exit_code == 0
    assert len(plugin_list.output.split()) > 10


def test_plugin_list_filtered():
    cli = CliRunner()
    plugin_list = cli.invoke(list_plugins)
    plugin_list_filtered = cli.invoke(list_plugins, ["-t", "backend", "-s", "stable"])
    assert plugin_list.exit_code == 0
    assert plugin_list_filtered.exit_code == 0
    assert len(plugin_list.output.split()) > len(plugin_list_filtered.output.split())


def test_plugin_list_search():
    cli = CliRunner()
    plugin_list = cli.invoke(list_plugins)
    plugin_list_search = cli.invoke(list_plugins, ["Sysmon"])
    assert plugin_list.exit_code == 0
    assert plugin_list_search.exit_code == 0
    assert len(plugin_list.output.split()) > len(plugin_list_search.output.split())


def test_plugin_show_help():
    cli = CliRunner()
    result = cli.invoke(plugin_group, ["show", "--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 20


def test_plugin_show_identifier():
    cli = CliRunner()
    plugin_show = cli.invoke(plugin_group, ["show", "splunk"])
    assert plugin_show.exit_code == 0
    assert "Splunk" in plugin_show.output


def test_plugin_show_nonexisting():
    cli = CliRunner()
    plugin_show = cli.invoke(plugin_group, ["show", "notexisting"])
    assert plugin_show.exit_code != 0
    assert "error" in plugin_show.output.lower()


def test_plugin_show_uuid():
    cli = CliRunner()
    plugin_show = cli.invoke(
        plugin_group, ["show", "-u", "4af37b53-f1ec-4567-8017-2fb9315397a1"]
    )
    assert plugin_show.exit_code == 0
    assert "Splunk" in plugin_show.output


def test_plugin_install_notexisting():
    cli = CliRunner()
    result = cli.invoke(install_plugin, ["notexisting"])
    assert result.exit_code != 0
    assert "error" in result.output.lower()


def test_plugin_install():
    cli = CliRunner()
    result = cli.invoke(install_plugin, ["-f", "splunk"])
    assert result.exit_code == 0
    assert "Successfully installed" in result.output


def test_plugin_uninstall():
    cli = CliRunner()
    result = cli.invoke(uninstall_plugin, ["splunk"])
    assert result.exit_code == 0
    assert "Successfully uninstalled" in result.output


@pytest.fixture
def stubbed_plugin(monkeypatch):
    """
    An installed plugin with two releases on (stubbed) PyPI: 1.0.0 is compatible with the installed
    pySigma 1.x, 2.0.0 requires pySigma 2.x. pip calls and the pySigma check are recorded.
    """
    requirements = {
        "1.0.0": ["pysigma (>=1.0.0,<2.0.0)"],
        "2.0.0": ["pysigma (>=2.0.0,<3.0.0)"],
    }

    def fake_pypi_json(package, version=None):
        if version is None:
            return {"releases": {v: [{"file": 1}] for v in requirements}}
        return {"info": {"requires_dist": requirements[version]}}

    plugin = SigmaPlugin.from_dict(
        {
            "uuid": "00000000-0000-4000-8000-000000000001",
            "type": "backend",
            "id": "demo",
            "description": "demo",
            "package": "pysigma-backend-demo",
            "project-url": "https://example.invalid",
            "report-issue-url": "https://example.invalid",
            "state": "stable",
            "pysigma-version": ">=0.1",
        }
    )
    directory = SigmaPluginDirectory()
    directory.register_plugin(plugin)

    calls = {"pip": [], "check_pysigma": 0}

    def fake_check_call(cmd, *args, **kwargs):
        calls["pip"].append(cmd[cmd.index("install") + 1 :])

    def fake_check_pysigma():
        calls["check_pysigma"] += 1

    monkeypatch.setattr(sigma.plugins.SigmaPlugin, "_get_pypi_json", staticmethod(fake_pypi_json))
    monkeypatch.setattr(sigma.plugins.SigmaPlugin, "is_installed", lambda self: True)
    monkeypatch.setattr(sigma.plugins.subprocess, "check_call", fake_check_call)
    monkeypatch.setattr(
        sigma.cli.plugin.SigmaPluginDirectory, "default_plugin_directory", lambda *a, **k: directory
    )
    monkeypatch.setattr(sigma.cli.plugin, "check_pysigma_command", fake_check_pysigma)
    return calls


def test_plugin_upgrade_installs_compatible_release(stubbed_plugin):
    cli = CliRunner()
    result = cli.invoke(upgrade_plugin, [])
    assert result.exit_code == 0
    assert "Successfully upgrade plugin 'demo'" in result.output
    assert stubbed_plugin["pip"][-1][-1] == "pysigma-backend-demo==1.0.0"
    assert stubbed_plugin["check_pysigma"] == 1


def test_plugin_upgrade_without_compatibility_check(stubbed_plugin):
    cli = CliRunner()
    result = cli.invoke(upgrade_plugin, ["--no-compatibility-check", "--no-check-pysigma"])
    assert result.exit_code == 0
    assert "--upgrade" in stubbed_plugin["pip"][-1]
    assert stubbed_plugin["pip"][-1][-1] == "pysigma-backend-demo"
    assert stubbed_plugin["check_pysigma"] == 0
