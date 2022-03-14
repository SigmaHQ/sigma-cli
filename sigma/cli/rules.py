import click
from sigma.collection import SigmaCollection

def load_rules(input, file_pattern):
    rule_paths = SigmaCollection.resolve_paths(
        input,
        recursion_pattern="**/" + file_pattern,
    )
    with click.progressbar(list(rule_paths), label="Parsing Sigma rules") as progress_rule_paths:
        rule_collection = SigmaCollection.load_ruleset(
            progress_rule_paths,
            collect_errors=True,
            )
    return rule_collection