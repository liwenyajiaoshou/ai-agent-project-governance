"""Schema-aligned immutable TaskContract model."""

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping


@dataclass(frozen=True)
class TaskContract:
    schema_version: str
    task_id: str
    project_mode: str
    task_level: str
    status: str
    objective: tuple[str, ...]
    read_scope: tuple[str, ...]
    write_scope: Mapping[str, Any]
    autonomy: Mapping[str, Any]
    stop_conditions: tuple[str, ...]
    verification: Mapping[str, Any]
    report: Mapping[str, Any]
    governance: Mapping[str, Any] = field(default_factory=dict)
    scope_contract: Mapping[str, Any] = field(default_factory=dict)
    supersession: Mapping[str, Any] | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TaskContract":
        copied = dict(value)
        for name in ("objective", "read_scope", "stop_conditions"):
            copied[name] = tuple(copied[name])
        return cls(**copied)

    def to_mapping(self) -> dict[str, Any]:
        result = {"schema_version": self.schema_version, "task_id": self.task_id, "project_mode": self.project_mode, "task_level": self.task_level, "status": self.status, "objective": list(self.objective), "read_scope": list(self.read_scope), "write_scope": dict(self.write_scope), "autonomy": dict(self.autonomy), "stop_conditions": list(self.stop_conditions), "verification": dict(self.verification), "report": dict(self.report)}
        if self.governance:
            result["governance"] = dict(self.governance)
        if self.scope_contract:
            result["scope_contract"] = dict(self.scope_contract)
        if self.supersession:
            result["supersession"] = dict(self.supersession)
        return result


def supersede(active: TaskContract, successor: TaskContract, approval_evidence: str) -> TaskContract:
    if active.status != "ACTIVE" or successor.status != "ACTIVE" or not approval_evidence:
        raise ValueError("TASK_CONTRACT_SUPERSESSION_REQUIRED")
    digest = lambda item: hashlib.sha256(json.dumps(item.to_mapping(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return replace(active, status="SUPERSEDED", supersession={
        "previous_task_id": active.task_id, "previous_task_digest": digest(active),
        "successor_task_id": successor.task_id, "successor_task_digest": digest(successor),
        "superseded_at": datetime.now(timezone.utc).isoformat(), "approval_evidence": approval_evidence,
    })
