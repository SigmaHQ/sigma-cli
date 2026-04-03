import click
from sigma.plugins import InstalledSigmaPlugins
from sigma.modifiers import modifier_mapping
from sigma.processing.transformations import transformations
from sigma.processing.conditions import (
    rule_conditions,
    detection_item_conditions,
    field_name_conditions,
)
from prettytable import PrettyTable
from textwrap import dedent, fill

plugins = InstalledSigmaPlugins.autodiscover()


def _plugin_id_from_module(module_name: str, namespace: str) -> str:
    """Extract the Sigma plugin identifier from a module name.

    Sigma backends live in ``sigma.backends.<plugin_id>.*`` and pipelines in
    ``sigma.pipelines.<plugin_id>.*``.  Splitting on '.' and picking the
    component after the namespace prefix returns the plugin identifier directly
    (e.g. ``sigma.backends.splunk.backend`` → ``splunk``).
    """
    parts = module_name.split(".")
    # Expected layout: sigma . <namespace> . <plugin_id> [. submodule ...]
    try:
        idx = parts.index(namespace)
        plugin_id = parts[idx + 1]
        return plugin_id if plugin_id else "n/a"
    except (ValueError, IndexError):
        return "n/a"


def _get_backend_plugin_id(backend_class) -> str:
    """Return the Sigma plugin identifier for a backend class."""
    return _plugin_id_from_module(backend_class.__module__, "backends")


def _get_pipeline_plugin_id(pipeline_obj) -> str:
    """Return the Sigma plugin identifier for a pipeline object or function."""
    # Plain function: use its own module
    module_name = getattr(pipeline_obj, "__module__", None)
    if module_name and module_name != "sigma.pipelines.base":
        return _plugin_id_from_module(module_name, "pipelines")
    # Pipeline-decorator instance: retrieve the wrapped function's module
    func = getattr(pipeline_obj, "func", None)
    if func is not None:
        func_module = getattr(func, "__module__", None)
        if func_module:
            return _plugin_id_from_module(func_module, "pipelines")
    return "n/a"


# Pre-compute plugin IDs for all discovered pipelines (keyed by identifier).
# This must be done before the resolver resolves pipeline callables into plain
# ProcessingPipeline objects, which no longer carry module information.
_pipeline_plugin_ids: dict = {
    name: _get_pipeline_plugin_id(pipeline)
    for name, pipeline in plugins.pipelines.items()
}


@click.group(name="list", help="List available targets or processing pipelines.")
def list_group():
    pass


@list_group.command(name="targets", help="List conversion target query languages.")
def list_targets():
    if len(plugins.backends) == 0:
        click.echo(
            "No backends installed. Use "
            + click.style("sigma plugin list", bold=True, fg="green")
            + " to list available plugins."
        )
    else:
        table = PrettyTable()
        table.field_names = (
            "Identifier",
            "Target Query Language",
            "Processing Pipeline Required",
            "Plugin",
        )
        table.add_rows(
            [
                (
                    name,
                    fill(backend.name, width=60),
                    "Yes" if backend.requires_pipeline else "No",
                    _get_backend_plugin_id(backend),
                )
                for name, backend in plugins.backends.items()
            ]
        )
        table.align = "l"
        click.echo(table.get_string())


@list_group.command(
    name="formats", help="List formats supported by specified conversion backend."
)
@click.argument(
    "backend",
    type=click.Choice(plugins.backends.keys()),
)
def list_formats(backend):
    table = PrettyTable()
    table.field_names = ("Format", "Description")
    table.add_rows(
        [
            (name, fill(description, width=60))
            for name, description in plugins.backends[backend].formats.items()
        ]
    )
    table.align = "l"
    click.echo(table.get_string())

