import copy
from typing import Dict, List
from sigma.rule import SigmaRule, SigmaLevel
from sigma.collection import SigmaCollection


rule_level_mapping = {
    None: "None",
    SigmaLevel.INFORMATIONAL: "Informational",
    SigmaLevel.LOW: "Low",
    SigmaLevel.MEDIUM: "Medium",
    SigmaLevel.HIGH: "High",
    SigmaLevel.CRITICAL: "Critical",
}

template_stat_detail = {
    "Overall": 0,
    "Critical": 0,
    "High": 0,
    "Medium": 0,
    "Low": 0,
    "Informational": 0,
    "None": 0,
}


def format_row(row: str, column_widths: List) -> str:
    """Format rows for table."""
    return " | ".join(
        f"{str(item).ljust(width)}" for item, width in zip(row, column_widths)
    )


def get_rulelevel_mapping(rule: SigmaRule) -> int:
    """Calculate rule score according to rule_level_scores."""
    return rule_level_mapping[rule.level]


def create_logsourcestats(rules: SigmaCollection) -> Dict[str, int]:
    """
    Iterate through all the rules and count SigmaLevel grouped by
    Logsource Category Name.
    """
    stats = {}

    for rule in rules:
        if hasattr(rule, "logsource"):
            # Create stats key for logsource category.
            if not rule.logsource.category in stats:
                stats[rule.logsource.category] = copy.deepcopy(template_stat_detail)

            stats[rule.logsource.category]["Overall"] += 1
            stats[rule.logsource.category][get_rulelevel_mapping(rule)] += 1

    return stats
