# 卫兵 v1.5.1｜P0 Reality Check and Minimal Repair Plan

## Stage record

- `stage`: `V1_5_1_P0_REALITY_CHECK_AND_MINIMAL_REPAIR_PLAN`
- `mode / level`: `EXECUTION / C`, Level 2 planning only; no implementation is authorized in this stage.
- `isolated_branch`: `agc-v1.5.1-p0-contract-closure`
- `isolated_worktree`: `/home/liyouran1997/projects/agc-v1.5.1-p0-contract-closure`
- `baseline`: `v1.5.0` = `efd8f51503e71fb5b426e565433da0368390fbe3`
- `authority_input`: the primary-main untracked report `../ai-agent-project-governance/reports/AGC_V1_5_0_PRE_V1_5_REQUIREMENT_COVERAGE_AUDIT_20260910.md`, read only and not copied or changed.
- `writes in this stage`: this report only, in the isolated worktree. No code, schema, test, commit, tag, release, network, or primary-main mutation occurred.

## Scope match

In scope, and only in scope: C01, C02, C05, C06, C09, C15, and C16 from the authority audit.

Excluded: C10, C12, C13, C19, C20, C22, Publication Authority, Broad Asset Copier, Adoption Wizard, and every P1/P2 item. In particular, C06 may consume an existing workspace-baseline identifier but must not become a Workspace Delta/attribution implementation.

`8/8 PASS` and the 39-schema release check are release-quality evidence only. They do not establish the per-requirement public-path coverage below.

## Reality-check routes

### C01 — TestPlan runtime/schema parity

- `classification`: `A. SCHEMA_PARITY_FIX`.
- `runtime now`: `governance.verification.test_planner.create()` emits `selected_commands` plus redundant partition views `required_tests`, `regression_tests`, and `informational_tests`. Each selected item uses `command_id`, `level`, argv/cwd/timeout, `required`, and reason (`task_relevant` or `affected_module_regression`). A blocked plan emits the same three partition fields as empty arrays.
- `schema now`: `schemas/test_plan.schema.json` permits `selected_commands` but rejects all three partition fields via `additionalProperties: false`.
- `actual public persistence`: `scripts/agent_test_plan.py create` reads `.agent_state/active_task.yaml` and `.agent_state/last_guard_result.yaml`, calls `create(...)`, then calls `store.save_p3(layout.TEST_PLAN, value, "test_plan.schema.json")`. `save_p3` schema-validates before atomically writing `.agent_state/test_plan.yaml`. The CLI currently passes no `task_relevant_command_ids`, so its READY output makes every selected command regression; this is a second public-path gap, distinct from the schema rejection.
- `minimal repair`: make the schema accept the planner's one plan representation rather than deleting correct runtime partition data. `selected_commands` remains the canonical command collection; partition lists, if retained, must be schema-declared derived views with the same item shape. Bind required command IDs to the active contract's verification input (or another already-authorized contract field) before the CLI invokes the planner; do not trust a second free-form TestPlan semantics source.
- `why schema first`: the planner already represents the audited required/regression distinction and the immediate failure is schema rejection at the only persistence boundary. Changing runtime to hide fields would remove the requested public evidence and still would not make the CLI select task-relevant commands.
- `required public-path tests`: subprocess/temporary-state tests for `agent_test_plan.py create` proving (1) READY persistence with at least one required and one regression command, (2) BLOCKED persistence, and (3) schema validation/load of the saved file. Direct planner tests remain supplementary.

### C02 — VerificationResult runtime/schema parity

- `classification`: `B. RUNTIME_NORMALIZATION_FIX`.
- `actual chain`: `agent_test_run.py` writes runner-shaped items to `.agent_state/test_results.yaml` (`command_id`, `level`, `required`, status, exit/duration, bounded sanitized output tails and digests). `scripts/agent_verify.py` loads those results, calls `verification_builder.build(...)`, and persists its result with `store.save_p3(..., "verification_result.schema.json")` to `.agent_state/verification_result.yaml`.
- `conflict`: the builder forwards `results` unchanged, while the schema instead requires each test item to have `command`, `level`, `status`, and `summary`; it also permits only `PASS`, `FAIL`, and `NOT_RUN`, although the runner can produce `TIMEOUT` and `ERROR`.
- `normalization point`: normalize exactly once at the input boundary of `verification_builder.build`, from runner result to a single canonical persisted TestResult. The canonical item should retain command identity, level, required/regression role, status (including timeout/error), concise summary, and the existing compact output digest/redaction metadata where appropriate. The verification schema must declare precisely that item. Neither `agent_test_run.py` nor Closure may maintain an alternative TestResult meaning.
- `required tests`: direct builder fixtures for baseline-only and task-created failures; subprocess/temporary-state `agent_verify.py` persistence for runner-shaped PASS, required FAIL, TIMEOUT/ERROR; and Closure outcomes for baseline-degraded/no-new-failure versus task-created failure.

### C05 — TaskContract supersession / stage transition

