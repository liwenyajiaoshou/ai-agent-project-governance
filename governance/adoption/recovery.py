"""Exact-byte recovery of an activated, not-yet-preflighted adoption Runtime."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from governance.adoption.contract_viability import require_adoption_lifecycle_viability
from governance.adoption.installer import digest
from governance.adoption.io import text_bytes, write_bytes_atomic, write_json_exclusive
from governance.adoption.planner import target_identity
from governance.models.task_contract import TaskContract, supersede
from governance.schema_loader import load_mapping, validate_mapping


def _raw(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _approval_fresh(value: dict[str, Any]) -> None:
    if value.get("approved_by_user") is not True or value.get("approved_action") != "RECOVER_ACTIVATED_TASK_CONTRACT":
        raise ValueError("RECOVERY_APPROVAL_REQUIRED")
    try:
        expires = datetime.fromisoformat(value["expires_at"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("RECOVERY_APPROVAL_INVALID") from exc
    if expires <= datetime.now(timezone.utc):
        raise ValueError("RECOVERY_APPROVAL_EXPIRED")


def compile_contract_recovery(target_root: Path, successor_task: Path, installation_receipt: Path, activation_receipt: Path, output: Path) -> dict[str, Any]:
    target = target_root.expanduser().resolve(strict=True)
    old_path, state_path = target / "task.yaml", target / "project_state.yaml"
    old, successor, state = load_mapping(old_path), load_mapping(successor_task), load_mapping(state_path)
    install, activation = load_mapping(installation_receipt), load_mapping(activation_receipt)
    validate_mapping(install, "adoption_installation_receipt.schema.json"); validate_mapping(activation, "activation_receipt.schema.json")
    if install.get("target_identity_digest") != target_identity(target)["identity_digest"] or activation.get("target_identity_digest") != install.get("target_identity_digest") or activation.get("installation_receipt_digest") != digest(install):
        raise ValueError("RECOVERY_INSTALLATION_ACTIVATION_EVIDENCE_INVALID")
    if install.get("file_hashes", {}).get("task.yaml") != _raw(old_path) or activation.get("task_contract_digest") != _raw(old_path):
        raise ValueError("RECOVERY_OLD_TASK_PROVENANCE_INVALID")
    validate_mapping(old, "task_contract.schema.json"); validate_mapping(successor, "task_contract.schema.json")
    validate_mapping(state, "project_state.schema.json")
    if state.get("status") != "ACTIVATED_NOT_PREFLIGHTED" or state.get("lifecycle_stage") != "ACTIVATED_NOT_PREFLIGHTED":
        raise ValueError("RECOVERY_UNSUPPORTED_LIFECYCLE_STATE")
    require_adoption_lifecycle_viability(successor)
    if successor.get("supersession"):
        raise ValueError("SUCCESSOR_ALREADY_BOUND")
    if set(successor["write_scope"]["allow"]) - set(old["write_scope"]["allow"]):
        scope_delta = sorted(set(successor["write_scope"]["allow"]) - set(old["write_scope"]["allow"]))
    else:
        scope_delta = []
    old_model, successor_model = TaskContract.from_mapping(old), TaskContract.from_mapping(successor)
    old_active = old_model if old_model.status == "ACTIVE" else TaskContract.from_mapping({**old, "status": "ACTIVE"})
    successor_active = successor_model if successor_model.status == "ACTIVE" else TaskContract.from_mapping({**successor, "status": "ACTIVE"})
    supersession = supersede(old_active, successor_active, "BOUND_BY_RECOVERY_APPROVAL").supersession
    bound = {**successor_active.to_mapping(), "supersession": supersession}
    successor_bytes = text_bytes(json.dumps(bound, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    value = {
        "schema_version": "1.0", "artifact_type": "ADOPTION_TASK_CONTRACT_RECOVERY",
        "target_identity_digest": target_identity(target)["identity_digest"],
        "expected_state": "ACTIVATED_NOT_PREFLIGHTED", "old_task_digest": _raw(old_path),
        "old_state_digest": _raw(state_path), "successor_task_digest": hashlib.sha256(successor_bytes).hexdigest(),
        "successor_task": bound, "scope_delta": scope_delta,
        "writeset": ["task.yaml", "project_state.yaml"],
        "installation_receipt_digest": digest(install), "activation_receipt_digest": digest(activation),
        "upstream_evidence_digests": [item.get("evidence_file_digest", item["evidence_digest"]) for item in state.get("lifecycle_evidence", [])],
    }
    value["manifest_digest"] = digest(value)
    validate_mapping(value, "adoption_recovery_manifest.schema.json")
    write_json_exclusive(output, value)
    return value


def recover_approved(target_root: Path, manifest_path: Path, approval_path: Path, installation_receipt: Path, activation_receipt: Path, evidence_output: Path) -> dict[str, Any]:
    target = target_root.expanduser().resolve(strict=True)
    task_path, state_path = target / "task.yaml", target / "project_state.yaml"
    manifest, approval, state = load_mapping(manifest_path), load_mapping(approval_path), load_mapping(state_path)
    validate_mapping(manifest, "adoption_recovery_manifest.schema.json"); validate_mapping(approval, "adoption_recovery_approval.schema.json")
    if digest(load_mapping(installation_receipt)) != manifest.get("installation_receipt_digest") or digest(load_mapping(activation_receipt)) != manifest.get("activation_receipt_digest"):
        raise ValueError("RECOVERY_EVIDENCE_MUTATED")
    if manifest.get("manifest_digest") != digest({k: v for k, v in manifest.items() if k != "manifest_digest"}):
        raise ValueError("RECOVERY_MANIFEST_TAMPERED")
    _approval_fresh(approval)
    if approval.get("manifest_digest") != manifest["manifest_digest"] or approval.get("target_identity_digest") != manifest["target_identity_digest"]:
        raise ValueError("RECOVERY_APPROVAL_SCOPE_MISMATCH")
    if approval.get("approved_writeset") != manifest["writeset"] or approval.get("approved_scope_delta") != manifest["scope_delta"]:
        raise ValueError("RECOVERY_APPROVAL_SCOPE_MISMATCH")
    if target_identity(target)["identity_digest"] != manifest["target_identity_digest"] or _raw(task_path) != manifest["old_task_digest"] or _raw(state_path) != manifest["old_state_digest"]:
        raise ValueError("RECOVERY_EXTERNAL_MUTATION")
    if state.get("status") != "ACTIVATED_NOT_PREFLIGHTED" or state.get("lifecycle_stage") != "ACTIVATED_NOT_PREFLIGHTED":
        raise ValueError("RECOVERY_UNSUPPORTED_LIFECYCLE_STATE")
    successor = manifest["successor_task"]
    validate_mapping(successor, "task_contract.schema.json"); require_adoption_lifecycle_viability(successor)
    successor_bytes = text_bytes(json.dumps(successor, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    if hashlib.sha256(successor_bytes).hexdigest() != manifest["successor_task_digest"]:
        raise ValueError("RECOVERY_SUCCESSOR_TAMPERED")
    approval_digest = digest(approval)
    evidence = {"schema_version": "1.0", "evidence_type": "RecoveryEvidence", "status": "RECOVERED", "target_identity_digest": manifest["target_identity_digest"], "previous_state_digest": manifest["old_state_digest"], "upstream_evidence_digests": manifest["upstream_evidence_digests"], "payload": {"old_task_digest": manifest["old_task_digest"], "successor_task_digest": manifest["successor_task_digest"], "approval_digest": approval_digest, "manifest_digest": manifest["manifest_digest"]}}
    write_json_exclusive(evidence_output, evidence)
    evidence_digest = _raw(evidence_output)
    updated = dict(state)
    updated["lifecycle_evidence"] = [*state.get("lifecycle_evidence", []), {"stage": "ACTIVATED_NOT_PREFLIGHTED", "evidence_type": "recovery_approval", "evidence_digest": evidence_digest, "evidence_file_digest": evidence_digest, "evidence_file": str(evidence_output.resolve(strict=True)), "previous_state_digest": manifest["old_state_digest"], "target_identity_digest": manifest["target_identity_digest"], "upstream_evidence_digests": manifest["upstream_evidence_digests"]}]
    validate_mapping(updated, "project_state.schema.json")
    old_task_bytes, old_state_bytes = task_path.read_bytes(), state_path.read_bytes()
    try:
        write_bytes_atomic(task_path, successor_bytes)
        write_bytes_atomic(state_path, text_bytes(yaml.safe_dump(updated, allow_unicode=True, sort_keys=False)))
    except Exception as exc:
        write_bytes_atomic(task_path, old_task_bytes); write_bytes_atomic(state_path, old_state_bytes)
        raise ValueError("RECOVERY_ATOMIC_WRITE_FAILED") from exc
    return evidence
