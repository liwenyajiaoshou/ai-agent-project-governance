# 卫兵 v1.5.1｜Batch 3 C16/C15 Semantic and Owner Gate Report

## Stage record

- `worktree`: `/home/liyouran1997/projects/agc-v1.5.1-p0-contract-closure`
- `branch`: `agc-v1.5.1-p0-contract-closure`
- `baseline`: `v1.5.0` / `efd8f51503e71fb5b426e565433da0368390fbe3`
- `Batch 2 checkpoint`: `56e18d6900f7359e6475d146a5ff089d14eded89`
- `scope`: C16 followed by C15 only. C05 remains a requirement-definition correction; C06, Workspace, Adoption lifecycle refactoring, and all P1/P2 remain untouched.

## C16 — three independent semantic axes

- `task_type`: only `task_classifier` determines execution/task form. Its fallback no longer promotes a task to C merely because external/production risk flags are present.
- `risk_kinds`: only `risk_detector` derives risks from structured inputs/text/project context.
- `governance_level`: only `governance_level(context, risk_kinds)` derives authorization level. Any risk remains sufficient for Level 3; no risk was downgraded, deleted, or reinterpreted.
- `persistence`: preflight writes all three results to the existing `TaskContract.governance` decision: `task_type`, `risk_kinds`, and existing `level`. The TaskContract schema declares these fields.

The contradictory matrix covers declared A/B/C with no risk and external risk, plus A production and unknown risk. It proves that declared type remains intact while risk independently produces Level 3. An unstructured small-form external task remains inferred A with external risk and Level 3, rather than being rewritten to C.

## C15 — one ApprovalRecord authority and existing effect gates

`approval.schema.json`, `approval_store`, `freshness`, `ApprovalGuard`, and the existing `SideEffectGate` remain the only approval system.

Structured effect mapping is frozen and implemented as:

| Structured effect | Approval type | Existing gate |
| --- | --- | --- |
| `external_access` | `external_access` | `EXTERNAL_OPERATION` |
| `formal_data_write` | `formal_data_write` | `FORMAL_DATA_WRITE` |
| `git_write` | `git_write` | `GIT_INTEGRATION` |
| generic production write without formal-data evidence, or unknown effect | `unmapped_effect` | fail closed; no gate |

`agent_approve add` now requires the active TaskContract, exact task/effect type, canonical scope, canonical environment fingerprint, and contract digest. It persists the same fingerprint and digest that `agent_guard` evaluates. `effect_authorization()` selects a fresh ApprovalRecord, verifies task/scope/environment/expiry/contract digest, and then creates an EFFECTIVE existing SideEffectGate bound to the approval record digest. Guard results persist this binding.

No effect stays `not_required`; objective prose no longer grants or requests authorization. Missing, wrong-type, stale, wrong-task, scope-mismatched, expired, contract-mismatched, and unmapped effects remain blocked.

## Acceptance matrix

| Requirement | Implementation | Schema | Public path / persistence | Targeted and integration evidence | Result |
| --- | --- | --- | --- | --- | --- |
| C16 independent task/risk/governance semantics | classifier decoupled; detector and level retained; contract builder persists axes | TaskRequest and TaskContract governance fields | `agent_preflight.py` writes/reloads schema-valid TaskContract | contradictory matrix plus public preflight output/load | COMPLETE |
| C15 one Owner authority | existing ApprovalRecord/store/freshness/guard reused | ApprovalRecord plus Guard effect-binding schema | `agent_approve.py` persists canonical fingerprint/digest; `agent_guard.py` persists authorization | public preflight → approve → guard → EFFECTIVE gate | COMPLETE |
| C15 frozen effect mapping | exact mapping to three existing GateTypes; unmapped fail closed | TaskContract effect declaration and strict Guard status enum | same ordinary public path | no effect, missing, valid, wrong type, stale, scope, expired, contract, wrong task, unmapped matrix | COMPLETE |

`C16_RESULT = COMPLETE`
`C15_RESULT = COMPLETE`
`BATCH3_STATUS = BATCH3_C16_C15_PASS`

## Changed files

- `governance/preflight/task_classifier.py`, `contract_builder.py`, `engine.py`: C16 separation and persisted axes.
- `schemas/task_request.schema.json`, `schemas/task_contract.schema.json`: structured effect input and governance decision contract.
- `governance/state/approval_store.py`, `freshness.py`: canonical approval digest and contract-digest freshness.
- `governance/guards/approval_guard.py`, `result_builder.py`, `scripts/agent_approve.py`, `scripts/agent_guard.py`: ordinary owner-gate wiring and effective SideEffectGate binding.
- `schemas/guard_result.schema.json`: persisted effect authorization.
- `tests/unit/test_v1_5_1_semantic_axes.py`, `tests/unit/test_v1_5_1_owner_gate.py`, `tests/integration/test_p2_acceptance_matrix.py`, `tests/fixtures/compatibility/schema_baseline.json`: coverage and compatibility contract.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.unit.test_v1_5_1_semantic_axes tests.unit.test_v1_5_1_owner_gate tests.unit.test_approval_guard tests.unit.test_approval_lifecycle tests.unit.core.test_gates tests.integration.test_p2_acceptance_matrix
# PASS: 15 tests

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.unit.test_v1_5_1_semantic_axes tests.unit.test_v1_5_1_owner_gate tests.unit.test_preflight_runtime tests.unit.test_approval_guard tests.unit.test_approval_lifecycle tests.unit.core.test_gates tests.integration.test_p2_acceptance_matrix tests.unit.test_schema_contracts tests.contracts.test_p5_schema_compatibility
# PASS: 29 tests

python3 scripts/check_schema_compatibility.py
# PASS: 39 schemas, stable fields and enums

PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_governance.py
# PASS: 39 schemas, rules index, module registry, references

git diff --check
# PASS
```

No network, production, external API, tag, release, push, or primary-main action occurred. Batch 3 remains uncommitted for the next explicit checkpoint or release instruction.