- `classification`: `E. ARCHITECTURE_DECISION_REQUIRED`.
- `completed`: `TaskContract.status` includes `SUPERSEDED`; `supersede(active, successor, approval_evidence)` requires two ACTIVE contracts and records both task IDs/digests, time, and approval evidence. The contract schema and `test_v1_5_reality_check.py` support that linkage.
- `not present`: no ordinary-TaskContract `stage` field, stage-transition graph, transition validator, state persistence path, or public transition CLI exists.
- `separate existing lifecycle`: `governance.adoption.lifecycle.transition_project_state()` implements a CAS, evidence-bound graph for Adoption `ProjectState` (`ACTIVATED_NOT_PREFLIGHTED` through `CLOSED`). The architecture document expressly describes TaskContract lifecycle as statuses, not this Adoption stage graph.
- `decision`: authority must say whether the original C05 requirement intended a new ordinary-contract stage model, or incorrectly merged Adoption lifecycle stages into TaskContract. Without that decision, do not create a Stage Manager or copy Adoption lifecycle machinery. C05 has no v1.5.1 implementation batch.

### C06 — Closure Window / autonomous repair boundary

- `classification`: `C. EXISTING_COMPONENT_WIRING`.
- `existing responsibilities`: `AutonomousRemediationBudget` allows bounded local fixture/helper/mock/test-isolation/schema/report work and fails closed for network, formal data, Git/release, scope, product, and risk escalation. `ExecutionEnvelope` separately classifies recoverable actions and hard blockers under `GOV-ENVELOPE-001`/`GOV-BLOCKER-001`. Generic `closure_evaluator.close()` only maps verification status and an externally supplied `stale` boolean. Adoption Closure is a stronger, separate provenance/state/workspace recheck.
- `minimum wiring point`: extend the existing generic verification-to-closure handoff so Closure consumes one compact repair-boundary record derived from the active contract, current guard/freshness evidence, and the already-existing budget/envelope decision. Closure must block on invalidated baseline/freshness, a hard blocker, or a repair outside the budget; otherwise it closes the existing verification outcome. Reuse `closure_evaluator` and its public `agent_close.py` path; do not add a second Closure engine or adopt Adoption's state machine.
- `required tests`: fresh bounded local repair can close; stale/invalidated boundary blocks; unknown/hard action blocks; public `agent_close.py` persists the corresponding ClosureResult. No C10/C13 path projection is required.

### C09 — compact task-relevant Closure Evidence

- `classification`: `D. MINIMAL_CONTRACT_EXTENSION`.
- `existing inputs`: C01's selected plan already carries `required` and reason; the runner sanitizes bounded tails and digests; `build_test_evidence()` already excludes environment values; `verification_builder` knows failure attribution. Generic Verification and Closure schemas do not retain a task-relevance evidence binding, and `report_builder` reads the incompatible runner field directly.
- `minimal extension`: after C01/C02 canonicalize plan/result, add one schema-declared compact verification/closure evidence summary: task ID, required-command identities/statuses/reasons, regression aggregate or identities as needed, failure-isolation state, and digest references/redaction metadata only. Closure copies/binds this summary or its digest; it must not persist raw stdout/stderr or a second evidence collection.
- `required tests`: required versus regression plan flows into persisted verification and closure; raw/sensitive output is absent while digest/compact evidence is present; baseline failure remains non-task-created; task-created required failure prevents CLOSED.

### C15 — Minimum Owner Gate integration

- `classification`: `C. EXISTING_COMPONENT_WIRING`.
- `existing chain`: `approval.schema.json` records owner identity, task, type, scope, environment fingerprint, timestamps/expiry, and optional contract digest. `approval_store` persists validated records; `freshness.evaluate` checks approved status, task, fingerprint, expiry, and requested scope; `ApprovalGuard.check` selects same-type records and applies freshness. `SideEffectGate` separately models external/formal-data/Git effect states and only accepts opaque approval evidence; it has no schema/store use and no generic caller. Adoption supplies its own explicit approval artifacts.
- `ordinary-task missing wiring`: `agent_approve add` stores an empty environment fingerprint, whereas `agent_guard` computes a non-empty current fingerprint, so a normal saved approval cannot become fresh-valid through this path. `ApprovalGuard.required` is only an objective-text API heuristic; it does not resolve all applicable effects. `SideEffectGate` is never constructed or bound to a fresh ApprovalRecord by ordinary Preflight/Guard/executor paths.
- `minimal repair`: retain ApprovalRecord as the only approval persistence system. Derive effect requirement from structured risk/effect data (not title text), create/bind the existing SideEffectGate to the selected fresh approval record/digest and current contract/baseline fingerprint, and make the normal Guard/effect entry reject missing, stale, scope-mismatched, or wrong-effect approval. Repair `agent_approve` so it records the same canonical fingerprint/contract binding that the Guard evaluates. Do not create a parallel approval store or adoption-style approval protocol.
- `required tests`: missing, valid reusable, stale fingerprint, scope mismatch, and wrong gate-type cases through a normal ordinary-task Guard/effect path; prove one approval cannot authorize another effect.

### C16 — execution form / risk kind / governance level separation

