import pathlib
import click

from sigma.exceptions import SigmaError

from sigma.cli.rules import load_rules

@click.command()
@click.option(
    "--file-pattern", "-P",
    default="*.yml",
    show_default=True,
    help="Pattern for file names to be included in recursion into directories.",
)
@click.argument(
    "input",
    nargs=-1,
    type=click.Path(exists=True, path_type=pathlib.Path),
)
def check(input, file_pattern):
    """Check Sigma rules for validity and best practices (not yet implemented)."""
    try:
        rule_collection = load_rules(input, file_pattern)
        error_count = 0
        for rule in rule_collection.rules:
            for error in rule.errors:
                click.echo(error)
                error_count += 1
        if error_count > 0:
            click.echo(f"Found {error_count} errors!")
            click.get_current_context().exit(1)
        else:
            click.echo("No errors found!")
    except SigmaError as e:
        click.echo("Check error: " + str(e), err=True)