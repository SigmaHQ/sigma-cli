import click
from sigma.plugins import SigmaPluginDirectory, SigmaPluginType, SigmaPluginState, SigmaPlugin
from sigma.exceptions import SigmaPluginNotFoundError
from prettytable import PrettyTable

@click.group(name="plugin", help="pySigma plugin management (backends, processing pipelines and validators).")
def plugin_group():
    pass

@plugin_group.command(name="list", help="List installable plugins.")
@click.option("--plugin-type", "-t", type=click.Choice([ str(item) for item in SigmaPluginType ], case_sensitive=False), help="Display only plugins of given type.")
@click.option("--plugin-state", "-s", type=click.Choice([ str(item) for item in SigmaPluginState ], case_sensitive=False), help="Display only plugins with given state.")
@click.option("--compatible", "-c", is_flag=True, help="Show only plugins that are compatible with the installed pySigma version.")
@click.argument("search", default="")
def list_plugins(plugin_type : str, plugin_state : str, compatible : bool, search : str):
    plugins = SigmaPluginDirectory.default_plugin_directory()
    compatibility_state = {
        True: "yes",
        False: "no",
        None: "unknown",
    }

    get_plugins_args = dict()
    if plugin_type:
        get_plugins_args["plugin_types"] = { SigmaPluginType[ plugin_type.upper() ]}
    if plugin_state:
        get_plugins_args["plugin_states"] = { SigmaPluginState[ plugin_state.upper() ]}
    norm_search = search.lower()

    table = PrettyTable()
    table.field_names = ("Identifier", "Type", "State", "Description", "Compatible?")
    table.add_rows([
        (plugin.id, str(plugin.type), str(plugin.state), plugin.description, compatibility_state[plugin.is_compatible()])
        for plugin in plugins.get_plugins(compatible_only=compatible, **get_plugins_args)
        if norm_search in plugin.id.lower() or norm_search in plugin.description.lower()
    ])
    table.align = "l"
    click.echo(table.get_string())

def get_plugin(uuid : bool, plugin_identifier : str) -> SigmaPlugin:
    plugins = SigmaPluginDirectory.default_plugin_directory()
    try:
        if uuid:
            return plugins.get_plugin_by_uuid(plugin_identifier)
        else:
            return plugins.get_plugin_by_id(plugin_identifier)
    except SigmaPluginNotFoundError as e:
        raise click.exceptions.ClickException(str(e))

@plugin_group.command(name="install", help="Install plugin by identifier or UUID.")
@click.option("--uuid", "-u", is_flag=True, help="Install plugin by UUID.")
@click.option("--compatibility-check/--no-compatibility-check", "-c/-C", default=True, help="Enable or disable plugin compatibility check.")
@click.argument("plugin-identifier")
def install_plugin(uuid : bool, compatibility_check : bool, plugin_identifier : str):
    plugin = get_plugin(uuid, plugin_identifier)
    if not compatibility_check or plugin.is_compatible():
        plugin.install()
        click.echo(f"Successfully installed plugin '{plugin_identifier}'")
    else:
        raise click.exceptions.ClickException("Plugin not compatible with installed pySigma version!")

@plugin_group.command(name="uninstall", help="Uninstall plugin by identifier or UUID.")
@click.option("--uuid", "-u", is_flag=True, help="Uninstall plugin by UUID.")
@click.argument("plugin-identifier")
def uninstall_plugin(uuid : bool, plugin_identifier : str):
    plugin = get_plugin(uuid, plugin_identifier)
    plugin.uninstall()
    click.echo(f"Successfully uninstalled plugin '{plugin_identifier}'")