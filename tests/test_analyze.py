import pytest
from click.testing import CliRunner
from sigma.cli.analyze import analyze_group, analyze_attack, analyze_logsource, analyze_fields
from sigma.rule import (
    SigmaRule,
    SigmaLogSource,
    SigmaDetections,
    SigmaDetection,
    SigmaDetectionItem,
    SigmaLevel,
    SigmaRuleTag,
)
from sigma.types import SigmaString
from sigma.analyze.attack import (
    calculate_attack_scores,
    score_count,
    score_max,
    score_level,
    rule_level_scores,
    score_functions,
)
from sigma.analyze.stats import create_logsourcestats, get_rulelevel_mapping, format_row


def test_analyze_group():
    cli = CliRunner()
    result = cli.invoke(analyze_group, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 8


def test_attack_help():
    cli = CliRunner()
    result = cli.invoke(analyze_attack, ["--help"])
    assert result.exit_code == 0
    for func in score_functions.keys():
        assert func in result.stdout
    assert len(result.stdout.split()) > 8


def test_attack_generate():
    cli = CliRunner()
    result = cli.invoke(analyze_attack, ["max", "-", "tests/files/valid"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 25
    assert "T1505.003" in result.stdout
    assert "persistence" in result.stdout
    assert "#ff0000" in result.stdout
    assert "#ffffff00" in result.stdout
    assert '"maxValue": 4' in result.stdout
    assert '"minValue": 0' in result.stdout


def test_attack_generate_max_value():
    cli = CliRunner()
    result = cli.invoke(
        analyze_attack, ["--max-score", "2", "max", "-", "tests/files/valid"]
    )
    assert result.exit_code == 0
    assert '"maxValue": 2' in result.stdout


def test_attack_generate_min_value():
    cli = CliRunner()
    result = cli.invoke(
        analyze_attack, ["--min-score", "2", "max", "-", "tests/files/valid"]
    )
    assert result.exit_code == 0
    assert '"minValue": 2' in result.stdout


def test_attack_generate_max_color():
    cli = CliRunner()
    result = cli.invoke(
        analyze_attack, ["--max-color", "#123456", "max", "-", "tests/files/valid"]
    )
    assert result.exit_code == 0
    assert "#123456" in result.stdout


def test_attack_generate_min_color():
    cli = CliRunner()
    result = cli.invoke(
        analyze_attack, ["--min-color", "#123456", "max", "-", "tests/files/valid"]
    )
    assert result.exit_code == 0
    assert "#123456" in result.stdout


def test_attack_generate_no_subtechniques():
    cli = CliRunner()
    result = cli.invoke(
        analyze_attack, ["--no-subtechniques", "max", "-", "tests/files/valid"]
    )
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 25
    assert 'T1505"' in result.stdout
    assert "persistence" in result.stdout

def test_attack_invalid_rule():
    cli = CliRunner()
    result = cli.invoke(analyze_attack, ["max", "-", "tests/files/sigma_rule_without_condition.yml"])
    assert result.exit_code != 0
    assert "at least one condition" in result.stderr


@pytest.fixture
def sigma_rules():
    logsource = SigmaLogSource(category="test")
    detections = SigmaDetections(
        {"test": SigmaDetection([SigmaDetectionItem("field", [], [SigmaString("value")])])}, ["test"]
    )
    return [
        SigmaRule(
            title="Medium severity rule",
            logsource=logsource,
            detection=detections,
            level=SigmaLevel.MEDIUM,
            tags=[SigmaRuleTag("test", "tag"), SigmaRuleTag("attack", "t1234.001")],
        ),
        SigmaRule(
            title="None severity rule",
            logsource=logsource,
            detection=detections,
            tags=[SigmaRuleTag("attack", "t1234.001")],
        ),
        SigmaRule(
            title="Low severity rule",
            logsource=logsource,
            detection=detections,
            level=SigmaLevel.LOW,
        ),
        SigmaRule(
            title="Critical severity rule",
            logsource=logsource,
            detection=detections,
            level=SigmaLevel.CRITICAL,
            tags=[SigmaRuleTag("attack", "t4321")],
        ),
        SigmaRule(
            title="Informational severity rule",
            logsource=logsource,
            detection=detections,
            level=SigmaLevel.INFORMATIONAL,
            tags=[SigmaRuleTag("attack", "t4321")],
        ),
        SigmaRule(
            title="High severity rule",
            logsource=logsource,
            detection=detections,
            level=SigmaLevel.HIGH,
            tags=[SigmaRuleTag("attack", "t4321")],
        ),
    ]


def test_attack_score_count(sigma_rules):
    assert score_count(sigma_rules) == 6


def test_attack_score_max(sigma_rules):
    assert score_max(sigma_rules) == 5


def test_attack_score_level(sigma_rules):
    assert score_level(sigma_rules) == sum(rule_level_scores.values())


def test_generate_attack_scores(sigma_rules):
    assert calculate_attack_scores(sigma_rules, score_count) == {
        "T1234.001": 2,
        "T4321": 3,
    }


def test_generate_attack_scores_no_subtechniques(sigma_rules):
    assert calculate_attack_scores(sigma_rules, score_count, True) == {
        "T1234": 2,
        "T4321": 3,
    }


def test_logsource_help():
    cli = CliRunner()
    result = cli.invoke(analyze_logsource, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 8


def test_logsource_get_rulelevel_mapping(sigma_rules):
    for sigma_rule in sigma_rules:
        if sigma_rule.level:
            assert (
                str(get_rulelevel_mapping(sigma_rule)).lower()
                == sigma_rule.level.name.lower()
            )
        else:
            assert str(get_rulelevel_mapping(sigma_rule)).lower() == "none"


def test_logsource_create_logsourcestats(sigma_rules):
    ret = create_logsourcestats(sigma_rules)

    assert 'test' in ret
    assert ret['test'].get("Overall") == len(sigma_rules)

def test_logsource_invalid_rule():
    cli = CliRunner()
    result = cli.invoke(analyze_logsource, ["-", "tests/files/sigma_rule_without_condition.yml"])
    assert result.exit_code != 0
    assert "at least one condition" in result.stderr


def test_fields_help():
    cli = CliRunner()
    result = cli.invoke(analyze_fields, ["--help"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 8


def test_fields_extract():
    cli = CliRunner()
    result = cli.invoke(analyze_fields, ["-t", "text_query_test", "-", "tests/files/valid"])
    assert result.exit_code == 0
    # Should have extracted at least some fields
    assert len(result.stdout.split()) > 0


def test_fields_extract_correlation_rule():
    cli = CliRunner()
    result = cli.invoke(analyze_fields, ["-t", "text_query_test", "-", "tests/files/sigma_correlation_rules.yml"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 0


def test_fields_extract_with_pipelines():
    cli = CliRunner()
    result = cli.invoke(analyze_fields, ["-t", "text_query_test", "-p", "tests/files/custom_pipeline.yml", "-p", "dummy_test", "-", "tests/files/valid"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 0


def test_fields_invalid_rule():
    cli = CliRunner()
    result = cli.invoke(analyze_fields, ["-t", "text_query_test", "-", "tests/files/sigma_rule_without_condition.yml"])
    assert result.exit_code != 0
    assert "at least one condition" in result.stderr

def test_fields_grouped_extract():
    cli = CliRunner()
    result = cli.invoke(analyze_fields, ["-t", "text_query_test", "--group", "-", "tests/files/valid"])
    assert result.exit_code == 0
    # Should have extracted at least some fields
    assert len(result.stdout.split()) > 0
    assert "+----------" in result.stdout  # Check for table format