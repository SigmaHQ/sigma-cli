from typing import List
import click
from sigma.plugins import (
    SigmaPluginDirectory,
    SigmaPluginType,
    SigmaPluginState,
    SigmaPlugin,
)
from sigma.exceptions import SigmaPluginNotFoundError
from prettytable import PrettyTable
from textwrap import fill

from sigma.cli.pysigma import check_pysigma as check_pysigma_command


@click.group(
    name="plugin",
    help="pySigma plugin management (backends, processing pipelines and validators).",
)
def plugin_group():
    pass


@plugin_group.command(name="list", help="List installable plugins.")
@click.option(
    "--plugin-type",
    "-t",
    type=click.Choice([str(item) for item in SigmaPluginType], case_sensitive=False),
    help="Display only plugins of given type.",
)
@click.option(
    "--plugin-state",
    "-s",
    type=click.Choice([str(item) for item in SigmaPluginState], case_sensitive=False),
    help="Display only plugins with given state.",
)
@click.option(
    "--compatible",
    "-c",
    is_flag=True,
    help="Show only plugins that are compatible with the installed pySigma version.",
)
@click.argument("search", default="")
def list_plugins(plugin_type: str, plugin_state: str, compatible: bool, search: str):
    plugins = SigmaPluginDirectory.default_plugin_directory()
    compatibility_state = {
        True: "yes",
        False: "no",
        None: "unknown",
    }

    get_plugins_args = dict()
    if plugin_type:
        get_plugins_args["plugin_types"] = {SigmaPluginType[plugin_type.upper()]}
    if plugin_state:
        get_plugins_args["plugin_states"] = {SigmaPluginState[plugin_state.upper()]}
    norm_search = search.lower()

    table = PrettyTable()
    table.field_names = ("Identifier", "Type", "State", "Description", "Compatible?", "Capabilities")
    table.add_rows(
        [
            (
                plugin.id,
                str(plugin.type),
                str(plugin.state),
                fill(plugin.description, width=60),
                compatibility_state[plugin.is_compatible()],
                len(plugin.capabilities),
            )
            for plugin in plugins.get_plugins(
                compatible_only=compatible, **get_plugins_args
            )
            if norm_search in plugin.id.lower()
            or norm_search in plugin.description.lower()
        ]
    )
    table.align = "l"
    click.echo(table.get_string())


def get_plugin(uuid: bool, plugin_identifier: str) -> SigmaPlugin:
    plugins = SigmaPluginDirectory.default_plugin_directory()
    try:
        if uuid:
            return plugins.get_plugin_by_uuid(plugin_identifier)
        else:
            return plugins.get_plugin_by_id(plugin_identifier)
    except SigmaPluginNotFoundError as e:
        raise click.exceptions.ClickException(str(e))


# Display plugin details
@plugin_group.command(name="show", help="Show details about plugin.")
@click.option("--uuid", "-u", is_flag=True, help="Show plugin by UUID.")
@click.argument("plugin-identifier")
def show_plugin(uuid: bool, plugin_identifier: str):
    plugin = get_plugin(uuid, plugin_identifier)
    table = PrettyTable()
    table.field_names = ("Property", "Value")
    table.add_rows(
        [
            ("Identifier", plugin.id),
            ("UUID", plugin.uuid),
            ("Type", str(plugin.type)),
            ("State", str(plugin.state)),
            ("Package", plugin.package),
            ("Description", fill(plugin.description, width=60)),
            ("Required pySigma version", plugin.pysigma_version),
            ("Compatible?", plugin.is_compatible()),
            ("Capabilities", "\n".join(str(capability) for capability in plugin.capabilities)),
            ("Project URL", plugin.project_url),
            ("Report Issue URL", plugin.report_issue_url),
        ]
    )
    table.align = "l"
    click.echo(table.get_string())


@plugin_group.command(name="install", help="Install plugin by identifier or UUID.")
@click.option("--uuid", "-u", is_flag=True, help="Install plugin by UUID.")
@click.option(
    "--compatibility-check/--force-install",
    "-c/-f",
    default=True,
    help="Enable or disable plugin compatibility check.",
)
@click.option(
    "--check-pysigma/--no-check-pysigma",
    "-l/-L",
    default=True,
    help="Check after plugin installation if pySigma version is still matching the CLI requirement.",
)
@click.argument("plugin-identifiers", nargs=-1)
def install_plugin(
    uuid: bool, compatibility_check: bool, check_pysigma: bool, plugin_identifiers: List[str]
):
    for plugin_identifier in plugin_identifiers:
        plugin = get_plugin(uuid, plugin_identifier)
        if not compatibility_check or plugin.is_compatible():
            plugin.install()
            click.echo(f"Successfully installed plugin '{plugin_identifier}'")
        else:
            raise click.exceptions.ClickException(
                "Plugin not compatible with installed pySigma version! " + click.style("Use '--force-install' or its shortcut '-f' to install anyway.", fg="green")
            )
    
    if check_pysigma:
        check_pysigma_command()

@plugin_group.command(name="upgrade", help="Upgrade installed plugin.")
@click.option(
    "--compatibility-check/--no-compatibility-check",
    "-c/-C",
    default=True,
    help="Enable or disable plugin compatibility check.",
)
def upgrade_plugin(compatibility_check: bool):
    plugins_dir = SigmaPluginDirectory.default_plugin_directory()
    for plugin_id in plugins_dir.plugins:
        plugin = plugins_dir.get_plugin_by_uuid(uuid=plugin_id)
        if plugin.is_installed():
            if not compatibility_check or plugin.is_compatible():
                plugin.upgrade()
                click.echo(f"Successfully upgrade plugin '{plugin.id}'")
            else:
                click.echo(
                    f"Plugin '{plugin.id}' not compatible with installed pySigma version"
                )


@plugin_group.command(name="uninstall", help="Uninstall plugin by identifier or UUID.")
@click.option("--uuid", "-u", is_flag=True, help="Uninstall plugin by UUID.")
@click.argument("plugin-identifiers", nargs=-1)
def uninstall_plugin(uuid: bool, plugin_identifiers: List[str]):
    for plugin_identifier in plugin_identifiers:
        plugin = get_plugin(uuid, plugin_identifier)
        plugin.uninstall()
        click.echo(f"Successfully uninstalled plugin '{plugin_identifier}'")


# Report issue in plugin by opening the issue reporting URL in the default browser
@plugin_group.command(
    name="report-issue",
    help="Report issue in plugin by opening the issue reporting URL in the default browser.",
)
@click.option("--uuid", "-u", is_flag=True, help="Report issue in plugin by UUID.")
@click.argument("plugin-identifier")
def report_issue(uuid: bool, plugin_identifier: str):
    plugin = get_plugin(uuid, plugin_identifier)
    if plugin.report_issue_url:
        click.launch(plugin.report_issue_url)
    else:
        raise click.exceptions.ClickException(
            "Plugin does not have an issue reporting URL!"
        )
