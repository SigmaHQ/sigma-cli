import json
import os
import pathlib
import textwrap
from typing import Sequence

import click

from sigma.cli.rules import load_rules, check_rule_errors
from sigma.collection import SigmaCollection
from sigma.conversion.base import Backend
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


def render_output_filename(template: str, rule_source_path: pathlib.Path, base_dir: pathlib.Path, index: int = None) -> pathlib.Path:
    """
    Render output filename template with available variables.
    
    Args:
        template: Template string with variables {path}, {stem}, {index}
        rule_source_path: Path to the source rule file
        base_dir: Base directory to calculate relative path from
        index: Query index for rules that generate multiple queries (optional)
    
    Returns:
        Path object for the output file
    """
    # Calculate relative path from base directory
    try:
        relative_path = rule_source_path.relative_to(base_dir)
    except ValueError:
        # If rule_source_path is not relative to base_dir, use the rule path as-is
        relative_path = rule_source_path
    
    # Get parent directory path (without filename)
    if relative_path.parent != pathlib.Path("."):
        path_component = str(relative_path.parent)
    else:
        path_component = ""
    
    # Get filename stem (without extension)
    stem = rule_source_path.stem
    
    # Render template
    rendered = template.format(
        path=path_component,
        stem=stem,
        index=index if index is not None else ""
    )
    
    # Clean up any double slashes or empty path components
    rendered = rendered.replace("//", "/").strip("/")
    
    return pathlib.Path(rendered)


