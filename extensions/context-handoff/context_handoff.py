"""Optional, opt-in derived context views for the Context Handoff extension."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parent
STATE_DIR = ".agent_context_handoff"
EVENTS = {"TASK_STARTED", "HARD_BLOCKED", "EXECUTION_COMPLETED", "PHASE_CLOSED", "REMOTE_MERGED", "RELEASE_STATUS_CHANGED"}
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
MAX_INDEX_TASKS = 20
LOCK_TIMEOUT_SECONDS = 5.0
LOCK_STALE_SECONDS = 30.0


def _token(value: str, label: str) -> str:
    if not SAFE_TOKEN.fullmatch(value):
        raise ValueError(f"{label} must be 1-80 letters, digits, underscores, or hyphens")
    return value


def _git(root: Path, *args: str, fallback: str = "UNKNOWN") -> str:
    try:
        return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip() or fallback
    except (OSError, subprocess.CalledProcessError):
        return fallback


def _load_mapping(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("evidence input must be a YAML or JSON object")
    return value


def _single(values: Any, default: str) -> str:
    if not isinstance(values, list) or not values:
        return default
    unique = {str(value) for value in values if value is not None}
    return next(iter(unique)) if len(unique) == 1 else "CONFLICT_REQUIRES_REVIEW"


def build_snapshot(target: Path, project_id: str, task_id: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a derived view from structured local input; never infer authority from prose."""
    target = target.resolve()
    evidence = evidence or {}
    task_status = _single(evidence.get("task_statuses"), "UNKNOWN")
    verification_status = _single(evidence.get("verification_statuses"), "UNKNOWN")
    conflict = "CONFLICT_REQUIRES_REVIEW" in {task_status, verification_status}
    remote_merged = evidence.get("remote_merge_status") == "REMOTE_MERGED" and bool(evidence.get("pr_url")) and bool(evidence.get("merge_commit"))
    final_status = "CONFLICT_REQUIRES_REVIEW" if conflict else ("REMOTE_MERGED" if remote_merged else "LOCAL_ONLY")
    authoritative = [str(path) for path in evidence.get("authoritative_files", []) if isinstance(path, str)]
    if not authoritative:
        authoritative = [str(path.relative_to(target)) for path in (target / "docs").glob("*.md") if path.name in {"IMPLEMENTATION_PLAN.md", "ARCHITECTURE.md", "CHANGELOG.md"}]
    dirty = _git(target, "status", "--porcelain")
    snapshot = {
        "schema_version": "1.0", "project_id": project_id, "project_name": str(evidence.get("project_name") or target.name), "task_id": task_id,
        "report_type": "CURRENT_STATE_SNAPSHOT", "task_status": task_status, "repository": str(target), "branch": _git(target, "branch", "--show-current"), "head": _git(target, "rev-parse", "HEAD"),
        "worktree_status": "UNKNOWN" if dirty == "UNKNOWN" else ("DIRTY" if dirty else "CLEAN"), "verification_status": verification_status, "final_status": final_status,
        "blockers": [str(value) for value in evidence.get("blockers", [])], "next_gate": str(evidence.get("next_gate") or "REVIEW_AUTHORITATIVE_EVIDENCE"),
        "next_action": str(evidence.get("next_action") or "Provide structured task and verification evidence."), "authoritative_files": authoritative,
        "supersedes": evidence.get("supersedes"), "superseded_by": evidence.get("superseded_by"), "generated_at": str(evidence.get("generated_at") or datetime.now(timezone.utc).isoformat()),
    }
    for key in ("pr_url", "merge_commit", "release_status", "deployment_status", "external_api_requests", "production_writes", "database_writes", "workspace_baseline_id", "environment_id", "runtime_bundle_id", "machine_manifest_id", "side_effect_gate_summary", "autonomous_budget_summary"):
        if key in evidence:
            snapshot[key] = evidence[key]
    return snapshot


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    schema = json.loads((ROOT / "schemas" / "current_state_snapshot.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(snapshot)
    rendered = yaml.safe_dump(snapshot, allow_unicode=True, sort_keys=False)
    if len(rendered.splitlines()) > 40:
        raise ValueError("snapshot exceeds the 40-line token policy")


def _render(name: str, values: dict[str, Any]) -> str:
    text = (ROOT / "templates" / name).read_text(encoding="utf-8")
    normalized = dict(values)
    if "blockers" in values:
        normalized["blockers"] = ", ".join(values["blockers"]) or "None"
    if "authoritative_files" in values:
        normalized["authoritative_files"] = "\n".join(f"- {path}" for path in values["authoritative_files"]) or "- UNKNOWN"
    for key, value in normalized.items():
        text = text.replace("{{ " + key + " }}", str(value))

    optional_fields = ["workspace_baseline_id", "environment_id", "runtime_bundle_id", "machine_manifest_id", "side_effect_gate_summary", "autonomous_budget_summary"]
    extras = [f"- {k}: {normalized[k]}" for k in optional_fields if k in normalized]
    if extras:
        text += "\n\n## Governance Identity\n" + "\n".join(extras) + "\n"

    return text


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class _ProjectLock:
    def __init__(self, path: Path) -> None:
        self.path = path

    def __enter__(self) -> "_ProjectLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        while True:
            try:
                descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(json.dumps({"pid": os.getpid(), "created_at": time.time()}) + "\n")
                return self
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                    if age > LOCK_STALE_SECONDS:
                        self.path.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"PROJECT_LOCK_TIMEOUT: {self.path}")
                time.sleep(0.02)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def paths_for(target: Path, project_id: str, task_id: str) -> dict[str, Path]:
    base = target / STATE_DIR
    project = base / project_id
    return {"state": base / "extension_state.yaml", "ownership": base / "ownership.json", "ownership_lock": base / ".ownership.lock", "current": project / f"CURRENT_STATE__{task_id}.md", "index": project / "DOCUMENT_INDEX.md", "proposed_index": project / "DOCUMENT_INDEX.proposed.md", "lock": project / ".index.lock", "snapshot": project / "snapshots" / f"{task_id}.yaml", "handoff": project / "handoffs" / f"{task_id}.md"}


def desired_files(target: Path, project_id: str, task_id: str, evidence: dict[str, Any]) -> dict[str, bytes]:
    snapshot = build_snapshot(target, project_id, task_id, evidence)
    validate_snapshot(snapshot)
    return {"current": _render("CURRENT_STATE.md.template", snapshot).encode(), "snapshot": yaml.safe_dump(snapshot, allow_unicode=True, sort_keys=False).encode(), "handoff": _render("CONTEXT_HANDOFF.md.template", snapshot).encode()}


def _relative(target: Path, path: Path) -> str:
    return str(path.relative_to(target)).replace("\\", "/")


def _load_project_snapshots(target: Path, project_id: str) -> tuple[list[tuple[dict[str, Any], Path]], list[str]]:
    directory = target / STATE_DIR / project_id / "snapshots"
    valid, warnings = [], []
    if not directory.exists():
        return valid, warnings
    for path in sorted(directory.glob("*.yaml"), key=lambda item: item.stem):
        try:
            value = _load_mapping(path)
            validate_snapshot(value)
            if value["project_id"] != project_id or value["task_id"] != path.stem:
                raise ValueError("project_id or task_id does not match the snapshot path")
            valid.append((value, path))
        except (OSError, ValueError, ValidationError, yaml.YAMLError, json.JSONDecodeError) as exc:
            warnings.append(f"INVALID_TASK_SNAPSHOT: {_relative(target, path)} ({exc})")
    return valid, warnings


def _render_index(target: Path, project_id: str, snapshots: list[tuple[dict[str, Any], Path]], warnings: list[str]) -> bytes:
    rows = []
    for snapshot, snapshot_path in snapshots[:MAX_INDEX_TASKS]:
        task_id = snapshot["task_id"]
        handoff = target / STATE_DIR / project_id / "handoffs" / f"{task_id}.md"
        files = ", ".join(snapshot["authoritative_files"]) or "UNKNOWN"
        rows.extend((
            f"## {task_id}",
            f"- task_status: {snapshot['task_status']}; verification_status: {snapshot['verification_status']}; final_status: {snapshot['final_status']}",
            f"- generated_at: {snapshot['generated_at']}",
            f"- snapshot_path: {_relative(target, snapshot_path)}; handoff_path: {_relative(target, handoff)}",
            f"- authoritative_files: {files}",
        ))
    archived = max(0, len(snapshots) - MAX_INDEX_TASKS)
    warning_rows = ["## Warnings", *[f"- {warning}" for warning in warnings]] if warnings else []
    text = _render("DOCUMENT_INDEX.md.template", {"project_id": project_id, "entries": "\n".join(rows) or "No valid task snapshots.", "archived_count": archived, "warnings": "\n".join(warning_rows)})
    if len(text.splitlines()) > 150:
        raise ValueError("document index exceeds the 150-line token policy")
    return text.encode()


def _rebuild_index(target: Path, project_id: str, paths: dict[str, Path], ownership: dict[str, Any]) -> tuple[str, list[str]]:
    snapshots, warnings = _load_project_snapshots(target, project_id)
    content = _render_index(target, project_id, snapshots, warnings)
    index = paths["index"]
    recorded = ownership["files"].get(str(index))
    if index.exists() and (recorded is None or _digest(index.read_bytes()) != recorded):
        _atomic_write(paths["proposed_index"], content)
        ownership["files"][str(paths["proposed_index"])] = _digest(content)
        return "OWNERSHIP_CONFLICT", warnings
    _atomic_write(index, content)
    ownership["files"][str(index)] = _digest(content)
    return ("ENABLED_WITH_WARNINGS" if warnings else "ENABLED"), warnings


def preview(target: Path, project_id: str, task_id: str, evidence: dict[str, Any]) -> dict[str, Any]:
    _token(project_id, "project_id"); _token(task_id, "task_id")
    paths = paths_for(target.resolve(), project_id, task_id)
    return {"action": "preview", "writes": [str(paths[key]) for key in ("state", "ownership", "current", "index", "snapshot", "handoff") if not paths[key].exists()], "modifies": [str(path) for path in paths.values() if path.exists()], "will_not_modify": ["Core rules", "Core CLI", "task.yaml", "project_state.yaml", "formal reports", "remote systems"], "compatibility": "core_schema=1.0; optional; default-disabled", "conflicts": [str(path) for path in paths.values() if path.exists() and path.name not in {"extension_state.yaml", "ownership.json"}], "owned_paths": [str(paths["state"]), str(paths["ownership"])]}


def _load_ownership(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "files": {}}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("files"), dict):
        raise ValueError("invalid extension ownership manifest")
    return value


