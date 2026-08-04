import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from governance.adoption.provenance import git_metadata


def preview_isolation(
    source_root: Path,
    proposed_branch: str,
    proposed_worktree_path: Path
) -> dict[str, Any]:
    # Never mutate Git. Just detect.
    metadata = git_metadata(source_root)
    source_ref = metadata.get("branch", "UNKNOWN")
    source_commit = metadata.get("head", "UNKNOWN")

    path_exists = proposed_worktree_path.exists()

    git_exec = shutil.which("git") or "git"

    def run_git(*args: str) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                [git_exec, "-C", str(source_root), *args],
                capture_output=True,
                text=True,
                check=False
            )
        except Exception:
            return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")

    branch_check = run_git("show-ref", "--verify", f"refs/heads/{proposed_branch}")
    branch_exists = (branch_check.returncode == 0)

    worktree_check = run_git("worktree", "list")
    worktree_registered = False
    if worktree_check.returncode == 0:
        if str(proposed_worktree_path.resolve()) in worktree_check.stdout:
            worktree_registered = True

    git_dir = source_root / ".git"
    git_metadata_writable = os.access(git_dir, os.W_OK) if git_dir.exists() else False

    status_check = run_git("status", "--porcelain")
    repository_dirty = False
    if status_check.returncode == 0 and status_check.stdout.strip():
        repository_dirty = True

    conflicts = []
    if path_exists and not worktree_registered:
        conflicts.append("Target path exists but is not a registered worktree.")
    if branch_exists:
        conflicts.append("Target branch already exists.")
    if not git_metadata_writable:
        conflicts.append("Git metadata is not writable.")

    action = "PROCEED"
    if conflicts:
        action = "RESOLVE_CONFLICTS_MANUALLY"

    return {
        "source_repository": str(source_root.resolve()),
        "source_ref": source_ref,
        "source_commit": source_commit,
        "proposed_branch": proposed_branch,
        "proposed_worktree_path": str(proposed_worktree_path.resolve()),
        "path_exists": path_exists,
        "branch_exists": branch_exists,
        "worktree_registered": worktree_registered,
        "git_metadata_writable": git_metadata_writable,
        "repository_dirty": repository_dirty,
        "conflicts": conflicts,
        "recommended_action": action
    }
