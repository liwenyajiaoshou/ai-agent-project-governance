from ..state import approval_store
from ..state.freshness import evaluate
from ..core.gates import GateType, SideEffectGate

EFFECTS = {
    "external_access": ("external_access", GateType.EXTERNAL_OPERATION),
    "formal_data_write": ("formal_data_write", GateType.FORMAL_DATA_WRITE),
    "git_write": ("git_write", GateType.GIT_INTEGRATION),
}

def check(required_type, fingerprint, task_id, scope=None, contract_digest=None):
    if required_type == "unmapped_effect": return "unmapped_effect"
    if not required_type: return "not_required"
    candidates=[a for a in approval_store.load() if a.get("approval_type")==required_type]
    if not candidates: return "missing"
    statuses=[evaluate(a,fingerprint,task_id,scope,contract_digest) for a in candidates]
    return "valid" if "valid" in statuses else "scope_mismatch" if "scope_mismatch" in statuses else "contract_mismatch" if "contract_mismatch" in statuses else "state_mismatch" if "state_mismatch" in statuses else "expired"

def required(contract):
    effect = contract.get("governance", {}).get("effect_type")
    if effect is None: return None
    return EFFECTS[effect][0] if effect in EFFECTS else "unmapped_effect"

def effect_authorization(contract, fingerprint):
    effect = contract.get("governance", {}).get("effect_type")
    required_type = required(contract)
    scope = contract.get("governance", {}).get("effect_scope", {})
    contract_digest = fingerprint["contract_digest"]
    status = check(required_type, fingerprint, contract["task_id"], scope, contract_digest)
    value = {"effect_type": effect, "approval_type": required_type, "status": status}
    if status != "valid": return value
    record = next(item for item in approval_store.load() if item.get("approval_type") == required_type and evaluate(item, fingerprint, contract["task_id"], scope, contract_digest) == "valid")
    gate_type = EFFECTS[effect][1]
    record_digest = approval_store.digest(record)
    gate = SideEffectGate(f"effect-{record['approval_id']}", gate_type, contract["task_id"], fingerprint["head_commit"], contract_digest, record_digest, effect, contract["write_scope"]["allow"], contract["write_scope"]["deny"])
    gate.ready_for_approval(); gate.approve(record_digest)
    return {**value, "approval_id": record["approval_id"], "approval_digest": record_digest, "gate": gate.to_dict()}
