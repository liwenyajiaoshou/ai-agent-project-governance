import os
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from governance.workspace.isolation import preview_isolation

class TestWorkspaceIsolation(unittest.TestCase):
    @patch("governance.workspace.isolation.subprocess.run")
    @patch("governance.workspace.isolation.git_metadata")
    def test_isolation_preview_does_not_mutate_git(self, mock_meta, mock_run):
        mock_meta.return_value = {"branch": "main", "head": "abc"}
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as td:
            repo_path = Path(td) / "repo"
            repo_path.mkdir()
            git_dir = repo_path / ".git"
            git_dir.mkdir()

            target_path = Path(td) / "target"
            # target_path does not exist

            res = preview_isolation(repo_path, "new-branch", target_path)
            self.assertEqual(res["proposed_branch"], "new-branch")
            self.assertEqual(res["recommended_action"], "PROCEED")

            for call in mock_run.call_args_list:
                args = call[0][0]
                self.assertIn(args[3], ["show-ref", "worktree", "status"])

    @patch("governance.workspace.isolation.subprocess.run")
    @patch("governance.workspace.isolation.git_metadata")
    def test_isolation_detects_existing_path(self, mock_meta, mock_run):
        mock_meta.return_value = {}
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        with tempfile.TemporaryDirectory() as td:
            repo_path = Path(td) / "repo"
            repo_path.mkdir()
            git_dir = repo_path / ".git"
            git_dir.mkdir()

            target_path = Path(td) / "target"
            target_path.mkdir() # path exists

            res = preview_isolation(repo_path, "new-branch", target_path)
            self.assertTrue(res["path_exists"])
            self.assertIn("Target path exists but is not a registered worktree.", res["conflicts"])
            self.assertEqual(res["recommended_action"], "RESOLVE_CONFLICTS_MANUALLY")

    @patch("governance.workspace.isolation.subprocess.run")
    @patch("governance.workspace.isolation.git_metadata")
    def test_isolation_detects_existing_branch(self, mock_meta, mock_run):
        mock_meta.return_value = {}

        def fake_run(*args, **kwargs):
            cmd = args[0]
            if "show-ref" in cmd:
                return MagicMock(returncode=0, stdout="some hash")
            return MagicMock(returncode=1, stdout="")
        mock_run.side_effect = fake_run

        with tempfile.TemporaryDirectory() as td:
            repo_path = Path(td) / "repo"
            repo_path.mkdir()
            git_dir = repo_path / ".git"
            git_dir.mkdir()

            target_path = Path(td) / "target"

            res = preview_isolation(repo_path, "new-branch", target_path)
            self.assertTrue(res["branch_exists"])
            self.assertIn("Target branch already exists.", res["conflicts"])

    @patch("governance.workspace.isolation.subprocess.run")
    @patch("governance.workspace.isolation.git_metadata")
    def test_isolation_detects_registered_worktree(self, mock_meta, mock_run):
        mock_meta.return_value = {}

        with tempfile.TemporaryDirectory() as td:
            repo_path = Path(td) / "repo"
            repo_path.mkdir()
            git_dir = repo_path / ".git"
            git_dir.mkdir()

            target_path = Path(td) / "target"
            target_path.mkdir() # path exists

            def fake_run(*args, **kwargs):
                cmd = args[0]
                if "worktree" in cmd:
                    return MagicMock(returncode=0, stdout=f"{target_path.resolve()}  (branch)\n")
                return MagicMock(returncode=1, stdout="")
            mock_run.side_effect = fake_run

            res = preview_isolation(repo_path, "new-branch", target_path)
            self.assertTrue(res["worktree_registered"])
            self.assertNotIn("Target path exists but is not a registered worktree.", res["conflicts"])

    @patch("governance.workspace.isolation.subprocess.run")
    @patch("governance.workspace.isolation.git_metadata")
    def test_isolation_reports_git_metadata_not_writable(self, mock_meta, mock_run):
        mock_meta.return_value = {}
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        with tempfile.TemporaryDirectory() as td:
            repo_path = Path(td) / "repo"
            repo_path.mkdir()
            # DO NOT CREATE .git dir to simulate unwritable/missing git

            target_path = Path(td) / "target"

            res = preview_isolation(repo_path, "new-branch", target_path)
            self.assertFalse(res["git_metadata_writable"])
            self.assertIn("Git metadata is not writable.", res["conflicts"])
