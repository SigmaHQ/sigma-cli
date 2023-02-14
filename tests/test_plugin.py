from click.testing import CliRunner

from sigma.cli.plugin import list_plugins, install_plugin, uninstall_plugin

def test_plugin_list():
    cli = CliRunner()
    plugin_list = cli.invoke(list_plugins)
    assert plugin_list.exit_code == 0
    assert len(plugin_list.output.split()) > 10

def test_plugin_list_filtered():
    cli = CliRunner()
    plugin_list = cli.invoke(list_plugins)
    plugin_list_filtered = cli.invoke(list_plugins, [ "-t", "backend", "-s", "stable"])
    assert plugin_list.exit_code == 0
    assert plugin_list_filtered.exit_code == 0
    assert len(plugin_list.output.split()) > len(plugin_list_filtered.output.split())

def test_plugin_list_search():
    cli = CliRunner()
    plugin_list = cli.invoke(list_plugins)
    plugin_list_search = cli.invoke(list_plugins, [ "Sysmon" ])
    assert plugin_list.exit_code == 0
    assert plugin_list_search.exit_code == 0
    assert len(plugin_list.output.split()) > len(plugin_list_search.output.split())

def test_plugin_install_notexisting():
    cli = CliRunner()
    result = cli.invoke(install_plugin, ["notexisting"])
    assert result.exit_code != 0
    assert "error" in result.output.lower()

def test_plugin_install():
    cli = CliRunner()
    result = cli.invoke(install_plugin, ["splunk"])
    assert result.exit_code == 0
    assert "Successfully installed" in result.output

def test_plugin_uninstall():
    cli = CliRunner()
    result = cli.invoke(uninstall_plugin, ["splunk"])
    assert result.exit_code == 0
    assert "Successfully uninstalled" in result.output