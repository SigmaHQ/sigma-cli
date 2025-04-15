from pathlib import Path
from sys import stderr
import click
from sigma.collection import SigmaCollection


def load_rules(input, file_pattern):
    """
    Load Sigma rules from files or stdin.
    """
    rule_collection = SigmaCollection([], [])

    for path in list(input):
        if path == Path("-"):
            rule_collection = SigmaCollection.merge([
                rule_collection,
                SigmaCollection.from_yaml(click.get_text_stream("stdin"))
            ])
        else:
            rule_paths = SigmaCollection.resolve_paths(
                [path],
                recursion_pattern="**/" + file_pattern,
            )
            with click.progressbar(
                    list(rule_paths), label="Parsing Sigma rules", file=stderr
            ) as progress_rule_paths:
                rule_collection = SigmaCollection.merge([
                    rule_collection,
                    SigmaCollection.load_ruleset(
                        progress_rule_paths,
                        collect_errors=True,
                    )
                ])

    rule_collection.resolve_rule_references()

    return rule_collection

def check_rule_errors(sigma_collection):
    """
    Check if the SigmaCollection contains errors and handle them.
    """
    if sigma_collection.errors:
        click.echo("Errors found in Sigma rules:", err=True)
        for error in sigma_collection.errors:
            click.echo(f"* {error}", err=True)
        raise click.ClickException(
            "Errors found in Sigma rules. Please check the output above."
        )