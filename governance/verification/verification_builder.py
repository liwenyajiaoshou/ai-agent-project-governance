from datetime import datetime, timezone

from .evidence import build_task_relevance_evidence


RESULT_STATUSES = {"PASS", "FAIL", "NOT_RUN", "TIMEOUT", "ERROR"}


def normalize_result(result):
    """Convert a runner result once into the persisted TestResult contract."""
    status = result.get("status", "ERROR")
    if status not in RESULT_STATUSES:
        status = "ERROR"
    command_id = result.get("command_id", result.get("command", "unknown"))
    exit_code = result.get("exit_code")
    summary = result.get("summary")
    if not isinstance(summary, str):
        summary = f"{status.lower()}" if exit_code is None else f"{status.lower()} (exit_code={exit_code})"
    return {
        "command_id": str(command_id),
        "level": result.get("level", 1) if result.get("level", 1) in {1, 2, 3} else 1,
        "required": bool(result.get("required", False)),
        "status": status,
        "summary": summary,
        "exit_code": exit_code if isinstance(exit_code, int) else None,
        "duration_ms": result.get("duration_ms", 0) if isinstance(result.get("duration_ms", 0), int) and result.get("duration_ms", 0) >= 0 else 0,
        "stdout_digest": result.get("stdout_digest") if isinstance(result.get("stdout_digest"), str) else None,
        "stderr_digest": result.get("stderr_digest") if isinstance(result.get("stderr_digest"), str) else None,
        "redaction_count": result.get("redaction_count", 0) if isinstance(result.get("redaction_count", 0), int) and result.get("redaction_count", 0) >= 0 else 0,
        "redaction_rule_version": result.get("redaction_rule_version", "1.0"),
    }


def build(contract, guard, plan, results, orchestration=None, baseline_failures=()):
    results = [normalize_result(result) for result in results]
    baseline = tuple(sorted(set(baseline_failures)))
    post_failures = tuple(sorted(r["command_id"] for r in results if r["status"] != "PASS"))
    task_created = tuple(item for item in post_failures if item not in baseline)
    if guard["status"] in {"BLOCKED","ERROR"} or plan["status"]=="BLOCKED": outcome="BLOCKED"
    elif any((r["status"] in {"ERROR","TIMEOUT"} or (r["required"] and r["status"]=="FAIL")) and r["command_id"] in task_created for r in results): outcome="FAILED"
    elif guard["status"]=="WARN" or any(not r["required"] and r["status"]!="PASS" for r in results): outcome="PARTIAL"
    else: outcome="VERIFIED"
    closure_state = "REPOSITORY_BASELINE_DEGRADED" if outcome == "VERIFIED" and post_failures else "TASK_VERIFIED" if outcome == "VERIFIED" else "NO_NEW_FAILURE" if not task_created else "TASK_FAILURE"
    evidence = build_task_relevance_evidence(task_id=contract["task_id"], plan=plan, tests=results, baseline_failures=baseline, post_task_failures=post_failures, task_created_failures=task_created, closure_state=closure_state)
    value={"schema_version":"1.0","task_id":contract["task_id"],"scope_check":"PASS" if guard["status"]=="PASS" else "FAIL", "forbidden_operation_check":"PASS", "guard_status":guard["status"],"test_plan_status":plan["status"],"tests":results,"required_tests_passed":evidence["required_tests_satisfied"],"optional_tests_passed":outcome=="VERIFIED","completion_status":outcome,"remaining_risks":[] if outcome=="VERIFIED" else [outcome.lower()],"baseline_failures":list(baseline),"post_task_failures":list(post_failures),"task_created_failures":list(task_created),"closure_state":closure_state,"evidence_binding":evidence,"verified_at":datetime.now(timezone.utc).isoformat()}
    if orchestration:
        value["orchestration_id"]=orchestration["orchestration_id"]
        if orchestration.get("status") != "READY_FOR_VERIFICATION": value["completion_status"]="BLOCKED"; value["remaining_risks"]=["orchestration_not_ready"]
    return value
