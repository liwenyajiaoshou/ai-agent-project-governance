"""P1 deterministic, read-only Preflight engine."""

from dataclasses import dataclass
from typing import Any, Mapping

from ..models.project_state import ProjectState
from ..models.task_contract import TaskContract
from ..models.task_request import TaskRequest
from ..policy.execution_envelope import confirmation_requirement, governance_level
from ..schema_loader import validate_mapping
from .contract_builder import build_contract
from .gate_resolver import GateDecision, resolve_gate
from .mode_resolver import resolve_mode
from .risk_detector import RiskSummary, detect_risks
from .scope_resolver import resolve_scope
from .task_classifier import Classification, classify_task


@dataclass(frozen=True)
class PreflightResult:
    contract: TaskContract
    classification: Classification
    risks: RiskSummary
    exit_status: int


def is_code_task(task: TaskRequest) -> bool:
    return not any(word in task.text for word in ("read-only", "audit", "research", "documentation only"))


def run_preflight(task_value: Mapping[str, Any], state_value: Mapping[str, Any]) -> PreflightResult:
    validate_mapping(task_value, "task_request.schema.json")
    validate_mapping(state_value, "project_state.schema.json")
    task, state = TaskRequest.from_mapping(task_value), ProjectState.from_mapping(state_value)
    code_task = is_code_task(task)
    mode = resolve_mode(state.project_mode)
    classification = classify_task(task)
    risks = detect_risks(task, state, code_task)
    gate = resolve_gate(risks, code_task, mode.code_writes_allowed)
    scope = resolve_scope(task, state, gate.status, code_task)
    context = task.governance_context
    level = governance_level(context, risks.kinds)
    contract_value = build_contract(task, state.project_mode, classification.task_level, gate, scope, level, confirmation_requirement(level), risks.kinds)
    validate_mapping(contract_value, "task_contract.schema.json")
    return PreflightResult(TaskContract.from_mapping(contract_value), classification, risks, {"READY": 0, "DRAFT": 2, "BLOCKED": 3}[gate.status])
