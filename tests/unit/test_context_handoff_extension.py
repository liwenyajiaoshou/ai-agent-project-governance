from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
EXTENSION = ROOT / "extensions" / "context-handoff"
spec = importlib.util.spec_from_file_location("context_handoff", EXTENSION / "context_handoff.py")
context_handoff = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(context_handoff)


class ContextHandoffExtensionTest(unittest.TestCase):
    def evidence(self, **extra: object) -> dict:
        return {"project_name": "Example", "task_statuses": ["READY"], "verification_statuses": ["PASS"], "authoritative_files": ["docs/IMPLEMENTATION_PLAN.md"], "generated_at": "2026-07-18T00:00:00+00:00", **extra}

    def test_manifest_default_disabled_and_profile_is_optional(self) -> None:
        manifest = yaml.safe_load((EXTENSION / "extension.yaml").read_text(encoding="utf-8"))
        self.assertFalse(manifest["default_enabled"])
        self.assertFalse(yaml.safe_load((ROOT / "profiles" / "multi-agent-context" / "profile.yaml").read_text(encoding="utf-8"))["default_enabled"])

    def test_preview_writes_nothing_and_snapshot_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "one"; target.mkdir()
            result = context_handoff.preview(target, "PROJECT_A", "TASK_A", self.evidence())
            self.assertEqual("preview", result["action"]); self.assertFalse((target / ".agent_context_handoff").exists())
            unknown = context_handoff.build_snapshot(target, "PROJECT_A", "TASK_A")
            self.assertEqual("UNKNOWN", unknown["task_status"])
            conflict = context_handoff.build_snapshot(target, "PROJECT_A", "TASK_A", self.evidence(task_statuses=["READY", "CLOSED"]))
            self.assertEqual("CONFLICT_REQUIRES_REVIEW", conflict["task_status"])
            self.assertEqual("CONFLICT_REQUIRES_REVIEW", conflict["final_status"])
            context_handoff.validate_snapshot(unknown)

    def test_enable_is_idempotent_conflict_safe_and_disable_preserves_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp); data = self.evidence()
            first = context_handoff.enable(target, "PROJECT_A", "TASK_A", data, "TASK_STARTED")
            second = context_handoff.enable(target, "PROJECT_A", "TASK_A", data, "TASK_STARTED")
            self.assertEqual(first["generated"], second["generated"])
            paths = context_handoff.paths_for(target, "PROJECT_A", "TASK_A")
            before = paths["current"].read_bytes(); self.assertEqual("DISABLED", context_handoff.disable(target)["status"])
            self.assertEqual(before, paths["current"].read_bytes())
            paths["current"].write_text("user changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CONFLICT_REQUIRES_REVIEW"):
                context_handoff.enable(target, "PROJECT_A", "TASK_A", data, "TASK_STARTED")
            plan = context_handoff.uninstall(target)
            self.assertTrue(plan["history_preserved"])
            self.assertGreater(plan["preserved_history_count"], 0)
            self.assertIn(str(paths["state"]), plan["deletion_plan"])
            self.assertIn(str(paths["ownership"]), plan["control_files"])
            context_handoff.uninstall(target, apply=True)
            self.assertTrue(paths["current"].exists())
            self.assertFalse(paths["state"].exists())

    def test_project_and_task_paths_are_isolated_and_local_commit_is_not_remote_merge(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp); data = self.evidence(merge_commit="abc123")
            one = context_handoff.enable(target, "PROJECT_A", "TASK_A", data, "TASK_STARTED")
            two = context_handoff.enable(target, "PROJECT_B", "TASK_A", data, "TASK_STARTED")
            three = context_handoff.enable(target, "PROJECT_A", "TASK_B", data, "TASK_STARTED")
            self.assertEqual(11, len(set(one["generated"] + two["generated"] + three["generated"])))
            snapshot = yaml.safe_load(context_handoff.paths_for(target, "PROJECT_A", "TASK_A")["snapshot"].read_text(encoding="utf-8"))
            self.assertEqual("LOCAL_ONLY", snapshot["final_status"])
            self.assertEqual("READY", snapshot["task_status"])

    def test_snapshot_schema_rejects_extra_authority_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            snapshot = context_handoff.build_snapshot(Path(temp), "PROJECT_A", "TASK_A", self.evidence())
            snapshot["may_complete_task"] = True
            with self.assertRaises(Exception):
                context_handoff.validate_snapshot(snapshot)

    def test_index_aggregates_two_tasks_updates_one_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            context_handoff.enable(target, "PROJECT_A", "TASK_A", self.evidence(generated_at="2026-07-18T00:00:00+00:00"), "TASK_STARTED")
            context_handoff.enable(target, "PROJECT_A", "TASK_B", self.evidence(generated_at="2026-07-18T00:01:00+00:00"), "TASK_STARTED")
            index = context_handoff.paths_for(target, "PROJECT_A", "TASK_A")["index"]
            first = index.read_text(encoding="utf-8")
            self.assertIn("## TASK_A", first); self.assertIn("## TASK_B", first)
            self.assertEqual(2, first.count("## TASK_"))
            context_handoff.enable(target, "PROJECT_A", "TASK_B", self.evidence(task_statuses=["CLOSED"], generated_at="2026-07-18T00:02:00+00:00"), "PHASE_CLOSED")
            updated = index.read_text(encoding="utf-8")
            self.assertIn("## TASK_A", updated); self.assertIn("task_status: CLOSED", updated)
            self.assertEqual(2, updated.count("## TASK_"))
            context_handoff.enable(target, "PROJECT_A", "TASK_A", self.evidence(generated_at="2026-07-18T00:00:00+00:00"), "TASK_STARTED")
            self.assertEqual(2, index.read_text(encoding="utf-8").count("## TASK_"))

    def test_index_is_deterministic_and_projects_remain_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as one_temp, tempfile.TemporaryDirectory() as two_temp:
            one, two = Path(one_temp), Path(two_temp)
            a = self.evidence(generated_at="2026-07-18T00:00:00+00:00")
            b = self.evidence(generated_at="2026-07-18T00:01:00+00:00")
            context_handoff.enable(one, "PROJECT_A", "TASK_B", b, "TASK_STARTED")
            context_handoff.enable(one, "PROJECT_A", "TASK_A", a, "TASK_STARTED")
            context_handoff.enable(two, "PROJECT_A", "TASK_A", a, "TASK_STARTED")
            context_handoff.enable(two, "PROJECT_A", "TASK_B", b, "TASK_STARTED")
            first = context_handoff.paths_for(one, "PROJECT_A", "TASK_A")["index"].read_text(encoding="utf-8")
            second = context_handoff.paths_for(two, "PROJECT_A", "TASK_A")["index"].read_text(encoding="utf-8")
            self.assertEqual(first, second)
            context_handoff.enable(one, "PROJECT_B", "TASK_C", a, "TASK_STARTED")
            self.assertNotIn("## TASK_C", first)
            self.assertNotIn("## TASK_A", context_handoff.paths_for(one, "PROJECT_B", "TASK_C")["index"].read_text(encoding="utf-8"))

    def test_unknown_conflict_and_invalid_snapshots_fail_closed_without_erasing_valid_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            context_handoff.enable(target, "PROJECT_A", "TASK_A", self.evidence(), "TASK_STARTED")
            unknown = context_handoff.enable(target, "PROJECT_A", "TASK_UNKNOWN", {}, "TASK_STARTED")
            self.assertEqual("ENABLED", unknown["status"])
            conflict = context_handoff.enable(target, "PROJECT_A", "TASK_CONFLICT", self.evidence(task_statuses=["READY", "CLOSED"]), "TASK_STARTED")
            self.assertEqual("ENABLED", conflict["status"])
            paths = context_handoff.paths_for(target, "PROJECT_A", "TASK_A")
            invalid = paths["snapshot"].parent / "TASK_INVALID.yaml"
            invalid.write_text("not: [valid", encoding="utf-8")
            schema_invalid = paths["snapshot"].parent / "TASK_SCHEMA_INVALID.yaml"
            schema_invalid.write_text(yaml.safe_dump({"project_id": "PROJECT_A", "task_id": "TASK_SCHEMA_INVALID"}), encoding="utf-8")
            result = context_handoff.enable(target, "PROJECT_A", "TASK_B", self.evidence(), "TASK_STARTED")
            rendered = paths["index"].read_text(encoding="utf-8")
            self.assertEqual("ENABLED_WITH_WARNINGS", result["status"])
            self.assertIn("task_status: UNKNOWN", rendered)
            self.assertIn("CONFLICT_REQUIRES_REVIEW", rendered)
            self.assertIn("INVALID_TASK_SNAPSHOT", rendered)
            self.assertIn("## TASK_A", rendered); self.assertIn("## TASK_B", rendered)
            self.assertNotIn("## TASK_INVALID", rendered)
            self.assertNotIn("## TASK_SCHEMA_INVALID", rendered)

    def test_user_modified_index_is_preserved_as_a_proposed_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            context_handoff.enable(target, "PROJECT_A", "TASK_A", self.evidence(), "TASK_STARTED")
            paths = context_handoff.paths_for(target, "PROJECT_A", "TASK_A")
            paths["index"].write_text("user authored index\n", encoding="utf-8")
            result = context_handoff.enable(target, "PROJECT_A", "TASK_B", self.evidence(), "TASK_STARTED")
            self.assertEqual("OWNERSHIP_CONFLICT", result["status"])
            self.assertEqual("user authored index\n", paths["index"].read_text(encoding="utf-8"))
            proposal = paths["proposed_index"].read_text(encoding="utf-8")
            self.assertIn("## TASK_A", proposal); self.assertIn("## TASK_B", proposal)

    def test_parallel_enables_keep_a_complete_index_without_temp_or_lock_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            def run(task_id: str) -> dict:
                return context_handoff.enable(target, "PROJECT_A", task_id, self.evidence(generated_at=f"2026-07-18T00:0{task_id[-1]}:00+00:00"), "TASK_STARTED")
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(run, ("TASK_A", "TASK_B")))
            self.assertEqual(["ENABLED", "ENABLED"], sorted(result["status"] for result in results))
            paths = context_handoff.paths_for(target, "PROJECT_A", "TASK_A")
            rendered = paths["index"].read_text(encoding="utf-8")
            self.assertIn("## TASK_A", rendered); self.assertIn("## TASK_B", rendered)
            self.assertFalse(paths["lock"].exists()); self.assertFalse(paths["ownership_lock"].exists())
            self.assertFalse(list((target / ".agent_context_handoff").rglob(".write-*")))

    def test_index_stays_within_the_token_line_limit_for_twenty_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            for number in range(21):
                context_handoff.enable(target, "PROJECT_A", f"TASK_{number:02d}", self.evidence(generated_at=f"2026-07-18T00:{number:02d}:00+00:00"), "TASK_STARTED")
                if number + 1 in {2, 10, 20, 21}:
                    checkpoint = context_handoff.paths_for(target, "PROJECT_A", "TASK_00")["index"].read_text(encoding="utf-8")
                    self.assertEqual(min(number + 1, 20), checkpoint.count("## TASK_"))
                    self.assertLessEqual(len(checkpoint.splitlines()), 150)
            index = context_handoff.paths_for(target, "PROJECT_A", "TASK_00")["index"].read_text(encoding="utf-8")
            self.assertEqual(20, index.count("## TASK_"))
            self.assertIn("ARCHIVED_TASK_COUNT: 1", index)
            self.assertLessEqual(len(index.splitlines()), 150)

    def test_cli_returns_nonzero_for_invalid_snapshot_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            context_handoff.enable(target, "PROJECT_A", "TASK_A", self.evidence(), "TASK_STARTED")
            paths = context_handoff.paths_for(target, "PROJECT_A", "TASK_A")
            (paths["snapshot"].parent / "TASK_INVALID.yaml").write_text("broken: [", encoding="utf-8")
            result = subprocess.run([sys.executable, str(EXTENSION / "manage.py"), "context-handoff", "enable", "--target", str(target), "--project-id", "PROJECT_A", "--task-id", "TASK_B"], text=True, capture_output=True, check=False)
            self.assertEqual(2, result.returncode)
            self.assertEqual("ENABLED_WITH_WARNINGS", json.loads(result.stdout)["status"])

    def test_uninstall_does_not_follow_ownership_paths_outside_its_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); target = root / "target"; target.mkdir()
            foreign = root / "foreign_extension_state.yaml"; foreign.write_text("keep me", encoding="utf-8")
            context_handoff.enable(target, "PROJECT_A", "TASK_A", self.evidence(), "TASK_STARTED")
            paths = context_handoff.paths_for(target, "PROJECT_A", "TASK_A")
            ownership = json.loads(paths["ownership"].read_text(encoding="utf-8"))
            ownership["files"][str(foreign)] = context_handoff._digest(foreign.read_bytes())
            paths["ownership"].write_text(json.dumps(ownership), encoding="utf-8")
            context_handoff.uninstall(target, apply=True)
            self.assertTrue(foreign.exists())
            self.assertFalse(paths["state"].exists())


if __name__ == "__main__":
    unittest.main()
