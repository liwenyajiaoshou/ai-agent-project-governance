from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from governance.adoption.lifecycle import build_adoption_test_plan, build_guard_evidence, close_adoption, run_adoption_test_plan, transition_project_state, verify_adoption
from governance.adoption.lifecycle_evidence_adapter import ReferenceEvidence
from governance.adoption.lifecycle_context import AdoptionLifecycleContext, run_adoption_preflight, snapshot_workspace, task_request_from_contract
from governance.adoption.installer import digest
from governance.evidence import EvidenceBinding, EvidenceObject, EvidenceResolver, InMemoryEvidenceStore


ROOT = Path("/tmp/agc-adoption-04f-b")
ROOT.mkdir(parents=True, exist_ok=True)


def contract() -> dict:
    return {"schema_version":"1.0","task_id":"ADOPTION-1","project_mode":"EXECUTION","task_level":"A","status":"DRAFT","objective":["Change src only"],"read_scope":["src/**"],"write_scope":{"allow":["src/**"],"deny":["secrets/**"]},"autonomy":{"may_debug_test_failures":False,"may_edit_adjacent_tests":False,"may_edit_same_module_helpers":False,"must_not_expand_architecture":True},"stop_conditions":["BLOCKED_DECISION:network_access"],"verification":{"level_1":[],"level_2":[],"level_3":[]},"report":{"format":"compact","fields":["tests"]},"governance":{"level":"LEVEL_3_HIGH_RISK","confirmation_fields":["activation_approval"],"parent_task_id":None,"execution_envelope_rule":"GOV-ENVELOPE-001"}}


def state() -> dict:
    return {"schema_version":"1.0","project_mode":"EXECUTION","architecture_status":"confirmed","implementation_plan_status":"confirmed","repository_root":".","adapter":"generic","high_risk_paths":["secrets/**"],"default_forbidden_operations":["network_access"],"status":"ACTIVATED_NOT_PREFLIGHTED","activated":True,"activation_status":"ACTIVATED_NOT_PREFLIGHTED","activation_approval_digest":"a" * 64,"activation_receipt_digest":"b" * 64,"lifecycle_stage":"ACTIVATED_NOT_PREFLIGHTED","lifecycle_evidence":[]}


