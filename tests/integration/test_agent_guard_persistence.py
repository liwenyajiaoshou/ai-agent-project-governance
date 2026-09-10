import unittest
from pathlib import Path
from unittest.mock import patch
from governance.state import store
class GuardPersistenceTest(unittest.TestCase):
 def test_task_mismatch_rejected(self):
  value={"schema_version":"1.0","task_id":"B","status":"PASS","repository_root":".","branch":"main","head_commit":"x","changed_paths":[],"allowed_changes":[],"conditional_changes":[],"denied_changes":[],"unmatched_changes":[],"approval_status":"not_required","effect_authorization":{"effect_type":None,"approval_type":None,"status":"not_required"},"state_status":"OK","forbidden_operation_status":"PASS","reasons":[],"run_at":"2026-01-01T00:00:00+00:00"}
  with patch("governance.state.store.active",return_value={"task_id":"A"}):
   with self.assertRaises(ValueError): store.save_p3(Path("x"),value,"guard_result.schema.json")
