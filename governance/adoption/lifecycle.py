"""Provenance-bound adapter over the existing formal lifecycle components."""
from __future__ import annotations

try:
    import fcntl
except ImportError:
    fcntl = None
    import msvcrt
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from governance.adoption.evidence_registry import validate_historical_evidence_chain
from governance.adoption.lifecycle_evidence_adapter import (
    LegacyEvidenceFile, LifecycleEvidenceAdapter, ReferenceEvidence,
)
from governance.adoption.installer import digest
from governance.adoption.io import write_text_atomic
from governance.adoption.lifecycle_context import snapshot_workspace
from governance.guards.scope_guard import check as check_scope
from governance.models.project_state import ProjectState
from governance.schema_loader import load_mapping, validate_mapping
from governance.verification.command_registry import get as registry_command
from governance.verification.command_runner import run as run_command
from governance.verification.closure_evaluator import close
from governance.verification.verification_builder import build as build_verification


NEXT = {"ACTIVATED_NOT_PREFLIGHTED": "PREFLIGHT_PASSED", "PREFLIGHT_PASSED": "GUARDED", "GUARDED": "TEST_PLANNED", "TEST_PLANNED": "TEST_EXECUTED", "TEST_EXECUTED": "VERIFIED", "VERIFIED": "CLOSED"}


