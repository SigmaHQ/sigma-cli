import pathlib
import click

from sigma.exceptions import SigmaConditionError, SigmaError
from sigma.cli.rules import load_rules
from sigma.validation import SigmaValidator
from sigma.validators import validators

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
    "--fail-on-issue/--pass-on-issue", "-i/-I",
    default=False,
    show_default=True,
    help="Fail on Sigma rule validation issues.",
)
@click.argument(
    "input",
    nargs=-1,
    type=click.Path(exists=True, path_type=pathlib.Path),
)
def check(input, validation_config, file_pattern, fail_on_error, fail_on_issue):
    """Check Sigma rules for validity and best practices (not yet implemented)."""
    if validation_config is None:   # no validation config provided, use basic config with all validators
        rule_validator = SigmaValidator(validators.values())
    else:
        rule_validator = SigmaValidator.from_yaml(validation_config.read())

    try:
        rule_collection = load_rules(input, file_pattern)
        error_count = 0
        check_rules = list()
        for rule in rule_collection.rules:
            if len(rule.errors) > 0:        # rule has errors: print errors and skip further checking of rule
                for error in rule.errors:
                    click.echo(error)
                    error_count += 1
            else:                           # rule has no errors, parse condition
                try:
                    for condition in rule.detection.parsed_condition:
                        condition.parse()
                    check_rules.append(rule)
                except SigmaConditionError as e:        # Error in condition
                    click.echo(f"Condition error in { str(condition.source) }:{ str(e) }")
                    error_count += 1

        with click.progressbar(check_rules, label="Checking Sigma rules") as rules:
            issues = rule_validator.validate_rule_collection(rules)

        issue_count = len(issues)
        if issue_count > 0:
            click.echo("=== Issues ===")
            for issue in issues:
                click.echo(issue)

        click.echo(f"Found {error_count} errors and { issue_count } issues.")
        if fail_on_error and error_count > 0 or fail_on_issue and issue_count > 0:
            click.get_current_context().exit(1)
    except SigmaError as e:
        click.echo("Check error: " + str(e), err=True)