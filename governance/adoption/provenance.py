"""Truthful toolchain-provenance binding for public adoption planning."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from governance.schema_loader import validate_mapping


SOURCE_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_GENERATION_PATH = "scripts/agent_adopt.py:dry-run"
GENERATOR_SOURCE_BASIS = "git_head_blob"
GENERATOR_SOURCE_CONTRACT_VERSION = 2
GIT_COMMAND_TIMEOUT_SECONDS = 10
GENERATOR_INPUTS = (
    "VERSION",
    "scripts/agent_adopt.py",
    "governance/adoption/planner.py",
    "governance/adoption/provenance.py",
    "governance/adoption/scope_contract.py",
    "schemas/adoption_plan.schema.json",
    "schemas/adoption_scope_input.schema.json",
    "schemas/adoption_provenance_receipt.schema.json",
)


def canonical_digest(value: Mapping[str, Any], *, omit: tuple[str, ...] = ()) -> str:
    payload = {key: item for key, item in value.items() if key not in omit}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def framework_version(source_root: Path | None = None) -> str:
    return ((source_root or SOURCE_ROOT) / "VERSION").read_text(encoding="utf-8").strip()


def _run_git(root: Path, *args: str, input_data: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    executable = git_executable()
    if executable is None:
        raise ValueError("Git provenance unavailable: executable not found")
    try:
        result = subprocess.run(
            [executable, "-C", str(root), *args],
            capture_output=True,
            check=False,
            input=input_data,
            timeout=GIT_COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"Git provenance unavailable: {exc}") from exc
    return result


def _require_git_success(root: Path, operation: str, *args: str) -> bytes:
    result = _run_git(root, *args)
    if result.returncode != 0:
        raise ValueError(f"Git provenance unavailable: {operation} failed")
    return result.stdout


def _generator_input_paths(inputs: tuple[str, ...]) -> tuple[str, ...]:
    if not inputs:
        raise ValueError("Git provenance unavailable: generator input set is empty")
    normalized: list[str] = []
    for relative_path in inputs:
        path = PurePosixPath(relative_path)
        if (
            path.is_absolute()
            or relative_path != path.as_posix()
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            raise ValueError(f"Git provenance unavailable: unsafe generator input path {relative_path!r}")
        normalized.append(relative_path)
    return tuple(normalized)


@lru_cache(maxsize=16)
def _repository_root(root_path: str) -> Path:
    resolved_root = Path(root_path).resolve()
    top_level = Path(
        _require_git_success(resolved_root, "repository root lookup", "rev-parse", "--show-toplevel").decode("utf-8").strip(),
    ).resolve()
    if top_level != resolved_root:
        raise ValueError("Git provenance unavailable: generator source root is not the repository root")
    return resolved_root


def _generator_repository_root(root: Path) -> tuple[Path, str]:
    repository_root = _repository_root(str(root.resolve()))
    head = _require_git_success(repository_root, "HEAD lookup", "rev-parse", "HEAD").decode("utf-8").strip()
    return repository_root, head


def _require_clean_generator_sources(root: Path, paths: tuple[str, ...]) -> None:
    result = _run_git(root, "status", "--porcelain=v1", "--untracked-files=no", "--", *paths)
    if result.returncode != 0:
        raise ValueError("Git provenance unavailable: generator source status check failed")
    for line in result.stdout.decode("utf-8", errors="replace").splitlines():
        if len(line) < 2:
            raise ValueError("Git provenance unavailable: malformed generator source status")
        if line[0] != " ":
            raise ValueError("generator source index contains staged changes")
        if line[1] != " ":
            raise ValueError("generator source working tree is dirty")


def _require_generator_inputs_tracked(root: Path, paths: tuple[str, ...]) -> None:
    tracked = _run_git(root, "ls-files", "--error-unmatch", "--", *paths)
    if tracked.returncode != 0:
        raise ValueError("Git provenance unavailable: generator input is not tracked")
    listed = set(tracked.stdout.decode("utf-8").splitlines())
    missing = [relative_path for relative_path in paths if relative_path not in listed]
    if missing:
        raise ValueError(f"Git provenance unavailable: generator input is not tracked: {missing[0]}")


@lru_cache(maxsize=128)
def _head_blob_digest(
    repository_root: str, head: str, paths: tuple[str, ...], source_basis: str, contract_version: int,
) -> str:
    root = Path(repository_root)
    requests = b"".join(f"{head}:{relative_path}\n".encode("utf-8") for relative_path in paths)
    result = _run_git(root, "cat-file", "--batch", input_data=requests)
    if result.returncode != 0:
        raise ValueError("Git provenance unavailable: HEAD blob batch read failed")
    payload = result.stdout
    offset = 0
    rows: dict[str, str] = {}
    for relative_path in paths:
        line_end = payload.find(b"\n", offset)
        if line_end < 0:
            raise ValueError(f"Git provenance unavailable: HEAD blob unavailable: {relative_path}")
        header = payload[offset:line_end].split()
        if len(header) != 3 or header[1] != b"blob":
            raise ValueError(f"Git provenance unavailable: HEAD blob unavailable: {relative_path}")
        try:
            size = int(header[2])
        except ValueError as exc:
            raise ValueError(f"Git provenance unavailable: malformed HEAD blob: {relative_path}") from exc
        data_start = line_end + 1
        data_end = data_start + size
        if data_end >= len(payload) or payload[data_end:data_end + 1] != b"\n":
            raise ValueError(f"Git provenance unavailable: malformed HEAD blob: {relative_path}")
        rows[relative_path] = hashlib.sha256(payload[data_start:data_end]).hexdigest()
        offset = data_end + 1
    if offset != len(payload):
        raise ValueError("Git provenance unavailable: unexpected HEAD blob batch output")
    return canonical_digest(rows)


def generator_source_digest(*, root: Path | None = None, inputs: tuple[str, ...] = GENERATOR_INPUTS) -> str:
    """Digest fixed generator inputs from clean Git HEAD blobs, never checkout bytes."""
    repository_root, head = _generator_repository_root(root or SOURCE_ROOT)
    paths = _generator_input_paths(inputs)
    _require_clean_generator_sources(repository_root, paths)
    _require_generator_inputs_tracked(repository_root, paths)
    return _head_blob_digest(
        str(repository_root), head, paths, GENERATOR_SOURCE_BASIS, GENERATOR_SOURCE_CONTRACT_VERSION,
    )


@lru_cache(maxsize=1)
def command_contract_digest() -> str:
    return canonical_digest({
        "entrypoint": PUBLIC_GENERATION_PATH,
        "required": ["--project-root", "--scope-file", "--format", "--output", "dry-run"],
        "target_write_policy": "FORBIDDEN",
    })


@lru_cache(maxsize=1)
def git_executable() -> str | None:
    """Resolve Git without assuming Windows GUI PATH inheritance."""
    discovered = shutil.which("git")
    if discovered:
        return discovered
    if os.name == "nt":
        candidates = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "cmd" / "git.exe",
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Git" / "cmd" / "git.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    return None


def git_metadata(root: Path) -> dict[str, str]:
    def run(*args: str) -> str:
        executable = git_executable()
        if executable is None:
            return "UNAVAILABLE"
        try:
            result = subprocess.run(
                [executable, "-C", str(root), *args], text=True, encoding="utf-8", errors="replace",
                capture_output=True, check=False,
            )
        except OSError:
            return "UNAVAILABLE"
        return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"
    return {"branch": run("branch", "--show-current") or "DETACHED", "head": run("rev-parse", "HEAD")}


def build_provenance_receipt(
    *, target_identity: Mapping[str, Any], target_root: Path, plan_payload_digest: str,
    formal_scope_digests: Mapping[str, str] | None, generation_path: str, source_root: Path | None = None,
) -> dict[str, Any]:
    trusted_root = source_root or SOURCE_ROOT
    target_git = git_metadata(target_root)
    framework_git = git_metadata(trusted_root)
    source_digest = generator_source_digest(root=trusted_root)
    receipt: dict[str, Any] = {
        "schema_version": "1.0",
        "binding_type": "TOOLCHAIN_PROVENANCE_BINDING",
        "generator_id": "ai-agent-project-governance-planner",
        "generator_version": framework_version(trusted_root),
        "generator_source_digest": source_digest,
        "generator_source_basis": GENERATOR_SOURCE_BASIS,
        "generator_source_contract_version": GENERATOR_SOURCE_CONTRACT_VERSION,
        "generation_path": generation_path,
        "generation_command_contract_digest": command_contract_digest(),
        "formal_scope_input_digest": (formal_scope_digests or {}).get("raw_sha256", hashlib.sha256(b"").hexdigest()),
        "formal_scope_normalized_text_digest": (formal_scope_digests or {}).get("normalized_text_sha256", hashlib.sha256(b"").hexdigest()),
        "target_identity": dict(target_identity),
        "target_branch": target_git["branch"],
        "target_head": target_git["head"],
        "framework_commit": framework_git["head"],
        "plan_payload_digest": plan_payload_digest,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    receipt["provenance_receipt_digest"] = canonical_digest(receipt)
    validate_mapping(receipt, "adoption_provenance_receipt.schema.json")
    return receipt


def validate_provenance_receipt(
    plan: Mapping[str, Any], *, target_root: Path | None = None, require_public_cli: bool,
) -> dict[str, Any]:
    receipt = plan.get("provenance_receipt")
    if not isinstance(receipt, dict):
        raise ValueError("SUPERSEDED_REQUIRES_FRESH_DRY_RUN")
    validate_mapping(receipt, "adoption_provenance_receipt.schema.json")
    if receipt["provenance_receipt_digest"] != canonical_digest(receipt, omit=("provenance_receipt_digest",)):
        raise ValueError("provenance receipt digest does not match receipt contents")
    if receipt["plan_payload_digest"] != plan.get("plan_digest"):
        raise ValueError("provenance plan payload digest does not match plan digest")
    if receipt["generator_source_basis"] != GENERATOR_SOURCE_BASIS:
        raise ValueError("generator source basis does not match current provenance contract")
    if receipt["generator_source_contract_version"] != GENERATOR_SOURCE_CONTRACT_VERSION:
        raise ValueError("generator source contract version does not match current provenance contract")
    current_source_digest = generator_source_digest()
    if receipt["generator_version"] != framework_version():
        raise ValueError("generator version does not match repository VERSION")
    if receipt["generator_source_digest"] != current_source_digest:
        raise ValueError("generator source digest does not match current toolchain")
    if receipt["generation_command_contract_digest"] != command_contract_digest():
        raise ValueError("generation command contract digest does not match public CLI")
    if require_public_cli and receipt["generation_path"] != PUBLIC_GENERATION_PATH:
        raise ValueError("FORMAL_SCOPE_FLOW_ONLY: private planner calls cannot masquerade as public CLI")
    if git_metadata(SOURCE_ROOT)["head"] != receipt["framework_commit"]:
        raise ValueError("framework commit mismatch")
    if target_root is not None:
        current = git_metadata(target_root)
        if current["branch"] != receipt["target_branch"] or current["head"] != receipt["target_head"]:
            raise ValueError("target branch/HEAD mismatch")
    return receipt
