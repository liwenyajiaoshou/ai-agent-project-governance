"""Test-only process launcher; never used by the public CLI."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import GENERATOR_FIXTURE
sys.path.insert(0, str(ROOT / "scripts"))
import agent_adopt

raise SystemExit(agent_adopt.main(sys.argv[1:], _test_provenance_source_root=GENERATOR_FIXTURE))
