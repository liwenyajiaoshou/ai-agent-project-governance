from typing import Any, Dict, List
import hashlib
from datetime import datetime, timezone
import json
from governance.adoption.provenance import canonical_digest

def build_machine_manifest(task_id: str, baseline_id: str, environment_id: str, bundle_id: str, source_commit: str,
                           changed_paths: List[str], artifact_digests: Dict[str, str], test_commands: List[str], test_results: List[str],
                           network_calls: List[str], external_writes: List[str], gate_summary: str, result: str) -> Dict[str, Any]:
    manifest = {
        "schema_version": "1.0",
        "task_id": task_id,
        "workspace_baseline_id": baseline_id,
        "environment_id": environment_id,
        "runtime_bundle_id": bundle_id,
        "baseline_commit": source_commit,
        "changed_paths": sorted(changed_paths),
        "artifact_digests": artifact_digests,
        "test_commands": test_commands,
        "test_results": test_results,
        "network_calls": network_calls,
        "external_writes": external_writes,
        "gate_summary": gate_summary,
        "result": result,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    digest = canonical_digest(manifest, omit=("manifest_id", "created_at"))
    manifest["manifest_id"] = hashlib.sha256(digest.encode()).hexdigest()[:16]
    return manifest
