from typing import Callable, Dict, Iterable, List
from sigma.rule import SigmaRule, SigmaLevel
from sigma.collection import SigmaCollection
from collections import defaultdict


def score_count(rules: Iterable[SigmaRule]) -> int:
    """Return count of rules."""
    return len(list(rules))


def score_max(rules: Iterable[SigmaRule]) -> int:
    """Return maximum rule level value."""
    return max(
        map(lambda rule: rule.level.value if rule.level is not None else 0, rules)
    )


rule_level_scores = {
    None: 1,
    SigmaLevel.INFORMATIONAL: 1,
    SigmaLevel.LOW: 2,
    SigmaLevel.MEDIUM: 4,
    SigmaLevel.HIGH: 8,
    SigmaLevel.CRITICAL: 12,
}


def rule_score(rule: SigmaRule) -> int:
    """Calculate rule score according to rule_level_scores."""
    return rule_level_scores[rule.level]


def score_level(rules: Iterable[SigmaRule]) -> int:
    return sum(map(rule_score, rules))


score_functions = {
    "count": (score_count, "Count of rules"),
    "max": (score_max, "Maximum severity value"),
    "level": (score_level, "Summarized level score"),
}


def calculate_attack_scores(
    rules: SigmaCollection,
    score_function: Callable[[Iterable[SigmaRule]], int],
    no_subtechniques: bool = False,
) -> Dict[str, int]:
    """Generate MITRE™️ ATT&CK Navigator heatmap according to scoring function."""
    attack_rules = defaultdict(list)
    for rule in rules:
        for tag in rule.tags:
            if tag.namespace == "attack":
                technique = tag.name.upper()
                if no_subtechniques:
                    technique = technique.split(".")[0]
                attack_rules[technique].append(rule)
    return {attack: score_function(rules) for attack, rules in attack_rules.items()}
