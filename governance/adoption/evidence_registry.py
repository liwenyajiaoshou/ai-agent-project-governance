"""The single evidence registry for adoption lifecycle state edges."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from governance.schema_loader import load_mapping, validate_mapping


EDGE_REQUIREMENTS: dict[tuple[str, str], tuple[str, str]] = {
    ("ACTIVATED_NOT_PREFLIGHTED", "PREFLIGHT_PASSED"): ("PreflightEvidence", "PASS"),
    ("PREFLIGHT_PASSED", "GUARDED"): ("GuardEvidence", "PASS"),
    ("GUARDED", "TEST_PLANNED"): ("TestPlanEvidence", "READY"),
    ("TEST_PLANNED", "TEST_EXECUTED"): ("TestRunEvidence", "PASS"),
    ("TEST_EXECUTED", "VERIFIED"): ("VerificationEvidence", "PASS"),
    ("VERIFIED", "CLOSED"): ("ClosureEvidence", "CLOSED"),
}


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def required_for(previous_stage: str, next_stage: str) -> tuple[str, str]:
    try:
        return EDGE_REQUIREMENTS[(previous_stage, next_stage)]
    except KeyError as exc:
        raise ValueError("unregistered lifecycle state transition") from exc


def upstream_digests(state: Mapping[str, Any]) -> list[str]:
    digests: list[str] = []
    for item in state.get("lifecycle_evidence", []):
        expected = item.get("evidence_file_digest", item["evidence_digest"])
        evidence_file = item.get("evidence_file")
        if evidence_file:
            path = Path(evidence_file)
            if not path.is_file() or path.is_symlink() or file_digest(path) != expected:
                raise ValueError("previous lifecycle evidence file changed or disappeared")
        digests.append(expected)
    return digests


def validate_evidence_file(
    path: Path,
    *,
    previous_stage: str,
    next_stage: str,
    target_identity_digest: str,
    previous_state_digest: str,
    expected_upstream: list[str],
) -> tuple[dict[str, Any], str]:
    if not path.is_file() or path.is_symlink():
        raise ValueError("lifecycle evidence file is missing or unsafe")
    value = load_mapping(path)
    validate_evidence_content(
        value,
        previous_stage=previous_stage,
        next_stage=next_stage,
        target_identity_digest=target_identity_digest,
        previous_state_digest=previous_state_digest,
        expected_upstream=expected_upstream,
    )
    return value, file_digest(path)


def validate_evidence_content(
    value: Mapping[str, Any],
    *,
    previous_stage: str,
    next_stage: str,
    target_identity_digest: str,
    previous_state_digest: str,
    expected_upstream: list[str],
) -> None:
    """Validate lifecycle meaning for already supplied evidence content.

    This is intentionally transport-agnostic.  Callers still own safe file
    handling or verified reference resolution; this registry remains the sole
    owner of lifecycle edge requirements.
    """
    validate_mapping(value, "adoption_lifecycle_evidence.schema.json")
    required_type, required_status = required_for(previous_stage, next_stage)
    if value["evidence_type"] != required_type or value["status"] != required_status:
        raise ValueError("lifecycle evidence does not satisfy this state edge")
    if value["target_identity_digest"] != target_identity_digest:
        raise ValueError("lifecycle evidence target identity mismatch")
    if value["previous_state_digest"] != previous_state_digest:
        raise ValueError("lifecycle evidence previous-state digest mismatch")
    if value["upstream_evidence_digests"] != expected_upstream:
        raise ValueError("lifecycle evidence upstream chain mismatch")
