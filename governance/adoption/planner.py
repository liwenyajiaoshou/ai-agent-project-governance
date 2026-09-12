"""Assemble a safe, local-only adoption plan without changing the target project."""
from __future__ import annotations

import json
import unicodedata
from hashlib import sha256
from pathlib import Path
from typing import Any

from governance.adapters import detect_adapters, get
from governance.adoption.io import raw_and_normalized_digests
from governance.adoption.provenance import build_provenance_receipt
from governance.adoption.scope_contract import load_formal_scope
from governance.audit.checks import run_audit
from governance.schema_loader import validate_mapping


SOURCE_ROOT = Path(__file__).resolve().parents[2]
MAX_COMPARISON_BYTES = 128 * 1024
HUMAN_TEXT_SUFFIXES = {".md", ".txt", ".rst"}
ASSETS = (
    ("AGENTS.md", "AGENTS.md", "Agent-facing project boundary instructions."),
    ("agent_rules", "agent_rules", "Reusable governance rules; tailor project-specific rules manually."),
    ("config/presets", "config/presets", "Preset definitions for review, not an automatic selection."),
    ("governance", "governance", "Local runtime package; ownership requires review."),
    ("schemas", "schemas", "Runtime data contracts; preserve version compatibility."),
    ("scripts/agent_preflight.py", "scripts/agent_preflight.py", "Preflight entry point after approved configuration."),
    ("scripts/agent_state.py", "scripts/agent_state.py", "State entry point; do not activate automatically."),
    ("scripts/agent_guard.py", "scripts/agent_guard.py", "Guard entry point after explicit state activation."),
    ("scripts/agent_test_plan.py", "scripts/agent_test_plan.py", "Test-plan entry point; commands require review."),
    ("scripts/agent_test_run.py", "scripts/agent_test_run.py", "Test runner; never execute from this planner."),
    ("scripts/agent_verify.py", "scripts/agent_verify.py", "Verification entry point after reviewed evidence."),
    ("scripts/agent_close.py", "scripts/agent_close.py", "Closure entry point after verified evidence."),
)

FIELD_SEMANTICS = {
    "audit_configuration_completeness_score": {
        "meaning": "Fixed-weight completeness score produced by the existing local adoption audit.",
        "does_not_mean": "It is not a security certification, adoption approval, or product readiness score.",
    },
    "adapter_detection_confidence": {
        "meaning": "Strength of supported-stack markers found by the existing detector.",
        "does_not_mean": "It does not prove the stack is complete, compatible, safe, or authorized for adoption.",
    },
    "test_candidate_confidence": {
        "meaning": "Completeness of static local evidence for a candidate command.",
        "does_not_mean": "It does not prove a command will pass, avoid network or writes, or have human approval to run.",
    },
    "preset_recommendation_confidence": {
        "meaning": "Completeness of the local audit evidence behind the recommendation.",
        "does_not_mean": "It is not an automatic preset choice or authorization to copy or activate governance assets.",
    },
}


def _sha256(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_COMPARISON_BYTES:
            return None
        return sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _asset_entry(source_relative: str, target_relative: str, ownership_note: str, root: Path) -> dict[str, object]:
    source = SOURCE_ROOT / source_relative
    target = root / target_relative
    entry: dict[str, object] = {
        "source": source_relative,
        "target": target_relative,
        "conflict": False,
        "ownership_note": ownership_note,
        "requires_confirmation": True,
    }
    if not source.exists():
        entry["operation"] = "MISSING_SOURCE"
    elif not target.exists():
        entry["operation"] = "CREATE"
    elif source.is_file() and target.is_file():
        source_hash = _sha256(source)
        target_hash = _sha256(target)
        if source_hash is not None:
            entry["source_raw_sha256"] = source_hash
        if target_hash is not None:
            entry["target_raw_sha256"] = target_hash
        same = source_hash is not None and source_hash == target_hash
        if source.suffix.lower() in HUMAN_TEXT_SUFFIXES and source_hash is not None and target_hash is not None:
            try:
                source_identity = raw_and_normalized_digests(source.read_bytes())
                target_identity_value = raw_and_normalized_digests(target.read_bytes())
            except UnicodeDecodeError:
                pass
            else:
                entry["source_normalized_text_sha256"] = source_identity["normalized_text_sha256"]
                entry["target_normalized_text_sha256"] = target_identity_value["normalized_text_sha256"]
                same = source_identity["normalized_text_sha256"] == target_identity_value["normalized_text_sha256"]
        entry["operation"] = "EXISTS_SAME" if same else "EXISTS_DIFFERENT"
        entry["conflict"] = not same
    else:
        entry["operation"] = "REQUIRES_CONFIRMATION"
        entry["conflict"] = True
        entry["ownership_note"] += " Existing directories or unlike path types are not compared recursively."
    return entry


def _asset_manifest(root: Path) -> list[dict[str, object]]:
    return [_asset_entry(source, target, note, root) for source, target, note in ASSETS]


def _marker_evidence(detection: Any, adapter_id: str) -> list[str]:
    for evidence in detection.evidence:
        if evidence.adapter_id == adapter_id:
            return list(evidence.matched_markers)
    return []


def _candidate(candidate_id: str, command: str, evidence: list[str], confidence: str, scope: str) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "command": command,
        "evidence": evidence,
        "confidence": confidence,
        "estimated_scope": scope,
        "network_risk": "unknown_until_review",
        "write_risk": "unknown_until_review",
        "requires_confirmation": True,
    }


