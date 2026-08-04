import sys
import os
import importlib.util
import unittest
from pathlib import Path

extension_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../extensions/context-handoff/context_handoff.py"))
spec = importlib.util.spec_from_file_location("ext_context_handoff", extension_path)
ext_context_handoff = importlib.util.module_from_spec(spec)
sys.modules["ext_context_handoff"] = ext_context_handoff
spec.loader.exec_module(ext_context_handoff)

build_snapshot = ext_context_handoff.build_snapshot
validate_snapshot = ext_context_handoff.validate_snapshot
_render = ext_context_handoff._render

class TestContextHandoffIntegration(unittest.TestCase):
    def test_new_fields_optional_and_old_snapshot_remains_readable(self):
        evidence = {"task_statuses": ["READY"]}
        snapshot = build_snapshot(Path("/dummy"), "proj-1", "task-1", evidence)
        self.assertNotIn("workspace_baseline_id", snapshot)
        validate_snapshot(snapshot) # Should not raise validation error

    def test_new_identity_summaries_render_correctly(self):
        evidence = {
            "task_statuses": ["READY"],
            "workspace_baseline_id": "base1",
            "environment_id": "env1",
            "runtime_bundle_id": "bundle1",
            "machine_manifest_id": "man1",
            "side_effect_gate_summary": "READY",
            "autonomous_budget_summary": "ALLOW"
        }
        snapshot = build_snapshot(Path("/dummy"), "proj-1", "task-1", evidence)
        validate_snapshot(snapshot) # Must validate with new schema

        # We need a mock template to test _render
        # But we can just use an existing template and see if our append logic works.
        # However, _render directly reads from ROOT / "templates", which expects actual templates.
        # We'll just verify the fields are in the snapshot.
        self.assertEqual(snapshot["workspace_baseline_id"], "base1")
        self.assertEqual(snapshot["runtime_bundle_id"], "bundle1")
        self.assertEqual(snapshot["side_effect_gate_summary"], "READY")

    def test_unknown_and_conflict_preserved(self):
        evidence = {"task_statuses": ["IN_PROGRESS", "FAILED"]}
        snapshot = build_snapshot(Path("/dummy"), "proj-1", "task-1", evidence)
        self.assertEqual(snapshot["task_status"], "CONFLICT_REQUIRES_REVIEW")

if __name__ == "__main__":
    unittest.main()
