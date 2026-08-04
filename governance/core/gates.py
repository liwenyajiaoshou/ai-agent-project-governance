from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

class GateState:
    DRAFT = "DRAFT"
    READY_FOR_APPROVAL = "READY_FOR_APPROVAL"
    EFFECTIVE = "EFFECTIVE"

class GateType:
    EXTERNAL_OPERATION = "EXTERNAL_OPERATION"
    FORMAL_DATA_WRITE = "FORMAL_DATA_WRITE"
    GIT_INTEGRATION = "GIT_INTEGRATION"

class SideEffectGate:
    def __init__(self, gate_id: str, gate_type: str, task_id: str, workspace_baseline_id: str,
                 runtime_bundle_id: str, manifest_id: str, requested_effect: str,
                 allowed_scope: List[str], forbidden_scope: List[str]):
        self.gate_id = gate_id
        if gate_type not in (GateType.EXTERNAL_OPERATION, GateType.FORMAL_DATA_WRITE, GateType.GIT_INTEGRATION):
            raise ValueError(f"Invalid gate_type: {gate_type}")
        self.gate_type = gate_type
        self.state = GateState.DRAFT
        self.task_id = task_id
        self.workspace_baseline_id = workspace_baseline_id
        self.runtime_bundle_id = runtime_bundle_id
        self.manifest_id = manifest_id
        self.requested_effect = requested_effect
        self.allowed_scope = allowed_scope
        self.forbidden_scope = forbidden_scope
        self.approval_evidence: Optional[str] = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.effective_at: Optional[str] = None
        self.invalidated_reason: Optional[str] = None

    def ready_for_approval(self):
        if not (self.workspace_baseline_id and self.runtime_bundle_id and self.manifest_id):
            raise ValueError("READY_FOR_APPROVAL requires complete identity")
        self.state = GateState.READY_FOR_APPROVAL

    def approve(self, evidence: str):
        if self.state != GateState.READY_FOR_APPROVAL:
            raise ValueError("Can only approve from READY_FOR_APPROVAL state")
        if not evidence:
            raise ValueError("EFFECTIVE requires approval evidence")
        self.approval_evidence = evidence
        self.state = GateState.EFFECTIVE
        self.effective_at = datetime.now(timezone.utc).isoformat()

    def invalidate(self, reason: str):
        self.state = GateState.DRAFT
        self.invalidated_reason = reason
        self.effective_at = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "gate_type": self.gate_type,
            "state": self.state,
            "task_id": self.task_id,
            "workspace_baseline_id": self.workspace_baseline_id,
            "runtime_bundle_id": self.runtime_bundle_id,
            "manifest_id": self.manifest_id,
            "requested_effect": self.requested_effect,
            "allowed_scope": self.allowed_scope,
            "forbidden_scope": self.forbidden_scope,
            "approval_evidence": self.approval_evidence,
            "created_at": self.created_at,
            "effective_at": self.effective_at,
            "invalidated_reason": self.invalidated_reason
        }
