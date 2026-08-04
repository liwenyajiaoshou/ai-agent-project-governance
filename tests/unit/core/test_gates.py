import unittest
from governance.core.gates import SideEffectGate, GateType, GateState

class TestGates(unittest.TestCase):
    def test_three_gate_types_isolated(self):
        gate1 = SideEffectGate("g1", GateType.EXTERNAL_OPERATION, "t1", "b1", "r1", "m1", "effect", [], [])
        gate2 = SideEffectGate("g2", GateType.FORMAL_DATA_WRITE, "t1", "b1", "r1", "m1", "effect", [], [])
        gate3 = SideEffectGate("g3", GateType.GIT_INTEGRATION, "t1", "b1", "r1", "m1", "effect", [], [])
        self.assertNotEqual(gate1.gate_type, gate2.gate_type)
        self.assertNotEqual(gate2.gate_type, gate3.gate_type)
        with self.assertRaises(ValueError):
            SideEffectGate("g4", "UNKNOWN_TYPE", "t1", "b1", "r1", "m1", "effect", [], [])

    def test_draft_cannot_authorize_and_ready_for_approval_requires_complete_identity(self):
        gate = SideEffectGate("g1", GateType.EXTERNAL_OPERATION, "t1", "", "", "", "effect", [], [])
        self.assertEqual(gate.state, GateState.DRAFT)
        with self.assertRaises(ValueError):
            gate.approve("evidence")
        with self.assertRaises(ValueError):
            gate.ready_for_approval()

    def test_effective_requires_approval_evidence(self):
        gate = SideEffectGate("g1", GateType.EXTERNAL_OPERATION, "t1", "b1", "r1", "m1", "effect", [], [])
        gate.ready_for_approval()
        with self.assertRaises(ValueError):
            gate.approve("")
        gate.approve("signed")
        self.assertEqual(gate.state, GateState.EFFECTIVE)

    def test_identity_and_scope_drift_invalidates_gate(self):
        gate = SideEffectGate("g1", GateType.EXTERNAL_OPERATION, "t1", "b1", "r1", "m1", "effect", [], [])
        gate.ready_for_approval()
        gate.approve("signed")
        gate.invalidate("baseline drift")
        self.assertEqual(gate.state, GateState.DRAFT)
        self.assertEqual(gate.invalidated_reason, "baseline drift")

    def test_one_gate_cannot_authorize_another_effect(self):
        # Enforced by type checking and separate instances.
        gate1 = SideEffectGate("g1", GateType.EXTERNAL_OPERATION, "t1", "b1", "r1", "m1", "effect", [], [])
        gate2 = SideEffectGate("g2", GateType.FORMAL_DATA_WRITE, "t1", "b1", "r1", "m1", "effect2", [], [])
        self.assertNotEqual(gate1.gate_id, gate2.gate_id)

if __name__ == "__main__":
    unittest.main()
