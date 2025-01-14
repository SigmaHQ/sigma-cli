import json
import pathlib
import textwrap
import os
from typing import Sequence

import click

from sigma.cli.rules import load_rules
from sigma.conversion.base import Backend
from sigma.collection import SigmaCollection
from sigma.exceptions import (
    SigmaError,
    SigmaPipelineNotAllowedForBackendError,
    SigmaPipelineNotFoundError,
)
from sigma.plugins import InstalledSigmaPlugins

plugins = InstalledSigmaPlugins.autodiscover()
backends = plugins.backends
pipelines = plugins.pipelines
pipeline_resolver = plugins.get_pipeline_resolver()
pipeline_list = list(pipeline_resolver.pipelines.keys())


def ensure_dir_exists(ctx, param, value):
    if value is None:
        return value
    # Split the path into its components
    path_parts = value.split(os.sep)
    current_path = ""

    for part in path_parts:
        current_path = os.path.join(current_path, part)

        # Check if the current path exists
        if not os.path.exists(current_path):
            # If it doesn't exist, create it
            click.echo(f"Creating specified output directory '{current_path}'")
            os.makedirs(current_path, exist_ok=True)
        elif not os.path.isdir(current_path):
            # If it exists but is not a directory, raise an error
            raise NotADirectoryError(
                f"Cannot create directory '{current_path}' because a file with the same name exists."
            )

    return value


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
            return {k: int(v)}
        except ValueError:
            return {k: v}


class ChoiceWithPluginHint(click.Choice):
    """Custom base class that shows a command line for listing the appropriate plugins if user tries to use an unknown
    backend or pipeline."""

    def __init__(
        self, choices: Sequence[str], plugin_type: str, case_sensitive: bool = True
    ) -> None:
        self.plugin_type = plugin_type
        super().__init__(choices, case_sensitive)

    def fail(self, message: str, param, ctx):
        return super().fail(
            message
            + " - run "
            + click.style(
                f"sigma plugin list --plugin-type {self.plugin_type}",
                bold=True,
                fg="green",
            )
            + " for a list of available plugins.",
            param,
            ctx,
        )


@click.command()
@click.option(
    "--target",
    "-t",
    type=ChoiceWithPluginHint(backends.keys(), "backend"),
    required=True,
    help="Target query language ("
    + click.style("sigma list targets", bold=True, fg="green")
    + ")",
)
@click.option(
    "--pipeline",
    "-p",
    multiple=True,
    help="Specify processing pipelines as identifiers ("
    + click.style("sigma list pipelines", bold=True, fg="green")
    + ") or YAML files or directories",
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
    "--format",
    "-f",
    default="default",
    show_default=True,
    help="Select backend output format",
)
@click.option(
    "--correlation-method",
    "-c",
    help="Select method for generation of correlation queries. If not given the default method of the backend is used.",
)
@click.option(
    "--filter",
    multiple=True,
    type=click.Path(exists=True, allow_dash=True, path_type=pathlib.Path),
    help="Select filters/exclusions to apply to the rules. Multiple Sigma meta filters can be applied.",
)
@click.option(
    "--file-pattern",
    "-P",
    default="*.yml",
    show_default=True,
    help="Pattern for file names to be included in recursion into directories.",
)
@click.option(
    "--skip-unsupported/--fail-unsupported",
    "-s/",
    default=False,
    help="Skip conversion of rules that can't be handled by the backend.",
)
@click.option(
    "--output",
    "-o",
    type=click.File("wb"),
    default="-",
    show_default=True,
    help="Write result to specified file. '-' writes to standard output.",
)
@click.option(
    "--output-dir",
    "-od",
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, exists=False, resolve_path=False
    ),
    default=None,
    show_default=True,
    help="Write result in INDIVIDUAL files for each rule in specified directory.",
    callback=ensure_dir_exists,
)
@click.option(
    "--nesting-level",
    "-nl",
    type=int,
    default=1,
    show_default=True,
    help="To be used in combination with --output-dir. \n While writing results in individual files for each rule in the specified directory, the original hierarchical structure of the rule files is conserved for the specified levels.",
)
@click.option(
    "--encoding",
    "-e",
    type=str,
    default="utf-8",
    show_default=True,
    help="Output encoding for string backend outputs. This is ignored for backends that return binary output.",
)
@click.option(
    "--json-indent",
    "-j",
    type=int,
    default=None,
    help="Pretty-print and indent JSON output with given indentation width per level.",
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
    type=click.Path(exists=True, allow_dash=True, path_type=pathlib.Path),
)
@click.option(
    "--verbose",
    required=False,
    is_flag=True,
    default=False,
    type=click.BOOL,
    help="Verbose output.",
)

