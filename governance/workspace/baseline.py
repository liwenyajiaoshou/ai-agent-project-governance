import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class WorkspaceBaselineError(Exception):
    """Base exception for workspace baseline."""


class UnacceptedDirtyAssetError(WorkspaceBaselineError):
    """Raised when there are dirty assets not covered by the accepted list."""


def build_accepted_dirty_manifest(
    baseline_id: str,
    accepted_paths: list[str],
    owner: str = "system"
) -> dict[str, Any]:
    manifest = {
        "manifest_id": hashlib.sha256(f"{baseline_id}:{','.join(sorted(accepted_paths))}".encode()).hexdigest()[:16],
        "baseline_id": baseline_id,
        "accepted_paths": sorted(accepted_paths),
        "path_classification": "USER_ACKNOWLEDGED",
        "path_digest_or_metadata": "N/A",
        "acceptance_reason": "Pre-approved dirtiness",
        "owner": owner,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "exclusions": []
    }
    return manifest


def capture_baseline(
    repository_root: Path,
    tracked_changes: list[str],
    untracked_assets: list[str],
    accepted_dirty_paths: Optional[list[str]] = None,
    user_owned_assets: Optional[list[str]] = None,
    git_head: str = "UNKNOWN",
    git_branch: str = "UNKNOWN",
    captured_at: Optional[str] = None
) -> dict[str, Any]:
    accepted = accepted_dirty_paths or []

    unaccepted_tracked = [p for p in tracked_changes if p not in accepted]
    unaccepted_untracked = [p for p in untracked_assets if p not in accepted]

    if unaccepted_tracked or unaccepted_untracked:
        raise UnacceptedDirtyAssetError(
            f"Unaccepted dirty assets found. Tracked: {unaccepted_tracked}, Untracked: {unaccepted_untracked}"
        )

    state = "CLEAN" if not (tracked_changes or untracked_assets) else "ACCEPTED_DIRTY"

    time_str = captured_at or datetime.now(timezone.utc).isoformat()
    baseline_id = hashlib.sha256(f"{git_head}:{git_branch}:{time_str}".encode()).hexdigest()[:16]

    manifest = build_accepted_dirty_manifest(baseline_id, accepted) if state == "ACCEPTED_DIRTY" else None

    payload = {
        "baseline_id": baseline_id,
        "schema_version": "1.0",
        "repository_root": str(repository_root.resolve()),
        "git_head": git_head,
        "git_branch": git_branch,
        "git_tag_context": "UNKNOWN",
        "worktree_state": state,
        "captured_at": time_str,
        "tracked_changes": sorted(tracked_changes),
        "untracked_assets": sorted(untracked_assets),
        "accepted_dirty_manifest": manifest,
        "user_owned_assets": sorted(user_owned_assets) if user_owned_assets else [],
        "task_owned_assets": [],
        "runtime_evidence_assets": [],
        "generated_report_assets": [],
        "temporary_assets": [],
        "archive_assets": [],
        "exclusions": []
    }
    return payload
