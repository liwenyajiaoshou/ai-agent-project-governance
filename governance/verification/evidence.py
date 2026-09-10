"""Build redacted, reproducible local test-evidence records."""

from __future__ import annotations

import hashlib
import json
from typing import Mapping, Sequence


def build_test_evidence(
    *,
    command: Sequence[str],
    working_directory: str,
    node_scope: str,
    marker: str | None,
    environment_variable_names: Sequence[str],
    dependency_summary: Mapping[str, str],
    basetemp: str | None,
    counts: Mapping[str, int],
    failed_nodes: Sequence[str],
    junit_path: str | None = None,
) -> dict[str, object]:
    """Return evidence without environment values, credentials, or timestamps."""
    names = tuple(environment_variable_names)
    if any("=" in name or not name for name in names):
        raise ValueError("environment_variable_names must contain names only")
    expected_counts = {"collected", "passed", "failed", "skipped", "warning"}
    if set(counts) != expected_counts or any(not isinstance(value, int) or value < 0 for value in counts.values()):
        raise ValueError("counts must include non-negative collected, passed, failed, skipped, and warning values")
    return {
        "command": list(command),
        "working_directory": working_directory,
        "node_scope": node_scope,
        "marker": marker,
        "environment_variable_names": list(names),
        "dependency_summary": dict(sorted(dependency_summary.items())),
        "basetemp": basetemp,
        "counts": dict(counts),
        "failed_nodes": list(failed_nodes),
        "junit_path": junit_path,
    }


def _digest(value: Mapping[str, object]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_task_relevance_evidence(
    *, task_id: str, plan: Mapping[str, object], tests: Sequence[Mapping[str, object]],
    baseline_failures: Sequence[str], post_task_failures: Sequence[str],
    task_created_failures: Sequence[str], closure_state: str,
) -> dict[str, object]:
    """Build the one compact Verification-to-Closure evidence binding.

    The plan is the authority for required/regr. role and reason. Runner output
    tails are deliberately excluded; only pre-existing digest/redaction fields
    are retained.
    """
    plan_items = {item["command_id"]: item for item in plan.get("selected_commands", [])}
    compact = []
    for test in tests:
        item = plan_items.get(test["command_id"], {})
        required = bool(item.get("required", test["required"]))
        compact.append({
            "command_id": test["command_id"], "status": test["status"], "required": required,
            "reason": item.get("reason", "task_relevant" if required else "affected_module_regression"),
            "stdout_digest": test["stdout_digest"], "stderr_digest": test["stderr_digest"],
            "redaction_count": test["redaction_count"], "redaction_rule_version": test["redaction_rule_version"],
        })
    required = [item for item in compact if item["required"]]
    regression = [item for item in compact if not item["required"]]
    value = {
        "task_id": task_id,
        "required_tests": required,
        "regression_tests": regression,
        "required_tests_satisfied": all(item["status"] == "PASS" for item in required),
        "failure_isolation": {
            "baseline_failures": list(baseline_failures), "post_task_failures": list(post_task_failures),
            "task_created_failures": list(task_created_failures), "closure_state": closure_state,
        },
    }
    return {**value, "evidence_digest": _digest(value)}


def valid_task_relevance_evidence(value: Mapping[str, object], task_id: str) -> bool:
    if value.get("task_id") != task_id or not isinstance(value.get("evidence_digest"), str):
        return False
    unsigned = {key: item for key, item in value.items() if key != "evidence_digest"}
    return value["evidence_digest"] == _digest(unsigned)
