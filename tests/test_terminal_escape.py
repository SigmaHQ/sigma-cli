"""Rule-derived text must not reach the terminal with raw control or escape sequences."""

import pytest
from click.testing import CliRunner

from sigma.cli.analyze import analyze_group
from sigma.cli.check import check
from sigma.cli.convert import convert
from sigma.cli.rules import escape_control_chars

ESC = "\x1b"

RULE_TEMPLATE = """title: {title}
id: 5013332f-8a70-4e04-bcc1-06a98a2cca2e
status: test
level: {level}
logsource:
  category: test
detection:
  sel:
    {field}: x
  condition: sel
"""


def write_rule(path, title="Test rule", level="low", field="fieldA"):
    path.write_text(RULE_TEMPLATE.format(title=title, level=level, field=field))
    return path


def invoke_tty(command, args):
    # color=True keeps ANSI sequences like an interactive terminal does.
    return CliRunner().invoke(command, args, color=True)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("plain text", "plain text"),
        ("tab\tand\nnewline", "tab\tand\nnewline"),
        ("\x1b[2Jclear", "\\x1b[2Jclear"),
        ("osc\x1b]52;c;SGVsbG8=\x07", "osc\\x1b]52;c;SGVsbG8=\\x07"),
        ("carriage\rreturn", "carriage\\rreturn"),
        ("c1\x9bcsi\x7fdel", "c1\\x9bcsi\\x7fdel"),
        ("unicode ok: äöü", "unicode ok: äöü"),
    ],
)
def test_escape_control_chars(value, expected):
    assert escape_control_chars(value) == expected


def test_escape_control_chars_non_string():
    assert escape_control_chars(KeyError("a")) == "'a'"


def test_check_escapes_rule_level_in_error(tmp_path):
    rule = write_rule(tmp_path / "rule.yml", level='"\\e[2J\\e[Hlow"')
    result = invoke_tty(check, [str(rule)])
    assert "not a valid Sigma rule level" in result.output
    assert ESC not in result.output
    assert "\\x1b[2J" in result.output


def test_check_escapes_rule_file_name(tmp_path):
    rule = write_rule(tmp_path / f"rule{ESC}[8m.yml", level="nope")
    result = invoke_tty(check, [str(rule)])
    assert "not a valid Sigma rule level" in result.output
    assert ESC not in result.output
    assert "rule\\x1b[8m.yml" in result.output


def test_convert_escapes_rule_errors(tmp_path):
    rule = write_rule(tmp_path / "rule.yml", level='"\\e]52;c;SGVsbG8=\\alow"')
    result = invoke_tty(convert, ["-t", "text_query_test", str(rule)])
    assert result.exit_code != 0
    assert "not a valid Sigma rule level" in result.output
    assert ESC not in result.output
    assert "\x07" not in result.output


def test_analyze_fields_escapes_field_names(tmp_path):
    rule = write_rule(tmp_path / "rule.yml", field='"field\\e[31mRED"')
    result = invoke_tty(analyze_group, ["fields", "-t", "text_query_test", str(rule)])
    assert result.exit_code == 0, result.output
    assert ESC not in result.output
    assert "field\\x1b[31mRED" in result.output


def test_analyze_fields_group_escapes_field_names(tmp_path):
    rule = write_rule(tmp_path / "rule.yml", field='"field\\e[31mRED"')
    result = invoke_tty(
        analyze_group, ["fields", "-t", "text_query_test", "--group", str(rule)]
    )
    assert result.exit_code == 0, result.output
    assert ESC not in result.output
    assert "field\\x1b[31mRED" in result.output


def test_analyze_logsource_escapes_logsource(tmp_path):
    rule = tmp_path / "rule.yml"
    rule.write_text(RULE_TEMPLATE.format(title="t", level="low", field="fieldA").replace(
        "category: test", 'category: "\\e[31mcat"'
    ))
    result = invoke_tty(analyze_group, ["logsource", "-", str(rule)])
    assert result.exit_code == 0, result.output
    assert ESC not in result.output
    assert "\\x1b[31mcat" in result.output


def test_check_escapes_validation_issue_rule_path(tmp_path):
    # The unused detection 'dangling' triggers a validation issue that names the rule file.
    rule = tmp_path / f"issue{ESC}[2K.yml"
    rule.write_text(
        RULE_TEMPLATE.format(title="Title", level="low", field="fieldA")
        + "  dangling:\n    fieldB: y\n"
    )
    result = invoke_tty(check, [str(rule)])
    assert "=== Issues ===" in result.output
    assert "issue\\x1b[2K.yml" in result.output
    assert f"issue{ESC}[2K" not in result.output
