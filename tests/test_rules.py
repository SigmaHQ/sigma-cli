import io
from pathlib import Path

from click.testing import CliRunner
import pytest

from sigma.cli.convert import convert
from sigma.cli.rules import load_rules
from sigma.exceptions import SigmaRuleNotFoundError


BASE_RULE = """title: Example base rule
id: 3f2e4e28-0bb8-46dd-a15d-c77aa65a3153
name: example_base
logsource:
    category: test
detection:
    selection:
        ExampleField: hello
    condition: selection
"""

CORRELATION_RULE = """title: Example event count
correlation:
    type: event_count
    rules:
        - {reference}
    timespan: 5m
    condition:
        gte: 2
"""


@pytest.mark.parametrize(
    "reference", ["example_base", "3f2e4e28-0bb8-46dd-a15d-c77aa65a3153"]
)
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    "input_kind", ["files", "directories", "stdin_base", "stdin_correlation"]
)
def test_convert_correlations_across_inputs(tmp_path, reference, reverse, input_kind):
    base_dir = tmp_path / "base"
    correlation_dir = tmp_path / "correlations"
    base_dir.mkdir()
    correlation_dir.mkdir()
    base_path = base_dir / "base.yml"
    correlation_path = correlation_dir / "correlation.yml"
    correlation = CORRELATION_RULE.format(reference=reference)
    base_path.write_text(BASE_RULE, encoding="utf-8")
    correlation_path.write_text(correlation, encoding="utf-8")

    stdin = None
    if input_kind == "directories":
        inputs = [base_dir, correlation_dir]
    elif input_kind == "stdin_base":
        inputs = ["-", correlation_path]
        stdin = BASE_RULE
    elif input_kind == "stdin_correlation":
        inputs = [base_path, "-"]
        stdin = correlation
    else:
        inputs = [base_path, correlation_path]
    if reverse:
        inputs.reverse()

    result = CliRunner().invoke(
        convert, ["-t", "text_query_test", *map(str, inputs)], input=stdin
    )

    assert result.exit_code == 0, result.output
    assert result.stdout == (
        'ExampleField="hello"\n'
        "| aggregate window=5min count() as event_count\n"
        "| where event_count >= 2\n"
    )


def test_load_rules_keeps_missing_reference_error(tmp_path):
    correlation_path = tmp_path / "correlation.yml"
    correlation_path.write_text(
        CORRELATION_RULE.format(reference="missing_rule"), encoding="utf-8"
    )

    with pytest.raises(SigmaRuleNotFoundError, match="missing_rule"):
        load_rules([correlation_path], "*.yml")


def test_load_rules_keeps_source_locations_and_errors(tmp_path):
    base_path = tmp_path / "base.yml"
    invalid_path = tmp_path / "invalid.yml"
    base_path.write_text(BASE_RULE, encoding="utf-8")
    invalid_path.write_text("title: Incomplete rule\n", encoding="utf-8")

    collection = load_rules([base_path, invalid_path], "*.yml")

    assert len(collection.rules) == 2
    assert collection.rules[0].source.path == base_path
    assert collection.rules[1].source.path == invalid_path
    assert collection.errors == collection.rules[1].errors
    assert collection.errors


def test_load_rules_from_stdin_keeps_missing_reference_error(monkeypatch):
    monkeypatch.setattr(
        "click.get_text_stream",
        lambda stream: io.StringIO(CORRELATION_RULE.format(reference="missing_rule")),
    )

    with pytest.raises(SigmaRuleNotFoundError, match="missing_rule"):
        load_rules([Path("-")], "*.yml")
