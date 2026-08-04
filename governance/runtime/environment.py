from typing import Any, Dict
import platform
import os
import sys
from datetime import datetime, timezone
import subprocess
import hashlib

def capture_environment_contract(repository_root: str, baseline_id: str) -> Dict[str, Any]:
    env = {
        "schema_version": "1.0",
        "environment_id": "UNKNOWN",
        "os": platform.system(),
        "architecture": platform.machine(),
        "shell": os.environ.get("SHELL", "UNKNOWN"),
        "working_directory": os.getcwd(),
        "repository_root": str(repository_root),
        "git_head": "UNKNOWN",
        "git_branch": "UNKNOWN",
        "worktree_state": "UNKNOWN",
        "workspace_baseline_id": baseline_id,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "runtime_dependencies": "UNKNOWN",
        "network_mode": "UNKNOWN",
        "tun_expectation": "UNKNOWN",
        "git_metadata_accessible": False,
        "terminal_sandbox_state": "UNKNOWN",
        "warnings": [],
        "captured_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        head = subprocess.check_output(["git", "-C", repository_root, "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
        branch = subprocess.check_output(["git", "-C", repository_root, "branch", "--show-current"], text=True, stderr=subprocess.DEVNULL).strip()
        if not branch:
            branch = "DETACHED"
        env["git_head"] = head
        env["git_branch"] = branch
        env["git_metadata_accessible"] = True
    except (OSError, subprocess.CalledProcessError):
        env["warnings"].append("Git metadata inaccessible")
        env["git_metadata_accessible"] = False

    id_source = f"{env['os']}:{env['architecture']}:{env['python_version']}:{env['repository_root']}:{env['git_head']}"
    env["environment_id"] = hashlib.sha256(id_source.encode()).hexdigest()[:16]

    return env
