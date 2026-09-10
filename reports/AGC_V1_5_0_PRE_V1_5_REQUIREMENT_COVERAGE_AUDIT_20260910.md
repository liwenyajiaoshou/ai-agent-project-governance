# 卫兵 v1.5.0｜Pre-v1.5 Requirement Coverage Audit

## Audit identity

- `formal_version`: `v1.5.0`
- `release_commit`: `efd8f51503e71fb5b426e565433da0368390fbe3`
- `release_status`: `AGC_V1_5_0_GIT_RELEASE_PUBLISHED`
- `audit_workspace`: `/home/liyouran1997/projects/ai-agent-project-governance`
- `audit_head`: `efd8f51503e71fb5b426e565433da0368390fbe3`
- `audit_branch`: `main`
- `v1_5_baseline`: `6cedc70629930fcb95aabbf829ede7a708967791`
- `workspace_at_audit_start`: clean
- `audit_mode`: read-only; no code/schema/test/release asset was modified
- `report_is_the_only_new_file`: yes

## Scope and method

本审计以当前 `HEAD`/`v1.5.0` tag 为最终代码事实，以 v1.5 Reality Check、Reuse Matrix、Final Manifest、Git Authority Reconciliation、Release Readiness 及 v1.4 正式报告为历史和范围证据。较早的 Release Readiness 中的 `RELEASE_BLOCKED` 是发布前快照，不能覆盖当前用户给出的已发布状态；它仅用于确认当时的发布权限边界。

`ALREADY_EXISTED_AND_REUSED` 只用于同时满足以下条件的条目：v1.5 前已有能力，并且 v1.5 Reality Check 明确把该能力归入复用/不重复建设范围。仅有相似代码、旧测试、发布门禁通过或历史报告中的“类似能力”，不作为完整覆盖证据。

`8/8 PASS`、39 schemas validation 和 `git diff --check` 只作为发布质量证据，不能替代下表的需求覆盖判断。

## Direct audit checks

