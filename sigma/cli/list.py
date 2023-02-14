import click
from sigma.plugins import InstalledSigmaPlugins
from prettytable import PrettyTable
from textwrap import dedent

plugins = InstalledSigmaPlugins.autodiscover()

@click.group(name="list", help="List available targets or processing pipelines.")
def list_group():
    pass

@list_group.command(name="targets", help="List conversion target query languages.")
def list_targets():
    if len(plugins.backends) == 0:
        click.echo("No backends installed. Use " + click.style("sigma plugin list", bold=True, fg="green") + " to list available plugins.")
    else:
        table = PrettyTable()
        table.field_names = ("Identifier", "Target Query Language", "Processing Pipeline Required")
        table.add_rows([
            (name, backend.name, "Yes" if backend.requires_pipeline else "No")
            for name, backend in plugins.backends.items()
        ])
        table.align = "l"
        click.echo(table.get_string())

@list_group.command(name="formats", help="List formats supported by specified conversion backend.")
@click.argument(
    "backend",
    type=click.Choice(plugins.backends.keys()),
)
def list_formats(backend):
    table = PrettyTable()
    table.field_names = ("Format", "Description")
    table.add_rows([
        (name, description)
        for name, description in plugins.backends[backend].formats.items()
    ])
    table.align = "l"
    click.echo(table.get_string())

@list_group.command(name="pipelines", help="List processing pipelines.")
@click.argument(
    "backend",
    required=False,
    type=click.Choice(plugins.backends.keys())
)
def list_pipelines(backend):
    pipeline_resolver = plugins.get_pipeline_resolver()
    pipelines = list(pipeline_resolver.list_pipelines())
    if len(pipelines) == 0:
        click.echo("No pipelines. Use " + click.style("sigma plugin list", bold=True, fg="green") + " to list available plugins.")
    else:
        table = PrettyTable()
        table.field_names = ("Identifier", "Priority", "Processing Pipeline", "Backends")
        for name, pipeline in pipelines:
            if backend is None or backend in pipeline.allowed_backends or len(pipeline.allowed_backends) == 0:
                if len(pipeline.allowed_backends) > 0:
                    backends = ", ".join(pipeline.allowed_backends)
                else:
                    backends = "all"
                table.add_row((name, pipeline.priority, pipeline.name, backends))
        table.align = "l"
        click.echo(table.get_string())

@list_group.command(name="validators", help="List rule validators.")
def list_validators():
    table = PrettyTable(
        field_names=("Name", "Description",),
        align="l",
    )
    table.add_rows([
        (name, dedent(validator.__doc__ or "-").strip())
        for name, validator in plugins.validators.items()
    ])
    click.echo(table.get_string())