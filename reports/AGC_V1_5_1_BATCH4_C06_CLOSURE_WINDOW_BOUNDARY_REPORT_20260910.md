# 卫兵 v1.5.1｜Batch 4 C06 Closure Window Boundary Report

## Scope and baseline

- `worktree`: `/home/liyouran1997/projects/agc-v1.5.1-p0-contract-closure`
- `branch`: `agc-v1.5.1-p0-contract-closure`
- `baseline`: `v1.5.0` / `efd8f51503e71fb5b426e565433da0368390fbe3`
- `Batch 3 checkpoint`: `46daddb3703df75c079df673b6c24e765d48175a`
- `scope`: C06 only. No TaskContract stage graph, workspace delta/attribution, Adoption lifecycle change, repair executor, second Closure engine, or approval system was added.

## Compact boundary model

`governance.verification.repair_boundary.evaluate()` is a deterministic evidence evaluator, not an executor or history store. It creates one compact record containing task/contract identity, Guard baseline identity/status, approval status, C09 verification-evidence digest, optional repair action, existing budget and execution-envelope decisions, hard-blocker/boundary-valid booleans, reason, and digest.

`NO_REPAIR_REQUIRED` is explicit when no repair occurred. The only allowed repair labels map to existing local policy: fixture, helper, mock, test isolation, schema fix, and report correction. Network, external API, formal-data write, Git integration, release, scope expansion, risk escalation, and unknown labels are fail-closed.

## Closure wiring

`agent_close.py` reads the active TaskContract, saved Guard evidence, and saved VerificationResult; it evaluates the compact boundary and passes it to the existing `closure_evaluator.close()`. Closure continues to use the existing Verification/C09 evidence logic, and additionally blocks any boundary that is invalid. `ClosureResult.repair_boundary` persists the exact compact record; it contains no stdout/stderr or output tails.

The boundary requires a matching task, nonempty baseline identity, Guard PASS, valid/no-required approval status, and C09 evidence digest. Existing `AutonomousRemediationBudget` and `ExecutionEnvelope` must both allow a repair action. Thus stale/missing baseline, invalid approval, hard/unknown action, or scope/risk/network/data/Git/release escalation cannot produce CLOSED.

## C06 acceptance matrix

| Requirement | Existing components | Schema / public persistence | Evidence | Result |
| --- | --- | --- | --- | --- |
| no repair or bounded local repair may close | Budget + Envelope + Verification + C09 | `agent_close.py` → `closure_result.yaml` | no repair and six allowed local actions close | COMPLETE |
| stale/hard/unknown/escalated boundary blocks | Budget + Envelope + Guard baseline | strict compact `repair_boundary` binding | stale baseline, unknown, network, API, data, Git, release, scope, risk cases | COMPLETE |
| required evidence and task-created failure prevent CLOSED | C09 binding + existing Verification outcome | Closure preserves both bindings | required failure fixture and C09 validation | COMPLETE |
| no raw output | C09 digest/redaction chain | Closure schema binding | public persisted Closure contains no tails/raw fixture text | COMPLETE |
| public path/schema load | existing `agent_close.py` and `save_p3` | ClosureResult schema | public verify → close integration validates/reloads artifact | COMPLETE |

`C06_RESULT = COMPLETE`
`BATCH4_STATUS = BATCH4_C06_PASS`

## Changed files

- `governance/verification/repair_boundary.py`: compact C06 evaluation.
- `governance/policy/execution_envelope.py`: existing recoverable local categories for mock/schema/report repair.
- `governance/verification/closure_evaluator.py`, `scripts/agent_close.py`: existing Closure/public-path wiring.
- `schemas/closure_result.schema.json`: compact repair-boundary persistence.
- `tests/unit/test_v1_5_1_repair_boundary.py`, `tests/unit/test_v1_5_1_compact_closure_evidence.py`: fail-closed and public-path evidence.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.unit.test_v1_5_1_repair_boundary
# PASS: 3 tests

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.unit.test_v1_5_1_repair_boundary tests.unit.test_v1_5_1_compact_closure_evidence tests.unit.test_v1_5_1_contract_parity tests.unit.test_v1_5_1_semantic_axes tests.unit.test_v1_5_1_owner_gate tests.unit.test_p3_core tests.integration.test_p3_acceptance_matrix tests.integration.test_p3_closure_cli tests.integration.test_p2_acceptance_matrix tests.unit.test_v1_5_reality_check tests.unit.test_execution_envelope tests.unit.test_schema_contracts tests.contracts.test_p5_schema_compatibility
# PASS: 39 tests

python3 scripts/check_schema_compatibility.py
# PASS: 39 schemas, stable fields and enums

PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_governance.py
# PASS: 39 schemas, rules index, module registry, references

git diff --check
# PASS
```

No network, production, external API, push, tag, release, or primary-main action occurred. Batch 4 remains uncommitted pending an explicit local checkpoint/release instruction.