| Check | Result | Evidence |
|---|---|---|
| Current release identity | PASS | `git rev-parse HEAD` and `git show -s efd8f515...` both resolve to the supplied release commit; `v1.5.0` tag points at it. |
| Worktree protection | PASS at audit start | `git status --short` was empty before this report was created. |
| Governance baseline validation | PASS | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_governance.py`; 39 schemas, rules index, module registry and references. |
| Whitespace check | PASS | `git diff --check`. |
| TestPlan runtime/schema parity | FAIL | `governance.verification.test_planner.create(...)` returns `required_tests`, `regression_tests`, and `informational_tests`, while `schemas/test_plan.schema.json` rejects them under `additionalProperties: false`. |
| VerificationResult runtime/schema parity | FAIL | `governance.verification.verification_builder.build(...)` emits `command_id`/`required` test entries, while `schemas/verification_result.schema.json` requires `command`/`summary` and rejects the emitted shape. |
| Additional full regression | NOT RUN | This was a read-only coverage audit; existing v1.5 formal evidence records the targeted 25-test pass and canonical 8/8 release gate. No new full test run was needed to establish the two schema contradictions above. |
| Network / external access | NONE | No network, API, package download, browser, production access, Git write, or release operation was performed. |

## Requirement coverage matrix

### P0 / core

#### C01 — Task-Relevant TestPlan

- `requirement`: TestPlan must distinguish task-relevant required tests from affected-module regression tests.
- `original_problem`: 原有计划按任务等级/适配器选择命令，但没有把“必须证明本任务”的测试与一般回归测试分开。
- `v1_5_status`: `PARTIALLY_SATISFIED`
- `evidence`: Reality Check states that required-versus-regression separation was implemented; `governance/verification/test_planner.py:27-38` accepts `task_relevant_command_ids`, sets `required`, and records `reason` as `task_relevant` or `affected_module_regression`.
- `implementation_location`: `governance/verification/test_planner.py`; `scripts/agent_test_plan.py`; `schemas/test_plan.schema.json`.
- `test_or_schema_evidence`: Existing P3 tests exercise direct planner output, but the direct v1.5 audit check proved that the planner output cannot pass the current TestPlan schema: `required_tests`, `regression_tests`, and `informational_tests` are emitted by code but not declared by schema. `scripts/agent_test_plan.py` persists through `store.save_p3`, which validates that schema.
- `remaining_gap`: The semantic partition exists in code but is not schema-compatible through the public persistence path; the v1.5 targeted tests do not cover this save/validate path.
- `recommended_future_action`: v1.5.1 P0 — reconcile schema and runtime fields, then add a public `agent_test_plan.py` persistence test covering required, regression, and blocked plans.
- `priority`: `P0`
- `confidence`: `HIGH`

#### C02 — Pre-existing / post-task / task-created Failure Isolation

- `requirement`: Verification must separate baseline failures, failures observed after the task, and failures attributable to the task.
- `original_problem`: 既有失败容易被误报为本任务造成，导致错误失败结论或错误收口。
- `v1_5_status`: `PARTIALLY_SATISFIED`
- `evidence`: `governance/verification/verification_builder.py:2-11` computes `baseline_failures`, `post_task_failures`, and `task_created_failures`; `schemas/verification_result.schema.json` contains the corresponding fields; the v1.5 test checks that a baseline failure is not task-created.
- `implementation_location`: `governance/verification/verification_builder.py`; `schemas/verification_result.schema.json`; `tests/unit/test_v1_5_reality_check.py:26-28`.
- `test_or_schema_evidence`: The direct baseline test passes. However, the emitted verification result cannot pass the current schema when real runner-shaped entries are supplied: code emits `command_id`/`required`, while the schema test item requires `command`/`summary`. The public `agent_verify.py` path persists through schema validation.
- `remaining_gap`: Attribution logic is present, but the public verification artifact is not serializable under its own schema; coverage also lacks a task-created-new-failure assertion and node/path-level attribution.
- `recommended_future_action`: v1.5.1 P0 — normalize runner results before `VerificationResult` persistence, add baseline-only and new-failure fixtures, and verify closure behavior for each isolation state.
- `priority`: `P0`
- `confidence`: `HIGH`

#### C03 — Risk Detector negative semantics

- `requirement`: Explicit negative statements such as “no network” and “no production write” must not create those risks, while a positive structured risk must still win.
- `original_problem`: 文本中同时出现风险词和禁止/否定语句时，简单 substring detector 会产生假阳性或错误阻断。
- `v1_5_status`: `IMPLEMENTED`
- `evidence`: `governance/preflight/risk_detector.py:17-38` implements negative phrase handling for external and production risks and keeps explicit booleans/structured `True` authoritative; the Reality Check names explicit negative risk semantics as a v1.5 implementation.
- `implementation_location`: `governance/preflight/risk_detector.py`; `tests/unit/test_v1_5_reality_check.py:13-24`.
- `test_or_schema_evidence`: v1.5 tests pass for negative external/production text and for structured external risk overriding a negative sentence; `schemas/task_request.schema.json` validates the input shape.
- `remaining_gap`: The implementation is a bounded phrase allowlist, not a general natural-language negation parser; delete/overwrite/secret phrases do not receive the same negative treatment. That broader behavior was not proven as part of the frozen v1.5 scope.
- `recommended_future_action`: Keep the bounded semantics for v1.5.1; only expand the negation contract if additional false-positive cases are formally accepted and fixture-backed.
- `priority`: `P0`
- `confidence`: `HIGH`

#### C04 — Structured risk hints

- `requirement`: Task requests must carry explicit structured risk hints that take precedence over ambiguous prose.
- `original_problem`: 仅依赖标题/描述文本无法稳定表达“通常不联网但本次明确要求联网”这类冲突语义。
- `v1_5_status`: `IMPLEMENTED`
- `evidence`: `schemas/task_request.schema.json` adds `hints.task_type` and `hints.risk_hints`; `risk_detector.py:19-26` consumes `risk_hints`; `tests/unit/test_v1_5_reality_check.py:20-24` proves a structured external hint blocks the task.
- `implementation_location`: `schemas/task_request.schema.json`; `governance/preflight/risk_detector.py`; `tests/unit/test_v1_5_reality_check.py`.
- `test_or_schema_evidence`: Schema validation and the structured-hint precedence test are present; the v1.5 Reality Check explicitly records structured hints taking precedence.
- `remaining_gap`: The v1.5 contract exposes only `external_access` and `production_write`; other risk classes remain represented by existing fields/text.
- `recommended_future_action`: No v1.5.1 action required; extend the schema only with an independently approved risk taxonomy.
- `priority`: `P0`
- `confidence`: `HIGH`

#### C05 — TaskContract Supersession / Stage Transition

- `requirement`: A successor TaskContract must audibly supersede the active contract, and contract lifecycle stage transitions must be explicit and constrained.
- `original_problem`: 任务变更后容易出现旧合同仍被使用、继任合同没有证据链，或阶段被跳过/倒退。
- `v1_5_status`: `PARTIALLY_SATISFIED`
- `evidence`: `governance/models/task_contract.py:46-54` creates `SUPERSEDED` status and binds previous/successor digests plus approval evidence; `schemas/task_contract.schema.json` adds the status and supersession object; `tests/unit/test_v1_5_reality_check.py:30-34` checks auditable linkage.
- `implementation_location`: `governance/models/task_contract.py`; `schemas/task_contract.schema.json`; `governance/adoption/lifecycle.py` is a separate adoption ProjectState transition path.
- `test_or_schema_evidence`: Supersession unit test and schema support are present. No TaskContract stage field or generic contract transition validator exists; adoption lifecycle stages are not a substitute for TaskContract stage transitions.
- `remaining_gap`: Supersession is implemented, but the “stage transition” half of the requirement is not represented or enforced for ordinary TaskContracts.
- `recommended_future_action`: v1.5.1 P0 — define the minimum contract stage model and transition validator, or explicitly split it from supersession as a v1.6 architecture decision.
- `priority`: `P0`
- `confidence`: `HIGH`

#### C06 — Closure Window / Autonomous Repair Boundary

- `requirement`: Ordinary local repair may continue within a bounded window before closure; crossing risk, scope, production, or authorization boundaries must stop.
- `original_problem`: 测试/fixture/helper 等普通工程故障要么被过早升级为人工阻断，要么在收口窗口中越过授权边界。
- `v1_5_status`: `PARTIALLY_SATISFIED`
- `evidence`: The v1.5 Reality Check explicitly reuses the autonomous remediation budget; `governance/core/budget.py:8-48` allowlists local repair and rejects network/data/Git/release/scope escalation; `governance/policy/execution_envelope.py:16-98` defines recoverable versus hard blockers; `closure_evaluator.py:2-6` only receives a caller-supplied `stale` flag.
- `implementation_location`: `governance/core/budget.py`; `governance/policy/execution_envelope.py`; `governance/verification/closure_evaluator.py`; `governance/adoption/lifecycle.py:168-187`.
- `test_or_schema_evidence`: `tests/unit/core/test_budget.py`, `tests/unit/test_execution_envelope.py`, and adoption lifecycle evidence cover the boundary. Generic Closure does not bind a workspace baseline, repair budget, or repair window itself; adoption Closure has its own stronger rechecks.
- `remaining_gap`: The autonomous repair policy exists, but the generic Closure path does not provide one integrated “repair allowed until this evidence/window, then close or block” contract.
- `recommended_future_action`: v1.5.1 P0 — connect repair authorization, workspace freshness, and Closure readiness in one ordinary-task path; keep adoption lifecycle as a reference implementation.
- `priority`: `P0`
- `confidence`: `HIGH`

#### C07 — Existing Project Adoption single formal entry

- `requirement`: Existing-project adoption needs one canonical formal entry that composes detection, audit, planning, drafts, review, and bounded downstream steps.
- `original_problem`: v1.0 adoption required many manual operations and had no formal `adopt` entry; users could confuse the new-project initializer with in-place adoption.
- `v1_5_status`: `ALREADY_EXISTED_AND_REUSED`
- `evidence`: v1.4 04B introduced `scripts/agent_adopt.py` as the public `dry-run` entry; `docs/EXISTING_PROJECT_ADOPTION.md:3-7,39-52` calls it the single recommended adoption path and documents the complete subcommand surface. The v1.5 Reality Check explicitly chooses reuse of the adoption lifecycle/evidence chain rather than a duplicate subsystem.
- `implementation_location`: `scripts/agent_adopt.py`; `governance/adoption/`; `docs/EXISTING_PROJECT_ADOPTION.md`; `tests/unit/test_agent_adopt.py:154-178`.
- `test_or_schema_evidence`: Current help/dispatcher parity and subcommand-help tests cover the public entry; the v1.4 04F-R2 acceptance covers the bounded synthetic lifecycle.
- `remaining_gap`: This is a canonical entry path, not a one-command adoption wizard; installation and activation remain separate explicit steps by design.
- `recommended_future_action`: Reuse as-is. Do not create a second `adopt --plan-only` or duplicate lifecycle entry.
- `priority`: `P0`
- `confidence`: `HIGH`

#### C08 — Adoption upstream evidence auto-derivation

- `requirement`: Each adoption lifecycle edge must derive and validate upstream evidence from persisted state rather than trusting a caller-provided list.
- `original_problem`: 下游阶段可能伪造、遗漏或替换前序 evidence，导致状态链断裂或重放。
- `v1_5_status`: `ALREADY_EXISTED_AND_REUSED`
- `evidence`: `governance/adoption/evidence_registry.py:11-18` is the single edge registry; `upstream_digests()` at lines 32-42 derives persisted digests and rechecks evidence files; `validate_evidence_file()` at lines 45-67 validates edge type, state digest, target identity and upstream chain. The v1.5 Reuse Matrix explicitly marks adoption evidence upstream for reuse.
- `implementation_location`: `governance/adoption/evidence_registry.py`; `governance/adoption/lifecycle.py:34-74`; `schemas/adoption_lifecycle_evidence.schema.json`.
- `test_or_schema_evidence`: `tests/unit/test_agent_adopt_activation.py` covers context reconstruction and state transitions; v1.4 04F-B/R1 reports cover modified/missing upstream evidence rejection.
- `remaining_gap`: No v1.5 gap was found for the bounded adoption lifecycle contract.
- `recommended_future_action`: Preserve the single registry and extend only through new registered edge tests if lifecycle stages change.
- `priority`: `P0`
- `confidence`: `HIGH`

#### C09 — Closure Evidence task relevance / evidence compression

- `requirement`: Closure evidence must identify task-relevant proof and remain compact, reproducible, and safe to store.
- `original_problem`: 收口报告容易堆积完整命令输出，或者只证明“某测试跑过”而没有证明它与本任务有关。
- `v1_5_status`: `PARTIALLY_SATISFIED`
- `evidence`: `governance/verification/test_planner.py:34-37` labels required task-relevant commands; `governance/verification/evidence.py:8-39` builds bounded reproducible evidence; adoption runner stores sanitized tails/digests; `docs/EXISTING_PROJECT_ADOPTION.md:139-145` documents compression and freshness.
- `implementation_location`: `governance/verification/test_planner.py`; `governance/verification/evidence.py`; `governance/verification/report_builder.py`; `governance/adoption/lifecycle.py`; `schemas/verification_result.schema.json` and `schemas/closure_result.schema.json`.
- `test_or_schema_evidence`: `tests/unit/test_execution_envelope.py:62-72` covers reproducible evidence input validation; adoption security tests cover sanitized output. The generic evidence helper has no `task_id`/task-relevance field, ClosureResult carries no compressed evidence summary, and the verification test-item schema disagrees with runner output.
- `remaining_gap`: Compression exists, but generic Closure does not retain a schema-level task-relevance binding and the public verification artifact currently fails its schema boundary.
- `recommended_future_action`: v1.5.1 P0 — normalize TestResult/VerificationResult, carry required-vs-regression evidence into Closure, and add a compact evidence digest field without storing raw output.
- `priority`: `P0`
- `confidence`: `HIGH`

### Workspace / Projection

#### C10 — Workspace Delta Projection

- `requirement`: A structured projection must show the workspace delta from pre-task baseline to post-task state.
- `original_problem`: 只有 baseline 或最终 changed-path 摘要时，无法稳定说明哪些变化在任务前存在、哪些在任务后出现，以及是否仍有未解释变化。
- `v1_5_status`: `NOT_IMPLEMENTED`
- `evidence`: Current `governance/workspace/baseline.py` captures baseline inputs and `governance/adoption/lifecycle_context.py` produces a snapshot digest, but neither exposes a generic before/after path delta. The v1.5 Final Manifest’s `final_changed_paths` and `task_created_changes` are release-specific evidence, not a reusable workspace projection.
- `implementation_location`: No dedicated `WorkspaceDeltaProjection` implementation, schema, or public entry was found. Related substrate: `governance/workspace/baseline.py`; `governance/adoption/lifecycle_context.py:25-40`.
- `test_or_schema_evidence`: Workspace tests cover clean/accepted-dirty baseline and isolation; adoption tests cover snapshot freshness. No generic delta projection schema/test exists.
- `remaining_gap`: No structured path-level before/after delta, classification, unexplained-change set, or projection digest is produced for ordinary tasks.
- `recommended_future_action`: v1.6 P1 — design a read-only path-level projection with explicit baseline, task-created, user-owned, generated, temporary, and unexplained categories.
- `priority`: `P1`
- `confidence`: `HIGH`

#### C11 — Workspace Health Projection

- `requirement`: Workspace health must be represented as a reusable local state/projection with clean, accepted-dirty, conflict, and manual-resolution outcomes.
- `original_problem`: 工作区状态散落在规则和临时判断中，Agent 无法区分可接受 dirty、冲突、Git 元数据不可写和真正不安全状态。
- `v1_5_status`: `ALREADY_EXISTED_AND_REUSED`
- `evidence`: v1.4 Phase 1 created `governance/workspace/baseline.py`, `isolation.py`, and `lifecycle.py`; its formal report records `CLEAN`/`ACCEPTED_DIRTY`, fail-closed unaccepted dirtiness, conflict detection, and 15 passing workspace tests. The v1.5 Reality Check explicitly selects workspace foundation/health/lifecycle for reuse.
- `implementation_location`: `governance/workspace/baseline.py`; `governance/workspace/isolation.py`; `governance/workspace/lifecycle.py`; `tests/unit/workspace/`.
- `test_or_schema_evidence`: `test_workspace_baseline.py`, `test_workspace_isolation.py`, and `test_asset_lifecycle.py` cover the existing contract; v1.4 Phase 1 report records the same evidence.
- `remaining_gap`: There is no separately named projection schema, but the existing baseline/isolation result contract is the selected reusable capability. A future normalized schema would be an extension, not evidence that v1.5 missed the reused base.
- `recommended_future_action`: Reuse current baseline/health/lifecycle; only add a projection schema as part of the separate Delta design.
- `priority`: `P1`
- `confidence`: `HIGH`

#### C12 — Repository Hygiene Audit

- `requirement`: The repository must have an explicit read-only hygiene audit covering tracked/untracked/ignored/generated/temporary and sensitive artifacts.
- `original_problem`: 文档完整性或敏感文件检查不能替代 Git/worktree hygiene；临时产物和未归属变化可能进入收口或发布。
- `v1_5_status`: `PARTIALLY_SATISFIED`
- `evidence`: `governance/audit/checks.py` provides bounded documentation, adapter, test-command, encoding, and sensitive filename/ignore checks; `scripts/agent_audit.py` is read-only. It does not inspect Git status or classify repository artifacts as a complete hygiene projection.
- `implementation_location`: `governance/audit/checks.py`; `scripts/agent_audit.py`; `governance/workspace/lifecycle.py`.
- `test_or_schema_evidence`: `tests/unit/test_agent_audit.py` covers audit behavior; v1.4 adoption reports record sensitive-file review. No repository-hygiene schema or tracked/untracked artifact matrix is present.
- `remaining_gap`: Existing adoption audit is configuration-completeness oriented, not a full repository hygiene audit with ownership and cleanup readiness.
- `recommended_future_action`: v1.6 P1 — add a read-only hygiene projection that consumes workspace attribution and reports only safe path metadata.
- `priority`: `P1`
- `confidence`: `HIGH`

#### C13 — Pre-existing vs task-created workspace attribution

- `requirement`: Workspace changes must be attributable to pre-existing/user-owned, task-created, generated, temporary, or unexplained sources.
- `original_problem`: dirty workspace 中的用户变化、任务变化和工具产物混在一起，无法可靠判断收口责任。
- `v1_5_status`: `PARTIALLY_SATISFIED`
- `evidence`: `capture_baseline()` exposes `user_owned_assets` and `task_owned_assets`, and `verification_builder` separates baseline/post/task-created failures. However, `capture_baseline()` initializes `task_owned_assets` as an empty list and does not derive file attribution; the Final Manifest’s attribution flags are release-specific.
- `implementation_location`: `governance/workspace/baseline.py:34-75`; `governance/verification/verification_builder.py:2-11`; `reports/AGC_V1_5_0_FINAL_MANIFEST_20260910.json`.
- `test_or_schema_evidence`: Workspace baseline tests cover accepted user-owned dirtiness; v1.5 failure-isolation test covers command failures. No path-level attribution schema/test exists for an ordinary task.
- `remaining_gap`: Representation exists, but generic automatic or evidence-bound file attribution does not.
- `recommended_future_action`: v1.6 P1 — build on Delta Projection; bind attribution to the captured baseline and post-task snapshot, with explicit unknown/unexplained output.
- `priority`: `P1`
- `confidence`: `HIGH`

#### C14 — Dirty-workspace escalation / closure readiness

- `requirement`: Unaccepted dirty state must escalate safely, and Closure must know whether workspace state is ready and fresh.
- `original_problem`: Agent 可能在 dirty workspace 中继续施工，或 generic Closure 只看测试/Guard 而忽略工作区变化。
- `v1_5_status`: `PARTIALLY_SATISFIED`
- `evidence`: v1.4 workspace baseline raises `UnacceptedDirtyAssetError`; `preview_isolation()` reports conflicts, repository dirtiness, and manual resolution; adoption Closure rechecks current workspace snapshots. Generic `closure_evaluator.close()` only accepts a boolean `stale` argument and has no direct baseline/readiness binding.
- `implementation_location`: `governance/workspace/baseline.py`; `governance/workspace/isolation.py`; `governance/adoption/lifecycle.py:168-187`; `governance/verification/closure_evaluator.py:2-6`.
- `test_or_schema_evidence`: Workspace isolation/baseline tests and v1.4 04F-R2 adoption closure tests cover the existing paths; no generic workspace-to-Closure integration test exists.
- `remaining_gap`: Dirty escalation and adoption freshness are present, but ordinary-task Closure readiness is not derived from the workspace baseline/projection.
- `recommended_future_action`: v1.5.1 P1 if generic Closure is the supported path; otherwise v1.6 together with C10/C13.
- `priority`: `P1`
- `confidence`: `HIGH`

### Execution / Owner Gate

#### C15 — Minimum Owner Gate

- `requirement`: Every boundary-crossing execution must have a minimum explicit Owner gate with identity, scope, freshness, and evidence.
- `original_problem`: 文本中的“已确认”或 Agent 自述不能等同于 Owner 授权，尤其是外部访问、正式写入、Git/release 和激活。
- `v1_5_status`: `PARTIALLY_SATISFIED`
- `evidence`: Existing `approval.schema.json` has `approved_by`, scope, environment fingerprint, expiry and `contract_digest`; `approval_guard.py` and `state.freshness.py` validate reusable approvals; `SideEffectGate` requires approval evidence. Adoption has explicit confirmation/approval commands. However, ordinary Preflight returns `confirmation_fields` but does not itself persist or enforce a universal Owner approval gate, and `SideEffectGate` is not wired to the generic approval store.
- `implementation_location`: `schemas/approval.schema.json`; `governance/state/approval_store.py`; `governance/state/freshness.py`; `governance/guards/approval_guard.py`; `governance/core/gates.py`; `governance/preflight/engine.py`.
- `test_or_schema_evidence`: `tests/unit/test_approval_guard.py`, `test_approval_lifecycle.py`, and `test_gates.py` cover separate primitives. No end-to-end ordinary-task test proves the minimum gate is enforced before every applicable effect.
- `remaining_gap`: Owner-gate primitives exist, but the minimum universal enforcement contract and one canonical approval path are incomplete.
- `recommended_future_action`: v1.5.1 P0 — define which effects require the gate, connect Preflight/Guard/SideEffectGate/approval freshness, and test both missing and reusable Owner approval.
- `priority`: `P0`
- `confidence`: `HIGH`

#### C16 — Execution Form Is Not Risk

- `requirement`: Execution form/task level, risk kind, and authorization level must remain separate semantic dimensions.
- `original_problem`: 把“代码/架构/发布/表单类型”直接当成风险，会导致安全误判或错误放行；反过来也会让风险词替代真实授权判断。
- `v1_5_status`: `PARTIALLY_SATISFIED`
- `evidence`: `PreflightResult` separately returns `classification`, `risks`, and `contract`; `governance_level()` in `execution_envelope.py:57-64` consumes risk/context separately from `task_level`; structured `task_type` can override classification. But `task_classifier.py:21-25` still elevates top-level external/production booleans to C, and risk/level semantics are not represented as a single schema-level decomposition.
- `implementation_location`: `governance/preflight/engine.py`; `governance/preflight/task_classifier.py`; `governance/preflight/risk_detector.py`; `governance/policy/execution_envelope.py`.
- `test_or_schema_evidence`: v1.5 tests prove structured type and risk output are separately observable; no matrix proves that all execution forms remain independent from risk kinds across structured and prose inputs.
- `remaining_gap`: Separation exists in the result model, but fallback classification still couples some risk flags to task level and lacks a complete semantic matrix.
- `recommended_future_action`: v1.5.1 P0 — define independent `task_type`, `risk_kinds`, and `governance_level` semantics, then add contradictory-input tests.
- `priority`: `P0`
- `confidence`: `HIGH`

#### C17 — low-risk utility fast path

- `requirement`: Low-risk local utilities such as fixture/helper/mock/basetemp repair should continue within the current task without a new high-risk approval.
- `original_problem`: 普通可验证工程恢复被不必要地升级为人工阻断，造成无效等待和重复任务。
- `v1_5_status`: `ALREADY_EXISTED_AND_REUSED`
- `evidence`: v1.4 Wave 2-4 implemented `AutonomousRemediationBudget`; v1.5 Reality Check explicitly reuses the autonomous remediation boundary. `governance/core/budget.py:8-48` allowlists local utility actions and rejects high-risk actions.
- `implementation_location`: `governance/core/budget.py`; `tests/unit/core/test_budget.py`.
- `test_or_schema_evidence`: Budget tests cover allowlisted local work, forbidden network/Git/data/release work, unknown actions, and identity invalidation.
- `remaining_gap`: Fast-path authorization is a policy primitive, not an executor; actual remediation remains Agent work inside the boundary by design.
- `recommended_future_action`: Reuse current budget; connect it to Closure Window only through C06.
- `priority`: `P0`
- `confidence`: `HIGH`

#### C18 — Runtime recovery boundary / Agent autonomous environment recovery

- `requirement`: The runtime must distinguish recoverable local environment/test issues from hard blockers requiring Owner or external action.
- `original_problem`: 缺 fixture、局部依赖、测试隔离、首次失败等普通问题被错误地当作必须停工；真实网络、生产、受保护资产和架构变化又可能被误认为可自行修复。
- `v1_5_status`: `ALREADY_EXISTED_AND_REUSED`
- `evidence`: `governance/policy/execution_envelope.py:16-98` defines recoverable and hard action sets plus `GOV-ENVELOPE-001`/`GOV-BLOCKER-001`; `governance/autonomy/failure_classifier.py` keeps autonomous engineering codes separate from human checkpoints. The v1.5 Reality Check explicitly reuses this autonomous boundary.
- `implementation_location`: `governance/policy/execution_envelope.py`; `governance/autonomy/failure_classifier.py`; `tests/unit/test_execution_envelope.py`.
- `test_or_schema_evidence`: Tests cover local recoveries, hard blockers, verifiability, authorization inheritance and boundary drift.
- `remaining_gap`: The runtime classifies the boundary but does not itself recover an environment or invoke external tooling; architecture intentionally leaves engineering execution to the Agent.
- `recommended_future_action`: Reuse as the policy layer; do not add autonomous network/dependency/production recovery.
- `priority`: `P0`
- `confidence`: `HIGH`

### Compatibility / UX

#### C19 — Windows / Codex Sandbox diagnostics

- `requirement`: Windows and Codex/linked-worktree sandbox failures must be diagnosable as environment limitations rather than repository or task failures.
- `original_problem`: Windows PATH/line-ending/Git behavior and sandbox linked-worktree restrictions can produce misleading “repository broken” conclusions.
- `v1_5_status`: `PARTIALLY_SATISFIED`
- `evidence`: `provenance.py:179-192` has Windows Git executable fallback; `docs/COMPATIBILITY.md:17-20` records Windows local smoke and Codex as instruction-compatible; v1.4 Phase 1 report explicitly diagnoses linked-worktree Git failure as sandbox limitation. These are compatibility evidence and documentation, not one structured diagnostics contract.
- `implementation_location`: `governance/adoption/provenance.py`; `docs/COMPATIBILITY.md`; v1.4 Phase 1 and Windows smoke reports; related compatibility tests.
- `test_or_schema_evidence`: `tests/unit/test_provenance_git_head_blob.py` covers Git/provenance and LF/CRLF behavior; `tests/unit/test_init_presets.py` and architecture baseline cover initializer compatibility. No Codex sandbox diagnostic schema or classification test exists.
- `remaining_gap`: Windows support and historical diagnosis exist, but sandbox/OS/tool failure causes are not normalized into a reusable diagnostic result.
- `recommended_future_action`: v1.6 P1 — add read-only diagnostic categories and fixtures for Windows PATH, line endings, linked worktree, and restricted Git metadata.
- `priority`: `P1`
- `confidence`: `MEDIUM`

#### C20 — legacy initializer compatibility

- `requirement`: The legacy new-project initializer must retain its template/preset behavior and must not be mistaken for an existing-project adoption path.
- `original_problem`: v1.5 runtime architecture could accidentally replace or route the old initializer into in-place adoption, breaking template renaming or silently broadening writes.
- `v1_5_status`: `PARTIALLY_SATISFIED`
- `evidence`: `scripts/init_new_project.py:33-39,162-180` retains template renaming, new-directory creation, preset writing and non-overwrite behavior; `docs/EXISTING_PROJECT_ADOPTION.md:37` explicitly says it is not an in-place adoption shortcut; architecture baseline test checks `rglob("*.template.*")` and absence of `GOVERNANCE_RUNTIME` in the initializer.
- `implementation_location`: `scripts/init_new_project.py`; `tests/integration/test_architecture_baseline.py:56-60`; `tests/unit/test_init_presets.py`.
- `test_or_schema_evidence`: Existing tests cover template rename marker, preset defaults, invalid preset, and existing-target refusal. No full legacy invocation/output compatibility matrix or explicit v1.5 Reality Check reuse entry exists.
- `remaining_gap`: The core invariant is preserved, but the audit cannot certify all legacy command/output/path combinations as reused compatibility.
- `recommended_future_action`: v1.6 P1 only if compatibility demand exists; add a bounded fixture matrix before changing the initializer.
- `priority`: `P1`
- `confidence`: `MEDIUM`

#### C21 — Task classifier structured semantics

- `requirement`: Task classification must accept a structured A/B/C type and return auditable classification semantics instead of relying only on prose.
- `original_problem`: 文本分类容易受词序和风险描述影响，无法稳定区分任务等级和风险类型。
- `v1_5_status`: `IMPLEMENTED`
- `evidence`: `schemas/task_request.schema.json` adds `hints.task_type`; `governance/preflight/task_classifier.py:16-30` returns the structured rule ID and reason; the v1.5 Reality Check explicitly names structured task type as implemented.
- `implementation_location`: `governance/preflight/task_classifier.py`; `schemas/task_request.schema.json`; `tests/unit/test_v1_5_reality_check.py:13-18`.
- `test_or_schema_evidence`: Structured task type test passes and `Classification` contains task level, matched rule IDs and reasons.
- `remaining_gap`: Structured task type is implemented; broader independence from risk semantics is tracked separately under C16.
- `recommended_future_action`: No standalone v1.5.1 action; preserve as the canonical classifier input.
- `priority`: `P0`
- `confidence`: `HIGH`

### Multi-Agent / Closure

#### C22 — multi-agent write overlap / isolation

- `requirement`: Parallel subtasks must not write overlapping scope without ordering, and assigned workspaces must be validated/isolation-aware.
- `original_problem`: 多 Agent 并行写同一路径会产生隐性覆盖；仅声明“不同任务”不足以证明工作区隔离。
- `v1_5_status`: `PARTIALLY_SATISFIED`
- `evidence`: `governance/orchestration/ownership.py:9-20` checks parent/deny scope and exact declared write overlap with serial dependency; `workspace_assignment.py` validates workspace kind and root containment. The v1.5 Reality Check explicitly chooses reuse of orchestration overlap validation.
- `implementation_location`: `governance/orchestration/ownership.py`; `governance/orchestration/workspace_assignment.py`; `schemas/workspace_assignment.schema.json`; `schemas/orchestration_conflict.schema.json`.
- `test_or_schema_evidence`: `tests/unit/test_orchestration_core.py` covers parallel-safe plans and conflict/cycle blocking; P6 acceptance covers required closure gating. The overlap check uses exact set intersection, so a `src/*` versus `src/a.py` glob/concrete collision is not proven; workspace assignment validates declarations but does not create or enforce isolated worktrees.
- `remaining_gap`: Reused overlap validation is present, but complete glob-aware conflict detection and actual workspace isolation are absent.
- `recommended_future_action`: v1.6 P1 — add normalized glob intersection, assignment-to-result binding, and fail-closed handling for shared current workspaces.
- `priority`: `P1`
- `confidence`: `HIGH`

#### C23 — Closure / Multi-Agent interface completion

- `requirement`: Multi-agent aggregation must complete a structured handoff into the existing Verification/Closure interface without creating a second closure evaluator.
- `original_problem`: 多 Agent 结果如果只停留在自然语言汇总，可能绕过 freshness、required-subtask 和 Closure 前置条件。
- `v1_5_status`: `ALREADY_EXISTED_AND_REUSED`
- `evidence`: `governance/orchestration/result_aggregator.py` emits `READY_FOR_VERIFICATION` only when required results/handoffs are valid; `governance/orchestration/closure.py:4-6` gates the existing P3 verifier and required auditor; `verification_builder.py:12-14` blocks when orchestration is not ready. The Reality Check explicitly rejects a duplicate multi-agent orchestrator and reuses existing overlap/closure interfaces.
- `implementation_location`: `governance/orchestration/result_aggregator.py`; `governance/orchestration/closure.py`; `governance/verification/verification_builder.py`; `scripts/agent_aggregate.py`.
- `test_or_schema_evidence`: `tests/integration/test_orchestration_cli_flow.py` exercises plan → validate → handoff → aggregate → verify → close; `tests/integration/test_p6_acceptance_matrix.py` covers required auditor/result gates.
- `remaining_gap`: Interface completion is present for the bounded local P6 contract; C22 tracks the separate limitation in overlap/isolation enforcement.
- `recommended_future_action`: Reuse current P6-to-P3 interface; do not introduce a parallel Closure engine.
- `priority`: `P1`
- `confidence`: `HIGH`

## Additional formal candidates from the v1.5 Reality Check

#### C24 — Test-only provenance isolation

- `requirement`: Tests must be able to exercise adoption provenance against an isolated, deterministic local generator source without changing product provenance semantics.
- `original_problem`: 测试若直接使用工作树 provenance，会受当前 checkout、dirty 状态和路径影响，并可能把测试临时资产误当作产品输入。
- `v1_5_status`: `IMPLEMENTED`
- `evidence`: The v1.5 Reality Check explicitly records test-only provenance isolation as implemented; `tests/__init__.py` creates a temporary Git fixture and redirects test provenance; `tests/agent_adopt_test_launcher.py` passes the fixture source root.
- `implementation_location`: `tests/__init__.py`; `tests/agent_adopt_test_launcher.py`; `governance/adoption/provenance.py:211-239` accepts an explicit source root for the test path.
- `test_or_schema_evidence`: v1.5 Final Manifest includes these test harness paths; adoption/provenance tests cover clean HEAD blob binding, LF/CRLF equivalence, dirty/staged rejection, and isolated generation.
- `remaining_gap`: This is intentionally test-only and does not add an alternate production provenance source.
- `recommended_future_action`: Preserve; do not promote the test fixture override into a production escape hatch.
- `priority`: `P0`
- `confidence`: `HIGH`

#### C25 — Duplicate governance subsystems

- `requirement`: Do not create duplicate lifecycle, evidence registry, workspace baseline, test platform, or multi-agent orchestrator subsystems when an existing owner/module already provides the contract.
- `original_problem`: v1.5 compression could have produced parallel implementations with divergent semantics, duplicated schemas, and competing authorities.
- `v1_5_status`: `NO_LONGER_NEEDED`
- `evidence`: The v1.5 Reality Check explicitly removes duplicate subsystem construction from the scope and the Reuse Matrix maps the capability to existing modules. `docs/GOVERNANCE_RUNTIME_ARCHITECTURE.md:26,156` rejects a duplicate platform and duplicate task-contract meanings; `docs/GOVERNANCE_RUNTIME_MODULE_REGISTRY.yaml` assigns ownership to existing modules.
- `implementation_location`: Existing owners under `governance/workspace/`, `governance/adoption/`, `governance/verification/`, and `governance/orchestration/`; architecture and module registry.
- `test_or_schema_evidence`: Governance baseline validation passes the module registry and 39 schemas; current v1.5 diff adds no parallel subsystem.
- `remaining_gap`: None for this candidate. It is no longer a desired implementation item because the architecture decision is to reuse the existing owners.
- `recommended_future_action`: No action; reject any future proposal that introduces a second owner for these contracts.
- `priority`: `P0`
- `confidence`: `HIGH`

#### C26 — Publication authority

- `requirement`: Release/publication actions must remain outside automatic runtime authority and require an explicit Owner decision.
- `original_problem`: Local readiness evidence could be mistaken for permission to push/tag/release, or a governance runtime could silently acquire publication authority.
- `v1_5_status`: `DEFERRED`
- `evidence`: The v1.5 Reality Check records publication authority as a remaining Owner decision; `docs/GOVERNANCE_RUNTIME_ARCHITECTURE.md:26` excludes publishing automation; the current release is published at the Owner-supplied commit, but no runtime publication authority or automation was added.
- `implementation_location`: Boundary documentation and release reports; no implementation location is claimed.
- `test_or_schema_evidence`: `AGC_V1_5_0_RELEASE_READINESS_20260910.md` documents the pre-publication owner gate; current tag/commit verifies the later publication event. Neither is a runtime authority implementation.
- `remaining_gap`: No automatic release/publish capability exists, intentionally. The only possible future work is an explicitly approved owner-operated publication workflow, which has low marginal benefit for the core runtime.
- `recommended_future_action`: Do not enter v1.5.1; consider v1.6 only if the Owner explicitly wants a separate, least-privilege publication integration.
- `priority`: `P2`
- `confidence`: `HIGH`

## Additional distinct historical candidates from the v1.4 adoption pool

The v1.4 04A candidate table is also reconciled here. Its `adopt --dry-run planner`, project scanner, test-entry candidate finder, preset recommender, configuration draft generator, post-adoption health check, and rollback checklist are not counted as new rows because they are sub-capabilities of C01/C07/C08/C09/C11/C14 and the current `governance.adoption.planner` composition. The following three 04A candidates are distinct and therefore counted.

#### C27 — Broad adoption asset copier

- `requirement`: After reviewed adoption planning, a bounded mechanism could copy approved governance assets into an existing project.
- `original_problem`: Manual copying is slow and omission-prone, but broad copying risks overwriting user-owned files, crossing project scope, or silently changing runtime semantics.
- `v1_5_status`: `DEFERRED`
- `evidence`: v1.4 04A placed Asset copier at P2 and required a reviewed manifest; current `docs/EXISTING_PROJECT_ADOPTION.md:30-37,83-100` keeps manual ownership review and only permits exact approved Runtime installation. `governance/adoption/installer.py` installs a narrow two-file Runtime writeset, not a broad asset copier.
- `implementation_location`: No broad copier; bounded alternative at `governance/adoption/installer.py` and `governance/adoption/writeset.py`.
- `test_or_schema_evidence`: Installer tests cover exact writeset, conflicts, provenance and manual rollback assessment; no broad-copy contract exists.
- `remaining_gap`: The broad copier remains intentionally absent. Its benefit is mostly convenience, while ownership/overwrite risk is material.
- `recommended_future_action`: Do not enter v1.5.1; v1.6 only after evidence of repeated manual-copy demand and a separate fail-closed writeset design.
- `priority`: `P2`
- `confidence`: `HIGH`

#### C28 — Interactive adoption wizard

- `requirement`: A guided wizard could reduce adoption UX friction after the read-only planner is proven.
- `original_problem`: Existing adoption required many manual decisions and had no guided flow, but a wizard can conceal risk choices and turn recommendations into accidental authorization.
- `v1_5_status`: `DEFERRED`
- `evidence`: v1.4 04A placed Interactive wizard at P2; `scripts/init_new_project.py` is a new-project wizard only, while `docs/EXISTING_PROJECT_ADOPTION.md:5-7,37` explicitly keeps adoption bounded and separate.
- `implementation_location`: No adoption wizard; existing new-project initializer remains `scripts/init_new_project.py`.
- `test_or_schema_evidence`: Initializer tests cover new-project preset/overwrite invariants; adoption CLI tests cover explicit subcommands, not an interactive adoption flow.
- `remaining_gap`: No guided adoption UX exists, intentionally; current planner and explicit confirmations are the safer minimum.
- `recommended_future_action`: Do not enter v1.5.1; v1.6 only after planner usability evidence and an explicit non-authorizing wizard contract.
- `priority`: `P2`
- `confidence`: `HIGH`

#### C29 — Separate `adopt --plan-only` command

- `requirement`: Provide a plan-only adoption command only if it is semantically distinct from dry-run.
- `original_problem`: Multiple names for the same read-only planner would fragment documentation and create command-surface ambiguity.
- `v1_5_status`: `NO_LONGER_NEEDED`
- `evidence`: v1.4 04A explicitly says a separate `adopt --plan-only` is redundant if it only renames dry-run; current `scripts/agent_adopt.py` exposes `dry-run` as the planner mode and current adoption docs say it is the only planner mode.
- `implementation_location`: `scripts/agent_adopt.py`; `docs/EXISTING_PROJECT_ADOPTION.md:16-37`.
- `test_or_schema_evidence`: Current command registry/help tests enumerate the actual subcommands and do not include `plan-only`; the documented dry-run path is covered by adoption tests.
- `remaining_gap`: None. The architecture has one planner spelling and one canonical entry.
- `recommended_future_action`: No action; retain `dry-run` and reject a duplicate alias unless semantics materially diverge.
- `priority`: `P2`
- `confidence`: `HIGH`

## Historical candidate-pool mapping

| v1.4 04A candidate | Coverage row | Reason not counted twice |
|---|---|---|
| `adopt --dry-run planner` | C07 | Same canonical adoption entry. |
| Project scanner | C07 | Current planner composes adapter detection and the existing audit. |
| Test-entry candidate finder | C01/C07 | C01 covers task-relevant TestPlan semantics; C07 covers adoption candidate discovery. |
| Preset recommender | C07 | Current planner reuses the existing audit recommendation and labels it as requiring confirmation. |
| Configuration draft generator | C07/C08 | Current planner/exporter emits untrusted drafts and binds them to provenance/evidence. |
| Post-adoption health check | C11/C14 | Existing audit, workspace health, and adoption freshness cover the bounded behavior; generic closure gap remains in C14. |
| Rollback checklist | C07 | Current adoption planner emits a review-only rollback checklist; no broad copier is implied. |
| Asset copier | C27 | Distinct broad-write candidate; bounded installer is not counted as broad copier completion. |
| Interactive wizard | C28 | Distinct adoption UX candidate; new-project initializer is not counted as adoption wizard. |
| `adopt --plan-only` | C29 | Explicitly redundant with `dry-run`. |

## Counts

| Status | Count |
|---|---:|
| `IMPLEMENTED` | 4 |
| `ALREADY_EXISTED_AND_REUSED` | 6 |
| `PARTIALLY_SATISFIED` | 13 |
| `DEFERRED` | 3 |
| `NOT_IMPLEMENTED` | 1 |
| `NO_LONGER_NEEDED` | 2 |
| **Total audited rows** | **29** |

## Conclusions

### A. `V1_5_FROZEN_SCOPE_COMPLETION`

`NO`

The frozen v1.5 intent is not fully complete in the current release artifact. The core v1.5 additions exist in code and formal evidence, but at least the public TestPlan and VerificationResult persistence paths contradict their schemas, and the combined TaskContract supersession/stage-transition requirement lacks the stage-transition half. These are requirement-coverage failures, not release-gate failures.

### B. `PRE_V1_5_FULL_DISCUSSION_COVERAGE`

`NO`

The pre-v1.5 discussion pool is not fully implemented. Workspace delta projection is absent; workspace hygiene, attribution, generic Closure readiness, Owner gate integration, execution-form/risk separation, Windows/sandbox diagnostics, legacy compatibility breadth, and multi-agent isolation remain partial; publication authority, broad asset copying, and an adoption wizard are deferred. Duplicate subsystem construction and a separate plan-only command are correctly no longer needed.

## NEXT_VERSION_CANDIDATE_LIST

Only `PARTIALLY_SATISFIED`, `DEFERRED`, and `NOT_IMPLEMENTED` rows are included below, ordered by priority.

### P0 — v1.5.1 recommended

| Row | Candidate | Status | v1.5.1 / v1.6 recommendation |
|---|---|---|---|
| C01 | TestPlan runtime/schema parity and public persistence coverage | `PARTIALLY_SATISFIED` | Worth v1.5.1; it blocks the intended task-relevant plan from the actual save path. |
| C02 | Failure-isolation result normalization and schema parity | `PARTIALLY_SATISFIED` | Worth v1.5.1; current verification persistence rejects runner-shaped evidence. |
| C05 | TaskContract stage-transition contract | `PARTIALLY_SATISFIED` | Worth v1.5.1 if stage transition is part of the frozen scope; otherwise make the split an explicit v1.6 decision. |
| C06 | Generic Closure Window wired to autonomous recovery boundary | `PARTIALLY_SATISFIED` | Worth v1.5.1 for ordinary-task correctness. |
| C09 | Task relevance carried into compact Closure evidence | `PARTIALLY_SATISFIED` | Worth v1.5.1 together with C01/C02. |
| C15 | Minimum Owner Gate integration | `PARTIALLY_SATISFIED` | Worth v1.5.1 for consistent high-risk authorization semantics. |
| C16 | Independent execution-form, risk-kind, and governance-level semantics | `PARTIALLY_SATISFIED` | Worth v1.5.1 because it controls classification safety. |

### P1 — v1.6 recommended, with C14 possibly pulled into v1.5.1

| Row | Candidate | Status | v1.5.1 / v1.6 recommendation |
|---|---|---|---|
| C10 | Workspace Delta Projection | `NOT_IMPLEMENTED` | v1.6; it needs a deliberate path-level projection design. |
| C12 | Repository Hygiene Audit | `PARTIALLY_SATISFIED` | v1.6 with C10/C13. |
| C13 | Pre-existing/task-created workspace attribution | `PARTIALLY_SATISFIED` | v1.6 with C10; no safe standalone implementation should be added ad hoc. |
| C14 | Dirty-workspace escalation into generic Closure readiness | `PARTIALLY_SATISFIED` | Pull into v1.5.1 if generic Closure remains a supported public path; otherwise v1.6. |
| C19 | Windows / Codex Sandbox diagnostic categories | `PARTIALLY_SATISFIED` | v1.6 after fixture-backed environment diagnostics are scoped. |
| C20 | Legacy initializer compatibility matrix | `PARTIALLY_SATISFIED` | v1.6 only if real compatibility demand exists. |
| C22 | Glob-aware multi-agent overlap and workspace isolation | `PARTIALLY_SATISFIED` | v1.6; current P6 interface is usable but isolation is incomplete. |

### P2 — defer beyond v1.5.1

| Row | Candidate | Status | v1.5.1 / v1.6 recommendation |
|---|---|---|---|
| C26 | Publication authority / optional publication integration | `DEFERRED` | Do not enter v1.5.1; v1.6 only with explicit Owner authorization and separate least-privilege scope. |
| C27 | Broad adoption asset copier | `DEFERRED` | Do not enter v1.5.1; v1.6 only after demonstrated demand and a new writeset contract. |
| C28 | Interactive adoption wizard | `DEFERRED` | Do not enter v1.5.1; v1.6 only after planner UX evidence and a non-authorizing design. |

## Audit stop state

- Existing release commit, tag, and formal assets were not modified.
- No code, schema, test, Git history, or remote state was modified.
- The requested audit report is the only task-created artifact.
- Stop after report creation as requested.
