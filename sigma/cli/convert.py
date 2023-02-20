from genericpath import exists
import json
import pathlib
import textwrap
from typing import Any, Optional
import click

from sigma.conversion.base import Backend
from sigma.collection import SigmaCollection
from sigma.exceptions import SigmaError

from sigma.cli.rules import load_rules
from sigma.plugins import InstalledSigmaPlugins

plugins = InstalledSigmaPlugins.autodiscover()
backends = plugins.backends
pipelines = plugins.pipelines

class KeyValueParamType(click.ParamType):
    """
    key=value type for backend-specific options.
    """
    name = "key-value"
    def convert(self, value, param, ctx):
        if not isinstance(value, str):
            self.fail(f"Value must be a string with format key=value", param, ctx)
        try:
            k, v = value.split("=", 1)
        except ValueError:
            self.fail(f"Value '{value}' has not format key=value", param, ctx)

        try:
            return { k: int(v) }
        except ValueError:
            return { k: v }


@click.command()
@click.option(
    "--target", "-t",
    type=click.Choice(backends.keys()),
    required=True,
    help="Target query language (list targets)",
)
@click.option(
    "--pipeline", "-p",
    multiple=True,
    help="Specify processing pipelines as identifiers (list pipelines) or YAML files",
)
@click.option(
    "--without-pipeline",
    is_flag=True,
    default=False,
    help="Proceed with conversion without processing pipeline, even if it is mandatory for the target.",
)
@click.option(
    "--pipeline-check/--disable-pipeline-check",
    default=True,
    help="Verify if a pipeline is used that is intended for another backend.",
)
@click.option(
    "--format", "-f",
    default="default",
    show_default=True,
    help="Select backend output format",
)
@click.option(
    "--file-pattern", "-P",
    default="*.yml",
    show_default=True,
    help="Pattern for file names to be included in recursion into directories.",
)
@click.option(
    "--skip-unsupported/--fail-unsupported", "-s/",
    default=False,
    help="Skip conversion of rules that can't be handled by the backend",
)
@click.option(
    "--output", "-o",
    type=click.File("wb"),
    default="-",
    show_default=True,
    help="Write result to specified file. '-' writes to standard output."
)
@click.option(
    "--encoding", "-e",
    type=str,
    default="utf-8",
    show_default=True,
    help="Output encoding for string backend outputs. This is ignored for backends that return binary output."
)
@click.option(
    "--json-indent", "-j",
    type=int,
    default=None,
    help="Pretty-print and indent JSON output with given indentation width per level."
)
@click.option(
    "--backend-option",
    "-O",
    type=KeyValueParamType(),
    multiple=True,
    help="Backend-specific options provided as key=value pair.",
)
@click.argument(
    "input",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, path_type=pathlib.Path),
)
def convert(target, pipeline, without_pipeline, pipeline_check, format, skip_unsupported, output, encoding, json_indent, backend_option, input, file_pattern):
    """
    Convert Sigma rules into queries. INPUT can be multiple files or directories. This command automatically recurses
    into directories and converts all files matching the pattern in --file-pattern.
    """
    # Check if pipeline is required
    if backends[target].requires_pipeline \
        and pipeline == () \
        and not without_pipeline:
        raise click.UsageError(textwrap.dedent(f"""
        Processing pipeline required by backend! Define a custom pipeline or choose a predefined one.

        Get all available pipelines for {target} with:
           sigma list pipelines {target}

        If you never heard about processing pipelines you should get familiar with them
        (https://sigmahq-pysigma.readthedocs.io/en/latest/Processing_Pipelines.html).
        If you know what you're doing add --without-pipeline to your command line to suppress this error.
        """))

    # Check if pipelines match to backend
    pipeline_resolver = plugins.get_pipeline_resolver()
    if pipeline_check:
        resolved_pipelines = {
            p: pipeline_resolver.resolve_pipeline(p)
            for p in pipeline
        }
        wrong_pipelines = [
            id
            for id, p in resolved_pipelines.items()
            if not (len(p.allowed_backends) == 0 or target in p.allowed_backends)
        ]
        if len(wrong_pipelines) > 0:
            raise click.UsageError(textwrap.dedent(f"""
            The following pipelines are not intended to be used with the target {target}: { ", ".join(wrong_pipelines)}.
            You can list all pipelines that are intended to be used with this target with (sigms list pipelines
            {target}). If you know what you're doing and want to use this pipeline(s) in this conversion, disable this
            check with --disable-pipeline-check.
            """))

    # Merge backend options: multiple occurences of a key result in array of values
    backend_options = dict()
    for option in backend_option:
        for k, v in option.items():
            backend_options.setdefault(k, list()).append(v)
    backend_options = {
        k: (
            v[0]                # if there's only one item, return it.
            if len(v) == 1
            else v
        )
        for k, v in backend_options.items()
    }

    # Initialize processing pipeline and backend
    backend_class = backends[target]
    processing_pipeline = pipeline_resolver.resolve(pipeline)
    try:
        backend : Backend = backend_class(
            processing_pipeline=processing_pipeline,
            collect_errors=skip_unsupported,
            **backend_options
            )
    except TypeError as e:
        param = str(e).split("'")[1]
        raise click.BadParameter(f"Parameter '{param}' is not supported by backend '{target}'.", param_hint="backend_option")

    if format not in backends[target].formats.keys():
        raise click.BadParameter(f"Output format '{format}' is not supported by backend '{target}'.", param_hint="format")

    try:
        rule_collection = load_rules(input, file_pattern)
        result = backend.convert(rule_collection, format)
        if isinstance(result, str):                     # String result
            click.echo(bytes(result, encoding), output)
        elif isinstance(result, bytes):                 # Bytes result: only allow to write it to file.
            if output.isatty():
                raise click.UsageError("Backend returns binary output. Please provide output file with --output/-o.")
            else:
                click.echo(result, output)
        elif isinstance(result, list) and all((         # List of strings Concatenate with newlines in between.
                isinstance(item, str)
                for item in result
            )):
            click.echo(bytes("\n\n".join(result), encoding), output)
        elif isinstance(result, list) and all((         # List of dicts: concatenate with newline and render each result als JSON.
                isinstance(item, dict)
                for item in result
            )):
            click.echo(bytes("\n".join((
                    json.dumps(item, indent=json_indent)
                    for item in result
                )), encoding), output)
        elif isinstance(result, dict):
            click.echo(bytes(json.dumps(result, indent=json_indent), encoding))
        else:
            click.echo(f"Backend returned unexpected format {str(type(result))}", err=True)
    except SigmaError as e:
        click.echo("Error while conversion: " + str(e), err=True)

    if len(backend.errors) > 0:
        click.echo("\nIgnored errors:", err=True)
        for rule, error in backend.errors:
            click.echo(f"{str(rule.source)}: {str(error)}", err=True)