"""Compile reviewed adoption drafts into immutable Runtime preview bundles."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from governance.adoption.exporter import BLOCKED_DECISIONS, _digest, _validate_confirmation, _validate_plan
from governance.adoption.io import text_bytes, write_bytes_exclusive, write_json_exclusive
from governance.adoption.planner import target_identity
from governance.adoption.scope_contract import assert_scope_equal, scope_digest, validate_plan_scope
from governance.adoption.writeset import canonical_sidecars, write_sidecars
from governance.adoption.contract_viability import require_adoption_lifecycle_viability
from governance.models.project_state import ProjectState
from governance.models.task_contract import TaskContract
from governance.schema_loader import load_mapping, validate_mapping


COMPILER_ID = "governance.adoption.runtime_artifact_compiler"
COMPILER_VERSION = "04E-C.3"
RUNTIME_FILENAMES = {
    "TASK_CONTRACT": "task_contract.runtime.yaml",
    "PROJECT_STATE": "project_state.runtime.yaml",
}
MANIFEST_FILENAME = "RUNTIME_ARTIFACT_MANIFEST.json"
RUNTIME_BLOCKED = (
    "production_data", "external_api", "network_access", "git_write", "release",
    "security_bypass", "business_semantic_change", "state_activation", "test_execution",
)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_digest(value: dict[str, Any], omitted_key: str | None = None) -> str:
    payload = {key: item for key, item in value.items() if key != omitted_key}
    return digest_bytes(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def compiler_identity() -> dict[str, str]:
    """Return a portable identity for every local input that affects Runtime bytes."""
    root = Path(__file__).resolve().parents[2]
    inputs = (
        "governance/adoption/runtime_artifact_compiler.py",
        "governance/adoption/scope_contract.py",
        "governance/adoption/writeset.py",
        "governance/adoption/io.py",
        "governance/adoption/contract_viability.py",
        "schemas/task_contract.schema.json",
        "schemas/project_state.schema.json",
    )
    payload = {
        "compiler_id": COMPILER_ID,
        "compiler_version": COMPILER_VERSION,
        "inputs": {name: digest_bytes((root / name).read_bytes()) for name in inputs},
    }
    return {"id": COMPILER_ID, "version": COMPILER_VERSION, "digest": canonical_digest(payload)}


def _draft(value: bytes, name: str) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(value.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid {name} draft") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"invalid {name} draft")
    return parsed


def _require_exact_drafts(plan: dict[str, Any], confirmation: dict[str, Any], drafts: dict[str, bytes]) -> None:
    expected = {"task.yaml", "project_state.yaml"}
    if set(drafts) != expected:
        raise ValueError("draft bundle does not contain the approved runtime sources")
    task, state = _draft(drafts["task.yaml"], "task"), _draft(drafts["project_state.yaml"], "project state")
    if set(task) != {"draft_status", "installation_status", "review_status", "task_id", "objective", "execution_mode", "scope_contract", "write_scope", "test_candidate", "blocked_decisions"}:
        raise ValueError("task draft has unsupported authority")
    if set(state) != {"draft_status", "activation_status", "review_status", "preflight_status", "tests_status", "verification_status", "closure_status", "blocked_decisions", "execution_mode", "scope_contract"}:
        raise ValueError("project-state draft has unsupported authority")
    scope = confirmation["scope"]
    scope_contract = validate_plan_scope(plan, require_formal=True)
    assert_scope_equal(scope_contract, task["scope_contract"], boundary="exported task draft")
    assert_scope_equal(scope_contract, state["scope_contract"], boundary="exported project-state draft")
    selected = confirmation["test_selection"]["candidate_id"]
    candidate = next((item for item in plan["test_candidates"] if item["candidate_id"] == selected), None)
    if task["draft_status"] != "UNTRUSTED_DRAFT" or task["installation_status"] != "NOT_INSTALLED" or task["review_status"] != "REQUIRES_FINAL_REVIEW":
        raise ValueError("task draft is not an untrusted adoption draft")
    if task["write_scope"] != {"allow": scope["allowed_paths"], "deny": scope["denied_paths"]}:
        raise ValueError("task draft scope does not match the confirmation")
    if task["task_id"] != scope_contract["task_id"] or task["objective"] != scope_contract["task_goal"] or task["execution_mode"] != scope_contract["execution_mode"]:
        raise ValueError("SCOPE_CONTRACT_MISMATCH: exported task identity")
    if task["test_candidate"] != (candidate["command"] if candidate else "UNRESOLVED"):
        raise ValueError("task draft candidate does not match the confirmation")
    if task["blocked_decisions"] != list(BLOCKED_DECISIONS):
        raise ValueError("task draft changed blocked decisions")
    if state != {"draft_status": "UNTRUSTED_DRAFT", "activation_status": "NOT_ACTIVATED", "review_status": "REQUIRES_FINAL_REVIEW", "preflight_status": "NOT_RUN", "tests_status": "NOT_EXECUTED", "verification_status": "NOT_COMPLETED", "closure_status": "NOT_COMPLETED", "blocked_decisions": list(BLOCKED_DECISIONS), "execution_mode": scope_contract["execution_mode"], "scope_contract": scope_contract}:
        raise ValueError("project-state draft changed installation semantics")


def _runtime_values(plan: dict[str, Any], confirmation: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    scope = confirmation["scope"]
    selected = confirmation["test_selection"]["candidate_id"]
    candidate = next((item for item in plan["test_candidates"] if item["candidate_id"] == selected), None)
    scope_contract = validate_plan_scope(plan, require_formal=True)
    task = {
        "schema_version": "1.0", "task_id": scope_contract["task_id"], "project_mode": "EXECUTION", "task_level": "B", "status": "DRAFT",
        "objective": [scope_contract["task_goal"]], "read_scope": list(scope["allowed_paths"]),
        "write_scope": {"allow": list(scope["allowed_paths"]), "deny": list(scope["denied_paths"])},
        "autonomy": {"may_debug_test_failures": False, "may_edit_adjacent_tests": False, "may_edit_same_module_helpers": False, "must_not_expand_architecture": True},
        "stop_conditions": [f"BLOCKED_DECISION:{name}" for name in RUNTIME_BLOCKED],
        "verification": {"level_1": [candidate["command"]] if candidate else [], "level_2": [], "level_3": []},
        "report": {"format": "compact", "fields": ["modified_files", "core_changes", "tests", "risks"]},
        "governance": {"level": "LEVEL_3_HIGH_RISK", "confirmation_fields": ["activation_approval"], "parent_task_id": None, "execution_envelope_rule": "GOV-ENVELOPE-001"},
        "scope_contract": scope_contract,
    }
    adapter = plan["adapter"]
    state = {"schema_version": "1.0", "project_mode": "EXECUTION", "architecture_status": "confirmed", "implementation_plan_status": "confirmed", "repository_root": ".", "adapter": adapter["primary_adapter"], "high_risk_paths": list(scope["denied_paths"]), "default_forbidden_operations": list(RUNTIME_BLOCKED), "auxiliary_adapters": list(adapter["auxiliary_adapters"]), "adapter_detection_status": adapter["status"], "status": "INSTALLED_NOT_ACTIVATED", "activated": False, "activation_status": "NOT_ACTIVATED", "activation_approval_digest": None, "activation_receipt_digest": None, "preflight_executed": False, "tests_executed": False, "verification_completed": False, "closure_completed": False, "production_ready": False, "release_authorized": False, "network_authorized": False, "git_write_authorized": False, "lifecycle_stage": "INSTALLED_NOT_ACTIVATED", "lifecycle_evidence": []}
    return task, state


def compile_runtime_artifacts(
    plan: dict[str, Any], confirmation: dict[str, Any], export_manifest: dict[str, Any],
    drafts: dict[str, bytes], target_root: Path,
) -> tuple[dict[str, bytes], dict[str, Any], dict[str, dict[str, Any]]]:
    """Create validated Runtime bytes and their approval-ready manifest in memory."""
    _validate_plan(plan, target_root=target_root)
    _validate_confirmation(plan, confirmation)
    if export_manifest.get("plan_digest") != plan["plan_digest"] or export_manifest.get("confirmation_digest") != _digest(confirmation, omitted_keys=()):
        raise ValueError("export manifest does not bind the confirmed inputs")
    _require_exact_drafts(plan, confirmation, drafts)
    task, state = _runtime_values(plan, confirmation)
    require_adoption_lifecycle_viability(task)
    validate_mapping(task, "task_contract.schema.json")
    validate_mapping(state, "project_state.schema.json")
    TaskContract.from_mapping(task)
    ProjectState.from_mapping(state)
    files = {
        RUNTIME_FILENAMES["TASK_CONTRACT"]: text_bytes(yaml.safe_dump(task, allow_unicode=True, sort_keys=False)),
        RUNTIME_FILENAMES["PROJECT_STATE"]: text_bytes(yaml.safe_dump(state, allow_unicode=True, sort_keys=False)),
    }
    sidecars = canonical_sidecars(plan=plan, root=target_root, runtime_files=files)
    identity = compiler_identity()
    manifest = {
        "schema_version": "1.0", "compiler_id": identity["id"], "compiler_version": identity["version"], "compiler_digest": identity["digest"],
        "plan_digest": plan["plan_digest"], "confirmation_digest": _digest(confirmation, omitted_keys=()), "export_manifest_digest": canonical_digest(export_manifest),
        "source_draft_digests": {name: digest_bytes(value) for name, value in sorted(drafts.items())},
        "scope_contract_digest": scope_digest(plan["scope_contract"]),
        "provenance_receipt_digest": plan["provenance_receipt"]["provenance_receipt_digest"],
        "sidecar_digests": {
            "INSTALL_WRITESET.json": sidecars["INSTALL_WRITESET.json"]["writeset_digest"],
            "PRE_INSTALL_HASHES.json": sidecars["PRE_INSTALL_HASHES.json"]["pre_install_hashes_digest"],
            "ROLLBACK_MANIFEST.json": sidecars["ROLLBACK_MANIFEST.json"]["rollback_manifest_digest"],
        },
        "runtime_artifacts": [
            {"artifact_type": "TASK_CONTRACT", "relative_path": RUNTIME_FILENAMES["TASK_CONTRACT"], "sha256": digest_bytes(files[RUNTIME_FILENAMES["TASK_CONTRACT"]]), "schema": "task_contract.schema.json", "loader": "TaskContract.from_mapping"},
            {"artifact_type": "PROJECT_STATE", "relative_path": RUNTIME_FILENAMES["PROJECT_STATE"], "sha256": digest_bytes(files[RUNTIME_FILENAMES["PROJECT_STATE"]]), "schema": "project_state.schema.json", "loader": "ProjectState.from_mapping"},
        ],
    }
    manifest["manifest_digest"] = canonical_digest(manifest)
    validate_mapping(manifest, "runtime_artifact_manifest.schema.json")
    return files, manifest, sidecars


def _assert_external_empty_output(output_dir: Path, target: Path) -> Path:
    output = output_dir.expanduser().resolve(strict=False)
    if output.exists() and (output.is_symlink() or not output.is_dir() or any(output.iterdir())):
        raise ValueError("runtime artifact output directory must be absent or empty")
    resolved_target = target.expanduser().resolve(strict=True)
    try:
        output.resolve(strict=False).relative_to(resolved_target)
    except ValueError:
        return output
    raise ValueError("runtime artifact output must be outside target project")


def compile_runtime_bundle(plan_path: Path, confirmation_path: Path, draft_bundle: Path, output_dir: Path, target_root: Path) -> dict[str, Any]:
    """Write one new external preview bundle; it never changes the target project."""
    plan, confirmation = load_mapping(plan_path), load_mapping(confirmation_path)
    target = target_root.expanduser().resolve(strict=True)
    if plan["target_identity"] != target_identity(target):
        raise ValueError("current target does not match original plan identity")
    export_manifest = load_mapping(draft_bundle / "EXPORT_MANIFEST.json")
    drafts = {"task.yaml": (draft_bundle / "task.yaml.draft").read_bytes(), "project_state.yaml": (draft_bundle / "project_state.yaml.draft").read_bytes()}
    files, manifest, sidecars = compile_runtime_artifacts(plan, confirmation, export_manifest, drafts, target)
    output = _assert_external_empty_output(output_dir, target)
    created_output = not output.exists()
    output.mkdir(parents=True, exist_ok=True)
    try:
        for name, content in files.items():
            write_bytes_exclusive(output / name, content)
        write_json_exclusive(output / MANIFEST_FILENAME, manifest)
        write_sidecars(output, sidecars)
    except Exception:
        # The directory was confirmed absent; no pre-existing output can be destroyed.
        if created_output:
            for path in output.iterdir():
                path.unlink()
            output.rmdir()
        raise
    return manifest