@list_group.command(
    name="correlation-methods", help="List correlation methods supported by specified backend."
)
@click.argument(
    "backend",
    type=click.Choice(plugins.backends.keys()),
)
def list_correlation_methods(backend):
    correlation_methods = plugins.backends[backend].correlation_methods
    if correlation_methods is None:
        click.echo("No correlation supported by specified backend.")
    else:
        table = PrettyTable()
        table.field_names = ("Method", "Description")
        table.add_rows(
            [
                (name, fill(description, width=60))
                for name, description in correlation_methods.items()
            ]
        )
        table.align = "l"
        click.echo(table.get_string())


@list_group.command(name="pipelines", help="List processing pipelines.")
@click.argument("backend", required=False, type=click.Choice(plugins.backends.keys()))
def list_pipelines(backend):
    pipeline_resolver = plugins.get_pipeline_resolver()
    pipelines = list(pipeline_resolver.list_pipelines())
    if len(pipelines) == 0:
        click.echo(
            "No pipelines. Use "
            + click.style("sigma plugin list", bold=True, fg="green")
            + " to list available plugins."
        )
    else:
        table = PrettyTable()
        table.field_names = (
            "Identifier",
            "Priority",
            "Processing Pipeline",
            "Backends",
            "Plugin",
        )
        for name, pipeline in pipelines:
            if (
                backend is None
                or backend in pipeline.allowed_backends
                or len(pipeline.allowed_backends) == 0
            ):
                if len(pipeline.allowed_backends) > 0:
                    backends = ", ".join(pipeline.allowed_backends)
                else:
                    backends = "all"
                table.add_row(
                    (
                        name,
                        pipeline.priority,
                        fill(pipeline.name, width=60),
                        backends,
                        _pipeline_plugin_ids.get(name, "n/a"),
                    )
                )
        table.align = "l"
        click.echo(table.get_string())


@list_group.command(name="validators", help="List rule validators.")
def list_validators():
    table = PrettyTable(
        field_names=(
            "Name",
            "Description",
        ),
        align="l",
    )
    table.add_rows(
        [
            (name, fill(dedent(validator.__doc__ or "-").strip(), width=60))
            for name, validator in plugins.validators.items()
        ]
    )
    click.echo(table.get_string())


@list_group.command(name="modifiers", help="List Sigma rule value modifiers.")
def list_modifiers():
    table = PrettyTable(
        field_names=(
            "Modifier",
            "Description",
        ),
        align="l",
    )
    modifier_classes = []
    for cls in modifier_mapping.values():
        if not cls in modifier_classes:
            modifier_classes.append(cls)
    modifiers = [
        (
            " / ".join(
                modifier for modifier, c in modifier_mapping.items() if c == cls
            ),
            cls,
        )
        for cls in modifier_classes
    ]
    table.add_rows(
        [
            (modifier, fill(dedent(cls.__doc__ or "-").strip(), width=60))
            for modifier, cls in modifiers  # modifier_mapping.items()
        ]
    )
    click.echo(table.get_string())


@list_group.command(
    name="transformations", help="List processing pipeline transformations."
)
def list_transformations():
    table = PrettyTable(
        field_names=(
            "Transformation",
            "Description",
        ),
        align="l",
    )
    table.add_rows(
        [
            (name, fill(dedent(cls.__doc__ or "-").strip(), width=60))
            for name, cls in transformations.items()
        ]
    )
    click.echo(table.get_string())


@list_group.command(name="conditions", help="List processing pipeline conditions.")
def list_conditions():
    table = PrettyTable(
        field_names=(
            "Type",
            "Condition",
            "Description",
        ),
        align="l",
    )
    table.add_rows(
        [
            ("Rule", name, fill(dedent(cls.__doc__ or "-").strip(), width=60))
            for name, cls in rule_conditions.items()
        ]
    )
    table.add_rows(
        [
            ("Detection Item", name, fill(dedent(cls.__doc__ or "-").strip(), width=60))
            for name, cls in detection_item_conditions.items()
        ]
    )
    table.add_rows(
        [
            ("Field Name", name, fill(dedent(cls.__doc__ or "-").strip(), width=60))
            for name, cls in field_name_conditions.items()
        ]
    )
    click.echo(table.get_string())
