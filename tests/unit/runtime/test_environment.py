import unittest
import os
import subprocess
from unittest.mock import patch
from governance.runtime.environment import capture_environment_contract

class TestEnvironmentContract(unittest.TestCase):
    def test_environment_deterministic_serialization(self):
        env = capture_environment_contract("/dummy", "baseline-123")
        self.assertEqual(env["schema_version"], "1.0")
        self.assertEqual(env["workspace_baseline_id"], "baseline-123")
        self.assertNotIn("password", env)
        self.assertNotIn("secret", env)
        self.assertIn("environment_id", env)

    @patch("subprocess.check_output")
    def test_unknown_fail_closed_behavior(self, mock_check_output):
        mock_check_output.side_effect = subprocess.CalledProcessError(1, "git")
        env = capture_environment_contract("/dummy", "baseline-123")
        self.assertFalse(env["git_metadata_accessible"])
        self.assertEqual(env["git_head"], "UNKNOWN")
        self.assertIn("Git metadata inaccessible", env["warnings"][0])

    @patch("subprocess.check_output")
    def test_linked_worktree_environment_representation(self, mock_check_output):
        def side_effect(args, **kwargs):
            if "HEAD" in args:
                return "abcd123"
            if "branch" in args:
                return ""  # detached
            return ""
        mock_check_output.side_effect = side_effect
        env = capture_environment_contract("/dummy", "baseline-123")
        self.assertTrue(env["git_metadata_accessible"])
        self.assertEqual(env["git_head"], "abcd123")
        self.assertEqual(env["git_branch"], "DETACHED")

if __name__ == "__main__":
    unittest.main()
