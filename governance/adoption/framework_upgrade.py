"""Bounded framework upgrades, including one pre-release template repair."""
from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from governance.adoption.installer import digest
from governance.adoption.io import write_bytes_atomic, write_json_exclusive
from governance.adoption.planner import target_identity
from governance.schema_loader import load_mapping, validate_mapping


BASELINE_COMMIT = "3e9a01fe40435fdb1bd3bff3181f1cd5dcb9da26"
PRE_RELEASE_TEMPLATE_BASELINE_COMMIT = "6743aa454440ff67e16386651cb5f7a766c5928a"
UPGRADE_ROOTS = ("governance/", "schemas/", "scripts/")
UPGRADE_FILES = ("VERSION",)
PRESERVED = {"task.yaml", "project_state.yaml"}
PRE_RELEASE_TEMPLATE_FILES = (
    "scripts/validate_governance.py",
    "tests/fixtures/compatibility/schema_baseline.json",
)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _commit_bytes(source: Path, commit: str, relative: str) -> bytes | None:
    result = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=source, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def _baseline_bytes(source: Path, relative: str) -> bytes | None:
    return _commit_bytes(source, BASELINE_COMMIT, relative)


def compile_framework_upgrade(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    source, target = source_root.resolve(strict=True), target_root.resolve(strict=True)
    if (source / "VERSION").read_text(encoding="utf-8").strip() != "1.5.2":
        raise ValueError("UPGRADE_SOURCE_VERSION_UNSUPPORTED")
    assets, conflicts = [], []
    candidates = [source / name for name in UPGRADE_FILES]
    for root_name in UPGRADE_ROOTS:
        candidates.extend(sorted((source / root_name.rstrip("/")).rglob("*")))
    for path in candidates:
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(source).as_posix(); new = path.read_bytes(); old = _baseline_bytes(source, relative)
        if old is not None and old == new:
            continue
        current_path = target / relative; current = current_path.read_bytes() if current_path.is_file() else None
        if current is not None and current != old and current != new:
            conflicts.append(relative)
        assets.append({"relative_path":relative, "source_sha256":_sha(new), "baseline_sha256":_sha(old) if old is not None else None, "target_sha256":_sha(current) if current is not None else None, "operation":"CREATE" if current is None else ("SKIP" if current == new else "MODIFY")})
    if conflicts:
        raise ValueError("UPGRADE_UNKNOWN_LOCAL_DRIFT:" + ",".join(conflicts))
    changed = [item for item in assets if item["operation"] != "SKIP"]
    value = {"schema_version":"1.0", "artifact_type":"FRAMEWORK_UPGRADE", "from_version":"1.5.1", "to_version":"1.5.2", "source_commit":BASELINE_COMMIT, "target_identity_digest":target_identity(target)["identity_digest"], "assets":changed, "writeset":[item["relative_path"] for item in changed], "preserved_paths":sorted(PRESERVED)}
    value["manifest_digest"] = digest(value); validate_mapping(value, "framework_upgrade_manifest.schema.json"); write_json_exclusive(output, value); return value


def install_framework_upgrade(source_root: Path, target_root: Path, manifest_path: Path, approval_path: Path, receipt_output: Path) -> dict[str, Any]:
    source, target = source_root.resolve(strict=True), target_root.resolve(strict=True)
    manifest, approval = load_mapping(manifest_path), load_mapping(approval_path)
    validate_mapping(manifest, "framework_upgrade_manifest.schema.json"); validate_mapping(approval, "framework_upgrade_approval.schema.json")
    if manifest.get("manifest_digest") != digest({k:v for k,v in manifest.items() if k != "manifest_digest"}): raise ValueError("UPGRADE_MANIFEST_TAMPERED")
    if approval.get("approved_by_user") is not True or approval.get("approved_action") != "UPGRADE_FRAMEWORK_1_5_1_TO_1_5_2" or approval.get("manifest_digest") != manifest["manifest_digest"] or approval.get("approved_writeset") != manifest["writeset"]: raise ValueError("UPGRADE_APPROVAL_MISMATCH")
    if target_identity(target)["identity_digest"] != manifest["target_identity_digest"]: raise ValueError("UPGRADE_TARGET_IDENTITY_MISMATCH")
    backups: dict[Path, bytes | None] = {}
    before_preserved = {name:_sha((target/name).read_bytes()) for name in PRESERVED if (target/name).is_file()}
    try:
        for asset in manifest["assets"]:
            relative = asset["relative_path"]
            if relative in PRESERVED or (relative not in UPGRADE_FILES and not relative.startswith(UPGRADE_ROOTS)): raise ValueError("UPGRADE_WRITESET_OUT_OF_BOUNDS")
            destination, source_file = target / relative, source / relative
            current = destination.read_bytes() if destination.is_file() else None
            if (asset["target_sha256"] is None) != (current is None) or (current is not None and _sha(current) != asset["target_sha256"]): raise ValueError("UPGRADE_EXTERNAL_MUTATION")
            content = source_file.read_bytes()
            if _sha(content) != asset["source_sha256"]: raise ValueError("UPGRADE_SOURCE_MUTATION")
            backups[destination] = current; write_bytes_atomic(destination, content)
    except Exception as exc:
        for path, content in reversed(list(backups.items())):
            if content is not None: write_bytes_atomic(path, content)
            elif path.exists(): path.unlink()
        raise ValueError("UPGRADE_ATOMIC_WRITE_FAILED") from exc
    after_preserved = {name:_sha((target/name).read_bytes()) for name in PRESERVED if (target/name).is_file()}
    if before_preserved != after_preserved: raise ValueError("UPGRADE_PRESERVATION_FAILED")
    receipt = {"schema_version":"1.0", "status":"UPGRADED", "from_version":"1.5.1", "to_version":"1.5.2", "manifest_digest":manifest["manifest_digest"], "approval_digest":digest(approval), "target_identity_digest":manifest["target_identity_digest"], "installed_files":manifest["writeset"], "preserved_digests":after_preserved, "completed_at":datetime.now(timezone.utc).isoformat()}
    write_json_exclusive(receipt_output, receipt); return receipt


def _pre_release_manifest_digest(value: dict[str, Any]) -> str:
    return digest({key: item for key, item in value.items() if key != "manifest_digest"})


def _require_v152(root: Path, *, label: str) -> None:
    if (root / "VERSION").read_text(encoding="utf-8").strip() != "1.5.2":
        raise ValueError(f"PRE_RELEASE_{label}_VERSION_UNSUPPORTED")


def _pre_release_source_assets(source: Path) -> tuple[list[dict[str, str]], str]:
    assets: list[dict[str, str]] = []
    baseline: dict[str, str] = {}
    for relative in PRE_RELEASE_TEMPLATE_FILES:
        old = _commit_bytes(source, PRE_RELEASE_TEMPLATE_BASELINE_COMMIT, relative)
        new = (source / relative).read_bytes()
        if old is None or old == new:
            raise ValueError("PRE_RELEASE_SOURCE_FIX_UNAVAILABLE:" + relative)
        old_hash, new_hash = _sha(old), _sha(new)
        baseline[relative] = old_hash
        assets.append({"relative_path": relative, "expected_old_sha256": old_hash, "source_sha256": new_hash})
    return assets, digest(baseline)


def compile_pre_release_generated_template_upgrade(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    """Preview only the known v1.5.2 generated-template schema repair.

    This intentionally has no generic same-version source-overwrite behavior.
    """
    source, target = source_root.resolve(strict=True), target_root.resolve(strict=True)
    _require_v152(source, label="SOURCE")
    _require_v152(target, label="TARGET")
    assets, source_baseline_digest = _pre_release_source_assets(source)
    conflicts: list[str] = []
    changed: list[dict[str, str]] = []
    for asset in assets:
        current_path = target / asset["relative_path"]
        current = current_path.read_bytes() if current_path.is_file() else None
        current_hash = _sha(current) if current is not None else None
        if current_hash not in (asset["expected_old_sha256"], asset["source_sha256"]):
            conflicts.append(asset["relative_path"])
        elif current_hash == asset["expected_old_sha256"]:
            changed.append(asset)
    if conflicts:
        raise ValueError("UPGRADE_UNKNOWN_LOCAL_DRIFT:" + ",".join(conflicts))
    value: dict[str, Any] = {
        "schema_version": "1.0",
        "artifact_type": "PRE_RELEASE_GENERATED_TEMPLATE_UPGRADE",
        "from_version": "1.5.2",
        "to_version": "1.5.2",
        "source_baseline_commit": PRE_RELEASE_TEMPLATE_BASELINE_COMMIT,
        "source_baseline_digest": source_baseline_digest,
        "target_identity_digest": target_identity(target)["identity_digest"],
        "assets": changed,
        "writeset": [asset["relative_path"] for asset in changed],
    }
    value["manifest_digest"] = _pre_release_manifest_digest(value)
    write_json_exclusive(output, value)
    return value


def approve_pre_release_generated_template_upgrade(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("manifest_digest") != _pre_release_manifest_digest(manifest):
        raise ValueError("PRE_RELEASE_MANIFEST_TAMPERED")
    return {
        "schema_version": "1.0",
        "approved_by_user": True,
        "approved_action": "UPGRADE_PRE_RELEASE_GENERATED_TEMPLATE",
        "manifest_digest": manifest["manifest_digest"],
        "target_identity_digest": manifest["target_identity_digest"],
        "approved_writeset": manifest["writeset"],
    }


def _validate_pre_release_approval(manifest: dict[str, Any], approval: dict[str, Any]) -> None:
    if manifest.get("manifest_digest") != _pre_release_manifest_digest(manifest):
        raise ValueError("PRE_RELEASE_MANIFEST_TAMPERED")
    expected = approve_pre_release_generated_template_upgrade(manifest)
    if approval != expected:
        raise ValueError("PRE_RELEASE_APPROVAL_MISMATCH")


def preflight_pre_release_generated_template_upgrade(target_root: Path, manifest_path: Path, approval_path: Path) -> dict[str, Any]:
    target = target_root.resolve(strict=True)
    manifest, approval = load_mapping(manifest_path), load_mapping(approval_path)
    _require_v152(target, label="TARGET")
    _validate_pre_release_approval(manifest, approval)
    if target_identity(target)["identity_digest"] != manifest.get("target_identity_digest"):
        raise ValueError("PRE_RELEASE_TARGET_IDENTITY_MISMATCH")
    conflicts = []
    for asset in manifest["assets"]:
        path = target / asset["relative_path"]
        current = path.read_bytes() if path.is_file() else None
        if current is None or _sha(current) != asset["expected_old_sha256"]:
            conflicts.append(asset["relative_path"])
    if conflicts:
        raise ValueError("UPGRADE_UNKNOWN_LOCAL_DRIFT:" + ",".join(conflicts))
    return {
        "schema_version": "1.0",
        "status": "PREFLIGHT_PASSED",
        "artifact_type": manifest["artifact_type"],
        "manifest_digest": manifest["manifest_digest"],
        "approval_digest": digest(approval),
        "target_identity_digest": manifest["target_identity_digest"],
        "writeset": manifest["writeset"],
    }


def install_pre_release_generated_template_upgrade(source_root: Path, target_root: Path, manifest_path: Path, approval_path: Path, preflight_path: Path, receipt_output: Path) -> dict[str, Any]:
    source, target = source_root.resolve(strict=True), target_root.resolve(strict=True)
    manifest, approval, preflight = load_mapping(manifest_path), load_mapping(approval_path), load_mapping(preflight_path)
    _require_v152(source, label="SOURCE")
    _validate_pre_release_approval(manifest, approval)
    expected_preflight = preflight_pre_release_generated_template_upgrade(target, manifest_path, approval_path)
    if preflight != expected_preflight:
        raise ValueError("PRE_RELEASE_PREFLIGHT_MISMATCH")
    writes: list[tuple[Path, bytes, bytes]] = []
    for asset in manifest["assets"]:
        relative = asset["relative_path"]
        if relative not in PRE_RELEASE_TEMPLATE_FILES:
            raise ValueError("PRE_RELEASE_WRITESET_OUT_OF_BOUNDS")
        old, new = (target / relative).read_bytes(), (source / relative).read_bytes()
        if _sha(old) != asset["expected_old_sha256"]:
            raise ValueError("UPGRADE_UNKNOWN_LOCAL_DRIFT:" + relative)
        if _sha(new) != asset["source_sha256"]:
            raise ValueError("PRE_RELEASE_SOURCE_MUTATION:" + relative)
        writes.append((target / relative, old, new))
    try:
        for destination, _, content in writes:
            write_bytes_atomic(destination, content)
    except Exception as exc:
        for destination, old, _ in reversed(writes):
            if destination.exists():
                write_bytes_atomic(destination, old)
        raise ValueError("PRE_RELEASE_ATOMIC_WRITE_FAILED") from exc
    mismatches = [str(path.relative_to(target)) for path, _, new in writes if path.read_bytes() != new]
    if mismatches:
        raise ValueError("PRE_RELEASE_POST_UPGRADE_VALIDATION_FAILED:" + ",".join(mismatches))
    receipt = {
        "schema_version": "1.0",
        "status": "UPGRADED",
        "artifact_type": manifest["artifact_type"],
        "from_version": "1.5.2",
        "to_version": "1.5.2",
        "manifest_digest": manifest["manifest_digest"],
        "approval_digest": digest(approval),
        "preflight_digest": digest(preflight),
        "target_identity_digest": manifest["target_identity_digest"],
        "installed_files": manifest["writeset"],
        "post_upgrade_validation": "PASS",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json_exclusive(receipt_output, receipt)
    return receipt
