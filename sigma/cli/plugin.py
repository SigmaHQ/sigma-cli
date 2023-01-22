import click
from sigma.plugins import SigmaPluginDirectory, SigmaPluginType, SigmaPluginState
from prettytable import PrettyTable

@click.group(name="plugin", help="pySigma plugin management (backends, processing pipelines and validators).")
def plugin_group():
    pass

@plugin_group.command(name="list", help="List installable plugins.")
@click.option("--plugin-type", "-t", type=click.Choice([ str(item) for item in SigmaPluginType ], case_sensitive=False), help="Display only plugins of given type.")
@click.option("--plugin-state", "-s", type=click.Choice([ str(item) for item in SigmaPluginState ], case_sensitive=False), help="Display only plugins with given state.")
@click.option("--compatible", "-c", is_flag=True, help="Show only plugins that are compatible with the installed pySigma version.")
def list_plugins(plugin_type : str, plugin_state : str, compatible : bool):
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

    table = PrettyTable()
    table.field_names = ("Identifier", "Type", "State", "Description", "Compatible?")
    table.add_rows([
        (plugin.id, str(plugin.type), str(plugin.state), plugin.description, compatibility_state[plugin.is_compatible()])
        for plugin in plugins.get_plugins(compatible_only=compatible, **get_plugins_args)
    ])
    table.align = "l"
    click.echo(table.get_string())