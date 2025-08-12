from click.testing import CliRunner

from sigma.cli.plugin import (
    plugin_group,
    list_plugins,
    install_plugin,
    uninstall_plugin,
)


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
