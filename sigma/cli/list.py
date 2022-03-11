import click
from .backends import backends
from .pipelines import pipelines
from prettytable import PrettyTable

@click.group(name="list", help="List available targets or processing pipelines.")
def list_group():
    pass

@list_group.command(name="targets", help="List conversion target query languages.")
def list_targets():
    table = PrettyTable()
    table.field_names = ("Identifier", "Target Query Language")
    table.add_rows([
        (name, backend.text)
        for name, backend in backends.items()
    ])
    table.align = "l"
    click.echo(table.get_string())

@list_group.command(name="formats", help="List formats supported by specified conversion backend.")
@click.argument(
    "backend",
    type=click.Choice(backends.keys()),
)
def list_formats(backend):
    table = PrettyTable()
    table.field_names = ("Format", "Description")
    table.add_rows([
        (name, description)
        for name, description in backends[backend].formats.items()
    ])
    table.align = "l"
    click.echo(table.get_string())

@list_group.command(name="pipelines", help="List processing pipelines.")
def list_pipelines():
    table = PrettyTable()
    table.field_names = ("Identifier", "Priority", "Processing Pipeline")
    for name in pipelines.pipelines.keys():
        pipeline = pipelines.resolve_pipeline(name)
        table.add_row((name, pipeline.priority, pipeline.name))
    table.align = "l"
    click.echo(table.get_string())