def _test_candidates(root: Path, detection: Any) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    adapters = set(detection.detected_adapters)
    if "python" in adapters and (root / "tests").is_dir():
        evidence = _marker_evidence(detection, "python") + ["tests/"]
        candidates.append(_candidate("python-project-tests", "python3 -m unittest discover -s tests", evidence, "medium", "Python tests below tests/"))
    node = get("node")
    if node and ("node" in adapters or "wechat_miniprogram" in adapters) and "test" in node.package_scripts(root):
        evidence = _marker_evidence(detection, "node") + ["package.json:scripts.test"]
        candidates.append(_candidate("node-package-test", "npm test", evidence, "high", "Project package.json test script"))
    if not candidates:
        candidates.append(_candidate("generic-python-smoke", "python3 -c pass", ["generic local smoke"], "medium", "No project-specific test runner detected"))
    return candidates


IDENTITY_MARKERS = ("pyproject.toml", "package.json", "requirements.txt", "go.mod", "Cargo.toml", "Makefile")


def target_identity(project_root: Path) -> dict[str, object]:
    """Return a privacy-preserving, stable identity for one local target project."""
    root = project_root.expanduser().resolve(strict=True)
    marker_rows = []
    for name in IDENTITY_MARKERS:
        marker = root / name
        if marker.is_file():
            marker_rows.append({"name": name, "sha256": sha256(marker.read_bytes()).hexdigest()})
    canonical_root_fingerprint = sha256(str(root).encode("utf-8")).hexdigest()
    project_markers_digest = sha256(json.dumps(marker_rows, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    value = {
        "canonical_root_fingerprint": canonical_root_fingerprint,
        "project_markers_digest": project_markers_digest,
        "git_repository": (root / ".git").exists(),
    }
    value["identity_digest"] = sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return value


def validate_unique_candidate_ids(candidates: list[dict[str, object]]) -> None:
    """Reject ambiguous identifiers after normalization, before any export can occur."""
    seen: set[str] = set()
    for candidate in candidates:
        raw = candidate.get("candidate_id")
        if not isinstance(raw, str) or not raw:
            raise ValueError("test candidate ID must be a non-empty string")
        normalized = unicodedata.normalize("NFC", raw).strip().casefold()
        if not normalized or normalized in seen:
            raise ValueError("duplicate test candidate ID")
        seen.add(normalized)


def _audit_mapping(root: Path) -> dict[str, object]:
    audit = run_audit(root)
    return {
        "schema_version": audit.schema_version,
        "tool_version": audit.tool_version,
        "configuration_completeness_score": audit.score,
        "level": audit.level,
        "recommended_preset": audit.recommended_preset,
        "checks": [check.to_dict() for check in audit.checks],
        "score_meaning": FIELD_SEMANTICS["audit_configuration_completeness_score"]["meaning"],
        "score_does_not_mean": FIELD_SEMANTICS["audit_configuration_completeness_score"]["does_not_mean"],
    }


def _adapter_mapping(root: Path) -> tuple[Any, dict[str, object]]:
    detection = detect_adapters(root)
    return detection, {
        "schema_version": detection.schema_version,
        "primary_adapter": detection.primary_adapter,
        "detected_adapters": list(detection.detected_adapters),
        "auxiliary_adapters": list(detection.auxiliary_adapters),
        "detection_confidence": detection.confidence,
        "confidence_meaning": FIELD_SEMANTICS["adapter_detection_confidence"]["meaning"],
        "confidence_does_not_mean": FIELD_SEMANTICS["adapter_detection_confidence"]["does_not_mean"],
        "evidence": [item.to_mapping() for item in detection.evidence],
        "conflicts": list(detection.conflicts),
        "status": detection.status,
    }


def _preset_recommendation(audit: dict[str, object], detection: Any) -> dict[str, object]:
    recommendation = str(audit["recommended_preset"])
    alternatives = [item for item in ("lightweight", "standard", "strict") if item != recommendation]
    confidence = "medium" if detection.status == "DETECTED" else "low"
    evidence = [f"audit:{check['check_id']}={check['status']}" for check in audit["checks"] if check["status"] != "PASS"]
    return {
        "recommendation": recommendation,
        "reason": "Recommendation is reused from the local configuration-completeness audit and requires owner review.",
        "evidence": evidence or ["all audit checks passed"],
        "confidence": confidence,
        "confidence_meaning": FIELD_SEMANTICS["preset_recommendation_confidence"]["meaning"],
        "confidence_does_not_mean": FIELD_SEMANTICS["preset_recommendation_confidence"]["does_not_mean"],
        "alternatives": alternatives,
        "requires_confirmation": True,
    }


def _task_draft() -> dict[str, object]:
    return {
        "draft_status": "UNTRUSTED_DRAFT",
        "authorization": "REQUIRES_CONFIRMATION",
        "task_id": "UNRESOLVED",
        "objective": "UNRESOLVED: define one reversible first task.",
        "read_scope": ["UNRESOLVED"],
        "write_scope": {"allow": [], "deny": ["production/**", "secrets/**", ".env", ".agent_state/**", "deploy/**", "data/production/**"]},
        "test_command": "UNRESOLVED",
        "note": "This is not a valid or authorized task.yaml. Review every field before creating a file.",
    }


def _scope_candidates(task_draft: dict[str, object]) -> list[dict[str, object]]:
    """Expose reviewable scope choices without treating them as authorization."""
    return [{
        "candidate_id": "scope-default",
        "allowed_paths": list(task_draft["write_scope"]["allow"]),
        "denied_paths": list(task_draft["write_scope"]["deny"]),
        "scope_contract": task_draft.get("scope_contract"),
        "requires_confirmation": True,
    }]

def _parse_and_validate_scope(scope_file: Path | None) -> tuple[dict[str, object] | None, str]:
    """Compatibility wrapper for focused parser tests."""
    if not scope_file:
        return None, sha256(b"").hexdigest()
    scope, digests = load_formal_scope(scope_file)
    return scope, digests["raw_sha256"]


def _project_state_draft() -> dict[str, object]:
    return {
        "draft_status": "UNTRUSTED_DRAFT",
        "authorization": "REQUIRES_CONFIRMATION",
        "project_mode": "UNRESOLVED",
        "architecture_status": "UNRESOLVED",
        "implementation_plan_status": "UNRESOLVED",
        "adapter": "RECOMMENDATION_ONLY",
        "high_risk_paths": ["UNRESOLVED"],
        "default_forbidden_operations": ["production_write", "external_api", "git_write", "release", "deployment"],
        "note": "This is not a valid or authorized project_state.yaml and is never written by the planner.",
    }


def _confirmations() -> list[dict[str, str]]:
    return [
        {"area": "preset", "reason": "A recommendation does not select a preset.", "status": "REQUIRES_CONFIRMATION"},
        {"area": "asset_manifest", "reason": "Every create, conflict, ownership, and overwrite decision needs review.", "status": "REQUIRES_CONFIRMATION"},
        {"area": "task_scope", "reason": "Allowed and denied paths cannot be inferred safely.", "status": "REQUIRES_CONFIRMATION"},
        {"area": "project_state", "reason": "Mode and high-risk paths determine runtime behavior.", "status": "REQUIRES_CONFIRMATION"},
        {"area": "test_command", "reason": "Candidates are not approved to execute.", "status": "REQUIRES_CONFIRMATION"},
    ]


def _blocked_decisions() -> list[dict[str, str]]:
    decisions = (
        "production data or database access",
        "credentials, secrets, external APIs, or network access",
        "Git writes, release, deployment, or remote repository operations",
        "business-semantic or security-policy changes",
        "state activation, test execution, asset copying, or formal configuration generation",
    )
    return [{"decision": decision, "reason": "The read-only planner has no authority to decide or perform this action.", "status": "MUST_NOT_AUTO_DECIDE"} for decision in decisions]


def _next_commands(root: Path, candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    commands: list[dict[str, object]] = [
        {"command": "Review this dry-run plan and resolve required confirmations.", "requires_confirmation": False, "note": "No target-project modification occurs."},
        {"command": "python3 scripts/agent_audit.py --project-root <target-project> --format json", "requires_confirmation": False, "note": "Optional repeated read-only audit."},
    ]
    if candidates:
        commands.append({"command": "Review one test candidate before adding it to an approved task plan.", "requires_confirmation": True, "note": "Do not run the candidate from this planner."})
    if any((root / target).exists() for _, target, _ in ASSETS):
        commands.append({"command": "Resolve existing asset conflicts manually against the reviewed manifest.", "requires_confirmation": True, "note": "No copy or overwrite command is generated."})
    return commands


def _warnings(detection: Any, candidates: list[dict[str, object]]) -> list[str]:
    warnings = ["This dry-run plan did not modify the target project, create .agent_state, copy assets, or run tests."]
    if detection.confidence == "low":
        warnings.append("Adapter detection is low confidence; treat the stack and test guidance as unresolved until reviewed.")
    if not candidates:
        warnings.append("No reliable test candidate was found. Do not guess or execute a command automatically.")
    return warnings


def _scope_bound_drafts(scope_data: dict[str, Any] | None) -> tuple[dict[str, object], dict[str, object]]:
    task_draft = _task_draft()
    project_state_draft = _project_state_draft()
    if scope_data is None:
        project_state_draft["execution_mode"] = "UNRESOLVED"
        return task_draft, project_state_draft
    task_draft.update({
        "task_id": scope_data["task_id"],
        "objective": scope_data["task_goal"],
        "authorization": "INJECTED_FROM_SCOPE",
        "note": "Task draft injected from formal scope input. Review required.",
        "scope_contract": scope_data,
    })
    task_draft["write_scope"] = {"allow": scope_data["allowed_paths"], "deny": scope_data["denied_paths"]}
    if scope_data["known_safe_commands"]:
        task_draft["test_command"] = scope_data["known_safe_commands"][0]
    project_state_draft.update({
        "project_mode": scope_data["execution_mode"],
        "execution_mode": scope_data["execution_mode"],
        "authorization": "INJECTED_FROM_SCOPE",
    })
    return task_draft, project_state_draft


def build_plan(
    project_root: Path,
    scope_file: Path | None = None,
    *,
    generation_path: str = "governance.adoption.planner.build_plan",
    provenance_source_root: Path | None = None,
) -> dict[str, object]:
    """Build and schema-validate an untrusted adoption plan using reads only."""
    root = project_root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError("--project-root must be an existing directory")

    if scope_file:
        scope_data, formal_scope_digests = load_formal_scope(scope_file)
    else:
        scope_data, formal_scope_digests = None, None

    detection, adapter = _adapter_mapping(root)
    audit = _audit_mapping(root)
    candidates = _test_candidates(root, detection)
    validate_unique_candidate_ids(candidates)
    manifest = _asset_manifest(root)
    # Local import avoids a module cycle while keeping one canonical classifier.
    from governance.adoption.writeset import classify_install_paths
    install_classifications = classify_install_paths(manifest, root)
    task_draft, project_state_draft = _scope_bound_drafts(scope_data)
    from governance.adoption.contract_viability import adoption_lifecycle_viability
    lifecycle_viability = adoption_lifecycle_viability(task_draft)

    target_id = target_identity(root)

    value: dict[str, object] = {
        "schema_version": "1.0",
        "mode": "dry-run",
        "project_root": "<target-project>",
        "read_only": True,
        "target_identity": target_id,
        "scope_contract": scope_data,
        "field_semantics": FIELD_SEMANTICS,
        "adapter": adapter,
        "audit": audit,
        "preset_recommendation": _preset_recommendation(audit, detection),
        "test_candidates": candidates,
        "asset_manifest": manifest,
        "install_classifications": install_classifications,
        "conflicts": [item for item in manifest if item["conflict"]],
        "task_draft": task_draft,
        "scope_candidates": _scope_candidates(task_draft),
        "project_state_draft": project_state_draft,
        "adoption_lifecycle_viability": lifecycle_viability,
        "required_confirmations": _confirmations(),
        "blocked_decisions": _blocked_decisions(),
        "next_commands": _next_commands(root, candidates),
        "rollback_checklist": [
            "No target-project changes occurred in this dry run.",
            "Before any future write, create a normal backup or branch approved by the project owner.",
            "For each approved create or overwrite, record the target and its recovery source before applying it.",
            "Do not execute rollback automatically; review the approved change set first.",
        ],
        "warnings": _warnings(detection, candidates),
    }
    value["plan_digest"] = sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    value["provenance_receipt"] = build_provenance_receipt(
        target_identity=target_id,
        target_root=root,
        plan_payload_digest=value["plan_digest"],
        formal_scope_digests=formal_scope_digests,
        generation_path=generation_path,
        source_root=provenance_source_root,
    )

    validate_mapping(value, "adoption_plan.schema.json")
    return value
