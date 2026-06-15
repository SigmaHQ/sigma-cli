import pathlib
import xml.etree.ElementTree as ET
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

severity_color = {"low": "green", "medium": "yellow", "high": "red"}

# JUnit-specific icons covering PySigma validation and parsing possibilities
SEVERITY_ICONS = {
    "critical": "💥",
    "high": "🔴",
    "medium": "🟠",
    "low": "🟡",
    "informational": "ℹ️",
    "parsing_error": "🚫",
    "condition_error": "❌",
    "error": "❌",  # Fallback for other SigmaError subclasses
    "ok": "✅",
}


def generate_junit_report(results, output_file):
    """Generates JUnit XML grouped by PySigma error/issue types."""
    root = ET.Element("testsuites", name="Sigma Rule Validation")

    suites = {}
    for res in results:
        suite_name = res.get("issue_type", "Validation Success")
        if suite_name not in suites:
            suites[suite_name] = []
        suites[suite_name].append(res)

    for suite_name, tests in suites.items():
        failures = len([t for t in tests if t["status"] == "failed"])
        test_suite = ET.SubElement(
            root,
            "testsuite",
            name=suite_name,
            tests=str(len(tests)),
            failures=str(failures),
        )

        for res in tests:
            severity = (res.get("severity") or "ok").lower()
            icon = SEVERITY_ICONS.get(severity, SEVERITY_ICONS["error"])

            test_case = ET.SubElement(
                test_suite,
                "testcase",
                name=f"{icon} {res['rule_name']}",
                classname=suite_name,
                file=res.get("file_path", "unknown"),
            )

            if res["status"] == "failed":
                failure = ET.SubElement(
                    test_case,
                    "failure",
                    message=f"{res.get('issue_type')}: {res.get('severity', '').upper()}",
                )
                failure.text = res.get("description", "")

    tree = ET.ElementTree(root)
    with open(output_file, "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)


# ==========================================
# Data Processing & Extraction Functions
# ==========================================
def setup_validator(validation_config, exclude):
    
    plugins = InstalledSigmaPlugins.autodiscover()
    validators = plugins.validators

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
    
        report_config_warnings(exclude_invalid, exclude_valid)
    
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
    return rule_validator
    
# ==========================================
# Reporting & Output Functions
# ==========================================

def report_config_warnings(exclude_invalid, exclude_valid):
    """Prints warnings regarding invalid or excluded validators."""
    if len(exclude_invalid) > 0:
        click.echo(f"Invalid validators name : {exclude_invalid} use 'sigma list validators'")
    if len(exclude_valid) > 0:
        click.echo(f"Ignoring these validators : {exclude_valid}'")

def validate_loaded_rules(check_rules, rule_validator):
    with click.progressbar(
        check_rules, label="Checking Sigma rules", file=stderr
    ) as rules:
        issues = rule_validator.validate_rules(rules)
    return issues


def load_and_check_rules(input, file_pattern, rule_errors, cond_errors, junit_results=None):
    rule_collection = load_rules(input, file_pattern)
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
                if junit_results is not None:
                    error_type = error.__class__.__name__
                    rule_name = rule.title or str(rule.path)
                    file_path = str(rule.source) if rule.source else "unknown"
                    sev = "parsing_error" if "Parse" in error_type else "error"
                    junit_results.append({
                        "rule_name": rule_name, "file_path": file_path, "status": "failed",
                        "issue_type": error_type, "severity": sev, "description": str(error)
                    })
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
                if junit_results is not None:
                    junit_results.append({
                        "rule_name": rule.title or str(rule.path),
                        "file_path": str(rule.source) if rule.source else "unknown",
                        "status": "failed",
                        "issue_type": e.__class__.__name__,
                        "severity": "condition_error",
                        "description": str(error),
                    })
        else:
            check_rules.append(rule)
    return check_rules

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
    "--junitxml",
    type=click.Path(path_type=pathlib.Path),
    help="Output results in JUnit XML format to the specified file.",
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
    input, validation_config, file_pattern, fail_on_error, fail_on_issues, junitxml, exclude
):
    """Check Sigma rules for validity and best practices (not yet implemented)."""
    
    rule_validator = setup_validator(validation_config, exclude)

    try:
        rule_errors = Counter()
        cond_errors = Counter()
        junit_results = [] if junitxml else None
        check_rules = load_and_check_rules(input, file_pattern, rule_errors, cond_errors, junit_results)

        # TODO: From Python 3.10 the commented line below can be used.
        rule_error_count = sum(rule_errors.values())
        # rule_error_count = rule_errors.total()

        issues = validate_loaded_rules(check_rules, rule_validator)

        issue_count = len(issues)
        issue_counter = Counter()
        if issue_count > 0:
            click.echo("=== Issues ===")
            for issue in issues:
                # Need to split SigmaValidationIssue __str__
                formatted_rules_output = ", ".join(
                    [
                        str(rule_with_issue.source)
                        if rule_with_issue.source is not None
                        else str(rule_with_issue.id) or rule_with_issue.title
                        for rule_with_issue in issue.rules
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
                    + click.style(formatted_rules_output, bold=True, fg="blue")
                    + f" {additional_fields}"
                )
                issue_counter.update((issue.__class__,))
                if junit_results is not None:
                    for rule in issue.rules:
                        junit_results.append({
                            "rule_name": rule.title or str(rule.path),
                            "file_path": str(rule.source) if rule.source else "unknown",
                            "status": "failed",
                            "issue_type": type(issue).__name__,
                            "severity": issue.severity.name.lower(),
                            "description": str(issue.description),
                        })

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

        if junitxml:
            generate_junit_report(junit_results, junitxml)
            click.echo(f"\nJUnit report saved to: {junitxml}")

        if (
            fail_on_error
            and (rule_error_count > 0 or cond_error_count > 0)
            or fail_on_issues
            and issue_count > 0
        ):
            click.echo("Check failure")
            click.get_current_context().exit(1)
    except SigmaError as e:
        if junitxml:
            generate_junit_report([{
                "rule_name": "Global/Collection Loading Error",
                "file_path": str(input),
                "status": "failed",
                "issue_type": e.__class__.__name__,
                "severity": "error",
                "description": str(e),
            }], junitxml)
        raise click.ClickException("Check error: " + str(e))
