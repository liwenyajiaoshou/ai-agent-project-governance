"""Bounded, provenance-checked activation for an installed adoption Runtime."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from governance.adoption.installer import digest
from governance.adoption.io import text_bytes, write_json_exclusive, write_text_atomic
from governance.adoption.planner import target_identity
from governance.adoption.runtime_artifact_compiler import MANIFEST_FILENAME, canonical_digest, compiler_identity, digest_bytes
from governance.adoption.contract_viability import require_adoption_lifecycle_viability
from governance.adoption.writeset import SIDECAR_FILES, load_and_validate_sidecars
from governance.models.project_state import ProjectState
from governance.models.task_contract import TaskContract
from governance.schema_loader import load_mapping, validate_mapping


def _external_new(path: Path, target: Path) -> Path:
    value = path.expanduser().resolve(strict=False)
    if value.exists():
        raise ValueError("activation receipt path must be new and outside the target project")
    try:
        value.relative_to(target)
    except ValueError:
        return value
    raise ValueError("activation receipt path must be new and outside the target project")


def _external_existing(path: Path, target: Path, label: str) -> Path:
    value = path.expanduser().resolve(strict=True)
    try:
        value.relative_to(target)
    except ValueError:
        return value
    raise ValueError(f"{label} must be outside the target project")


def _exclusive_json(path: Path, value: dict[str, Any]) -> None:
    write_json_exclusive(path, value)


def _finalize_json(path: Path, value: dict[str, Any]) -> None:
    write_text_atomic(path, json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _replace_mapping(path: Path, value: dict[str, Any]) -> None:
    write_text_atomic(path, yaml.safe_dump(value, allow_unicode=True, sort_keys=False))


def _runtime_manifest(path: Path, target: Path) -> tuple[dict[str, Any], Path]:
    value = _external_existing(path, target, "runtime artifact manifest")
    if value.name != MANIFEST_FILENAME:
        raise ValueError("runtime artifact manifest filename is invalid")
    root = value.parent
    expected = {MANIFEST_FILENAME, "task_contract.runtime.yaml", "project_state.runtime.yaml", *SIDECAR_FILES}
    if {item.name for item in root.iterdir()} != expected:
        raise ValueError("runtime artifact bundle contains unapproved extra files")
    manifest = load_mapping(value)
    validate_mapping(manifest, "runtime_artifact_manifest.schema.json")
    if manifest["manifest_digest"] != canonical_digest(manifest, "manifest_digest"):
        raise ValueError("runtime artifact manifest digest does not match its contents")
    load_and_validate_sidecars(root)
    return manifest, root


def _validate_inputs(target: Path, task_path: Path, state_path: Path, manifest_path: Path, final_approval_path: Path, install_receipt_path: Path, activation_approval_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if task_path.expanduser().resolve(strict=True) != target / "task.yaml" or state_path.expanduser().resolve(strict=True) != target / "project_state.yaml":
        raise ValueError("adoption activation requires canonical task.yaml and project_state.yaml")
    manifest, _ = _runtime_manifest(manifest_path, target)
    final_approval = load_mapping(_external_existing(final_approval_path, target, "final install approval"))
    installation_receipt = load_mapping(_external_existing(install_receipt_path, target, "installation receipt"))
    approval = load_mapping(_external_existing(activation_approval_path, target, "activation approval"))
    validate_mapping(final_approval, "adoption_final_approval.schema.json")
    validate_mapping(installation_receipt, "adoption_installation_receipt.schema.json")
    validate_mapping(approval, "activation_approval.schema.json")
    task, state = load_mapping(task_path), load_mapping(state_path)
    validate_mapping(task, "task_contract.schema.json"); TaskContract.from_mapping(task)
    validate_mapping(state, "project_state.schema.json"); ProjectState.from_mapping(state)
    require_adoption_lifecycle_viability(task)
    return manifest, final_approval, installation_receipt, approval, task, state


def _verify_provenance(target: Path, manifest: dict[str, Any], final_approval: dict[str, Any], install: dict[str, Any], approval: dict[str, Any], task_path: Path, state_path: Path) -> None:
    task_digest, state_digest = digest_bytes(task_path.read_bytes()), digest_bytes(state_path.read_bytes())
    artifacts = {item["artifact_type"]: item for item in manifest["runtime_artifacts"]}
    if target_identity(target)["identity_digest"] != approval["target_identity_digest"] or install["target_identity_digest"] != approval["target_identity_digest"]:
        raise ValueError("target identity does not match activation approval")
    if manifest["manifest_digest"] != approval["runtime_artifact_manifest_digest"] or manifest["manifest_digest"] != install["runtime_artifact_manifest_digest"]:
        raise ValueError("runtime manifest provenance does not match activation approval")
    if digest(final_approval) != approval["final_install_approval_digest"] or digest(install) != approval["installation_receipt_digest"]:
        raise ValueError("approval does not bind current installation provenance")
    identity = {"id": manifest["compiler_id"], "version": manifest["compiler_version"], "digest": manifest["compiler_digest"]}
    if identity != compiler_identity() or identity != approval["compiler"] or identity != final_approval["compiler"] or identity != install["compiler"]:
        raise ValueError("compiler identity does not match approved Runtime preview")
    if task_digest != artifacts["TASK_CONTRACT"]["sha256"] or task_digest != final_approval["runtime_artifacts"]["task_contract"]["sha256"] or task_digest != install["file_hashes"]["task.yaml"] or task_digest != approval["runtime_artifacts"]["task_contract_sha256"]:
        raise ValueError("installed TaskContract bytes do not match approved provenance")
    if state_digest != artifacts["PROJECT_STATE"]["sha256"] or state_digest != final_approval["runtime_artifacts"]["project_state"]["sha256"] or state_digest != install["file_hashes"]["project_state.yaml"] or state_digest != approval["runtime_artifacts"]["project_state_sha256"] or state_digest != approval["expected_current_state"]["project_state_sha256"]:
        raise ValueError("installed ProjectState bytes do not match approved provenance")
    if install["status"] != "INSTALLED_NOT_ACTIVATED" or not install["installed"] or install["activated"] or any(install[name] for name in ("tests_executed", "verification_completed", "closure_completed")):
        raise ValueError("installation receipt is not eligible for activation")


def activate_approved(target_root: Path, task_contract: Path, project_state: Path, runtime_artifact_manifest: Path, final_install_approval: Path, installation_receipt: Path, activation_approval: Path, activation_receipt_output: Path) -> dict[str, Any]:
    """Perform only the installed-to-activated state transition after exact revalidation."""
    target = target_root.expanduser().resolve(strict=True)
    manifest, final, install, approval, task, state = _validate_inputs(target, task_contract, project_state, runtime_artifact_manifest, final_install_approval, installation_receipt, activation_approval)
    _verify_provenance(target, manifest, final, install, approval, task_contract, project_state)
    if state["status"] != "INSTALLED_NOT_ACTIVATED" or state.get("activated") or state.get("activation_status") != "NOT_ACTIVATED":
        raise ValueError("project state is not eligible for activation")
    output = _external_new(activation_receipt_output, target)
    approval_digest = digest(approval)
    binding_digest = hashlib.sha256(json.dumps({"target_identity_digest": approval["target_identity_digest"], "activation_approval_digest": approval_digest, "project_state_digest_before": digest_bytes(project_state.read_bytes()), "task_contract_digest": digest_bytes(task_contract.read_bytes())}, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    activated_state = dict(state)
    activated_state.update({"status": "ACTIVATED_NOT_PREFLIGHTED", "activated": True, "activation_status": "ACTIVATED_NOT_PREFLIGHTED", "activation_approval_digest": approval_digest, "activation_receipt_digest": binding_digest, "lifecycle_stage": "ACTIVATED_NOT_PREFLIGHTED", "lifecycle_evidence": [{"stage": "ACTIVATED_NOT_PREFLIGHTED", "evidence_type": "activation_approval", "evidence_digest": approval_digest, "previous_state_digest": digest_bytes(project_state.read_bytes())}]})
    validate_mapping(activated_state, "project_state.schema.json"); ProjectState.from_mapping(activated_state)
    before_digest, after_bytes = digest_bytes(project_state.read_bytes()), text_bytes(yaml.safe_dump(activated_state, allow_unicode=True, sort_keys=False))
    after_digest = digest_bytes(after_bytes)
    receipt = {"schema_version": "1.0", "status": "PENDING_ACTIVATION", "target_identity_digest": approval["target_identity_digest"], "runtime_artifact_manifest_digest": manifest["manifest_digest"], "final_install_approval_digest": digest(final), "installation_receipt_digest": digest(install), "activation_approval_digest": approval_digest, "activation_receipt_binding_digest": binding_digest, "compiler_id": manifest["compiler_id"], "compiler_version": manifest["compiler_version"], "compiler_digest": manifest["compiler_digest"], "task_contract_digest": digest_bytes(task_contract.read_bytes()), "project_state_digest_before": before_digest, "project_state_digest_after": after_digest, "activated": False, "preflight_executed": False, "tests_executed": False, "verification_completed": False, "closure_completed": False}
    validate_mapping(receipt, "activation_receipt.schema.json")
    _exclusive_json(output, receipt)
    try:
        _replace_mapping(project_state, activated_state)
        if digest_bytes(project_state.read_bytes()) != after_digest:
            raise ValueError("activated ProjectState digest did not persist")
        receipt.update({"status": "ACTIVATED_NOT_PREFLIGHTED", "activated": True})
        validate_mapping(receipt, "activation_receipt.schema.json")
        _finalize_json(output, receipt)
        return receipt
    except Exception as exc:
        raise ValueError("ACTIVATED_REQUIRES_MANUAL_REVIEW") from exc
