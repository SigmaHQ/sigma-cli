import pytest
from click.testing import CliRunner
from sigma.cli.analyze import analyze_group, analyze_attack
from sigma.rule import SigmaRule, SigmaLogSource, SigmaDetections, SigmaDetection, SigmaDetectionItem, SigmaLevel, SigmaRuleTag
from sigma.analyze.attack import calculate_attack_scores, score_count, score_max, score_level, rule_level_scores, score_functions

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
    result = cli.invoke(analyze_attack, ["--max-score", "2", "max", "-", "tests/files/valid"])
    assert result.exit_code == 0
    assert '"maxValue": 2' in result.stdout

def test_attack_generate_min_value():
    cli = CliRunner()
    result = cli.invoke(analyze_attack, ["--min-score", "2", "max", "-", "tests/files/valid"])
    assert result.exit_code == 0
    assert '"minValue": 2' in result.stdout

def test_attack_generate_max_color():
    cli = CliRunner()
    result = cli.invoke(analyze_attack, ["--max-color", "#123456", "max", "-", "tests/files/valid"])
    assert result.exit_code == 0
    assert "#123456" in result.stdout

def test_attack_generate_min_color():
    cli = CliRunner()
    result = cli.invoke(analyze_attack, ["--min-color", "#123456", "max", "-", "tests/files/valid"])
    assert result.exit_code == 0
    assert "#123456" in result.stdout

def test_attack_generate_no_subtechniques():
    cli = CliRunner()
    result = cli.invoke(analyze_attack, ["--no-subtechniques", "max", "-", "tests/files/valid"])
    assert result.exit_code == 0
    assert len(result.stdout.split()) > 25
    assert "T1505\"" in result.stdout
    assert "persistence" in result.stdout

@pytest.fixture
def sigma_rules():
    logsource = SigmaLogSource("test")
    detections = SigmaDetections(
        {
            "test": SigmaDetection(
                [SigmaDetectionItem("field", [], "value")]
            )
        },
        ["test"]
    )
    return [
        SigmaRule("Medium severity rule", logsource, detections, level=SigmaLevel.MEDIUM, tags=[SigmaRuleTag("test", "tag"), SigmaRuleTag("attack", "t1234.001")]),
        SigmaRule("None severity rule", logsource, detections, tags=[SigmaRuleTag("attack", "t1234.001")]),
        SigmaRule("Low severity rule", logsource, detections, level=SigmaLevel.LOW),
        SigmaRule("Critical severity rule", logsource, detections, level=SigmaLevel.CRITICAL, tags=[SigmaRuleTag("attack", "t4321")]),
        SigmaRule("Informational severity rule", logsource, detections, level=SigmaLevel.INFORMATIONAL, tags=[SigmaRuleTag("attack", "t4321")]),
        SigmaRule("High severity rule", logsource, detections, level=SigmaLevel.HIGH, tags=[SigmaRuleTag("attack", "t4321")]),
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