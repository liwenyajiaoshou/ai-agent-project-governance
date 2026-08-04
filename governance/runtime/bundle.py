from typing import Any, Dict, List
import hashlib
from datetime import datetime, timezone
import json
from governance.adoption.provenance import canonical_digest

def build_runtime_bundle(baseline_id: str, environment_id: str, source_commit: str, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
    bundle = {
        "schema_version": "1.0",
        "workspace_baseline_id": baseline_id,
        "environment_id": environment_id,
        "source_commit": source_commit,
        "runner_identity": "Antigravity",
        "artifacts": artifacts,
        "resource_bindings": [],
        "entrypoints": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    digest = canonical_digest(bundle, omit=("bundle_id", "bundle_digest", "created_at"))
    bundle["bundle_id"] = hashlib.sha256(digest.encode()).hexdigest()[:16]
    bundle["bundle_digest"] = digest
    return bundle
