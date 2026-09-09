from pathlib import Path
import unittest

from governance.models.task_contract import TaskContract, supersede
from governance.preflight.engine import run_preflight
from governance.schema_loader import load_mapping
from governance.verification.verification_builder import build

ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "preflight"


class V15RealityCheckTest(unittest.TestCase):
    def test_negative_risk_text_and_structured_type(self):
        task = load_mapping(ROOT / "task_safe_patch.yaml")
        task["title"] = "No network, no real API, no production write"
        task["hints"]["task_type"] = "B"
        result = run_preflight(task, load_mapping(ROOT / "project_state_execution.yaml"))
        self.assertEqual(("B", ()), (result.classification.task_level, result.risks.kinds))

    def test_structured_risk_overrides_negative_text(self):
        task = load_mapping(ROOT / "task_safe_patch.yaml")
        task["description"] = "No network normally, but access is explicitly requested."
        task["hints"]["risk_hints"] = {"external_access": True}
        self.assertEqual("BLOCKED", run_preflight(task, load_mapping(ROOT / "project_state_execution.yaml")).contract.status)

    def test_baseline_failure_is_not_task_created(self):
        result = build({"task_id":"T"}, {"status":"PASS"}, {"status":"READY"}, [{"command_id":"legacy","status":"FAIL","required":True}], baseline_failures=("legacy",))
        self.assertEqual(([], "REPOSITORY_BASELINE_DEGRADED"), (result["task_created_failures"], result["closure_state"]))

    def test_supersession_is_auditable(self):
        base = {"schema_version":"1.0","project_mode":"EXECUTION","task_level":"B","status":"ACTIVE","objective":["x"],"read_scope":[],"write_scope":{"allow":["x"],"deny":[]},"autonomy":{"may_debug_test_failures":True,"may_edit_adjacent_tests":True,"may_edit_same_module_helpers":True,"must_not_expand_architecture":True},"stop_conditions":[],"verification":{"level_1":[],"level_2":[],"level_3":[]},"report":{"format":"compact","fields":["tests"]}}
        old = TaskContract.from_mapping({**base, "task_id":"old"})
        new = TaskContract.from_mapping({**base, "task_id":"new"})
        self.assertEqual("new", supersede(old, new, "owner-approval").supersession["successor_task_id"])


if __name__ == "__main__": unittest.main()
