from typing import List, Dict, Any

class BudgetDecision:
    ALLOW_AUTONOMOUS = "ALLOW_AUTONOMOUS"
    STOP_AND_REPORT = "STOP_AND_REPORT"

class AutonomousRemediationBudget:
    DEFAULT_ALLOWED = {
        "fixture", "helper", "mock", "temporary directory", "test isolation",
        "same-goal tests", "schema/type/path fixes", "report/manifest correction",
        "behavior-preserving local refactor"
    }

    FORBIDDEN_ACTIONS = {
        "real network", "external API", "dependency download", "formal data write",
        "production asset", "Git write/integration", "release", "destructive cleanup",
        "scope expansion", "product-semantic decision", "risk escalation"
    }

    def __init__(self, budget_id: str, task_id: str, workspace_baseline_id: str, runtime_bundle_id: str):
        self.budget_id = budget_id
        self.task_id = task_id
        self.workspace_baseline_id = workspace_baseline_id
        self.runtime_bundle_id = runtime_bundle_id
        self.allowed_actions = list(self.DEFAULT_ALLOWED)
        self.forbidden_actions = list(self.FORBIDDEN_ACTIONS)
        self.max_scope = []
        self.decision = None
        self.reason = None
        self.invalidated_reason = None

    def evaluate(self, action: str) -> str:
        if self.invalidated_reason:
            self.decision = BudgetDecision.STOP_AND_REPORT
            self.reason = f"Budget invalidated: {self.invalidated_reason}"
            return self.decision

        if action in self.FORBIDDEN_ACTIONS:
            self.decision = BudgetDecision.STOP_AND_REPORT
            self.reason = f"Action is explicitly forbidden: {action}"
            return self.decision

        if action in self.DEFAULT_ALLOWED or any(a in action for a in self.DEFAULT_ALLOWED):
            self.decision = BudgetDecision.ALLOW_AUTONOMOUS
            self.reason = f"Action permitted by budget: {action}"
            return self.decision

        self.decision = BudgetDecision.STOP_AND_REPORT
        self.reason = f"Unknown action fails closed: {action}"
        return self.decision

    def invalidate(self, reason: str):
        self.invalidated_reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "budget_id": self.budget_id,
            "task_id": self.task_id,
            "workspace_baseline_id": self.workspace_baseline_id,
            "runtime_bundle_id": self.runtime_bundle_id,
            "allowed_actions": self.allowed_actions,
            "forbidden_actions": self.forbidden_actions,
            "max_scope": self.max_scope,
            "decision": self.decision,
            "reason": self.reason,
            "invalidated_reason": self.invalidated_reason
        }
