"""Deterministic command planning; adapters select only registered, evidenced commands."""
from datetime import datetime, timezone
from pathlib import Path
from .command_registry import COMMANDS
from ..adapters.registry import get as get_adapter


def adapter_command_ids(repo_root: Path, adapter_ids: tuple[str, ...]) -> tuple[str, ...]:
    selected = []
    for adapter_id in adapter_ids:
        adapter = get_adapter(adapter_id)
        if not adapter:
            continue
        scripts = set(adapter.package_scripts(repo_root)) if hasattr(adapter, "package_scripts") else set()
        for command_id in (*adapter.default_test_command_ids(), *adapter.default_quality_command_ids()):
            if command_id not in COMMANDS:
                continue
            if command_id == "python-pytest" and not any((repo_root / name).exists() for name in ("pytest.ini", "pyproject.toml", "tox.ini")):
                continue
            if command_id.startswith("node-npm-") and command_id.removeprefix("node-npm-") not in scripts:
                continue
            if command_id not in selected:
                selected.append(command_id)
    return tuple(selected)


def create(contract, guard, repo_root: Path | None = None, adapter_ids: tuple[str, ...] = (), task_relevant_command_ids: tuple[str, ...] = ()):
    if guard["status"] in {"BLOCKED", "ERROR"}:
        return {"schema_version":"1.0","task_id":contract["task_id"],"plan_id":"blocked","levels":[],"selected_commands":[],"required_tests":[],"regression_tests":[],"informational_tests":[],"skipped_levels":[1,2,3],"selection_reasons":["guard_blocked"],"requires_approval":False,"status":"BLOCKED","created_at":datetime.now(timezone.utc).isoformat()}
    level={"A":1,"B":2,"C":3}[contract["task_level"]]
    selected = [name for name, spec in COMMANDS.items() if name in {"unit_tests", "governance_validate", "quality_gate"} and spec["level"] <= level]
    if repo_root is not None:
        selected.extend(name for name in adapter_command_ids(repo_root, adapter_ids) if COMMANDS[name]["level"] <= level and name not in selected)
    relevant=set(task_relevant_command_ids); commands=[]
    for name in selected:
        category="required" if name in relevant else "regression"
        commands.append({"command_id":name,"level":COMMANDS[name]["level"],"argv":COMMANDS[name]["argv"],"working_directory":COMMANDS[name]["cwd"],"timeout_seconds":COMMANDS[name]["timeout"],"required":category=="required","reason":"task_relevant" if category=="required" else "affected_module_regression"})
    return {"schema_version":"1.0","task_id":contract["task_id"],"plan_id":f'{contract["task_id"]}-plan',"levels":list(range(1,level+1)),"selected_commands":commands,"required_tests":[item for item in commands if item["required"]],"regression_tests":[item for item in commands if not item["required"]],"informational_tests":[],"skipped_levels":[n for n in (1,2,3) if n > level],"selection_reasons":[f"task_level_{contract['task_level']}"],"requires_approval":False,"status":"READY","created_at":datetime.now(timezone.utc).isoformat()}
