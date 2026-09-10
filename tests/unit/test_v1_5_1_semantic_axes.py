from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from governance.preflight.engine import run_preflight
from governance.schema_loader import load_mapping, validate_mapping


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "preflight"


def task(task_type: str, *, external: bool = False, production: bool = False, unknown: bool = False) -> dict:
    value = load_mapping(FIXTURES / "task_safe_patch.yaml")
    value["hints"]["task_type"] = task_type
    value["hints"]["external_access"] = external
    value["hints"]["production_write"] = production
    if unknown:
        value["governance_context"] = {"risk_status": "unknown"}
    return value


class SemanticAxesTest(unittest.TestCase):
    def state(self) -> dict:
        return load_mapping(FIXTURES / "project_state_execution.yaml")

    def test_contradictory_matrix_keeps_three_axes_independent(self) -> None:
        cases = (
            ("A", False, False, False, (), "LEVEL_2_TASK"),
            ("A", True, False, False, ("external",), "LEVEL_3_HIGH_RISK"),
            ("A", False, True, False, ("production",), "LEVEL_3_HIGH_RISK"),
            ("A", False, False, True, ("unknown",), "LEVEL_3_HIGH_RISK"),
            ("B", False, False, False, (), "LEVEL_2_TASK"),
            ("B", True, False, False, ("external",), "LEVEL_3_HIGH_RISK"),
            ("C", False, False, False, (), "LEVEL_2_TASK"),
            ("C", True, False, False, ("external",), "LEVEL_3_HIGH_RISK"),
        )
        for declared, external, production, unknown, risks, level in cases:
            with self.subTest(declared=declared, risks=risks):
                result = run_preflight(task(declared, external=external, production=production, unknown=unknown), self.state())
                self.assertEqual(declared, result.classification.task_level)
                self.assertEqual(risks, result.risks.kinds)
                self.assertEqual(declared, result.contract.governance["task_type"])
                self.assertEqual(list(risks), result.contract.governance["risk_kinds"])
                self.assertEqual(level, result.contract.governance["level"])
                validate_mapping(result.contract.to_mapping(), "task_contract.schema.json")

    def test_inferred_form_is_not_elevated_by_risk(self) -> None:
        value = task("B", external=True)
        del value["hints"]["task_type"]
        result = run_preflight(value, self.state())
        self.assertEqual(("A", ("external",), "LEVEL_3_HIGH_RISK"), (result.classification.task_level, result.risks.kinds, result.contract.governance["level"]))

    def test_public_preflight_persists_and_reloads_axes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); task_file = root / "task.yaml"; state_file = root / "state.yaml"; output = root / "contract.yaml"
            task_file.write_text(yaml.safe_dump(task("B", external=True)), encoding="utf-8")
            state_file.write_text(yaml.safe_dump(self.state()), encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/agent_preflight.py"), "--task-file", str(task_file), "--project-state-file", str(state_file), "--output-file", str(output), "--quiet"], cwd=root, text=True, capture_output=True)
            self.assertEqual(3, result.returncode, result.stderr)
            persisted = load_mapping(output)
            validate_mapping(persisted, "task_contract.schema.json")
            self.assertEqual({"task_type": "B", "risk_kinds": ["external"], "level": "LEVEL_3_HIGH_RISK"}, {key: persisted["governance"][key] for key in ("task_type", "risk_kinds", "level")})


if __name__ == "__main__":
    unittest.main()