def enable(target: Path, project_id: str, task_id: str, evidence: dict[str, Any], event: str) -> dict[str, Any]:
    if event not in EVENTS:
        raise ValueError("enable requires an approved state event")
    target = target.resolve(); _token(project_id, "project_id"); _token(task_id, "task_id")
    paths = paths_for(target, project_id, task_id)
    desired = desired_files(target, project_id, task_id, evidence)
    with _ProjectLock(paths["ownership_lock"]), _ProjectLock(paths["lock"]):
        ownership = _load_ownership(paths["ownership"])
        for key, content in desired.items():
            path = paths[key]; recorded = ownership["files"].get(str(path))
            if path.exists() and (recorded is None or _digest(path.read_bytes()) != recorded):
                raise ValueError(f"CONFLICT_REQUIRES_REVIEW: refusing to overwrite {path}")
        state = {"id": "context-handoff", "enabled": True, "default_enabled": False, "event": event, "project_id": project_id, "task_id": task_id}
        for key, content in desired.items():
            path = paths[key]
            if not path.exists() or path.read_bytes() != content:
                _atomic_write(path, content)
            ownership["files"][str(path)] = _digest(content)
        state_bytes = yaml.safe_dump(state, sort_keys=False).encode()
        _atomic_write(paths["state"], state_bytes); ownership["files"][str(paths["state"])] = _digest(state_bytes)
        status, warnings = _rebuild_index(target, project_id, paths, ownership)
        _atomic_write(paths["ownership"], (json.dumps(ownership, indent=2, sort_keys=True) + "\n").encode())
    generated = [str(paths[key]) for key in (*desired, "index")]
    if status == "OWNERSHIP_CONFLICT":
        generated[-1] = str(paths["proposed_index"])
    return {"status": status, "event": event, "generated": generated, "warnings": warnings}


