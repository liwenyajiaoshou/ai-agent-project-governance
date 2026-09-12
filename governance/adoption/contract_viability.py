"""Cross-stage viability checks for the full Existing Project Adoption lifecycle."""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, Mapping


PROJECT_STATE_PATH = "project_state.yaml"
INSUFFICIENT = "ADOPTION_LIFECYCLE_WRITE_SCOPE_INSUFFICIENT"
ZERO_WRITE = "ZERO_WRITE_FULL_ADOPTION_UNSUPPORTED"


def _covers_project_state(pattern: str) -> bool:
    normalized = pattern.replace("\\", "/").lstrip("./")
    return normalized in {PROJECT_STATE_PATH, "*", "**", "**/*"} or PurePosixPath(PROJECT_STATE_PATH).match(normalized)


def adoption_lifecycle_viability(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Return a stable diagnostic; this applies only to the full adoption lifecycle."""
    allowed = contract.get("write_scope", {}).get("allow", [])
    allowed = allowed if isinstance(allowed, list) else []
    viable = any(isinstance(item, str) and _covers_project_state(item) for item in allowed)
    reasons: list[str] = []
    if not viable:
        reasons.append(ZERO_WRITE if not allowed else INSUFFICIENT)
    return {
        "viable": viable,
        "required_write_scope": [PROJECT_STATE_PATH],
        "missing_write_scope": [] if viable else [PROJECT_STATE_PATH],
        "reason_codes": reasons,
    }


def require_adoption_lifecycle_viability(contract: Mapping[str, Any]) -> dict[str, Any]:
    result = adoption_lifecycle_viability(contract)
    if not result["viable"]:
        raise ValueError(result["reason_codes"][0])
    return result
