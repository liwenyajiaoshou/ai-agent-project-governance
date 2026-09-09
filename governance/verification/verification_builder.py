from datetime import datetime, timezone
def build(contract, guard, plan, results, orchestration=None, baseline_failures=()):
    baseline = tuple(sorted(set(baseline_failures)))
    post_failures = tuple(sorted(r.get("command_id", r.get("command", "unknown")) for r in results if r["status"] not in {"PASS", "SKIP"}))
    task_created = tuple(item for item in post_failures if item not in baseline)
    if guard["status"] in {"BLOCKED","ERROR"} or plan["status"]=="BLOCKED": outcome="BLOCKED"
    elif any((r["status"] in {"ERROR","TIMEOUT"} or (r.get("required") and r["status"]=="FAIL")) and r.get("command_id", r.get("command", "unknown")) in task_created for r in results): outcome="FAILED"
    elif guard["status"]=="WARN" or any(not r.get("required") and r["status"]!="PASS" for r in results): outcome="PARTIAL"
    else: outcome="VERIFIED"
    closure_state = "REPOSITORY_BASELINE_DEGRADED" if outcome == "VERIFIED" and post_failures else "TASK_VERIFIED" if outcome == "VERIFIED" else "NO_NEW_FAILURE" if not task_created else "TASK_FAILURE"
    value={"schema_version":"1.0","task_id":contract["task_id"],"scope_check":"PASS" if guard["status"]=="PASS" else "FAIL", "forbidden_operation_check":"PASS", "guard_status":guard["status"],"test_plan_status":plan["status"],"tests":results,"required_tests_passed":outcome=="VERIFIED","optional_tests_passed":outcome=="VERIFIED","completion_status":outcome,"remaining_risks":[] if outcome=="VERIFIED" else [outcome.lower()],"baseline_failures":list(baseline),"post_task_failures":list(post_failures),"task_created_failures":list(task_created),"closure_state":closure_state,"verified_at":datetime.now(timezone.utc).isoformat()}
    if orchestration:
        value["orchestration_id"]=orchestration["orchestration_id"]
        if orchestration.get("status") != "READY_FOR_VERIFICATION": value["completion_status"]="BLOCKED"; value["remaining_risks"]=["orchestration_not_ready"]
    return value
