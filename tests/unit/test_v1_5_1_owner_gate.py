from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import yaml

from governance.core.gates import GateState, GateType
from governance.guards.approval_guard import effect_authorization
from governance.schema_loader import load_mapping, validate_mapping
from governance.state import approval_store


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "preflight"
FINGERPRINT = {"repository_root": "repo", "current_branch": "main", "head_commit": "head", "task_id": "GATE", "contract_digest": "contract"}


def contract(effect_type: str | None, scope: dict | None = None) -> dict:
    governance = {} if effect_type is None else {"effect_type": effect_type, "effect_scope": scope or {}}
    return {"task_id": "GATE", "write_scope": {"allow": ["src/**"], "deny": ["data/**"]}, "governance": governance}


def approval(approval_type: str, *, fingerprint=FINGERPRINT, task_id="GATE", scope=None, expires_at=None, contract_digest="contract") -> dict:
    return {"schema_version": "1.0", "approval_id": "APR", "task_id": task_id, "approval_type": approval_type, "status": "approved", "scope": scope or {}, "environment_fingerprint": fingerprint, "approved_by": "owner", "approved_at": "2026-09-10T00:00:00+00:00", "expires_when": ["task_changes"], "expires_at": expires_at, "contract_digest": contract_digest}


class OwnerGateTest(unittest.TestCase):
    def authorization(self, active: dict, records: list[dict]):
        with patch("governance.guards.approval_guard.approval_store.load", return_value=records):
            return effect_authorization(active, FINGERPRINT)

    def test_effect_mapping_and_rejection_matrix(self) -> None:
        self.assertEqual("not_required", self.authorization(contract(None), [])["status"])
        self.assertEqual("missing", self.authorization(contract("external_access"), [])["status"])
        valid = self.authorization(contract("external_access"), [approval("external_access")])
        self.assertEqual(("valid", GateType.EXTERNAL_OPERATION, GateState.EFFECTIVE), (valid["status"], valid["gate"]["gate_type"], valid["gate"]["state"]))
        self.assertEqual("missing", self.authorization(contract("external_access"), [approval("formal_data_write")])["status"])
        self.assertEqual("missing", self.authorization(contract("formal_data_write"), [approval("external_access")])["status"])
        self.assertEqual("state_mismatch", self.authorization(contract("external_access"), [approval("external_access", fingerprint={})])["status"])
        self.assertEqual("scope_mismatch", self.authorization(contract("external_access", {"provider": "x"}), [approval("external_access", scope={"provider": "y"})])["status"])
        expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        self.assertEqual("expired", self.authorization(contract("external_access"), [approval("external_access", expires_at=expired)])["status"])
        self.assertEqual("contract_mismatch", self.authorization(contract("external_access"), [approval("external_access", contract_digest="other")])["status"])
        self.assertEqual("expired", self.authorization(contract("external_access"), [approval("external_access", task_id="OTHER")])["status"])
        self.assertEqual("unmapped_effect", self.authorization(contract("unmapped"), [])["status"])

    def test_approval_schema_persistence_and_public_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for command in (("git", "init", "-b", "main"), ("git", "config", "user.email", "test@example.invalid"), ("git", "config", "user.name", "Test")):
                subprocess.run(command, cwd=root, check=True, capture_output=True)
            (root / ".gitignore").write_text(".agent_state/\n", encoding="utf-8")
            subprocess.run(("git", "add", ".gitignore"), cwd=root, check=True, capture_output=True)
            subprocess.run(("git", "commit", "-m", "init"), cwd=root, check=True, capture_output=True)
            task_value = load_mapping(FIXTURES / "task_external_api.yaml")
            task_value["hints"]["effect_type"] = "external_access"
            task_value["hints"]["effect_scope"] = {}
            task_file, state_file, output = root / "task.yaml", root / "state.yaml", root / "contract.yaml"
            task_file.write_text(yaml.safe_dump(task_value), encoding="utf-8")
            state_file.write_text((FIXTURES / "project_state_execution.yaml").read_text(encoding="utf-8"), encoding="utf-8")
            preflight = subprocess.run([sys.executable, str(ROOT / "scripts/agent_preflight.py"), "--task-file", str(task_file), "--project-state-file", str(state_file), "--output-file", str(output), "--quiet"], cwd=root, text=True, capture_output=True)
            self.assertEqual(3, preflight.returncode, preflight.stderr)
            state = root / ".agent_state"; state.mkdir()
            (state / "project_state.yaml").write_text(state_file.read_text(encoding="utf-8"), encoding="utf-8")
            (state / "active_task.yaml").write_text(output.read_text(encoding="utf-8"), encoding="utf-8")
            scope_file = root / "scope.yaml"; scope_file.write_text("{}\n", encoding="utf-8")
            subprocess.run(("git", "add", "task.yaml", "state.yaml", "contract.yaml", "scope.yaml"), cwd=root, check=True, capture_output=True)
            subprocess.run(("git", "commit", "-m", "inputs"), cwd=root, check=True, capture_output=True)
            approve = subprocess.run([sys.executable, str(ROOT / "scripts/agent_approve.py"), "add", "--task-id", task_value["task_id"], "--type", "external_access", "--scope-file", str(scope_file), "--approved-by", "owner"], cwd=root, text=True, capture_output=True)
            self.assertEqual(0, approve.returncode, approve.stderr)
            records = yaml.safe_load((state / "approvals.yaml").read_text(encoding="utf-8"))
            self.assertEqual(1, len(records)); validate_mapping(records[0], "approval.schema.json")
            guard = subprocess.run([sys.executable, str(ROOT / "scripts/agent_guard.py"), "check"], cwd=root, text=True, capture_output=True)
            self.assertEqual(0, guard.returncode, f"{guard.stdout}\n{guard.stderr}")
            result = yaml.safe_load((state / "last_guard_result.yaml").read_text(encoding="utf-8"))
            validate_mapping(result, "guard_result.schema.json")
            self.assertEqual(("valid", GateState.EFFECTIVE), (result["approval_status"], result["effect_authorization"]["gate"]["state"]))


if __name__ == "__main__":
    unittest.main()
