import pathlib
import click

from sigma.collection import SigmaCollection
from sigma.exceptions import SigmaError

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
        rule_collection = SigmaCollection.load_ruleset(
            input,
            recursion_pattern="**/" + file_pattern,
            collect_errors=True,
            )
        for rule in rule_collection.rules:
            for error in rule.errors:
                click.echo(error)
    except SigmaError as e:
        click.echo("Check error: " + str(e), err=True)