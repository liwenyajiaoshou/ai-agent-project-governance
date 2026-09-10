from datetime import datetime, timezone

def build(contract, root, branch, head, paths, groups, approval, state, forbidden, reasons, effect_authorization=None):
    status = "ERROR" if state != "OK" else "BLOCKED" if approval not in ("valid", "not_required") or forbidden == "BLOCKED" or groups["denied_changes"] or groups["unmatched_changes"] else "WARN" if groups["conditional_changes"] else "PASS"
    if approval not in ("valid", "not_required"): reasons.append(f"approval_{approval}")
    return {"schema_version":"1.0","task_id":contract["task_id"],"status":status,"repository_root":str(root),"branch":branch,"head_commit":head,"changed_paths":paths,**groups,"approval_status":approval,"effect_authorization":effect_authorization or {"effect_type":None,"approval_type":None,"status":approval},"state_status":state,"forbidden_operation_status":forbidden,"reasons":reasons,"run_at":datetime.now(timezone.utc).isoformat()}
