"""Deterministic task-level classification."""

from dataclasses import dataclass

from ..models.task_request import TaskRequest
from .default_rules import A_RULES, C_RULES


@dataclass(frozen=True)
class Classification:
    task_level: str
    matched_rule_ids: tuple[str, ...]
    brief_reasons: tuple[str, ...]


def classify_task(task: TaskRequest) -> Classification:
    text = task.text
    declared_type = task.hints.get("task_type")
    if declared_type in {"A", "B", "C"}:
        return Classification(declared_type, (f"CLASS-{declared_type}-STRUCTURED",), ("structured task type",))
    matched = [rule for key, rule in C_RULES.items() if key in text]
    if matched:
        return Classification("C", tuple(sorted(set(matched))), ("explicit major-work trigger",))
    small = [rule for key, rule in A_RULES.items() if key in text]
    paths = task.hints["likely_paths"]
    if small and paths and len(paths) == 1 and all(word not in text for word in ("refactor", "public interface", "cross-module")):
        return Classification("A", tuple(sorted(set(small))), ("small explicit scope",))
    return Classification("B", ("CLASS-B-CODE-CHANGE",), ("default non-major classification",))
