# 卫兵 v1.5.1｜Batch 2 C09 Compact Closure Evidence Report

## Scope and baseline

- `worktree`: `/home/liyouran1997/projects/agc-v1.5.1-p0-contract-closure`
- `branch`: `agc-v1.5.1-p0-contract-closure`
- `baseline`: `v1.5.0` / `efd8f51503e71fb5b426e565433da0368390fbe3`
- `Batch 1 checkpoint`: `c825e562ba91cbe5dbaff4f4c9d9eed68de9904c`
- `scope`: C09 only. C05 remains requirement-definition correction; C06/C15/C16, all P1/P2, and all release activity were untouched.

## Evidence model

`governance.verification.evidence.build_task_relevance_evidence()` is the one compact Verification-to-Closure binding. It is not a second evidence system or registry.

The binding contains:

- `task_id`;
- contract-authorized TestPlan required and regression command identities, statuses, and reasons;
- `required_tests_satisfied`;
- baseline/post-task/task-created failure isolation and closure state;
- existing stdout/stderr digest references, redaction counts, and redaction-rule version;
- deterministic `evidence_digest`.

It intentionally excludes runner `sanitized_stdout_tail` and `sanitized_stderr_tail`; it stores neither raw output nor copied output tails.

## Existing-chain bindings

1. Existing TaskContract verification authorization resolves command identity in Batch 1.
2. The canonical TestPlan supplies required/regression role and reason.
3. The normalized TestResult supplies only status and compact digest/redaction references.
4. `verification_builder.build()` creates and persists `VerificationResult.evidence_binding`.
5. `closure_evaluator.close()` validates its digest/task binding, rejects unsatisfied required evidence, and copies the exact compact binding into `ClosureResult.evidence_binding`.
6. `agent_verify.py` and `agent_close.py` retain their existing `store.save_p3` persistence paths and schema validation.

Thus Closure can inspect required satisfaction and failure isolation without a second Closure engine or raw-output evidence store. A task-created required failure remains `FAILED` and cannot become `CLOSED`; a baseline-only regression failure remains outside `task_created_failures`.

## C09 acceptance matrix

| Requirement | Implementation | Schema | Public verify path | Persistence | Public close path | Targeted/integration evidence | No-raw-output evidence | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| task-relevant compact Closure Evidence | one builder in `evidence.py`; `verification_builder` creates it | `verification_result.schema.json` declares binding | `agent_verify.py` | `.agent_state/verification_result.yaml` | `agent_close.py` validates/copies binding | direct required+regression plan→verify→close and subprocess public verify→close | test asserts no sanitized tails in binding | COMPLETE |
| required satisfaction and task-created failure blocking | binding calculates required status; Closure blocks unsatisfied binding | Verification and Closure binding schemas | public verify writes required status | saved Verification validated/loaded | public close writes bound result | required fail produces FAILED Closure | binding contains digests only | COMPLETE |
| baseline regression isolation | builder carries existing failure attribution into binding | failure-isolation schema fields | existing verify builder path | persisted compact summary supports those fields | Closure receives same binding | baseline regression fixture has empty task-created failures | no output fields appear | COMPLETE |
| digest/relevance integrity | deterministic digest over compact binding | digest pattern and strict additional-properties schemas | `agent_verify.py` | schema-validated Verification artifact | `agent_close.py` rejects invalid binding | direct and public load/validation tests | output tails excluded before digest | COMPLETE |

`C09_RESULT = COMPLETE`
`BATCH2_STATUS = BATCH2_C09_PASS`

## Changed files

- `governance/verification/evidence.py`: compact deterministic task-relevance binding and validation.
- `governance/verification/verification_builder.py`: create the binding after canonical result normalization and failure attribution.
- `governance/verification/closure_evaluator.py`: validate and carry the exact binding; reject unsatisfied required evidence.
- `schemas/verification_result.schema.json`: Verification binding contract.
- `schemas/closure_result.schema.json`: Closure binding contract.
- `tests/unit/test_v1_5_1_compact_closure_evidence.py`: direct, public persistence, isolation, required-failure, and no-output coverage.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.unit.test_v1_5_1_compact_closure_evidence
# PASS: 3 tests

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.unit.test_v1_5_1_compact_closure_evidence tests.unit.test_v1_5_1_contract_parity tests.unit.test_p3_core tests.integration.test_p3_acceptance_matrix tests.integration.test_p3_closure_cli tests.unit.test_v1_5_reality_check tests.unit.test_execution_envelope tests.unit.test_schema_contracts tests.contracts.test_p5_schema_compatibility
# PASS: 29 tests

python3 scripts/check_schema_compatibility.py
# PASS: 39 schemas, stable fields and enums

PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_governance.py
# PASS: 39 schemas, rules index, module registry, references

git diff --check
# PASS
```

No network, production, external API, Git history, tag, release, or primary-main action occurred. No commit was made for Batch 2; the worktree intentionally retains these C09 changes and this report for the next authorized checkpoint.
