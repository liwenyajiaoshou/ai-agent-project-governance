from __future__ import annotations

import hashlib
import json
import re
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import yaml

from governance.adoption import build_plan, compile_runtime_bundle, export_drafts, install_approved
from governance.adoption.c0_scanner import scan_directory_for_c0, scan_file_for_c0
from governance.adoption.exporter import _digest, _validate_plan
from governance.adoption.io import raw_and_normalized_digests, write_text_exclusive
from governance.adoption.provenance import PUBLIC_GENERATION_PATH, canonical_digest
from governance.adoption.scope_contract import canonical_scope
from governance.adoption.writeset import classify_install_paths
from tests.unit.adoption_flow import approved_inputs, formal_inputs, preview_inputs, run_cli


class Case001MinimumUnblockTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.target = self.base / "中文 target with spaces"
        self.target.mkdir()
        (self.target / "AGENTS.md").write_text("local only\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def scope(self, **changes) -> dict:
        value = {
            "task_id": "CASE001-SCOPE",
            "task_goal": "Verify canonical scope boundaries.",
            "execution_mode": "ACTIVE_DEVELOPMENT",
            "allowed_paths": ["src/core/**", "project_state.yaml"],
            "denied_paths": ["data/**", ".env"],
            "known_safe_commands": ["python -m unittest"],
            "network_policy": "BLOCKED",
            "data_write_policy": "BLOCKED",
            "git_policy": "BLOCKED",
            "owner_confirmed_empty_scope": False,
        }
        value.update(changes)
        return value

    def test_active_and_observation_scope_modes_fail_closed(self) -> None:
        self.assertEqual(["project_state.yaml", "src/core/**"], canonical_scope(self.scope(), source="active")["allowed_paths"])
        with self.assertRaisesRegex(ValueError, "EMPTY_ALLOWED_SCOPE_REQUIRES_EXPLICIT_OBSERVATION_MODE"):
            canonical_scope(self.scope(allowed_paths=[]), source="active empty")
        observation = self.scope(execution_mode="OBSERVATION_ONLY", allowed_paths=[], owner_confirmed_empty_scope=True)
        self.assertEqual("OBSERVATION_ONLY", canonical_scope(observation, source="observation")["execution_mode"])
        with self.assertRaisesRegex(ValueError, "EMPTY_ALLOWED_SCOPE_REQUIRES_EXPLICIT_OBSERVATION_MODE"):
            canonical_scope(dict(observation, owner_confirmed_empty_scope=False), source="unconfirmed observation")

    def test_private_planner_cannot_masquerade_as_public_cli(self) -> None:
        scope_path = self.base / "private-scope.yaml"
        scope_path.write_text(yaml.safe_dump(self.scope()), encoding="utf-8")
        plan = build_plan(self.target, scope_path)
        with self.assertRaisesRegex(ValueError, "private planner calls"):
            _validate_plan(plan, target_root=self.target)

    def test_scope_mismatch_rejected_at_plan_confirmation_and_draft_boundaries(self) -> None:
        plan, plan_path, confirmation_path, _ = formal_inputs(self.base, self.target, stem="mismatch", confirmed=True)
        changed = json.loads(json.dumps(plan))
        changed["task_draft"]["scope_contract"]["allowed_paths"] = ["other/**"]
        changed["plan_digest"] = _digest(changed)
        with self.assertRaisesRegex(ValueError, "SCOPE_CONTRACT_MISMATCH"):
            _validate_plan(changed, target_root=self.target)

        confirmation = yaml.safe_load(confirmation_path.read_text(encoding="utf-8"))
        confirmation["scope_contract"]["allowed_paths"] = ["other/**"]
        confirmation_path.write_text(yaml.safe_dump(confirmation), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SCOPE_CONTRACT_MISMATCH"):
            export_drafts(plan_path, confirmation_path, self.base / "bad-drafts", self.target)

        _, plan_path, confirmation_path, drafts, _, _ = preview_inputs(self.base, self.target, stem="draft-mismatch", confirmed=True)
        task_path = drafts / "task.yaml.draft"
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        task["scope_contract"]["allowed_paths"] = ["other/**"]
        task_path.write_text(yaml.safe_dump(task), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SCOPE_CONTRACT_MISMATCH"):
            compile_runtime_bundle(plan_path, confirmation_path, drafts, self.base / "bad-runtime", self.target)

    def test_plan_and_receipt_tampering_are_distinctly_rejected(self) -> None:
        plan, _, _, _ = formal_inputs(self.base, self.target, stem="tamper", confirmed=True)
        plan["task_draft"]["note"] = "ordinary plan tamper"
        plan["plan_digest"] = _digest(plan)
        with self.assertRaisesRegex(ValueError, "provenance plan payload digest"):
            _validate_plan(plan, target_root=self.target)

        plan, _, _, _ = formal_inputs(self.base, self.target, stem="receipt-tamper", confirmed=True)
        plan["provenance_receipt"]["target_head"] = "tampered"
        with self.assertRaisesRegex(ValueError, "provenance receipt digest"):
            _validate_plan(plan, target_root=self.target)

    def test_target_and_framework_git_bindings_fail_closed(self) -> None:
        for field, message in (("target_head", "target branch/HEAD mismatch"), ("framework_commit", "framework commit mismatch")):
            plan, _, _, _ = formal_inputs(self.base, self.target, stem=f"git-{field}", confirmed=True)
            plan["provenance_receipt"][field] = "0" * 40
            plan["provenance_receipt"]["provenance_receipt_digest"] = canonical_digest(
                plan["provenance_receipt"], omit=("provenance_receipt_digest",),
            )
            with self.assertRaisesRegex(ValueError, message):
                _validate_plan(plan, target_root=self.target)

    def test_canonical_writeset_classifies_existing_assets_as_manual(self) -> None:
        plan, _, _, _ = formal_inputs(self.base, self.target, stem="writeset", confirmed=True)
        classification = classify_install_paths(plan["asset_manifest"], self.target)
        self.assertEqual(["project_state.yaml", "task.yaml"], classification["CREATE"])
        self.assertIn("AGENTS.md", classification["MANUAL_ADOPTION_ASSET"])
        self.assertIn("config/presets", classification["MANUAL_ADOPTION_ASSET"])
        self.assertIn("scripts/agent_preflight.py", classification["MANUAL_ADOPTION_ASSET"])

    def test_existing_install_targets_reject_before_any_new_target_write(self) -> None:
        _, plan_path, confirmation_path, drafts, runtime, approval = approved_inputs(self.base, self.target, stem="existing")
        (self.target / "task.yaml").write_text("existing\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "sidecars|conflict"):
            install_approved(
                self.target, drafts, runtime, approval, self.base / "receipt.json", plan_path, confirmation_path,
            )
        self.assertFalse((self.target / "project_state.yaml").exists())

    def test_crlf_scope_preserves_raw_digest_and_outputs_lf(self) -> None:
        raw = yaml.safe_dump(self.scope(), sort_keys=False).replace("\n", "\r\n").encode("utf-8")
        digests = raw_and_normalized_digests(raw)
        self.assertNotEqual(digests["raw_sha256"], digests["normalized_text_sha256"])
        scope_path = self.base / "crlf-scope.yaml"
        scope_path.write_bytes(raw)
        plan = build_plan(self.target, scope_path, generation_path=PUBLIC_GENERATION_PATH)
        self.assertEqual(digests["raw_sha256"], plan["provenance_receipt"]["formal_scope_input_digest"])

    def test_public_cli_preview_flow_is_unapproved_lf_and_c0_clean(self) -> None:
        scope_path = self.base / "cli-scope.yaml"
        scope_path.write_text(yaml.safe_dump(self.scope(), sort_keys=False), encoding="utf-8")
        plan = self.base / "cli-plan.json"
        confirmation = self.base / "cli-confirmation.yaml"
        drafts, runtime, approval = self.base / "cli-drafts", self.base / "cli-runtime", self.base / "cli-approval.yaml"
        run_cli("--project-root", str(self.target), "--format", "json", "--output", str(plan), "--scope-file", str(scope_path), "dry-run")
        run_cli("confirmation-candidate", "--plan", str(plan), "--output", str(confirmation), "--target-project-root", str(self.target))
        run_cli("export-drafts", "--plan", str(plan), "--confirmations", str(confirmation), "--output-dir", str(drafts), "--target-project-root", str(self.target))
        run_cli("compile-runtime-artifacts", "--plan", str(plan), "--confirmations", str(confirmation), "--draft-bundle", str(drafts), "--output-dir", str(runtime), "--target-project-root", str(self.target))
        run_cli("approval-candidate", "--plan", str(plan), "--confirmations", str(confirmation), "--draft-bundle", str(drafts), "--runtime-artifact-bundle", str(runtime), "--target-project-root", str(self.target), "--output", str(approval))
        self.assertFalse(yaml.safe_load(confirmation.read_text(encoding="utf-8"))["confirmed_by_user"])
        candidate = yaml.safe_load(approval.read_text(encoding="utf-8"))
        self.assertFalse(candidate["install_approved"])
        self.assertFalse(candidate["activate_approved"])
        summary = (drafts / "ADOPTION_CONFIRMATION_SUMMARY.md").read_text(encoding="utf-8")
        self.assertIn("Draft proposes preset", summary)
        self.assertIn("No Owner confirmation recorded", summary)
        self.assertNotIn("The user confirmed", summary)
        self.assertEqual([], scan_directory_for_c0(self.base))
        formal_outputs = [plan, confirmation, approval, *drafts.rglob("*"), *runtime.rglob("*")]
        self.assertFalse(any(b"\r\n" in path.read_bytes() for path in formal_outputs if path.is_file()))

    def test_c0_scanner_rejects_illegal_control_character(self) -> None:
        path = self.base / "bad.md"
        path.write_bytes(b"hello\x01world\n")
        self.assertIn("Illegal C0 control character", scan_file_for_c0(path)[0])
        formal_path = self.base / "bad-formal.md"
        with self.assertRaisesRegex(ValueError, "illegal C0"):
            write_text_exclusive(formal_path, "hello\x01world\n")
        self.assertFalse(formal_path.exists())

    def test_canonical_findings_sets_are_exact_complete_and_c0_clean(self) -> None:
        root = Path(__file__).resolve().parents[2]
        report_root = root / "reports" / "case001"
        ledger = json.loads((report_root / "CASE001_FINDINGS_LEDGER.json").read_text(encoding="utf-8"))
        expected = {f"CASE-001-FINDING-{number:03d}" for number in range(1, 10)}
        records = ledger
        json_ids = [record["id"] for record in records]
        self.assertEqual(expected, set(json_ids))
        self.assertTrue(all(count == 1 for count in Counter(json_ids).values()))
        self.assertTrue(all({"status", "evidence", "resolution", "framework_version"} <= set(record) for record in records))

        matrix = (report_root / "CASE001_FINDINGS_RESOLUTION_MATRIX.md").read_text(encoding="utf-8")
        markdown_ids = re.findall(r"^\| (CASE-001-FINDING-\d{3}) \|", matrix, flags=re.MULTILINE)
        self.assertEqual(expected, set(markdown_ids))
        self.assertTrue(all(count == 1 for count in Counter(markdown_ids).values()))
        self.assertEqual([], scan_directory_for_c0(report_root))


if __name__ == "__main__":
    unittest.main()
