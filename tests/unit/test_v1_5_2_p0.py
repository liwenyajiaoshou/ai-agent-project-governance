from __future__ import annotations

import json
import tempfile
import unittest
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from governance.adoption.activation import activate_approved
from governance.adoption.contract_viability import adoption_lifecycle_viability, require_adoption_lifecycle_viability
from governance.adoption.installer import digest
from governance.adoption.recovery import compile_contract_recovery, recover_approved
from governance.adoption.runtime_artifact_compiler import MANIFEST_FILENAME
from governance.adoption.framework_upgrade import compile_framework_upgrade, install_framework_upgrade
from governance.adoption.lifecycle_context import build_lifecycle_context, run_adoption_preflight
from governance.adoption.evidence_registry import upstream_digests
from governance.adoption.lifecycle import transition_project_state
from governance.adoption.runtime_artifact_compiler import digest_bytes
from governance.schema_loader import load_mapping
from tests.unit import test_agent_adopt_activation as activation_fixture


class V152P0Test(unittest.TestCase):
    def test_viability_is_adoption_specific_and_requires_exact_state_scope(self):
        generic = {"write_scope":{"allow":[], "deny":[]}}
        self.assertEqual("ZERO_WRITE_FULL_ADOPTION_UNSUPPORTED", adoption_lifecycle_viability(generic)["reason_codes"][0])
        with self.assertRaisesRegex(ValueError, "ZERO_WRITE_FULL_ADOPTION_UNSUPPORTED"):
            require_adoption_lifecycle_viability(generic)
        self.assertTrue(adoption_lifecycle_viability({"write_scope":{"allow":["project_state.yaml"], "deny":[]}})["viable"])
        self.assertFalse(adoption_lifecycle_viability({"write_scope":{"allow":["src/**"], "deny":[]}})["viable"])

    def test_activated_runtime_recovery_preserves_history_and_rejects_replay(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temp:
            base = Path(temp); fixture = activation_fixture.ApprovedActivationTest()
            target, runtime, final, install, activation_approval = fixture.setup(base)
            activation_receipt = base / "activated.json"
            activate_approved(target, target/"task.yaml", target/"project_state.yaml", runtime/MANIFEST_FILENAME, final, install, activation_approval, activation_receipt)
            old_state = load_mapping(target/"project_state.yaml"); successor = load_mapping(target/"task.yaml")
            successor["task_id"] = "RECOVERED-TASK"; successor["status"] = "ACTIVE"
            successor_path = base/"successor.yaml"; successor_path.write_text(yaml.safe_dump(successor, sort_keys=False), encoding="utf-8")
            manifest_path = base/"recovery.json"
            manifest = compile_contract_recovery(target, successor_path, install, activation_receipt, manifest_path)
            now = datetime.now(timezone.utc)
            approval = {"schema_version":"1.0", "approved_by_user":True, "approved_action":"RECOVER_ACTIVATED_TASK_CONTRACT", "approved_at":now.isoformat(), "expires_at":(now+timedelta(hours=1)).isoformat(), "target_identity_digest":manifest["target_identity_digest"], "manifest_digest":manifest["manifest_digest"], "approved_writeset":manifest["writeset"], "approved_scope_delta":manifest["scope_delta"]}
            approval_path=base/"approval.json"; approval_path.write_text(json.dumps(approval), encoding="utf-8")
            evidence_path=base/"recovery-evidence.json"
            recover_approved(target, manifest_path, approval_path, install, activation_receipt, evidence_path)
            recovered, state = load_mapping(target/"task.yaml"), load_mapping(target/"project_state.yaml")
            self.assertEqual("RECOVERED-TASK", recovered["task_id"]); self.assertIn("supersession", recovered)
            self.assertEqual(old_state["lifecycle_evidence"], state["lifecycle_evidence"][:-1])
            self.assertEqual("ACTIVATED_NOT_PREFLIGHTED", state["lifecycle_stage"])
            context = build_lifecycle_context(target,target/"task.yaml",target/"project_state.yaml",install,activation_receipt,runtime_artifact_manifest=runtime/MANIFEST_FILENAME,final_install_approval=final,activation_approval=activation_approval,confirmation=base/"activation-confirmation.yaml",plan=base/"activation-plan.json")
            preflight = run_adoption_preflight(context,target/"task.yaml",target/"project_state.yaml")
            before=digest_bytes((target/"project_state.yaml").read_bytes()); current=load_mapping(target/"project_state.yaml")
            preflight_evidence={"schema_version":"1.0","evidence_type":"PreflightEvidence","status":"PASS","target_identity_digest":context.target_identity_digest,"previous_state_digest":before,"upstream_evidence_digests":upstream_digests(current),"payload":preflight}
            preflight_path=base/"preflight.json"; preflight_path.write_text(json.dumps(preflight_evidence),encoding="utf-8")
            transition_project_state(target/"project_state.yaml",expected_current_stage="ACTIVATED_NOT_PREFLIGHTED",expected_current_state_digest=before,evidence_path=preflight_path,requested_next_stage="PREFLIGHT_PASSED",target_identity_digest=context.target_identity_digest)
            self.assertEqual("PREFLIGHT_PASSED",load_mapping(target/"project_state.yaml")["lifecycle_stage"])
            with self.assertRaisesRegex(ValueError, "RECOVERY_EXTERNAL_MUTATION"):
                recover_approved(target, manifest_path, approval_path, install, activation_receipt, base/"replay.json")

    def test_expired_recovery_approval_fails_before_write(self):
        # Freshness is exercised independently so a stale decision never reaches writes.
        from governance.adoption.recovery import _approval_fresh
        stale = {"approved_by_user":True, "approved_action":"RECOVER_ACTIVATED_TASK_CONTRACT", "expires_at":(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()}
        with self.assertRaisesRegex(ValueError, "RECOVERY_APPROVAL_EXPIRED"):
            _approval_fresh(stale)

    def test_changed_only_upgrade_preserves_runtime_and_rejects_drift(self):
        source = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory(dir="/tmp") as temp:
            base=Path(temp); target=base/"target"; target.mkdir()
            (target/"task.yaml").write_text("runtime-task\n", encoding="utf-8"); (target/"project_state.yaml").write_text("runtime-state\n", encoding="utf-8")
            manifest_path=base/"upgrade.json"; manifest=compile_framework_upgrade(source, target, manifest_path)
            self.assertNotIn("task.yaml", manifest["writeset"]); self.assertTrue(manifest["writeset"])
            approval={"schema_version":"1.0","approved_by_user":True,"approved_action":"UPGRADE_FRAMEWORK_1_5_1_TO_1_5_2","manifest_digest":manifest["manifest_digest"],"target_identity_digest":manifest["target_identity_digest"],"approved_writeset":manifest["writeset"]}
            approval_path=base/"upgrade-approval.json"; approval_path.write_text(json.dumps(approval), encoding="utf-8")
            receipt=install_framework_upgrade(source,target,manifest_path,approval_path,base/"upgrade-receipt.json")
            self.assertEqual("UPGRADED",receipt["status"]); self.assertEqual("runtime-task\n",(target/"task.yaml").read_text())
            with self.assertRaisesRegex(ValueError,"UPGRADE_ATOMIC_WRITE_FAILED"):
                install_framework_upgrade(source,target,manifest_path,approval_path,base/"replay-receipt.json")

    def test_generic_preflight_redirects_activated_adoption_contract(self):
        source = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory(dir="/tmp") as temp:
            base=Path(temp)
            task={"schema_version":"1.0","task_id":"T","project_mode":"EXECUTION","task_level":"B","status":"ACTIVE","objective":["x"],"read_scope":[],"write_scope":{"allow":["project_state.yaml"],"deny":[]},"autonomy":{"may_debug_test_failures":False,"may_edit_adjacent_tests":False,"may_edit_same_module_helpers":False,"must_not_expand_architecture":True},"stop_conditions":[],"verification":{"level_1":[],"level_2":[],"level_3":[]},"report":{"format":"compact","fields":["tests"]}}
            state={"schema_version":"1.0","project_mode":"EXECUTION","architecture_status":"confirmed","implementation_plan_status":"confirmed","repository_root":".","adapter":"generic","high_risk_paths":[],"default_forbidden_operations":[],"lifecycle_stage":"ACTIVATED_NOT_PREFLIGHTED"}
            (base/"task.yaml").write_text(yaml.safe_dump(task),encoding="utf-8"); (base/"state.yaml").write_text(yaml.safe_dump(state),encoding="utf-8")
            result=subprocess.run([sys.executable,str(source/"scripts/agent_preflight.py"),"--task-file",str(base/"task.yaml"),"--project-state-file",str(base/"state.yaml")],cwd=source,text=True,capture_output=True,check=False)
            self.assertEqual(1,result.returncode); self.assertIn("USE_ADOPTION_LIFECYCLE_BRIDGE",result.stderr)


if __name__ == "__main__": unittest.main()
