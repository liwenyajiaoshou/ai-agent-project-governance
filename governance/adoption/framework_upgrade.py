"""Bounded v1.5.1-to-v1.5.2 framework upgrade preview and installation."""
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
UPGRADE_ROOTS = ("governance/", "schemas/", "scripts/")
UPGRADE_FILES = ("VERSION",)
PRESERVED = {"task.yaml", "project_state.yaml"}


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _baseline_bytes(source: Path, relative: str) -> bytes | None:
    result = subprocess.run(["git", "show", f"{BASELINE_COMMIT}:{relative}"], cwd=source, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


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
