import pathlib
from collections import Counter
from sys import stderr
from textwrap import fill

from dataclasses import fields

import click
from prettytable import PrettyTable

from sigma.cli.rules import load_rules
from sigma.exceptions import SigmaConditionError, SigmaError
from sigma.plugins import InstalledSigmaPlugins
from sigma.validation import SigmaValidator
from sigma.rule import SigmaRule

plugins = InstalledSigmaPlugins.autodiscover()
validators = plugins.validators

severity_color = {"low": "green", "medium": "yellow", "high": "red"}


@click.command()
@click.option(
    "--validation-config",
    "-c",
    type=click.File("r"),
    help="Validation configuration file in YAML format.",
)
@click.option(
    "--file-pattern",
    "-P",
    default="*.yml",
    show_default=True,
    help="Pattern for file names to be included in recursion into directories.",
)
@click.option(
    "--fail-on-error/--pass-on-error",
    "-e/-E",
    default=True,
    show_default=True,
    help="Fail on Sigma rule parsing errors.",
)
@click.option(
    "--fail-on-issues/--pass-on-issues",
    "-i/-I",
    default=False,
    show_default=True,
    help="Fail on Sigma rule validation issues.",
)
@click.option(
    "--exclude",
    "-x",
    default=[],
    show_default=True,
    multiple=True,
    help="List of validators to exclude from the validation. Repeat --exclude for multiple exclusions.",
)
@click.argument(
    "input",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, allow_dash=True, path_type=pathlib.Path),
)
def check(
    input, validation_config, file_pattern, fail_on_error, fail_on_issues, exclude
):
    """Check Sigma rules for validity and best practices (not yet implemented)."""
    if (
        validation_config is None
    ):  # no validation config provided, use basic config with all validators
        exclude_lower = [excluded.lower() for excluded in exclude]
        exclude_invalid = [
            excluded for excluded in exclude_lower if excluded not in validators.keys()
        ]
        exclude_valid = [
            excluded for excluded in exclude_lower if excluded not in exclude_invalid
        ]

        if len(exclude_invalid) > 0:
            click.echo(
                f"Invalid validators name : {exclude_invalid} use 'sigma list validators'"
            )
        if len(exclude_valid) > 0:
            click.echo(f"Ignoring these validators : {exclude_valid}'")

        validators_filtered = [
            validator
            for name, validator in validators.items()
            if name.lower() not in exclude_valid
        ]
        rule_validator = SigmaValidator(validators_filtered)
    else:
        if exclude:
            click.echo(
                f"A configuration file and the `--exclude` parameter was set, ignoring the `--exclude` parameter."
            )
        rule_validator = SigmaValidator.from_yaml(validation_config.read(), validators)

    try:
        rule_collection = load_rules(input, file_pattern)
        rule_errors = Counter()
        cond_errors = Counter()
        check_rules = list()
        first_error = True
        for rule in rule_collection.rules:
            if (
                len(rule.errors) > 0
            ):  # rule has errors: print errors and skip further checking of rule
                if first_error:
                    click.echo("=== Sigma Rule Errors ===")
                    first_error = False

                for error in rule.errors:
                    click.echo(error)
                    rule_errors.update((error.__class__.__name__,))
            elif isinstance(rule, SigmaRule):  # rule has no errors, parse condition
                try:
                    for condition in rule.detection.parsed_condition:
                        condition.parse()
                    check_rules.append(rule)
                except SigmaConditionError as e:  # Error in condition
                    error = str(e)
                    click.echo(
                        f"Condition error in { str(condition.source) }:{ error }"
                    )
                    cond_errors.update((error,))
            else:
                check_rules.append(rule)

        # TODO: From Python 3.10 the commented line below can be used.
        rule_error_count = sum(rule_errors.values())
        # rule_error_count = rule_errors.total()

        with click.progressbar(
            check_rules, label="Checking Sigma rules", file=stderr
        ) as rules:
            issues = rule_validator.validate_rules(rules)

        issue_count = len(issues)
        issue_counter = Counter()
        if issue_count > 0:
            click.echo("=== Issues ===")
            for issue in issues:
                # Need to split SigmaValidationIssue __str__
                rules = ", ".join(
                    [
                        str(rule.source)
                        if rule.source is not None
                        else str(rule.id) or rule.title
                        for rule in issue.rules
                    ]
                )
                additional_fields = " ".join(
                    [
                        f"{field.name}={click.style(issue.__getattribute__(field.name) or '-', bold=True, fg='blue')}"
                        for field in fields(issue)
                        if field.name not in ("rules", "severity", "description")
                    ]
                )

                click.echo(
                    "issue="
                    + click.style(issue.__class__.__name__, bold=True, fg="cyan")
                    + " severity="
                    + click.style(
                        issue.severity.name.lower(),
                        bold=True,
                        fg=severity_color[issue.severity.name.lower()],
                    )
                    + " description="
                    + click.style(issue.description, bold=True, fg="blue")
                    + " rule="
                    + click.style(rules, bold=True, fg="blue")
                    + f" {additional_fields}"
                )
                issue_counter.update((issue.__class__,))

        # TODO: From Python 3.10 the commented line below can be used.
        cond_error_count = sum(cond_errors.values())
        # cond_error_count = cond_errors.total()
        click.echo()
        click.echo("=== Summary ===")
        click.echo(
            f"Found {rule_error_count} errors, { cond_error_count } condition errors and { issue_count } issues."
        )

        if rule_error_count > 0:
            click.echo("\nRule error summary:")
            rule_error_table = PrettyTable(
                field_names=("Count", "Rule Error"),
                align="l",
            )
            rule_error_table.add_rows(
                [
                    (count, fill(error, width=60))
                    for error, count in sorted(
                        rule_errors.items(), key=lambda item: item[1], reverse=True
                    )
                ]
            )
            click.echo(rule_error_table.get_string())
        else:
            click.echo("No rule errors found.")

        if cond_error_count > 0:
            click.echo("\nCondition error summary:")
            cond_error_table = PrettyTable(
                field_names=("Count", "Condition Error"),
                align="l",
            )
            cond_error_table.add_rows(
                [
                    (count, fill(error, width=60))
                    for error, count in sorted(
                        cond_errors.items(), key=lambda item: item[1], reverse=True
                    )
                ]
            )
            click.echo(cond_error_table.get_string())
        else:
            click.echo("No condition errors found.")

        if issue_count > 0:
            click.echo("\nValidation issue summary:")
            validation_issue_summary = PrettyTable(
                field_names=("Count", "Issue", "Severity", "Description"),
                align="l",
            )
            validation_issue_summary.add_rows(
                [
                    (
                        count,
                        issue.__name__,
                        issue.severity.name,
                        fill(issue.description, width=60),
                    )
                    for issue, count in sorted(
                        issue_counter.items(), key=lambda item: item[1], reverse=True
                    )
                ]
            )
            click.echo(validation_issue_summary.get_string())
        else:
            click.echo("No validation issues found.")

        if (
            fail_on_error
            and (rule_error_count > 0 or cond_error_count > 0)
            or fail_on_issues
            and issue_count > 0
        ):
            click.echo("Check failure")
            click.get_current_context().exit(1)
    except SigmaError as e:
        raise click.ClickException("Check error: " + str(e))