- `classification`: `D. MINIMAL_CONTRACT_EXTENSION`.
- `current dimensions`: `TaskRequest.hints.task_type` is the execution-form declaration; `risk_detector.detect_risks()` produces risk kinds; `execution_envelope.governance_level(context, risks.kinds)` produces authorization level; `PreflightResult` exposes classification, risks, and contract separately.
- `current coupling`: without a structured task type, `task_classifier.classify_task()` elevates `external_access` or `production_write` hints to task level C. Conversely, an explicit `task_type` returns early. Risk kinds are not persisted as a named contract field, so consumers cannot inspect the complete three-axis decision in one public artifact.
- `minimal decoupling`: classifier determines only task form/impact from declared task type and form rules; risk detector alone determines risk kinds; governance level derives only from risk/context. Persist the computed risk kinds alongside (not inside) task type and governance level in the existing TaskContract governance decision, with schema and model/builder alignment. No repair may lower, discard, or reinterpret a risk merely to avoid Level 3.
- `required tests`: contradictory-input matrix: A/B/C declared task type crossed with none/external/production/unknown risks; assert task type is retained, risk kind is retained, and governance level is independently Level 2/3 as appropriate.

## Acceptance matrix

No row is `COMPLETE` at this planning stage. A later batch may mark a row complete only when every listed cell has executable evidence; a canonical release gate cannot substitute for a missing cell.

| P0 | Requirement → implementation | Schema | Public CLI/path → persistence | Targeted test | Integration test | Closure evidence | Status now |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C01 | Required vs regression plan → planner + contract-fed selection | TestPlan partition/canonical command shape | `agent_test_plan create` → `test_plan.yaml` | planner READY/BLOCKED | subprocess persistence READY required+regression+BLOCKED | required/reason available to C09 | OPEN |
| C02 | Failure isolation → builder normalization | canonical Verification TestResult | `agent_verify` → `verification_result.yaml` | baseline/new/timeout fixtures | runner-shaped CLI persistence | isolation state to C09/C06 | OPEN |
| C05 | Supersession done; stage model undecided | existing supersession only | no stage path exists | supersession existing | no generic stage integration possible | supersession linkage only | OWNER DECISION REQUIRED |
| C06 | Budget/envelope → generic Closure handoff | compact boundary reference, if needed | `agent_close` → `closure_result.yaml` | fresh/invalidated/hard boundary | public close persistence | boundary decision/freshness digest | OPEN |
| C09 | Required/regr. result → compact closure summary | Verification/Closure compact summary | verify → close artifacts | compact/no-raw tests | planned→run→verify→close chain | required identities/status/reasons + digests | OPEN |
| C15 | ApprovalRecord/freshness/guard/gate wiring | existing approval; binding only if required | approve → guard/effect path | missing/fresh/stale/scope/wrong-effect | ordinary effect gate path | approval ID/digest and gate state | OPEN |
| C16 | independent type/risk/level decisions | TaskRequest/TaskContract decision fields | preflight → active contract | contradictory matrix | preflight public path/schema load | decision axes in verification/closure summary when relevant | OPEN |

## Proposed minimal batches

1. **Batch 1 — C01 + C02:** establish one schema-valid public TestPlan/VerificationResult path and one TestResult normalization boundary. C09 depends on these identities and statuses.
2. **Batch 2 — C09:** carry Batch-1 required/regr. and failure-isolation evidence into a compact Closure summary. It must not store raw output.
3. **Batch 3 — C15 + C16:** make structured risk/effect and independent semantics available before wiring the Owner Gate. C16 supplies the non-heuristic facts C15 needs; neither batch reduces risk.
4. **Batch 4 — C06:** bind the existing repair budget/envelope to generic Closure using the now-normalized verification and compact evidence handoff. It reuses, rather than duplicates, generic Closure.
5. **C05 — no batch pending owner decision:** only enter implementation after the owner explicitly resolves ordinary TaskContract stages versus the separate Adoption ProjectState lifecycle and supplies the required authority/model boundary.

## Architecture decisions required

1. **C05 (blocking):** Is a constrained ordinary-TaskContract stage graph actually a frozen v1.5 requirement, or was the separate Adoption ProjectState lifecycle incorrectly folded into C05? If yes, owner must define stage vocabulary, legal transitions, persistence/authority, and relation to existing status/supersession before implementation.
2. **C01 contract source (bounded):** confirm that task-relevant command IDs are contract-authorized verification data, not CLI-supplied mutable assertions. This is needed for the requested public path to produce required tests.
3. **C15 effect taxonomy (bounded):** confirm the minimum mapping between structured risk/effect and the existing three `SideEffectGate` types. The implementation must not infer authority from objective prose.

## Verification and stop state

- Performed: tag/commit/worktree identity checks and read-only source/schema/CLI/test traceability inspection.
- Not run: unit, integration, canonical 8/8, schema validation, or any network/action test. This stage does not modify implementation and must not claim repaired behavior.
- Primary main was not changed; its authority audit remains untracked there.
- Stop here. The next authorized action is owner resolution of C05 (and the bounded decisions above), then implementation in the listed batch order.
