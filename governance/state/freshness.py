from datetime import datetime, timezone

def _covers(scope, requested):
    return all(scope.get(key) == value for key, value in requested.items())

def evaluate(approval, fingerprint, task_id, requested_scope=None, contract_digest=None):
    if approval.get("status") != "approved" or approval.get("task_id") != task_id:
        return "expired"
    if approval.get("environment_fingerprint") != fingerprint:
        return "state_mismatch"
    if contract_digest is not None and approval.get("contract_digest") != contract_digest:
        return "contract_mismatch"
    expiry = approval.get("expires_at")
    if expiry and datetime.fromisoformat(expiry.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
        return "expired"
    if requested_scope and not _covers(approval.get("scope", {}), requested_scope):
        return "scope_mismatch"
    return "valid"

def valid(approval, fingerprint, task_id):
    status=evaluate(approval,fingerprint,task_id)
    return status == "valid", status
