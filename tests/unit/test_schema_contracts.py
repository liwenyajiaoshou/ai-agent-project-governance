from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = {path.name: json.loads(path.read_text(encoding="utf-8")) for path in (ROOT / "schemas").glob("*.schema.json")}


def task_request() -> dict:
    return {
        "schema_version": "1.0", "task_id": "TASK-001", "title": "Example", "description": "Example task",
        "requested_by": "owner", "requested_at": "2026-07-12T12:00:00+08:00",
        "hints": {"likely_paths": ["docs/"], "external_access": False, "production_write": False},
    }


def project_state() -> dict:
    return {
        "schema_version": "1.0", "project_mode": "EXECUTION", "architecture_status": "confirmed",
        "implementation_plan_status": "confirmed", "repository_root": ".", "adapter": "generic",
        "high_risk_paths": [], "default_forbidden_operations": ["production_write"],
    }


def approval() -> dict:
    return {
        "schema_version": "1.0", "approval_id": "APR-001", "task_id": "TASK-001", "approval_type": "external_api_access",
        "status": "approved", "scope": {"provider": "example"}, "environment_fingerprint": {"workspace": "main"},
        "approved_by": "owner", "approved_at": "2026-07-12T12:00:00+08:00", "expires_when": ["task_changes"],
    }


def task_contract() -> dict:
    return {
        "schema_version": "1.0", "task_id": "TASK-001", "project_mode": "EXECUTION", "task_level": "A", "status": "READY",
        "objective": ["Fix example"], "read_scope": ["docs/example.md"], "write_scope": {"allow": ["docs/example.md"], "deny": ["data/"]},
        "autonomy": {"may_debug_test_failures": True, "may_edit_adjacent_tests": True, "may_edit_same_module_helpers": "conditional", "must_not_expand_architecture": True},
        "stop_conditions": ["new_user_permission_required"], "verification": {"level_1": ["python -m unittest"], "level_2": [], "level_3": []},
        "report": {"format": "compact", "fields": ["modified_files", "tests"]},
    }


def verification_result() -> dict:
    return {
        "schema_version": "1.0", "task_id": "TASK-001", "scope_check": "PASS", "forbidden_operation_check": "PASS",
        "tests": [{"command_id": "python-unittest-discover", "level": 1, "required": True, "status": "PASS", "summary": "1 passed", "exit_code": 0, "duration_ms": 1, "stdout_digest": None, "stderr_digest": None, "redaction_count": 0, "redaction_rule_version": "1.0"}],
        "completion_status": "VERIFIED", "remaining_risks": [],
    }


class SchemaContractsTest(unittest.TestCase):
    def validator(self, name: str) -> Draft202012Validator:
        return Draft202012Validator(SCHEMAS[name])

    def test_all_schemas_are_self_valid_and_identified(self) -> None:
        self.assertEqual(39, len(SCHEMAS))
        ids = set()
        for schema in SCHEMAS.values():
            Draft202012Validator.check_schema(schema)
            self.assertEqual("object", schema["type"])
            self.assertFalse(schema["additionalProperties"])
            self.assertTrue({"$schema", "$id", "title", "description"}.issubset(schema))
            ids.add(schema["$id"])
        self.assertEqual(39, len(ids))

    def test_minimum_valid_examples(self) -> None:
        examples = {
            "task_request.schema.json": task_request(), "project_state.schema.json": project_state(),
            "approval.schema.json": approval(), "task_contract.schema.json": task_contract(),
            "verification_result.schema.json": verification_result(),
            "governance_module_registry.schema.json": yaml.safe_load((ROOT / "docs/GOVERNANCE_RUNTIME_MODULE_REGISTRY.yaml").read_text(encoding="utf-8")),
            "rules_index.schema.json": yaml.safe_load((ROOT / "agent_rules/RULES_INDEX.yaml").read_text(encoding="utf-8")),
        }
        for name, example in examples.items():
            self.validator(name).validate(example)

    def test_missing_required_field_and_extra_field_fail(self) -> None:
        missing = task_request()
        del missing["title"]
        with self.assertRaises(ValidationError):
            self.validator("task_request.schema.json").validate(missing)
        extra = task_request()
        extra["unexpected"] = True
        with self.assertRaises(ValidationError):
            self.validator("task_request.schema.json").validate(extra)

    def test_invalid_enumerations_fail(self) -> None:
        invalid = task_contract()
        invalid["task_level"] = "Z"
        with self.assertRaises(ValidationError):
            self.validator("task_contract.schema.json").validate(invalid)

    def test_contract_expresses_autonomy_and_true_stop_conditions(self) -> None:
        contract = task_contract()
        self.validator("task_contract.schema.json").validate(contract)
        self.assertTrue(contract["autonomy"]["may_debug_test_failures"])
        self.assertEqual(["new_user_permission_required"], contract["stop_conditions"])

    def test_verification_models_all_closure_states(self) -> None:
        for status in ("VERIFIED", "PARTIAL", "BLOCKED", "FAILED"):
            result = copy.deepcopy(verification_result())
            result["completion_status"] = status
            self.validator("verification_result.schema.json").validate(result)


if __name__ == "__main__":
    unittest.main()
