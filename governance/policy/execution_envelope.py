"""GOV-ENVELOPE-001: closed, deterministic continuation decisions.

This module only classifies a proposed local action.  It never performs the
action, reads credentials, starts a network request, or changes project state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


RECOVERABLE_ACTIONS = frozenset({
    "fixture",
    "test_helper",
    "basetemp",
    "test_report",
    "test_marker",
    "local_dependency",
    "test_network_isolation",
    "test_extension",
    "mock",
    "schema_fix",
    "report_correction",
})

HARD_ACTIONS = frozenset({
    "network_download",
    "external_api",
    "production_write",
    "protected_asset",
    "production_registry",
    "production_semantics",
    "destructive_operation",
    "product_decision",
    "architecture_decision",
    "untrusted_baseline",
})

PROJECT_INITIALIZATION_EVENTS = frozenset({
    "first_takeover",
    "framework_deployment",
    "framework_major_upgrade",
    "core_stack_changed",
    "baseline_untrusted",
})


@dataclass(frozen=True)
class BlockerDecision:
    classification: str
    rule_id: str
    reason: str

    @property
    def may_continue(self) -> bool:
        return self.classification == "RECOVERABLE_BLOCKER"


def governance_level(context: Mapping[str, object], risk_kinds: tuple[str, ...] = ()) -> str:
    """Return the minimum governance layer from explicit context and risk."""
    if risk_kinds or context.get("risk_status") in {"known_high", "unknown"}:
        return "LEVEL_3_HIGH_RISK"
    if context.get("project_event", "ordinary_task") in PROJECT_INITIALIZATION_EVENTS:
        return "LEVEL_1_PROJECT_INITIALIZATION"
    return "LEVEL_2_TASK"


def confirmation_requirement(level: str) -> tuple[str, ...]:
    """Keep legacy high-risk confirmation while making ordinary tasks concise."""
    if level == "LEVEL_3_HIGH_RISK":
        return (
            "confirmed_by",
            "confirmation_date",
            "confirmed_scope",
            "remaining_accepted_risks",
            "first_execution_task",
        )
    return ("task_goal", "allowed_scope", "forbidden_scope", "required_tests", "report_path")


def classify_blocker(action_type: str, context: Mapping[str, object]) -> BlockerDecision:
    """Fail closed unless an action is explicitly inside the execution envelope."""
    flags = {
        "external_access": bool(context.get("external_access")),
        "production_write": bool(context.get("production_write")),
        "protected_asset": bool(context.get("protected_asset")),
        "production_semantics": bool(context.get("production_semantics")),
        "destructive_operation": bool(context.get("destructive_operation")),
        "scope_changed": bool(context.get("scope_changed")),
        "verifiable": context.get("verifiable") is not False,
    }
    if action_type in HARD_ACTIONS or any(flags[key] for key in flags if key != "verifiable"):
        return BlockerDecision("HARD_BLOCKER", "GOV-BLOCKER-001", "high-risk action or boundary change requires renewed authorization")
    if not flags["verifiable"]:
        return BlockerDecision("HARD_BLOCKER", "GOV-BLOCKER-001", "the recovery cannot be verified by the current task")
    if action_type == "local_dependency" and not bool(context.get("local_dependency_available")):
        return BlockerDecision("HARD_BLOCKER", "GOV-BLOCKER-001", "the dependency would require a network download")
    if action_type in RECOVERABLE_ACTIONS:
        return BlockerDecision("RECOVERABLE_BLOCKER", "GOV-ENVELOPE-001", "same-goal, local, test-verifiable recovery is authorized")
    return BlockerDecision("HARD_BLOCKER", "GOV-BLOCKER-001", "unknown action type fails closed")


def inherits_authorization(parent: Mapping[str, object], child: Mapping[str, object]) -> BlockerDecision:
    """Determine whether a same-task implementation, test, or report step inherits approval."""
    required = ("task_id", "task_goal", "allowed_scope", "forbidden_scope", "risk_level", "production_scope")
    if any(key not in parent or key not in child for key in required):
        return BlockerDecision("HARD_BLOCKER", "GOV-INHERIT-001", "authorization inheritance has incomplete task identity or boundaries")
    if any(parent[key] != child[key] for key in required):
        return BlockerDecision("HARD_BLOCKER", "GOV-INHERIT-001", "task goal, scope, risk, or production boundary changed")
    if child.get("parent_task_id", child["task_id"]) != parent["task_id"]:
        return BlockerDecision("HARD_BLOCKER", "GOV-INHERIT-001", "child does not identify the same parent task")
    return classify_blocker(str(child.get("action_type", "unknown")), child)
