"""Public-CLI fixtures for normal Existing Project Adoption success paths."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from governance.adoption import build_plan, compile_runtime_bundle, export_drafts, install_approved
from governance.adoption.approval_candidate import approve_install_candidate, build_approval_candidate, write_approval_candidate
from governance.adoption.exporter import confirmation_candidate
from governance.adoption.io import write_json_exclusive, write_yaml_exclusive
from governance.adoption.provenance import PUBLIC_GENERATION_PATH


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tests" / "agent_adopt_test_launcher.py"


def run_cli(*args: str) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, encoding="utf-8",
        capture_output=True, check=False, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )
    if result.returncode:
        raise AssertionError(f"public adoption CLI failed ({result.returncode}): {result.stderr or result.stdout}")


def formal_inputs(
    base: Path, target: Path, *, stem: str = "flow", allowed_paths: list[str] | None = None,
    execution_mode: str = "ACTIVE_DEVELOPMENT", confirmed: bool = True,
) -> tuple[dict[str, Any], Path, Path, Path]:
    allowed = ["src/core/**"] if allowed_paths is None else allowed_paths
    scope = {
        "task_id": f"CASE001-{stem.upper()}",
        "task_goal": "Verify one reversible governed adoption task.",
        "execution_mode": execution_mode,
        "allowed_paths": allowed,
        "denied_paths": ["data/**", ".env"],
        "known_safe_commands": ["python -m unittest"],
        "network_policy": "BLOCKED",
        "data_write_policy": "BLOCKED",
        "git_policy": "BLOCKED",
        "owner_confirmed_empty_scope": execution_mode == "OBSERVATION_ONLY",
    }
    scope_path = base / f"{stem}-scope.yaml"
    plan_path = base / f"{stem}-plan.json"
    confirmation_path = base / f"{stem}-confirmation.yaml"
    scope_path.write_text(yaml.safe_dump(scope, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    plan = build_plan(target, scope_path, generation_path=PUBLIC_GENERATION_PATH)
    write_json_exclusive(plan_path, plan)
    write_yaml_exclusive(confirmation_path, confirmation_candidate(plan, confirmed_by_user=confirmed))
    return plan, plan_path, confirmation_path, scope_path


def preview_inputs(
    base: Path, target: Path, *, stem: str = "flow", allowed_paths: list[str] | None = None,
    confirmed: bool = True,
) -> tuple[dict[str, Any], Path, Path, Path, Path, Path]:
    plan, plan_path, confirmation_path, _ = formal_inputs(
        base, target, stem=stem, allowed_paths=allowed_paths, confirmed=confirmed,
    )
    drafts, runtime, candidate = base / f"{stem}-drafts", base / f"{stem}-runtime", base / f"{stem}-approval-candidate.yaml"
    export_drafts(plan_path, confirmation_path, drafts, target)
    compile_runtime_bundle(plan_path, confirmation_path, drafts, runtime, target)
    write_approval_candidate(candidate, build_approval_candidate(
        plan_path=plan_path, confirmation_path=confirmation_path, draft_bundle=drafts,
        runtime_bundle=runtime, target_root=target,
    ))
    return plan, plan_path, confirmation_path, drafts, runtime, candidate


def approved_inputs(
    base: Path, target: Path, *, stem: str = "flow", allowed_paths: list[str] | None = None,
) -> tuple[dict[str, Any], Path, Path, Path, Path, Path]:
    plan, plan_path, confirmation_path, drafts, runtime, candidate = preview_inputs(
        base, target, stem=stem, allowed_paths=allowed_paths, confirmed=True,
    )
    approval = base / f"{stem}-approval.yaml"
    write_yaml_exclusive(approval, approve_install_candidate(candidate))
    return plan, plan_path, confirmation_path, drafts, runtime, approval


def installed_inputs(
    base: Path, target: Path, *, stem: str = "flow", allowed_paths: list[str] | None = None,
) -> tuple[dict[str, Any], Path, Path, Path, Path, Path, Path]:
    plan, plan_path, confirmation_path, drafts, runtime, approval = approved_inputs(
        base, target, stem=stem, allowed_paths=allowed_paths,
    )
    receipt = base / f"{stem}-receipt.json"
    install_approved(target, drafts, runtime, approval, receipt, plan_path, confirmation_path)
    return plan, plan_path, confirmation_path, drafts, runtime, approval, receipt
