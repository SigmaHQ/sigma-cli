from pathlib import Path
from sys import stderr
import click
from sigma.collection import SigmaCollection


def load_rules(input, file_pattern):
    if len(input) == 1 and input[0] == Path("-"):  # read rule from standard input
        rule_collection = SigmaCollection.from_yaml(click.get_text_stream("stdin"))
    else:
        rule_paths = SigmaCollection.resolve_paths(
            input,
            recursion_pattern="**/" + file_pattern,
        )
        with click.progressbar(
            list(rule_paths), label="Parsing Sigma rules", file=stderr
        ) as progress_rule_paths:
            rule_collection = SigmaCollection.load_ruleset(
                progress_rule_paths,
                collect_errors=True,
            )
    return rule_collection
