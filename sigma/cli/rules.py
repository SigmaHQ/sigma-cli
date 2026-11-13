from __future__ import annotations

import re
from pathlib import Path
from sys import stderr
from typing import TYPE_CHECKING
import click
from sigma.collection import SigmaCollection

if TYPE_CHECKING:
    from sigma.policy import SigmaPolicy

# C0 controls except tab and newline, DEL and C1 controls. ESC (0x1b) and the single-byte
# CSI/OSC introducers (0x9b, 0x9d) start terminal escape sequences.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_NAMED_ESCAPES = {"\r": "\\r"}


def escape_control_chars(value) -> str:
    """
    Render a value for terminal output with control characters escaped, so text taken from rule
    files (values, field names, file names) cannot inject terminal escape sequences.
    """
    return _CONTROL_CHARS.sub(
        lambda m: _NAMED_ESCAPES.get(m.group(), f"\\x{ord(m.group()):02x}"), str(value)
    )


def load_rules(input, file_pattern, policy: "SigmaPolicy | None" = None):
    """
    Load Sigma rules from files or stdin.
    """
    rule_collection = SigmaCollection([], [])

    for path in list(input):
        if path == Path("-"):
            rule_collection = SigmaCollection.merge([
                rule_collection,
                SigmaCollection.from_yaml(click.get_text_stream("stdin"), policy=policy)
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
            click.echo(f"* {escape_control_chars(error)}", err=True)
        raise click.ClickException(
            "Errors found in Sigma rules. Please check the output above."
        )