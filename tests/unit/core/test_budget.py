import unittest
from governance.core.budget import AutonomousRemediationBudget, BudgetDecision

class TestBudget(unittest.TestCase):
    def test_budget_allows_listed_low_risk_work(self):
        budget = AutonomousRemediationBudget("b1", "t1", "base1", "run1")
        decision = budget.evaluate("fixture creation")
        self.assertEqual(decision, BudgetDecision.ALLOW_AUTONOMOUS)

    def test_budget_rejects_network_git_data_release(self):
        budget = AutonomousRemediationBudget("b1", "t1", "base1", "run1")
        self.assertEqual(budget.evaluate("real network access"), BudgetDecision.STOP_AND_REPORT)
        self.assertEqual(budget.evaluate("Git write/integration"), BudgetDecision.STOP_AND_REPORT)
        self.assertEqual(budget.evaluate("formal data write"), BudgetDecision.STOP_AND_REPORT)
        self.assertEqual(budget.evaluate("release procedure"), BudgetDecision.STOP_AND_REPORT)

    def test_unknown_remediation_fails_closed(self):
        budget = AutonomousRemediationBudget("b1", "t1", "base1", "run1")
        self.assertEqual(budget.evaluate("some magical completely unknown action"), BudgetDecision.STOP_AND_REPORT)

    def test_budget_identity_drift_invalidates_decision(self):
        budget = AutonomousRemediationBudget("b1", "t1", "base1", "run1")
        budget.invalidate("identity drift")
        self.assertEqual(budget.evaluate("fixture"), BudgetDecision.STOP_AND_REPORT)

if __name__ == "__main__":
    unittest.main()
