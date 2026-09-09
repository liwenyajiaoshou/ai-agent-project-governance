"""Governance runtime baseline tests and local provenance fixture."""

import subprocess
import tempfile
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR_FIXTURE = Path(tempfile.mkdtemp(prefix="agc-provenance-fixture-"))
_INPUTS = ("VERSION", "scripts/agent_adopt.py", "governance/adoption/planner.py", "governance/adoption/provenance.py", "governance/adoption/scope_contract.py", "schemas/adoption_plan.schema.json", "schemas/adoption_scope_input.schema.json", "schemas/adoption_provenance_receipt.schema.json")
for _relative in _INPUTS:
    _path = GENERATOR_FIXTURE / _relative
    _path.parent.mkdir(parents=True, exist_ok=True)
    _path.write_bytes(subprocess.check_output(["git", "-C", str(ROOT), "show", f"HEAD:{_relative}"]))
for _args in (("init",), ("config", "user.email", "tests@example.invalid"), ("config", "user.name", "tests"), ("add", "."), ("commit", "-m", "fixture")):
    _env = {**os.environ, "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00", "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00"}
    subprocess.run(["git", "-C", str(GENERATOR_FIXTURE), *_args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=_env)

import governance.adoption as _adoption
import governance.adoption.planner as _planner
import governance.adoption.provenance as _provenance
_provenance.SOURCE_ROOT = GENERATOR_FIXTURE
_production_build_plan = _planner.build_plan
def _test_build_plan(*args, **kwargs):
    kwargs.setdefault("provenance_source_root", GENERATOR_FIXTURE)
    return _production_build_plan(*args, **kwargs)
_planner.build_plan = _test_build_plan
_adoption.build_plan = _test_build_plan