def convert(
    target,
    pipeline,
    without_pipeline,
    pipeline_check,
    format,
    correlation_method,
    filter,
    skip_unsupported,
    output,
    encoding,
    json_indent,
    backend_option,
    input,
    file_pattern,
    verbose,
    output_dir,
    nesting_level,
):
    """
    Convert Sigma rules into queries. INPUT can be multiple files or directories. This command automatically recurses
    into directories and converts all files matching the pattern in --file-pattern.
    """

    # Check if pipeline is required
    if backends[target].requires_pipeline and pipeline == () and not without_pipeline:
        raise click.UsageError(
            textwrap.dedent(
                f"""
        Processing pipeline required by backend! Define a custom pipeline or choose a predefined one.

        Get all available pipelines for {target} with:
        """
                + click.style(f"sigma list pipelines {target}", bold=True, fg="green")
                + """

        If you never heard about processing pipelines you should get familiar with them
        (https://sigmahq-pysigma.readthedocs.io/en/latest/Processing_Pipelines.html).
        If you know what you're doing add --without-pipeline to your command line to suppress this error.
        """
            )
        )

    # Merge backend options: multiple occurences of a key result in array of values
    backend_options = dict()
    for option in backend_option:
        for k, v in option.items():
            backend_options.setdefault(k, list()).append(v)
    backend_options = {
        k: (v[0] if len(v) == 1 else v)  # if there's only one item, return it.
        for k, v in backend_options.items()
    }
    # Initialize processing pipeline and backend
    backend_class = backends[target]
    try:
        processing_pipeline = pipeline_resolver.resolve(
            pipeline, target if pipeline_check else None
        )
    except SigmaPipelineNotFoundError as e:
        raise click.UsageError(
            f"The pipeline '{e.spec}' was not found.\n"
            + "List all installed processing pipelines with: "
            + click.style(f"sigma list pipelines {target}", bold=True, fg="green")
            + "\n"
            "List pipeline plugins for installation with: "
            + click.style(
                f"sigma plugin list --plugin-type pipeline", bold=True, fg="green"
            )
            + "\n"
            + "Pipelines not listed here are treated as file names."
        )
    except SigmaPipelineNotAllowedForBackendError as e:
        raise click.UsageError(
            textwrap.dedent(
                f"""
        The pipeline '{e.wrong_pipeline}' is not intended to be used with the target {target}.
        You can list all pipelines that are intended to be used with this target with """
                + click.style(f"sigma list pipelines {target}", bold=True, fg="green")
                + """.
        If you know what you're doing and want to use this pipeline(s) in this conversion, disable this
        check with --disable-pipeline-check.
        """
            )
        )

    try:
        backend: Backend = backend_class(
            processing_pipeline=processing_pipeline,
            collect_errors=skip_unsupported,
            **backend_options,
        )
    except TypeError as e:
        param = str(e).split("'")[1]
        raise click.BadParameter(
            f"Parameter '{param}' is not supported by backend '{target}'.",
            param_hint="backend_option",
        )
    if format not in backends[target].formats.keys():
        raise click.BadParameter(
            f"Output format '{format}' is not supported by backend '{target}'. Run "
            + click.style(f"sigma list formats {target}", bold=True, fg="green")
            + " to list all available formats of the target.",
            param_hint="format",
        )

    if correlation_method is not None:
        correlation_methods = backend.correlation_methods
        if correlation_methods is None:
            raise click.BadParameter(
                f"Backend '{target}' does not support correlations but correlation method was provided on command line.",
                param_hint="correlation_method",
            )
        elif correlation_method not in correlation_methods.keys():
            raise click.BadParameter(
                f"Correlation method '{correlation_method}' is not supported by backend '{target}'. Run "
                + click.style(
                    f"sigma list correlation-methods {target}", bold=True, fg="green"
                )
                + " to list all available correlation methods of the target.",
                param_hint="correlation_method",
            )

    try:
        rule_collection = load_rules(input + filter, file_pattern)
        result = backend.convert(rule_collection, format, correlation_method)
        if output_dir:
            writes_successful = True

            # Collect all Paths for Rules
            all_paths = []
            for dir_path in input:
                all_paths.extend(
                    list(
                        SigmaCollection.resolve_paths(
                            [dir_path],
                            recursion_pattern="**/" + file_pattern,
                        )
                    )
                )
            for index, path_of_input in enumerate(all_paths):
                original_path_part_to_keep = os.path.sep.join(
                    path_of_input.parts[-nesting_level:]
                )

                try:
                    out_path = os.path.join(output_dir, original_path_part_to_keep)
                    ensure_dir_exists(
                        ctx=None, param=None, value=os.path.dirname(out_path)
                    )
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(result[index])
                except Exception as ex:
                    click.echo(
                        f"Could not write translated rules into output-dir {output_dir}: \n {ex}"
                    )
                    writes_successful = False
            if writes_successful:
                click.echo(
                    f"Written {len(result)} translated rule(s) into individual files in specified output-dir '{output_dir}'"
                )
            else:
                click.echo(
                    f"Could not write {len(result)} translated rule(s) into individual files in specified output-dir '{output_dir}'"
                )

        if isinstance(result, str):  # String result
            click.echo(bytes(result, encoding), output)
        elif isinstance(result, bytes):  # Bytes result: only allow to write it to file.
            if output.isatty():
                raise click.UsageError(
                    "Backend returns binary output. Please provide output file with --output/-o."
                )
            else:
                click.echo(result, output)
        elif isinstance(result, list) and all(
            (  # List of strings Concatenate with newlines in between.
                isinstance(item, str) for item in result
            )
        ):
            click.echo(bytes("\n\n".join(result), encoding), output)
        elif isinstance(result, list) and all(
            (  # List of dicts: concatenate with newline and render each result als JSON.
                isinstance(item, dict) for item in result
            )
        ):
            click.echo(
                bytes(
                    "\n".join(
                        (json.dumps(item, indent=json_indent) for item in result)
                    ),
                    encoding,
                ),
                output,
            )
        elif isinstance(result, dict):
            click.echo(bytes(json.dumps(result, indent=json_indent), encoding))
        else:
            raise click.ClickException(
                f"Backend returned unexpected format {str(type(result))}"
            )
    except SigmaError as e:
        if verbose:
            click.echo("Error while converting")
            raise e
        else:
            raise click.ClickException("Error while converting: " + str(e))
    except NotImplementedError as e:
        if verbose:
            click.echo(
                "Feature required for conversion of Sigma rule is not supported by backend"
            )
            raise e
        else:
            raise click.ClickException(
                "Feature required for conversion of Sigma rule is not supported by backend: "
                + str(e)
            )

    if len(backend.errors) > 0:
        click.echo("\nIgnored errors:", err=True)
        for rule, error in backend.errors:
            raise click.ClickException(f"{str(rule.source)}: {str(error)}")
