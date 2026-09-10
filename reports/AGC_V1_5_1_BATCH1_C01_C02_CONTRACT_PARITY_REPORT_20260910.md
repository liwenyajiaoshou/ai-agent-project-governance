# 卫兵 v1.5.1｜Batch 1 C01/C02 Contract Parity Report

## Stage and baseline

- `worktree`: `/home/liyouran1997/projects/agc-v1.5.1-p0-contract-closure`
- `branch`: `agc-v1.5.1-p0-contract-closure`
- `baseline`: `efd8f51503e71fb5b426e565433da0368390fbe3` (`v1.5.0`)
- `scope`: C01 and C02 only. C05 was removed from implementation by the frozen requirement-definition correction; C06/C09/C15/C16 and all P1/P2 remained untouched.
- `VERSION`: unchanged (`1.5.0`); the repository version guidance does not require a development-time bump for this uncommitted batch.

## C01 — authority-bound TestPlan parity

`C01_CONTRACT_AUTHORITY = EXISTING_TASKCONTRACT_VERIFICATION_FIELDS`

`TaskContract.verification.level_1/level_2/level_3` is the existing test-authorization authority. The Adoption Runtime already writes confirmed test command text into this structure. `test_planner.authorized_command_ids()` now resolves only those authorized command texts (or an already-known registry ID) back to the closed command registry. It does not accept CLI-provided required-test input.

`selected_commands` remains the canonical collection. `required_tests`, `regression_tests`, and `informational_tests` are schema-declared derived views of the exact same command item shape. `agent_test_plan.py create` therefore persists a schema-valid plan that contains both a required command (`governance_validate`) and a regression command (`quality_gate`) when the active contract authorizes the first command. A blocked plan also persists successfully.

## C02 — one VerificationResult normalization boundary

`verification_builder.normalize_result()` is the sole runner-result-to-persisted-TestResult boundary. It accepts the runner-shaped record once and writes one canonical item with command identity, level, required role, status, compact summary, exit/duration, digest, and redaction metadata. It intentionally omits sanitized output tails from VerificationResult; no raw stdout/stderr is added.

`agent_test_run.py` continues to emit runner records and `agent_verify.py` continues to persist only the builder's canonical result. The Verification schema now declares `command_id` (not a legacy `command` alias) and supports `PASS`, `FAIL`, `NOT_RUN`, `TIMEOUT`, and `ERROR`. Baseline/post-task/task-created attribution is calculated after normalization and remains present on VerificationResult.

## Acceptance matrix

| Requirement | Implementation | Schema | Public CLI | Persistence | Targeted test | Integration evidence | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C01 required vs regression TestPlan | Contract verification authority → registry resolution → planner derived views | `test_plan.schema.json` declares all views | `agent_test_plan.py create` | `.agent_state/test_plan.yaml` via `save_p3` | direct READY and BLOCKED planner checks | subprocess public create for READY (required + regression) and BLOCKED, then schema validate/load | COMPLETE |
| C02 runner result parity and attribution | runner shape → `normalize_result` → builder attribution | `verification_result.schema.json` declares canonical TestResult | `agent_verify.py` | `.agent_state/verification_result.yaml` via `save_p3` | baseline-only, task-created, PASS/FAIL/TIMEOUT/ERROR checks | subprocess public verify persistence for PASS/FAIL/TIMEOUT/ERROR, then schema validate/load | COMPLETE |

## Changed files

- `governance/verification/test_planner.py`: resolve existing contract verification authority.
- `schemas/test_plan.schema.json`: declare the derived TestPlan views.
- `governance/verification/verification_builder.py`: single normalization boundary.
- `schemas/verification_result.schema.json`: canonical persisted TestResult shape and statuses.
- `tests/unit/test_v1_5_1_contract_parity.py`: C01/C02 direct and public persistence coverage.
- `tests/unit/test_schema_contracts.py`, `tests/fixtures/compatibility/schema_baseline.json`: schema example and compatibility contract alignment.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.unit.test_v1_5_1_contract_parity
# PASS: 4 tests

python3 scripts/check_schema_compatibility.py
# PASS: 39 schemas, stable fields and enums

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.unit.test_v1_5_1_contract_parity tests.unit.test_p3_core tests.integration.test_p3_acceptance_matrix tests.integration.test_p3_closure_cli tests.unit.test_v1_5_reality_check tests.unit.test_schema_contracts tests.contracts.test_p5_schema_compatibility
# PASS: 20 tests

PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_governance.py
# PASS: 39 schemas, rules index, module registry, references

git diff --check
# PASS
```

The initial `python` executable probe was unavailable in this worktree environment; all recorded Python checks used the available `python3` executable. No network, production, external API, Git history, tag, release, or primary-main operation occurred.

## Batch result

`C01_ACCEPTANCE_MATRIX = COMPLETE`
`C02_ACCEPTANCE_MATRIX = COMPLETE`
`BATCH1_C01_C02_PASS`

No commit was created. The isolated worktree remains intentionally dirty with the Batch 1 implementation, its tests, the prior planning report, and this report.
