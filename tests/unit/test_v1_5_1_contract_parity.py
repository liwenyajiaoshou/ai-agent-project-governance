from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from governance.schema_loader import validate_mapping
from governance.verification.test_planner import create
from governance.verification.verification_builder import build


ROOT = Path(__file__).resolve().parents[2]


def contract(task_id: str = "T", status: str = "READY") -> dict:
    return {
        "schema_version": "1.0", "task_id": task_id, "project_mode": "EXECUTION", "task_level": "B", "status": status,
        "objective": ["contract parity"], "read_scope": ["governance/"], "write_scope": {"allow": ["governance/"], "deny": []},
        "autonomy": {"may_debug_test_failures": True, "may_edit_adjacent_tests": True, "may_edit_same_module_helpers": "conditional", "must_not_expand_architecture": True},
        "stop_conditions": [],
        "verification": {"level_1": ["python scripts/validate_governance.py"], "level_2": [], "level_3": []},
        "report": {"format": "compact", "fields": ["tests"]},
    }


def runner_result(command_id: str, status: str, required: bool = True) -> dict:
    return {
        "command_id": command_id, "level": 2, "required": required, "status": status,
        "exit_code": 0 if status == "PASS" else 1 if status == "FAIL" else None, "duration_ms": 3,
        "sanitized_stdout_tail": "safe output", "sanitized_stderr_tail": "safe error",
        "stdout_digest": "a" * 64, "stderr_digest": "b" * 64, "redaction_count": 1,
        "redaction_rule_version": "1.0", "started_at": "2026-09-10T00:00:00+00:00", "finished_at": "2026-09-10T00:00:01+00:00",
    }


class V151ContractParityTest(unittest.TestCase):
    def state(self, root: Path, *, guard_status: str = "PASS") -> None:
        state = root / ".agent_state"; state.mkdir()
        (state / "active_task.yaml").write_text(yaml.safe_dump(contract()), encoding="utf-8")
        (state / "last_guard_result.yaml").write_text(yaml.safe_dump({"status": guard_status}), encoding="utf-8")

    def run_script(self, root: Path, name: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(ROOT / "scripts" / name), *args], cwd=root, text=True, capture_output=True)

    def test_c01_direct_ready_and_blocked(self) -> None:
        ready = create(contract(), {"status": "PASS"})
        self.assertEqual("READY", ready["status"])
        self.assertEqual(["governance_validate"], [item["command_id"] for item in ready["required_tests"]])
        self.assertEqual(["quality_gate"], [item["command_id"] for item in ready["regression_tests"]])
        validate_mapping(ready, "test_plan.schema.json")
        blocked = create(contract(), {"status": "BLOCKED"})
        self.assertEqual("BLOCKED", blocked["status"])
        validate_mapping(blocked, "test_plan.schema.json")

    def test_c01_public_create_persists_ready_and_blocked(self) -> None:
        for guard_status, expected in (("PASS", "READY"), ("BLOCKED", "BLOCKED")):
            with self.subTest(guard_status=guard_status), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); self.state(root, guard_status=guard_status)
                result = self.run_script(root, "agent_test_plan.py", "create")
                self.assertEqual(0 if expected == "READY" else 3, result.returncode, result.stderr)
                saved = yaml.safe_load((root / ".agent_state/test_plan.yaml").read_text(encoding="utf-8"))
                self.assertEqual(expected, saved["status"])
                validate_mapping(saved, "test_plan.schema.json")
                if expected == "READY":
                    self.assertTrue(saved["required_tests"])
                    self.assertTrue(saved["regression_tests"])

    def test_c02_failure_attribution_and_normalization(self) -> None:
        plan = create(contract(), {"status": "PASS"})
        baseline = build(contract(), {"status": "PASS"}, plan, [runner_result("legacy", "FAIL")], baseline_failures=("legacy",))
        self.assertEqual(([], "REPOSITORY_BASELINE_DEGRADED"), (baseline["task_created_failures"], baseline["closure_state"]))
        task_created = build(contract(), {"status": "PASS"}, plan, [runner_result("new", "FAIL")])
        self.assertEqual((['new'], "TASK_FAILURE"), (task_created["task_created_failures"], task_created["closure_state"]))
        for status in ("PASS", "FAIL", "TIMEOUT", "ERROR"):
            value = build(contract(), {"status": "PASS"}, plan, [runner_result("runner", status)])
            test = value["tests"][0]
            self.assertEqual(status, test["status"])
            self.assertIn("command_id", test)
            self.assertNotIn("sanitized_stdout_tail", test)
            validate_mapping(value, "verification_result.schema.json")

    def test_c02_public_verify_persists_runner_shape(self) -> None:
        for status in ("PASS", "FAIL", "TIMEOUT", "ERROR"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); self.state(root)
                plan = create(contract(), {"status": "PASS"})
                (root / ".agent_state/test_plan.yaml").write_text(yaml.safe_dump(plan), encoding="utf-8")
                (root / ".agent_state/test_results.yaml").write_text(yaml.safe_dump([runner_result("governance_validate", status)]), encoding="utf-8")
                result = self.run_script(root, "agent_verify.py")
                self.assertEqual({"PASS": 0, "FAIL": 4, "TIMEOUT": 4, "ERROR": 4}[status], result.returncode, result.stderr)
                saved = yaml.safe_load((root / ".agent_state/verification_result.yaml").read_text(encoding="utf-8"))
                self.assertEqual(status, saved["tests"][0]["status"])
                self.assertTrue(saved["tests"][0]["required"])
                validate_mapping(saved, "verification_result.schema.json")


if __name__ == "__main__":
    unittest.main()
