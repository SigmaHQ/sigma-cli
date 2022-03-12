from genericpath import exists
import pathlib
import click

from sigma.conversion.base import Backend
from sigma.collection import SigmaCollection
from sigma.exceptions import SigmaError
from .backends import backends
from .pipelines import pipelines

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
    type=click.File("w"),
    default="-",
    show_default=True,
    help="Write result to specified file. '-' writes to standard output."
)
@click.argument(
    "input",
    nargs=-1,
    type=click.Path(exists=True, path_type=pathlib.Path),
)
def convert(target, pipeline, format, skip_unsupported, output, input, file_pattern):
    """
    Convert Sigma rules into queries. INPUT can be multiple files or directories. This command automatically recurses
    into directories and converts all files matching the pattern in --file-pattern.
    """
    # Initialize processing pipeline and backend
    backend_class = backends[target].cls
    processing_pipeline = pipelines.resolve(pipeline)
    backend : Backend = backend_class(
        processing_pipeline=processing_pipeline,
        collect_errors=skip_unsupported,
        )

    if format not in backends[target].formats.keys():
        raise click.BadParameter(f"Output format '{format}' is not supported by backend '{target}'.", param_hint="format")

    try:
        rule_collection = SigmaCollection.load_ruleset(input, recursion_pattern="**/" + file_pattern)
        result = backend.convert(rule_collection, format)
        if isinstance(result, str):
            click.echo(result, output)
        else:
            click.echo("\n\n".join(result), output)
    except SigmaError as e:
        click.echo("Error while conversion: " + str(e), err=True)