def disable(target: Path) -> dict[str, Any]:
    base = target.resolve() / STATE_DIR; path = base / "extension_state.yaml"
    if not path.exists():
        return {"status": "ALREADY_DISABLED"}
    ownership_path = base / "ownership.json"
    with _ProjectLock(base / ".ownership.lock"):
        state = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or state.get("id") != "context-handoff":
            raise ValueError("CONFLICT_REQUIRES_REVIEW: state file is not extension-owned")
        state["enabled"] = False; content = yaml.safe_dump(state, sort_keys=False).encode(); _atomic_write(path, content)
        ownership = _load_ownership(ownership_path)
        ownership["files"][str(path)] = _digest(content)
        _atomic_write(ownership_path, (json.dumps(ownership, indent=2, sort_keys=True) + "\n").encode())
    return {"status": "DISABLED", "history_preserved": True}


def uninstall(target: Path, apply: bool = False) -> dict[str, Any]:
    target = target.resolve(); base = target / STATE_DIR; ownership_path = base / "ownership.json"
    ownership = _load_ownership(ownership_path)
    removable, preserved = [], []
    for name, digest in ownership["files"].items():
        path = Path(name).resolve()
        if not path.is_relative_to(base):
            preserved.append(path)
            continue
        if path.exists() and _digest(path.read_bytes()) == digest and path.name in {"extension_state.yaml"}:
            removable.append(path)
        elif path.exists():
            preserved.append(path)
    lock_files = sorted([base / ".ownership.lock", *base.glob("*/.index.lock")])
    controls = [ownership_path, *lock_files]
    result = {"status": "UNINSTALL_PLAN" if not apply else "UNINSTALLED", "deletion_plan": [str(path) for path in removable] + ([str(ownership_path)] if ownership_path.exists() else []), "control_files": [str(path) for path in controls], "history_preserved": True, "preserved_history_count": len(preserved)}
    if apply:
        for path in removable: path.unlink()
        if ownership_path.exists(): ownership_path.unlink()
    return result
