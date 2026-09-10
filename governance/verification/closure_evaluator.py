from datetime import datetime, timezone
from .evidence import valid_task_relevance_evidence

def close(verification, stale=False):
    status={"VERIFIED":"CLOSED","PARTIAL":"PARTIAL","BLOCKED":"BLOCKED","FAILED":"FAILED"}[verification["completion_status"]]
    reasons=["verification_stale_after_workspace_change"] if stale else []
    if stale: status="BLOCKED"
    evidence = verification.get("evidence_binding")
    if evidence and not valid_task_relevance_evidence(evidence, verification["task_id"]):
        status="BLOCKED"; reasons.append("invalid_task_relevance_evidence")
    elif evidence and not evidence["required_tests_satisfied"]:
        status="FAILED"; reasons.append("required_task_relevance_evidence_not_satisfied")
    value={"schema_version":"1.0","task_id":verification["task_id"],"status":status,"guard_status":verification["guard_status"],"verification_status":verification["completion_status"],"report_path":"","reasons":reasons,"remaining_risks":verification["remaining_risks"],"closed_at":datetime.now(timezone.utc).isoformat()}
    if evidence:
        value["evidence_binding"] = evidence
    return value
