import pathlib
import click
from collections import Counter
from prettytable import PrettyTable

from sigma.exceptions import SigmaConditionError, SigmaError
from sigma.cli.rules import load_rules
from sigma.validation import SigmaValidator
from sigma.plugins import InstalledSigmaPlugins

plugins = InstalledSigmaPlugins.autodiscover()
validators = plugins.validators

@click.command()
@click.option(
    "--validation-config", "-c",
    type=click.File("r"),
    help="Validation configuration file in YAML format.",
)
@click.option(
    "--file-pattern", "-P",
    default="*.yml",
    show_default=True,
    help="Pattern for file names to be included in recursion into directories.",
)
@click.option(
    "--fail-on-error/--pass-on-error", "-e/-E",
    default=True,
    show_default=True,
    help="Fail on Sigma rule parsing errors.",
)
@click.option(
    "--fail-on-issues/--pass-on-issues", "-i/-I",
    default=False,
    show_default=True,
    help="Fail on Sigma rule validation issues.",
)
@click.argument(
    "input",
    nargs=-1,
    type=click.Path(exists=True, path_type=pathlib.Path),
)
def check(input, validation_config, file_pattern, fail_on_error, fail_on_issues):
    """Check Sigma rules for validity and best practices (not yet implemented)."""
    if validation_config is None:   # no validation config provided, use basic config with all validators
        rule_validator = SigmaValidator(validators.values())
    else:
        rule_validator = SigmaValidator.from_yaml(validation_config.read(), validators)

    try:
        rule_collection = load_rules(input, file_pattern)
        rule_errors = Counter()
        cond_errors = Counter()
        check_rules = list()
        first_error = True
        for rule in rule_collection.rules:
            if len(rule.errors) > 0:        # rule has errors: print errors and skip further checking of rule
                if first_error:
                    click.echo("=== Sigma Rule Errors ===")
                    first_error = False

                for error in rule.errors:
                    click.echo(error)
                    rule_errors.update((error.__class__.__name__,))
            else:                           # rule has no errors, parse condition
                try:
                    for condition in rule.detection.parsed_condition:
                        condition.parse()
                    check_rules.append(rule)
                except SigmaConditionError as e:        # Error in condition
                    error = str(e)
                    click.echo(f"Condition error in { str(condition.source) }:{ error }")
                    cond_errors.update((error,))

        # TODO: From Python 3.10 the commented line below can be used.
        rule_error_count = sum(rule_errors.values())
        #rule_error_count = rule_errors.total()

        with click.progressbar(check_rules, label="Checking Sigma rules") as rules:
            issues = rule_validator.validate_rules(rules)

        issue_count = len(issues)
        issue_counter = Counter()
        if issue_count > 0:
            click.echo("=== Issues ===")
            for issue in issues:
                click.echo(issue)
                issue_counter.update((issue.__class__,))

        # TODO: From Python 3.10 the commented line below can be used.
        cond_error_count = sum(cond_errors.values())
        #cond_error_count = cond_errors.total()
        click.echo()
        click.echo("=== Summary ===")
        click.echo(f"Found {rule_error_count} errors, { cond_error_count } condition errors and { issue_count } issues.")

        if rule_error_count > 0:
            click.echo("\nRule error summary:")
            rule_error_table = PrettyTable(
                field_names=("Count", "Rule Error"),
                align="l",
            )
            rule_error_table.add_rows([
                (count, error)
                for error, count in sorted(rule_errors.items(), key=lambda item: item[1], reverse=True)
            ])
            click.echo(rule_error_table.get_string())
        else:
            click.echo("No rule errors found.")

        if cond_error_count > 0:
            click.echo("\nCondition error summary:")
            cond_error_table = PrettyTable(
                field_names=("Count", "Condition Error"),
                align="l",
            )
            cond_error_table.add_rows([
                (count, error)
                for error, count in sorted(cond_errors.items(), key=lambda item: item[1], reverse=True)
            ])
            click.echo(cond_error_table.get_string())
        else:
            click.echo("No condition errors found.")

        if issue_count > 0:
            click.echo("\nValidation issue summary:")
            validation_issue_summary = PrettyTable(
                field_names=("Count", "Issue", "Severity", "Description"),
                align="l",
            )
            validation_issue_summary.add_rows([
                (count, issue.__name__, issue.severity.name, issue.description)
                for issue, count in sorted(issue_counter.items(), key=lambda item: item[1], reverse=True)
            ])
            click.echo(validation_issue_summary.get_string())
        else:
            click.echo("No validation issues found.")

        if fail_on_error and rule_error_count > 0 or fail_on_issues and issue_count > 0:
            click.get_current_context().exit(1)
    except SigmaError as e:
        click.echo("Check error: " + str(e), err=True)