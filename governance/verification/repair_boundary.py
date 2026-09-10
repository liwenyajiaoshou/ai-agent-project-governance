"""Compact C06 boundary evaluation; it never performs a repair."""
from __future__ import annotations

import hashlib
import json

from ..core.budget import AutonomousRemediationBudget, BudgetDecision
from ..policy.execution_envelope import classify_blocker

_ACTIONS = {
    "fixture": ("fixture", "fixture"), "helper": ("helper", "test_helper"),
    "mock": ("mock", "mock"), "test_isolation": ("test isolation", "test_network_isolation"),
    "schema_fix": ("schema/type/path fixes", "schema_fix"), "report_correction": ("report/manifest correction", "report_correction"),
}
_HARD = {
    "network": ("real network", "network_download", {}), "external_api": ("external API", "external_api", {}),
    "formal_data_write": ("formal data write", "production_write", {}), "git_integration": ("Git write/integration", "unknown", {}),
    "release": ("release", "unknown", {}), "scope_expansion": ("scope expansion", "fixture", {"scope_changed": True}),
    "risk_escalation": ("risk escalation", "fixture", {"production_semantics": True}),
}

def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def evaluate(contract, guard, verification, repair_action=None):
    contract_digest = _digest(contract)
    action = repair_action or "NO_REPAIR_REQUIRED"
    base = {
        "task_id": verification["task_id"], "contract_digest": contract_digest,
        "baseline_identity": guard.get("head_commit"), "guard_status": guard.get("status"),
        "approval_status": guard.get("approval_status", "not_required"),
        "verification_evidence_digest": verification.get("evidence_binding", {}).get("evidence_digest"),
        "repair_action": action,
    }
    valid_inputs = base["task_id"] == contract.get("task_id") and bool(base["baseline_identity"]) and base["guard_status"] == "PASS" and base["approval_status"] in {"valid", "not_required"} and bool(base["verification_evidence_digest"])
    if repair_action is None:
        value = {**base, "budget_decision": "NOT_APPLICABLE", "envelope_decision": "NOT_APPLICABLE", "hard_blocker": False, "boundary_valid": valid_inputs, "reason": "NO_REPAIR_REQUIRED"}
    elif repair_action in _ACTIONS:
        budget_action, envelope_action = _ACTIONS[repair_action]
        budget = AutonomousRemediationBudget("closure-boundary", verification["task_id"], base["baseline_identity"], contract_digest)
        budget_decision = budget.evaluate(budget_action)
        envelope = classify_blocker(envelope_action, {})
        ok = budget_decision == BudgetDecision.ALLOW_AUTONOMOUS and envelope.may_continue
        value = {**base, "budget_decision": budget_decision, "envelope_decision": envelope.classification, "hard_blocker": not ok, "boundary_valid": valid_inputs and ok, "reason": budget.reason if not ok else envelope.reason}
    else:
        budget_action, envelope_action, context = _HARD.get(repair_action, (repair_action, "unknown", {}))
        budget = AutonomousRemediationBudget("closure-boundary", verification["task_id"], base["baseline_identity"] or "missing", contract_digest)
        budget_decision = budget.evaluate(budget_action)
        envelope = classify_blocker(envelope_action, context)
        value = {**base, "budget_decision": budget_decision, "envelope_decision": envelope.classification, "hard_blocker": True, "boundary_valid": False, "reason": budget.reason if budget_decision != BudgetDecision.ALLOW_AUTONOMOUS else envelope.reason}
    unsigned = dict(value)
    return {**value, "boundary_digest": _digest(unsigned)}
