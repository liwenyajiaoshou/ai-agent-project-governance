from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from governance.adoption import build_plan, render_markdown


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tests" / "agent_adopt_test_launcher.py"


def snapshot(root: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            entries.append((relative + "/", "directory"))
        else:
            entries.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return entries


class AgentAdoptTest(unittest.TestCase):
    def project(self, root: Path, kind: str) -> None:
        (root / "AGENTS.md").write_text("Allowed scope: src/. Do not push. Run tests and report closure.\n", encoding="utf-8")
        (root / ".gitignore").write_text(".env\n*.pem\n*.key\n", encoding="utf-8")
        if kind == "python":
            (root / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_sentinel.py").write_text("raise RuntimeError('planner must not run tests')\n", encoding="utf-8")
        elif kind == "node":
            (root / "package.json").write_text('{"scripts":{"test":"node --test"}}', encoding="utf-8")

    def cli(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, str(SCRIPT), "--project-root", str(root), *args, "dry-run"], cwd=ROOT, text=True, capture_output=True, check=False, env=env)

    def adopt_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))

    def assert_unchanged(self, root: Path, before: list[tuple[str, str]]) -> None:
        self.assertEqual(before, snapshot(root))
        self.assertFalse((root / ".agent_state").exists())

    def test_python_plan_has_candidate_drafts_and_confirmations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.project(root, "python")
            plan = build_plan(root)
        self.assertEqual("python", plan["adapter"]["primary_adapter"])
        self.assertEqual("python3 -m unittest discover -s tests", plan["test_candidates"][0]["command"])
        self.assertEqual("UNTRUSTED_DRAFT", plan["task_draft"]["draft_status"])
        self.assertIn("production/**", plan["task_draft"]["write_scope"]["deny"])
        self.assertTrue(all(item["status"] == "REQUIRES_CONFIRMATION" for item in plan["required_confirmations"]))
        self.assertTrue(all(item["status"] == "MUST_NOT_AUTO_DECIDE" for item in plan["blocked_decisions"]))

    def test_node_plan_uses_explicit_package_test_script_as_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.project(root, "node")
            plan = build_plan(root)
        candidate = plan["test_candidates"][0]
        self.assertEqual("npm test", candidate["command"])
        self.assertEqual("high", candidate["confidence"])
        self.assertTrue(candidate["requires_confirmation"])

    def test_generic_fallback_is_unresolved_and_network_is_not_used(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.project(root, "generic")
            with patch.object(socket, "socket", side_effect=AssertionError("network is forbidden")):
                plan = build_plan(root)
        self.assertEqual("generic", plan["adapter"]["primary_adapter"])
        self.assertEqual("generic-python-smoke", plan["test_candidates"][0]["candidate_id"])
        self.assertIn("Adapter detection is low confidence", " ".join(plan["warnings"]))
        self.assertEqual("low", plan["preset_recommendation"]["confidence"])

    def test_manifest_reports_create_same_and_different_without_copying(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.project(root, "generic")
            (root / "AGENTS.md").write_text((ROOT / "AGENTS.md").read_text(encoding="utf-8"), encoding="utf-8")
            first = build_plan(root)
            (root / "AGENTS.md").write_text("different\n", encoding="utf-8")
            second = build_plan(root)
        same = next(item for item in first["asset_manifest"] if item["target"] == "AGENTS.md")
        different = next(item for item in second["asset_manifest"] if item["target"] == "AGENTS.md")
        created = next(item for item in second["asset_manifest"] if item["target"] == "schemas")
        self.assertEqual("EXISTS_SAME", same["operation"])
        self.assertEqual("EXISTS_DIFFERENT", different["operation"])
        self.assertEqual("CREATE", created["operation"])

    def test_cli_stdout_json_is_sanitized_and_target_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "中文 project with spaces"
            root.mkdir()
            self.project(root, "python")
            before = snapshot(root)
            result = self.cli(root, "--format", "json")
            self.assertEqual(0, result.returncode, result.stderr)
            plan = json.loads(result.stdout)
            self.assertEqual("<target-project>", plan["project_root"])
            self.assertNotIn(str(root), result.stdout)
            self.assert_unchanged(root, before)

    def test_cli_writes_only_explicit_external_output_and_rejects_target_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "target"
            root.mkdir()
            self.project(root, "node")
            before = snapshot(root)
            external = base / "adoption-plan.md"
            written = self.cli(root, "--format", "markdown", "--output", str(external))
            rejected = self.cli(root, "--format", "json", "--output", str(root / "plan.json"))
            self.assertEqual(0, written.returncode, written.stderr)
            self.assertTrue(external.is_file())
            self.assertIn("This run did not modify the target project", external.read_text(encoding="utf-8"))
            self.assertEqual(3, rejected.returncode)
            self.assert_unchanged(root, before)

    def test_cli_canary_preserves_python_node_and_generic_projects(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for kind in ("python", "node", "generic"):
                root = base / kind
                root.mkdir()
                self.project(root, kind)
                before = snapshot(root)
                result = self.cli(root, "--format", "json")
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual("dry-run", json.loads(result.stdout)["mode"])
                self.assert_unchanged(root, before)

    def test_markdown_explains_untrusted_drafts_and_no_write_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.project(root, "generic")
            markdown = render_markdown(build_plan(root))
        self.assertIn("## Required human confirmations", markdown)
        self.assertIn("## Forbidden automatic decisions", markdown)
        self.assertIn("not authorization", markdown)
        self.assertIn("absolute paths are intentionally hidden", markdown)

    def test_agent_adopt_top_level_help_lists_all_commands(self) -> None:
        result = self.adopt_cli("--help")
        self.assertEqual(0, result.returncode, result.stderr)
        for command in ("dry-run", "export-drafts", "compile-runtime-artifacts", "install-approved", "assess-rollback", "rollback-install"):
            self.assertIn(command, result.stdout)
        self.assertNotIn("TOKEN=", result.stdout + result.stderr)

    def test_agent_adopt_help_matches_dispatcher_commands(self) -> None:
        result = self.adopt_cli("--help")
        self.assertEqual(0, result.returncode, result.stderr)
        declared = {"dry-run", "export-drafts", "compile-runtime-artifacts", "install-approved", "assess-rollback", "rollback-install"}
        self.assertTrue(all(command in result.stdout for command in declared))

    def test_agent_adopt_subcommand_help_lists_real_parameters_and_safety_boundaries(self) -> None:
        expected = {
            "dry-run": ("--project-root",),
            "export-drafts": ("--plan", "--confirmations", "--output-dir", "--target-project-root"),
            "compile-runtime-artifacts": ("--plan", "--confirmations", "--draft-bundle", "--output-dir", "--target-project-root"),
            "install-approved": ("--plan", "--confirmations", "--runtime-artifact-bundle", "does not activate"),
            "assess-rollback": ("--installation-receipt", "read-only"),
            "rollback-install": ("--rollback-approval", "unsupported"),
        }
        for command, fragments in expected.items():
            with self.subTest(command=command):
                result = self.adopt_cli(command, "--help")
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertTrue(all(fragment in result.stdout for fragment in fragments), result.stdout)
                self.assertNotIn("TOKEN=", result.stdout + result.stderr)

    def test_agent_adopt_unknown_subcommand_fails_closed(self) -> None:
        result = self.adopt_cli("unknown-command")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("invalid choice", result.stderr)
        self.assertNotIn("TOKEN=", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
