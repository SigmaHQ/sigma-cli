import click
from .backends import backends
from .pipelines import pipelines, pipeline_resolver
from prettytable import PrettyTable

@click.group(name="list", help="List available targets or processing pipelines.")
def list_group():
    pass

@list_group.command(name="targets", help="List conversion target query languages.")
def list_targets():
    table = PrettyTable()
    table.field_names = ("Identifier", "Target Query Language", "Processing Pipeline Required")
    table.add_rows([
        (name, backend.text, "Yes" if backend.requires_pipeline else "No")
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
@click.argument(
    "backend",
    required=False,
    type=click.Choice(backends.keys())
)
def list_pipelines(backend):
    table = PrettyTable()
    table.field_names = ("Identifier", "Priority", "Processing Pipeline", "Backends")
    for name, definition in pipelines.items():
        if backend is None or backend in definition.backends or len(definition.backends) == 0:
            pipeline = pipeline_resolver.resolve_pipeline(name)
            if len(definition.backends) > 0:
                backends = ", ".join(definition.backends)
            else:
                backends = "all"
            table.add_row((name, pipeline.priority, pipeline.name, backends))
    table.align = "l"
    click.echo(table.get_string())