class LifecycleFoundationTest(unittest.TestCase):
    def write_state(self, root: Path) -> Path:
        path = root / "project_state.yaml"; path.write_text(yaml.safe_dump(state()), encoding="utf-8"); return path

    def context(self, task: Path, state_path: Path, root: Path) -> AdoptionLifecycleContext:
        return AdoptionLifecycleContext(
            target_identity_digest="a" * 64, task_contract_digest=hashlib.sha256(task.read_bytes()).hexdigest(),
            project_state_digest=hashlib.sha256(state_path.read_bytes()).hexdigest(), runtime_artifact_manifest_digest="b" * 64,
            final_install_approval_digest="c" * 64, installation_receipt_digest="d" * 64,
            activation_approval_digest="e" * 64, activation_receipt_digest="f" * 64,
            compiler_id="synthetic.compiler", compiler_version="1", compiler_digest="1" * 64,
            confirmation_digest="2" * 64, confirmed_test_candidates=(("python-py-compile", "3" * 64),),
            confirmed_test_candidate_set_digest="4" * 64, blocked_decisions=("network_access",),
            blocked_decisions_digest="5" * 64, workspace_snapshot_digest=snapshot_workspace(root),
        )

    def evidence(self, root: Path, *, evidence_type: str, status: str, state_path: Path, target: str = "a" * 64, upstream: list[str] | None = None) -> Path:
        path = root / f"{evidence_type}.json"
        path.write_text(json.dumps({"schema_version":"1.0", "evidence_type":evidence_type, "status":status,
                                    "target_identity_digest":target, "previous_state_digest":hashlib.sha256(state_path.read_bytes()).hexdigest(),
                                    "upstream_evidence_digests":upstream or [], "payload":{}}, sort_keys=True), encoding="utf-8")
        return path

    def reference_evidence(self, *, evidence_type: str, status: str, state_path: Path, upstream: list[str] | None = None) -> ReferenceEvidence:
        payload = json.dumps({"schema_version":"1.0", "evidence_type":evidence_type, "status":status,
                              "target_identity_digest":"a" * 64, "previous_state_digest":hashlib.sha256(state_path.read_bytes()).hexdigest(),
                              "upstream_evidence_digests":upstream or [], "payload":{}}, sort_keys=True).encode()
        store = InMemoryEvidenceStore()
        obj = EvidenceObject.from_bytes(payload, evidence_type=evidence_type, schema_id="adoption_lifecycle_evidence.schema.json")
        return ReferenceEvidence(EvidenceBinding(evidence_type, store.publish(payload, obj)), EvidenceResolver(store))

    def test_contract_mapping_preserves_narrow_scope(self) -> None:
        request = task_request_from_contract(contract())
        self.assertEqual(["src/**"], request["hints"]["likely_paths"])
        self.assertFalse(request["hints"]["external_access"])
        bad = contract(); bad["write_scope"]["allow"] = []
        with self.assertRaises(ValueError): task_request_from_contract(bad)

    def test_adoption_preflight_reuses_formal_runtime(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp); task = root / "task.yaml"; state_path = self.write_state(root)
            task.write_text(yaml.safe_dump(contract()), encoding="utf-8")
            context = self.context(task, state_path, root)
            evidence = run_adoption_preflight(context, task, state_path)
            self.assertEqual("PASS", evidence["status"]); self.assertEqual(context.digest(), evidence["context_digest"])

    def test_transition_requires_exact_digest_and_order(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            path = self.write_state(Path(temp)); current = hashlib.sha256(path.read_bytes()).hexdigest()
            evidence = self.evidence(Path(temp), evidence_type="PreflightEvidence", status="PASS", state_path=path)
            with self.assertRaises(ValueError): transition_project_state(path, expected_current_stage="ACTIVATED_NOT_PREFLIGHTED", expected_current_state_digest="0" * 64, evidence_path=evidence, requested_next_stage="PREFLIGHT_PASSED", target_identity_digest="a" * 64)
            next_state = transition_project_state(path, expected_current_stage="ACTIVATED_NOT_PREFLIGHTED", expected_current_state_digest=current, evidence_path=evidence, requested_next_stage="PREFLIGHT_PASSED", target_identity_digest="a" * 64)
            self.assertEqual("PREFLIGHT_PASSED", next_state["lifecycle_stage"])
            with self.assertRaises(ValueError): transition_project_state(path, expected_current_stage="PREFLIGHT_PASSED", expected_current_state_digest=hashlib.sha256(path.read_bytes()).hexdigest(), evidence_path=evidence, requested_next_stage="CLOSED", target_identity_digest="a" * 64)

    def test_reference_and_mixed_chain_transitions_are_explicit_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp); path = self.write_state(root)
            reference = self.reference_evidence(evidence_type="PreflightEvidence", status="PASS", state_path=path)
            first = transition_project_state(path, expected_current_stage="ACTIVATED_NOT_PREFLIGHTED",
                expected_current_state_digest=hashlib.sha256(path.read_bytes()).hexdigest(), requested_next_stage="PREFLIGHT_PASSED",
                target_identity_digest="a" * 64, evidence_source=reference)
            self.assertNotIn("evidence_file", first["lifecycle_evidence"][-1])
            legacy = self.evidence(root, evidence_type="GuardEvidence", status="PASS", state_path=path,
                upstream=[reference.binding.reference.sha256])
            second = transition_project_state(path, expected_current_stage="PREFLIGHT_PASSED",
                expected_current_state_digest=hashlib.sha256(path.read_bytes()).hexdigest(), requested_next_stage="GUARDED",
                target_identity_digest="a" * 64, evidence_path=legacy, prior_reference_evidence=[reference])
            self.assertEqual([reference.binding.reference.sha256], second["lifecycle_evidence"][-1]["upstream_evidence_digests"])
            self.assertIn("evidence_file", second["lifecycle_evidence"][-1])

    def test_reference_failures_and_stale_cas_leave_state_unchanged(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            path = self.write_state(Path(temp)); before = path.read_bytes()
            missing_store = InMemoryEvidenceStore()
            payload = b'{"schema_version":"1.0"}'
            obj = EvidenceObject.from_bytes(payload, evidence_type="PreflightEvidence", schema_id="adoption_lifecycle_evidence.schema.json")
            missing = ReferenceEvidence(EvidenceBinding("missing", obj.reference()), EvidenceResolver(missing_store))
            with self.assertRaises(ValueError):
                transition_project_state(path, expected_current_stage="ACTIVATED_NOT_PREFLIGHTED", expected_current_state_digest=hashlib.sha256(before).hexdigest(), requested_next_stage="PREFLIGHT_PASSED", target_identity_digest="a" * 64, evidence_source=missing)
            self.assertEqual(before, path.read_bytes())
            with self.assertRaises(ValueError):
                transition_project_state(path, expected_current_stage="ACTIVATED_NOT_PREFLIGHTED", expected_current_state_digest="0" * 64, requested_next_stage="PREFLIGHT_PASSED", target_identity_digest="a" * 64, evidence_source=missing)
            self.assertEqual(before, path.read_bytes())

    def test_extra_or_ambiguous_sources_fail_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp); path = self.write_state(root); before = path.read_bytes()
            reference = self.reference_evidence(evidence_type="PreflightEvidence", status="PASS", state_path=path)
            legacy = self.evidence(root, evidence_type="PreflightEvidence", status="PASS", state_path=path)
            with self.assertRaises(ValueError):
                transition_project_state(path, expected_current_stage="ACTIVATED_NOT_PREFLIGHTED", expected_current_state_digest=hashlib.sha256(before).hexdigest(), requested_next_stage="PREFLIGHT_PASSED", target_identity_digest="a" * 64, evidence_path=legacy, evidence_source=reference)
            self.assertEqual(before, path.read_bytes())

    def test_guard_blocks_denied_path_and_confirmed_plan_is_exact(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp); (root / "src").mkdir(); (root / "src" / "ok.py").write_text("", encoding="utf-8")
            preflight = {"workspace_snapshot_digest": snapshot_workspace(root), "evidence_digest": "a" * 64}
            blocked = build_guard_evidence(contract(), preflight, root, ["secrets/key.txt"])
            self.assertEqual("BLOCKED", blocked["status"])
            passed = build_guard_evidence(contract(), preflight, root, ["src/ok.py"])
            self.assertEqual("PASS", passed["status"])
            spec = {"argv":["python","-c","pass"],"level":1,"timeout":1,"cwd":"."}
            with patch("governance.adoption.lifecycle.registry_command", return_value=spec):
                plan = build_adoption_test_plan("c" * 64, passed, {"confirmed": digest(spec)})
            self.assertEqual(["confirmed"], [item["candidate_id"] for item in plan["selected"]])
            with patch("governance.adoption.lifecycle.registry_command", return_value={**spec, "argv":["python","-c","fail"]}):
                with self.assertRaises(ValueError): build_adoption_test_plan("c" * 64, passed, {"confirmed": digest(spec)})

    def test_local_node_test_is_allowed_but_package_install_is_blocked(self) -> None:
        guard = {"status": "PASS", "evidence_digest": "a" * 64}
        local_test = {"argv": ["npm", "test"], "level": 1, "timeout": 30, "cwd": "."}
        with patch("governance.adoption.lifecycle.registry_command", return_value=local_test):
            plan = build_adoption_test_plan("c" * 64, guard, {"node-package-test": digest(local_test)})
        self.assertEqual(["npm", "test"], plan["selected"][0]["argv"])
        install = {"argv": ["npm", "install"], "level": 1, "timeout": 30, "cwd": "."}
        with patch("governance.adoption.lifecycle.registry_command", return_value=install):
            with self.assertRaisesRegex(ValueError, "unsafe"):
                build_adoption_test_plan("c" * 64, guard, {"node-package-test": digest(install)})

    def test_failed_or_stale_verification_cannot_close(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp); (root / "src").mkdir(); (root / "src" / "ok.py").write_text("", encoding="utf-8")
            guard = {"status":"PASS","evidence_digest":"a" * 64}; plan = {"status":"READY","test_plan_digest":"b" * 64}
            run = {"workspace_after_digest": snapshot_workspace(root), "test_run_digest":"c" * 64, "results":[{"status":"FAIL","required":True}]}
            context = {"task_id":"ADOPTION-1","context_digest":"d" * 64}
            failed = verify_adoption(context, guard, plan, run, root)
            self.assertEqual("FAILED", failed["status"])
            with self.assertRaises(ValueError): close_adoption(failed, root)
            run["results"] = [{"status":"PASS","required":True}]; run["workspace_after_digest"] = "0" * 64
            self.assertEqual("STALE", verify_adoption(context, guard, plan, run, root)["status"])

    def test_exact_runner_records_exit_code_without_shell(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp); plan = {"status":"READY","context_digest":"a" * 64,"guard_evidence_digest":"b" * 64,"selected":[{"candidate_id":"x","command_digest":"c" * 64,"argv":["python","-c","pass"],"cwd":".","timeout_seconds":1,"required":True}]}
            plan["test_plan_digest"] = digest(plan)
            with patch("governance.adoption.lifecycle.run_command", return_value={"status":"PASS","exit_code":0,"sanitized_stdout_tail":"","sanitized_stderr_tail":"","stdout_digest":"a" * 64,"stderr_digest":"b" * 64,"redaction_count":0,"redaction_rule_version":"1.0","duration_ms":1}):
                run = run_adoption_test_plan(root, plan)
            self.assertEqual("PASS", run["overall_status"]); self.assertEqual(0, run["results"][0]["exit_code"])


if __name__ == "__main__": unittest.main()
