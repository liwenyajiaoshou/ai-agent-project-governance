import json
import unittest
from pathlib import Path
from governance.workspace.baseline import (
    capture_baseline,
    UnacceptedDirtyAssetError,
)
from governance.adoption.provenance import canonical_digest

class TestWorkspaceBaseline(unittest.TestCase):
    def test_clean_workspace_baseline(self):
        baseline = capture_baseline(Path("/fake"), [], [])
        self.assertEqual(baseline["worktree_state"], "CLEAN")
        self.assertIsNone(baseline["accepted_dirty_manifest"])

    def test_accepted_dirty_workspace_baseline(self):
        baseline = capture_baseline(Path("/fake"), ["foo.py"], [], accepted_dirty_paths=["foo.py"])
        self.assertEqual(baseline["worktree_state"], "ACCEPTED_DIRTY")
        self.assertIsNotNone(baseline["accepted_dirty_manifest"])
        self.assertIn("foo.py", baseline["accepted_dirty_manifest"]["accepted_paths"])

    def test_unaccepted_dirty_asset_fails_closed(self):
        with self.assertRaises(UnacceptedDirtyAssetError):
            capture_baseline(Path("/fake"), ["foo.py"], ["bar.py"], accepted_dirty_paths=["foo.py"])

    def test_user_owned_asset_is_preserved(self):
        baseline = capture_baseline(Path("/fake"), [], [], user_owned_assets=["my_data.json"])
        self.assertIn("my_data.json", baseline["user_owned_assets"])

    def test_baseline_serialization_is_deterministic(self):
        baseline1 = capture_baseline(Path("/fake"), ["b.py", "a.py"], [], accepted_dirty_paths=["b.py", "a.py"])
        baseline2 = capture_baseline(Path("/fake"), ["a.py", "b.py"], [], accepted_dirty_paths=["a.py", "b.py"])

        # Override timestamps for deterministic testing
        baseline1["captured_at"] = "2026-08-04T00:00:00Z"
        baseline2["captured_at"] = "2026-08-04T00:00:00Z"
        baseline1["baseline_id"] = "fixed"
        baseline2["baseline_id"] = "fixed"
        if baseline1["accepted_dirty_manifest"]:
            baseline1["accepted_dirty_manifest"]["created_at"] = "2026-08-04T00:00:00Z"
            baseline1["accepted_dirty_manifest"]["manifest_id"] = "fixed_manifest"
            baseline1["accepted_dirty_manifest"]["baseline_id"] = "fixed"
        if baseline2["accepted_dirty_manifest"]:
            baseline2["accepted_dirty_manifest"]["created_at"] = "2026-08-04T00:00:00Z"
            baseline2["accepted_dirty_manifest"]["manifest_id"] = "fixed_manifest"
            baseline2["accepted_dirty_manifest"]["baseline_id"] = "fixed"

        digest1 = canonical_digest(baseline1)
        digest2 = canonical_digest(baseline2)

        self.assertEqual(digest1, digest2)

    def test_baseline_repeated_run_is_idempotent(self):
        time_fixed = "2026-08-04T00:00:00Z"
        baseline1 = capture_baseline(Path("/fake"), ["a.py"], [], accepted_dirty_paths=["a.py"], captured_at=time_fixed)
        baseline2 = capture_baseline(Path("/fake"), ["a.py"], [], accepted_dirty_paths=["a.py"], captured_at=time_fixed)

        # the baseline_ids should be identical
        self.assertEqual(baseline1["baseline_id"], baseline2["baseline_id"])
        self.assertEqual(
            baseline1["accepted_dirty_manifest"]["manifest_id"],
            baseline2["accepted_dirty_manifest"]["manifest_id"]
        )