def _raw_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def transition_project_state(
    path: Path, *, expected_current_stage: str, expected_current_state_digest: str,
    evidence_path: Path | None = None, requested_next_stage: str, target_identity_digest: str,
    evidence_source: ReferenceEvidence | None = None,
    prior_reference_evidence: Sequence[ReferenceEvidence] = (),
) -> dict[str, Any]:
    """Validate one explicit evidence source, then atomically compare-and-swap state."""
    lock_path = path.with_name(f".{path.name}.lifecycle.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        if fcntl:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        else:
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        current_bytes = path.read_bytes()
        current_digest = hashlib.sha256(current_bytes).hexdigest()
        if current_digest != expected_current_state_digest:
            raise ValueError("STATE_TRANSITION_BLOCKED: stale ProjectState digest")
        value = load_mapping(path)
        validate_mapping(value, "project_state.schema.json"); ProjectState.from_mapping(value)
        if value.get("lifecycle_stage") != expected_current_stage or NEXT.get(expected_current_stage) != requested_next_stage:
            raise ValueError("STATE_TRANSITION_BLOCKED: invalid lifecycle state transition")
        if (evidence_path is None) == (evidence_source is None):
            raise ValueError("STATE_TRANSITION_BLOCKED: exactly one current evidence source is required")
        references = tuple(prior_reference_evidence)
        if any(not isinstance(source, ReferenceEvidence) for source in references):
            raise ValueError("STATE_TRANSITION_BLOCKED: prior reference evidence is invalid")
        by_digest = {source.binding.reference.sha256: source for source in references}
        if len(by_digest) != len(references):
            raise ValueError("STATE_TRANSITION_BLOCKED: duplicate prior reference evidence")
        used_reference_digests: set[str] = set()
        adapter = LifecycleEvidenceAdapter()

        def resolve_prior(item: Mapping[str, Any], previous_stage: str, next_stage: str, upstream: list[str]) -> str:
            source = by_digest.get(item["evidence_digest"])
            if source is None:
                raise ValueError("STATE_TRANSITION_BLOCKED: prior reference evidence is missing")
            result = adapter.resolve(
                source, previous_stage=previous_stage, next_stage=next_stage,
                target_identity_digest=target_identity_digest,
                previous_state_digest=item["previous_state_digest"], expected_upstream=upstream,
            )
            used_reference_digests.add(result.evidence_digest)
            return result.evidence_digest

        frozen_upstream = validate_historical_evidence_chain(
            value, target_identity_digest=target_identity_digest, resolve_reference=resolve_prior,
        )
        if used_reference_digests != set(by_digest):
            raise ValueError("STATE_TRANSITION_BLOCKED: unused prior reference evidence")
        source = LegacyEvidenceFile(evidence_path) if evidence_path is not None else evidence_source
        normalized = adapter.resolve(
            source, previous_stage=expected_current_stage, next_stage=requested_next_stage,
            target_identity_digest=target_identity_digest, previous_state_digest=current_digest,
            expected_upstream=frozen_upstream,
        )
        updated = dict(value)
        updated["lifecycle_stage"] = requested_next_stage
        updated["lifecycle_evidence"] = [
            *value.get("lifecycle_evidence", []),
            {"stage": requested_next_stage, "evidence_type": normalized.content["evidence_type"],
             "evidence_digest": normalized.evidence_digest,
             "previous_state_digest": current_digest, "target_identity_digest": target_identity_digest,
             "upstream_evidence_digests": frozen_upstream,
             **({"evidence_file_digest": normalized.evidence_digest,
                 "evidence_file": str(normalized.legacy_path.expanduser().resolve(strict=True))}
                if normalized.legacy_path is not None else {})},
        ]
        if requested_next_stage == "CLOSED":
            updated["closure_completed"] = True
        validate_mapping(updated, "project_state.schema.json"); ProjectState.from_mapping(updated)
        write_text_atomic(path, json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
        return updated


def build_guard_evidence(contract: Mapping[str, Any], preflight_evidence: Mapping[str, Any], root: Path, changed_paths: list[str]) -> dict[str, Any]:
    """Reuse scope_guard while retaining denied and unmatched paths for revalidation."""
    before = preflight_evidence["workspace_snapshot_digest"]
    groups = check_scope(contract, changed_paths)
    status = "BLOCKED" if groups["denied_changes"] or groups["unmatched_changes"] else "PASS"
    value = {
        "status": status, "preflight_evidence_digest": preflight_evidence["evidence_digest"],
        "task_contract_digest": hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "allowed_scope_digest": digest({"paths": contract["write_scope"]["allow"]}),
        "denied_scope_digest": digest({"paths": contract["write_scope"]["deny"]}),
        "workspace_before_digest": before, "workspace_after_digest": snapshot_workspace(root),
        "allowed_changes": groups["allowed_changes"],
        "blocked_changes": [*groups["denied_changes"], *groups["unmatched_changes"]],
    }
    value["evidence_digest"] = digest(value)
    return value


def build_adoption_test_plan(context_digest: str, guard_evidence: Mapping[str, Any], confirmed_candidates: Mapping[str, str]) -> dict[str, Any]:
    """Select only exact confirmed registry IDs and immutable command identities."""
    if guard_evidence.get("status") != "PASS" or not confirmed_candidates:
        raise ValueError("TEST_NOT_ELIGIBLE")
    selected = []
    for candidate_id, expected_digest in sorted(confirmed_candidates.items()):
        command = registry_command(candidate_id)
        if not command or digest(command) != expected_digest:
            raise ValueError("confirmed test candidate does not match registry")
        argv = command["argv"]
        # The registry may contain a local `npm test` candidate for a Node
        # project.  It is not a package-resolution operation and runs with
        # shell=False.  Reject actual installers/downloaders instead of
        # rejecting every Node smoke command by program name.
        program, arguments = argv[0], set(argv[1:])
        if program in {"pip", "pip3", "curl", "wget", "npx"} or (
            program == "npm" and arguments & {"install", "ci", "add", "update"}
        ):
            raise ValueError("unsafe confirmed test candidate")
        selected.append({"candidate_id": candidate_id, "command_digest": expected_digest, "argv": argv, "cwd": command["cwd"], "timeout_seconds": command["timeout"], "required": True})
    plan = {"context_digest": context_digest, "guard_evidence_digest": guard_evidence["evidence_digest"], "selected": selected, "status": "READY"}
    plan["test_plan_digest"] = digest(plan)
    return plan


def _safe_runner_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Whitelist the sanitized runner contract; never copy arbitrary runner output."""
    required = {"status", "exit_code", "duration_ms", "sanitized_stdout_tail", "sanitized_stderr_tail", "stdout_digest", "stderr_digest", "redaction_count", "redaction_rule_version"}
    if not required.issubset(result) or not isinstance(result["stdout_digest"], str) or not isinstance(result["stderr_digest"], str):
        return {"status": "ERROR", "exit_code": None, "duration_ms": 0, "sanitized_stdout_tail": "", "sanitized_stderr_tail": "command output sanitization failed", "stdout_digest": None, "stderr_digest": None, "redaction_count": 0, "redaction_rule_version": "1.0"}
    return {key: result[key] for key in required}


def run_adoption_test_plan(root: Path, plan: Mapping[str, Any]) -> dict[str, Any]:
    if plan.get("status") != "READY" or plan.get("test_plan_digest") != digest({key: value for key, value in plan.items() if key != "test_plan_digest"}):
        raise ValueError("invalid test plan")
    before, results = snapshot_workspace(root), []
    for item in plan["selected"]:
        command = {"argv": item["argv"], "timeout_seconds": item["timeout_seconds"]}
        safe = _safe_runner_result(run_command(command, root / item["cwd"]))
        results.append({"command_id": item["candidate_id"], "required": item["required"], **safe})
    record = {"test_plan_digest": plan["test_plan_digest"], "workspace_before_digest": before,
              "workspace_after_digest": snapshot_workspace(root), "results": results,
              "overall_status": "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL"}
    record["test_run_digest"] = digest(record)
    return record


def verify_adoption(context: Mapping[str, Any], guard: Mapping[str, Any] | None, plan: Mapping[str, Any] | None, run: Mapping[str, Any] | None, root: Path, *, current_state_path: Path | None = None, expected_target_identity_digest: str | None = None) -> dict[str, Any]:
    """Reuse verification_builder and bind its result to current state and restrictions."""
    if not guard or not plan or not run:
        return {"status": "INCOMPLETE", "evidence_digest": digest({"status": "INCOMPLETE"})}
    if run.get("workspace_after_digest") != snapshot_workspace(root):
        return {"status": "STALE", "evidence_digest": digest({"status": "STALE", "run": run.get("test_run_digest")})}
    if guard.get("status") != "PASS" or guard.get("blocked_changes"):
        return {"status": "FAILED", "evidence_digest": digest({"status": "FAILED", "reason": "denied_scope_or_guard"})}
    if context.get("blocked_decisions") and not context.get("blocked_decisions_digest"):
        return {"status": "INCOMPLETE", "evidence_digest": digest({"status": "INCOMPLETE", "reason": "blocker_provenance"})}
    state_digest = _raw_digest(current_state_path) if current_state_path else None
    if current_state_path and expected_target_identity_digest and context.get("target_identity_digest") != expected_target_identity_digest:
        return {"status": "FAILED", "evidence_digest": digest({"status": "FAILED", "reason": "target_identity"})}
    native = build_verification({"task_id": context["task_id"]}, guard, {"status": "READY"}, run["results"])
    status = "PASS" if native["completion_status"] == "VERIFIED" else "FAILED"
    value = {"status": status, "context_digest": context["context_digest"], "guard_evidence_digest": guard["evidence_digest"],
             "test_plan_digest": plan["test_plan_digest"], "test_run_digest": run["test_run_digest"],
             "workspace_digest": run["workspace_after_digest"], "target_identity_digest": context.get("target_identity_digest"),
             "project_state_digest": state_digest, "installation_provenance_digest": context.get("installation_receipt_digest"),
             "activation_provenance_digest": context.get("activation_receipt_digest"),
             "unresolved_blocker_digest": context.get("blocked_decisions_digest"),
             "denied_scope_status_digest": digest({"blocked_changes": guard.get("blocked_changes", [])}), "native_verification": native}
    value["evidence_digest"] = digest(value)
    return value


def close_adoption(verification: Mapping[str, Any], root: Path, *, current_state_path: Path | None = None, expected_state_digest: str | None = None, expected_target_identity_digest: str | None = None, unresolved_blockers: list[str] | None = None, denied_scope_violations: list[str] | None = None) -> dict[str, Any]:
    """Revalidate verification, workspace, state, provenance and restrictions before closure."""
    if verification.get("status") != "PASS" or verification.get("workspace_digest") != snapshot_workspace(root):
        raise ValueError("CLOSURE_BLOCKED")
    if expected_target_identity_digest and verification.get("target_identity_digest") != expected_target_identity_digest:
        raise ValueError("CLOSURE_BLOCKED")
    if current_state_path:
        actual = _raw_digest(current_state_path)
        # Verification binds the TEST_EXECUTED state. The subsequent registered
        # transition creates a different VERIFIED-state digest, which Closure
        # must re-read rather than mistake for stale verification evidence.
        if expected_state_digest != actual:
            raise ValueError("CLOSURE_BLOCKED")
    if not verification.get("installation_provenance_digest") or not verification.get("activation_provenance_digest") or unresolved_blockers or denied_scope_violations:
        raise ValueError("CLOSURE_BLOCKED")
    native = close(verification["native_verification"])
    if native["status"] != "CLOSED":
        raise ValueError("CLOSURE_BLOCKED")
    return {"status": "CLOSED", "closed": True, "production_ready": False, "released": False, "deployed": False,
            "closure_digest": digest({"verification": verification["evidence_digest"], "state": expected_state_digest, "status": "CLOSED"})}
