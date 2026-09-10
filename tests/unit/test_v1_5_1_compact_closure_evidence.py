from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from governance.schema_loader import validate_mapping
from governance.verification.closure_evaluator import close
from governance.verification.test_planner import create
from governance.verification.verification_builder import build


ROOT = Path(__file__).resolve().parents[2]


def contract() -> dict:
    return {
        "schema_version": "1.0", "task_id": "C09", "project_mode": "EXECUTION", "task_level": "B", "status": "READY",
        "objective": ["compact closure evidence"], "read_scope": ["governance/"], "write_scope": {"allow": ["governance/"], "deny": []},
        "autonomy": {"may_debug_test_failures": True, "may_edit_adjacent_tests": True, "may_edit_same_module_helpers": "conditional", "must_not_expand_architecture": True},
        "stop_conditions": [], "verification": {"level_1": ["python scripts/validate_governance.py"], "level_2": [], "level_3": []},
        "report": {"format": "compact", "fields": ["tests"]},
    }


def result(command_id: str, status: str, required: bool) -> dict:
    return {
        "command_id": command_id, "level": 2, "required": required, "status": status,
        "exit_code": 0 if status == "PASS" else 1, "duration_ms": 1,
        "sanitized_stdout_tail": "token=redacted", "sanitized_stderr_tail": "safe tail",
        "stdout_digest": "a" * 64, "stderr_digest": "b" * 64, "redaction_count": 1, "redaction_rule_version": "1.0",
    }


class CompactClosureEvidenceTest(unittest.TestCase):
    def test_required_regression_verify_close_binding_has_no_output(self) -> None:
        plan = create(contract(), {"status": "PASS"})
        verification = build(contract(), {"status": "PASS"}, plan, [result("governance_validate", "PASS", True), result("quality_gate", "PASS", False)])
        closure = close(verification)
        self.assertEqual("CLOSED", closure["status"])
        binding = verification["evidence_binding"]
        self.assertEqual(binding, closure["evidence_binding"])
        self.assertEqual(["governance_validate"], [item["command_id"] for item in binding["required_tests"]])
        self.assertEqual(["quality_gate"], [item["command_id"] for item in binding["regression_tests"]])
        self.assertTrue(binding["required_tests_satisfied"])
        self.assertNotIn("sanitized_stdout_tail", json.dumps(binding))
        self.assertNotIn("sanitized_stderr_tail", json.dumps(closure))
        validate_mapping(verification, "verification_result.schema.json")
        validate_mapping(closure, "closure_result.schema.json")

    def test_baseline_regression_and_task_created_required_failure(self) -> None:
        plan = create(contract(), {"status": "PASS"})
        baseline = build(contract(), {"status": "PASS"}, plan, [result("governance_validate", "PASS", True), result("quality_gate", "FAIL", False)], baseline_failures=("quality_gate",))
        self.assertEqual([], baseline["task_created_failures"])
        self.assertEqual(["quality_gate"], baseline["evidence_binding"]["failure_isolation"]["baseline_failures"])
        self.assertEqual("NO_NEW_FAILURE", baseline["evidence_binding"]["failure_isolation"]["closure_state"])
        failed = build(contract(), {"status": "PASS"}, plan, [result("governance_validate", "FAIL", True), result("quality_gate", "PASS", False)])
        self.assertEqual("FAILED", failed["completion_status"])
        self.assertFalse(failed["evidence_binding"]["required_tests_satisfied"])
        self.assertEqual("FAILED", close(failed)["status"])

    def test_public_verify_and_close_persist_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = root / ".agent_state"; state.mkdir()
            active = contract(); plan = create(active, {"status": "PASS"})
            (state / "active_task.yaml").write_text(yaml.safe_dump(active), encoding="utf-8")
            (state / "last_guard_result.yaml").write_text(yaml.safe_dump({"status": "PASS"}), encoding="utf-8")
            (state / "test_plan.yaml").write_text(yaml.safe_dump(plan), encoding="utf-8")
            (state / "test_results.yaml").write_text(yaml.safe_dump([result("governance_validate", "PASS", True), result("quality_gate", "PASS", False)]), encoding="utf-8")
            verify = subprocess.run([sys.executable, str(ROOT / "scripts/agent_verify.py")], cwd=root, text=True, capture_output=True)
            self.assertEqual(0, verify.returncode, verify.stderr)
            persisted_verification = yaml.safe_load((state / "verification_result.yaml").read_text(encoding="utf-8"))
            validate_mapping(persisted_verification, "verification_result.schema.json")
            self.assertIn("evidence_binding", persisted_verification)
            close_result = subprocess.run([sys.executable, str(ROOT / "scripts/agent_close.py")], cwd=root, text=True, capture_output=True)
            self.assertEqual(0, close_result.returncode, close_result.stderr)
            persisted_closure = yaml.safe_load((state / "closure_result.yaml").read_text(encoding="utf-8"))
            validate_mapping(persisted_closure, "closure_result.schema.json")
            self.assertEqual(persisted_verification["evidence_binding"], persisted_closure["evidence_binding"])
            self.assertNotIn("sanitized_stdout_tail", json.dumps(persisted_closure))


if __name__ == "__main__":
    unittest.main()