def write_separate_files(
    rule_collection: SigmaCollection,
    backend: Backend,
    output_dir: pathlib.Path,
    filename_template: str,
    format: str,
    correlation_method: str,
    encoding: str,
    json_indent: int,
    base_dir: pathlib.Path,
):
    """
    Convert rules and write each to a separate file.
    
    Args:
        rule_collection: Collection of Sigma rules to convert
        backend: Backend instance for conversion
        output_dir: Directory to write output files
        filename_template: Template for output filenames
        format: Output format
        correlation_method: Correlation method
        encoding: Output encoding
        json_indent: JSON indentation
        base_dir: Base directory to calculate relative paths from
    
    Raises:
        click.UsageError: If the collection contains correlation rules
    """
    output_dir = pathlib.Path(output_dir)
    
    # Check for correlation rules - they cannot be converted individually
    # because they reference other rules in the collection
    for rule in rule_collection.rules:
        if type(rule).__name__ == 'SigmaCorrelationRule':
            raise click.UsageError(
                f"Cannot use --output-dir with correlation rules. "
                f"Correlation rule '{rule.title}' (ID: {rule.id}) references other rules "
                f"and must be converted as part of the full collection. "
                f"Use --output instead to write all rules to a single file."
            )
    
    # Track number of files written
    files_written = 0
    
    # Convert each rule individually
    for rule in rule_collection.rules:
        # Create a single-rule collection for this rule
        single_rule_collection = SigmaCollection([rule])
        
        # Convert the rule
        try:
            result = backend.convert(single_rule_collection, format, correlation_method)
        except Exception as e:
            # Skip rules that can't be converted - continue with remaining rules
            click.echo(f"Warning: Failed to convert {rule.source}: {e}. Skipping rule.", err=True)
            continue
        
        # Get rule source path
        if rule.source and hasattr(rule.source, 'path'):
            rule_source_path = pathlib.Path(rule.source.path)
        else:
            # If no source path, use rule ID or title as filename
            rule_source_path = pathlib.Path(f"{rule.id or rule.title}.yml")
        
        # Handle different result types
        if isinstance(result, str):
            # Single string result - write to one file
            output_path = output_dir / render_output_filename(filename_template, rule_source_path, base_dir, None)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(bytes(result, encoding))
            files_written += 1
            
        elif isinstance(result, bytes):
            # Binary result - write to one file
            output_path = output_dir / render_output_filename(filename_template, rule_source_path, base_dir, None)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(result)
            files_written += 1
            
        elif isinstance(result, list) and all(isinstance(item, str) for item in result):
            # List of strings - write each to a separate file with index
            if len(result) == 1:
                # Single result, no index needed
                output_path = output_dir / render_output_filename(filename_template, rule_source_path, base_dir, None)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(bytes(result[0], encoding))
                files_written += 1
            else:
                # Multiple results, add index to filename
                for idx, item in enumerate(result, start=1):
                    output_path = output_dir / render_output_filename(filename_template, rule_source_path, base_dir, idx)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(bytes(item, encoding))
                    files_written += 1
                    
        elif isinstance(result, list) and all(isinstance(item, dict) for item in result):
            # List of dicts - write each to a separate file with index as JSON
            if len(result) == 1:
                # Single result, no index needed
                output_path = output_dir / render_output_filename(filename_template, rule_source_path, base_dir, None)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(bytes(json.dumps(result[0], indent=json_indent), encoding))
                files_written += 1
            else:
                # Multiple results, add index to filename
                for idx, item in enumerate(result, start=1):
                    output_path = output_dir / render_output_filename(filename_template, rule_source_path, base_dir, idx)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(bytes(json.dumps(item, indent=json_indent), encoding))
                    files_written += 1
                    
        elif isinstance(result, dict):
            # Dict result - write as JSON
            output_path = output_dir / render_output_filename(filename_template, rule_source_path, base_dir, None)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(bytes(json.dumps(result, indent=json_indent), encoding))
            files_written += 1
        else:
            click.echo(f"Warning: Backend returned unexpected format {str(type(result))} for {rule.source}. Expected str, bytes, list, or dict. Skipping rule.", err=True)
    
    click.echo(f"Wrote {files_written} file(s) to {output_dir}", err=True)


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
    help="Select method for generation of correlation queries. If not given the default method of the backend is used."
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
    help="Skip conversion of rules that can't be handled by the backend",
)
@click.option(
    "--output",
    "-o",
    type=click.File("wb"),
    default="-",
    show_default=True,
    help="Write result to specified file. '-' writes to standard output. Mutually exclusive with --output-dir.",
)
@click.option(
    "--output-dir",
    "-od",
    type=click.Path(path_type=pathlib.Path),
    default=None,
    help="Write individual converted rules to separate files in this directory. Mutually exclusive with --output.",
)
@click.option(
    "--output-filename-template",
    "-ot",
    type=str,
    default="{stem}.txt",
    show_default=True,
    help="Template for output filenames when using --output-dir. "
    "Available variables: {path} (relative source path), {stem} (filename without extension), "
    "{index} (query index for rules that generate multiple queries). "
    "Example: '{path}/{stem}-{index}.txt' or 'converted/{stem}.esql'",
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
@click.option(
    "--enable-template-vars",
    is_flag=True,
    default=False,
    help="Enable template variable support in processing pipeline. WARNING: This feature can be dangerous and allow arbitrary code execution if used with untrusted Sigma rules.",
)
@click.option(
    "--template-vars-path",
    multiple=True,
    type=click.Path(exists=True, path_type=pathlib.Path),
    help="Allowed paths for template variable expansion. Can be specified multiple times.",
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
    output_dir,
    output_filename_template,
    encoding,
    json_indent,
    backend_option,
    enable_template_vars,
    template_vars_path,
    input,
    file_pattern,
    verbose,
):
    """
    Convert Sigma rules into queries. INPUT can be multiple files or directories. This command automatically recurses
    into directories and converts all files matching the pattern in --file-pattern.
    """

    # Validate mutually exclusive options
    if output_dir is not None and hasattr(output, 'name') and output.name != "<stdout>":
        raise click.UsageError(
            "--output/-o and --output-dir/-od are mutually exclusive. Use --output for single file output or --output-dir for separate file outputs."
        )

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
        
        # Configure template variable settings on the processing pipeline
        if enable_template_vars:
            processing_pipeline.allow_template_vars = True
        if template_vars_path:
            processing_pipeline.vars_allowed_paths = [str(p) for p in template_vars_path]
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
                + click.style(f"sigma list correlation-methods {target}", bold=True, fg="green")
                + " to list all available correlation methods of the target.",
                param_hint="correlation_method",
            )

    try:
        rule_collection = load_rules(input + filter, file_pattern)
        check_rule_errors(rule_collection)
        
        # Check if we should write to separate files
        if output_dir is not None:
            # Determine base directory for relative path calculation
            # Use the first input path as base directory
            base_dir = pathlib.Path.cwd()
            if input and input[0] != pathlib.Path("-"):
                first_input = pathlib.Path(input[0])
                if first_input.is_dir():
                    base_dir = first_input
                else:
                    base_dir = first_input.parent
            
            # Write separate files
            write_separate_files(
                rule_collection=rule_collection,
                backend=backend,
                output_dir=output_dir,
                filename_template=output_filename_template,
                format=format,
                correlation_method=correlation_method,
                encoding=encoding,
                json_indent=json_indent,
                base_dir=base_dir,
            )
        else:
            # Original behavior: convert entire collection and write to single output
            result = backend.convert(rule_collection, format, correlation_method)
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
            click.echo('Error while converting')
            raise e
        else:
            raise click.ClickException("Error while converting: " + str(e))
    except NotImplementedError as e:
        if verbose:
            click.echo('Feature required for conversion of Sigma rule is not supported by backend')
            raise e
        else:
            raise click.ClickException("Feature required for conversion of Sigma rule is not supported by backend: " + str(e))

    if len(backend.errors) > 0:
        click.echo("\nIgnored errors:", err=True)
        for rule, error in backend.errors:
            click.echo(f"{str(rule.source)}: {str(error)}", err=True)
