# AGC v1.5.2 P0 Existing Project Adoption Recovery Implementation Report

Date: 2026-09-12

## 1. SCOPE_MATCH_CHECK

- Mode / level: `EXECUTION`, C class, Level 2 bounded continuous execution.
- Frozen P0 implemented: lifecycle viability, activated recovery/rebinding, public adoption preflight, controlled `v1.5.1 → v1.5.2` framework upgrade.
- No Workspace/Hygiene/Multi-Agent, generic stage manager, package manager, broad copier, second lifecycle/evidence registry/approval store, Provider/API, or publication work was added.
- The indexed `agent_rules/11_project_specific_rules.md` is absent; the existing template was inspected and the absence was not repaired because it is outside P0.

## 2. BASELINE_IDENTITY

- Repository: `/home/liyouran1997/projects/ai-agent-project-governance`
- Branch: `main`
- Baseline tag/version: `v1.5.1` / `1.5.1`
- Baseline HEAD: `3e9a01fe40435fdb1bd3bff3181f1cd5dcb9da26`
- Initial worktree: only pre-existing untracked `.agent-reports/`; preserved.
- Local closure version: `1.5.2`; no tag or release created.

## 3. P0_SCOPE_IMPLEMENTED

1. Adoption-only cross-stage viability diagnostic and enforcement.
2. Exact-byte successor compilation, fresh exact Owner approval, two-file recovery writeset, replay/drift guards, recovery evidence, and rollback-on-partial-write behavior.
3. Canonical `adoption-preflight` command and stable generic-preflight redirect.
4. Fixed `v1.5.1 → v1.5.2` changed-only upgrade preview/approval/install, baseline-byte conflict detection, preservation checks, and receipt.

## 4. FILES_CHANGED_SUMMARY

- Runtime: `governance/adoption/{contract_viability,recovery,framework_upgrade}.py`, planner/compiler/installer/activation integration, `governance/cli.py`.
- Public CLI: `scripts/agent_adopt.py`.
- Schemas: adoption plan/lifecycle evidence plus recovery and upgrade manifest/approval contracts.
- Tests/fixtures: focused P0 fixture, existing adoption fixture scope updates, schema baseline/count updates.
- Trace/docs: `VERSION`, changelog, adoption guide, module registry, task registry, this report.

## 5. P0_1_VIABILITY_GATE

- Output fields: `viable`, `required_write_scope`, `missing_write_scope`, `reason_codes`.
- Stable failures: `ZERO_WRITE_FULL_ADOPTION_UNSUPPORTED` and `ADOPTION_LIFECYCLE_WRITE_SCOPE_INSUFFICIENT`.
- Planner diagnoses; compile, install, and activation fail closed.
- No scope is added automatically. Generic contracts remain schema-valid zero-write; only the full adoption lifecycle invokes this gate.

## 6. P0_2_RECOVERY_REBINDING

- Supported state is exactly `ACTIVATED_NOT_PREFLIGHTED`.
- Candidate binds target identity, old TaskContract/ProjectState bytes, installation/activation receipt digests, successor bytes, scope delta, upstream evidence, and exact writeset.
- Approval is explicit, manifest-bound, target-bound, writeset/scope-delta-bound, and expires.
- Recovery reuses TaskContract supersession vocabulary, preserves ProjectState history, appends recovery evidence, rejects replay/external mutation, and restores both Runtime files after a partial failure.

## 7. P0_3_PREFLIGHT_PUBLIC_ENTRY

- `scripts/agent_adopt.py adoption-preflight` reconstructs the existing lifecycle context, calls the existing formal preflight bridge, writes registered evidence, and performs the existing CAS transition to `PREFLIGHT_PASSED`.
- Generic preflight returns `USE_ADOPTION_LIFECYCLE_BRIDGE` for activated adoption contracts; it cannot bypass lifecycle evidence.

## 8. P0_4_CONTROLLED_UPGRADE

- Eligibility is fixed to source `VERSION=1.5.2` and baseline commit `3e9a01fe40435fdb1bd3bff3181f1cd5dcb9da26` (`v1.5.1`).
- Discovery compares source bytes with baseline Git blobs and target bytes; unknown target drift fails closed.
- Writes are limited to changed `VERSION`, `governance/`, `schemas/`, and `scripts/` assets.
- `task.yaml` and `project_state.yaml` are excluded and digest-checked for preservation. Approval binds the exact writeset; install emits an external receipt and rolls back bounded writes after failure.

## 9. EVIDENCE_AND_PROVENANCE

- Existing installation and activation receipts remain authority inputs; their digest chain is revalidated before recovery compilation.
- Old task identity/digest and ProjectState lifecycle evidence are preserved.
- Recovery evidence joins the existing ProjectState evidence history; formal preflight derives its upstream chain from persisted evidence.
- Upgrade receipt links baseline/new versions, manifest, approval, target identity, installed files, and preserved Runtime digests.
- No digest was manually injected into a real Runtime.

## 10. JINGWEI_COMPATIBILITY_REHEARSAL

- Target reads only: `/home/liyouran1997/projects/jingwei/task.yaml` and `project_state.yaml`.
- Schema compatibility: PASS.
- Current state: `ACTIVATED_NOT_PREFLIGHTED`; TaskContract remains zero-write.
- Current digests: task `85801ed810373f708b7380c5234dc634da75cbbb109c9e55d52254c200a8c79b`; state `42168d9c83b928b9b86b5395ff0984f1251c2966c4d5220d008feb52f3af6ddf`.
- Installation-to-activation receipt chain: PASS; both receipts bind the same current task digest.
- External `/tmp` recovery preview: PASS; writeset exactly `task.yaml,project_state.yaml`, scope delta exactly `project_state.yaml`, manifest digest `b33779e38a7186224f8c01eeb11dc61d2731d8137112409125f2ffa093da1df5`.
- No approval was created and no Jingwei Runtime byte was changed. Real recovery remains an Owner-controlled later action.

## 11. TEST_COMMANDS_AND_RESULTS

All commands ran from the repository root with `PYTHONDONTWRITEBYTECODE=1` where shown; no network marker or dependency download was used.

1. `python3 -m unittest tests.unit.test_v1_5_2_p0 tests.integration.test_agent_preflight_cli` — exit 0, 7 tests, OK.
2. `python3 -m unittest tests.unit.test_agent_adopt tests.unit.test_agent_adopt_export tests.unit.test_agent_adopt_install tests.unit.test_agent_adopt_activation tests.unit.test_adoption_lifecycle_foundation tests.unit.test_adoption_remediation_security tests.unit.test_public_adoption_assets tests.unit.test_v1_5_1_contract_parity tests.unit.test_v1_5_1_owner_gate tests.unit.test_v1_5_1_semantic_axes tests.unit.test_v1_5_2_p0` — exit 0, 65 tests, OK.
3. `python3 -m unittest tests.unit.test_case001_minimum_unblock tests.integration.test_agent_preflight_cli` — exit 0, 13 tests, OK after updating the full-adoption fixture to include ProjectState scope.
4. `python3 scripts/validate_governance.py` — exit 0, 43 schemas, PASS.
5. `python3 scripts/check_schema_compatibility.py` — exit 0, 43 schemas, PASS.
6. `python3 -m unittest tests.unit.test_schema_contracts tests.integration.test_architecture_baseline tests.contracts.test_p5_schema_compatibility` — exit 0, 12 tests, OK.
7. `python3 scripts/run_governance_ci.py` — exit 0, canonical gate PASS 8/8; full test discovery passed.
8. `python3 scripts/check_code_quality.py` — exit 0 with one soft warning: existing `build_parser` is now 90 lines.
9. `git diff --check` — exit 0.

The first canonical-gate attempt correctly failed after adding four schemas because schema count/compatibility fixtures still represented v1.5.1. Those local test-governance assets were updated, focused schema tests passed, then the canonical gate passed. No failing result was hidden.

## 12. REQUIREMENT_COVERAGE_MATRIX

| P0 requirement | Implementation / schema / public entry | Positive and negative evidence |
| --- | --- | --- |
| Lifecycle viability | `contract_viability.py`; planner/compiler/installer/activation; adoption-plan diagnostic | zero-write and wrong-path block; ProjectState scope passes; affected adoption regression passes |
| Activated recovery | `recovery.py`; recovery manifest/approval schemas; three CLI commands | local activation→recovery fixture; stale approval, replay/external mutation, exact approval/writeset/evidence/state guards |
| Formal preflight | existing lifecycle context/registry/transition; `adoption-preflight`; generic redirect | recovered Runtime reaches `PREFLIGHT_PASSED`; generic misuse test passes |
| Controlled upgrade | `framework_upgrade.py`; upgrade manifest/approval schemas; three CLI commands | changed-only synthetic install, Runtime preservation, replay/drift rejection, receipt |
| Compatibility | baseline Git blob comparison; stable existing schemas/enums | schema compatibility and 65-test affected regression pass |
| Lifecycle continuation | existing evidence registry and CAS transition | restart-style context reconstruction after recovery and preflight transition pass |

## 13. P1_MINIMUM_PROMOTIONS

- `P1_MINIMUM_PROMOTED_FOR_P0_SAFETY`: upgrade manifest records only the source baseline commit/version, changed asset byte identities, target identity, exact writeset, and preserved Runtime paths. No general inventory platform was introduced.

## 14. UNRESOLVED_GAPS

- Real Jingwei recovery/upgrade remains intentionally unexecuted and requires a separate exact Owner approval.
- Code-quality gate reports one soft function-length warning for `scripts/agent_adopt.py::build_parser`; canonical quality gate still passes. Refactoring was not expanded into P0.
- The missing root project-specific rules file remains outside P0.

## 15. STOP_CONDITIONS_TRIGGERED

- None during local framework implementation or read-only Jingwei compatibility rehearsal.
- The contingency “real Jingwei Runtime write required” did not occur because compatibility was established by exact preview; no formal target write was attempted.

## 16. FINAL_IMPLEMENTATION_STATUS

`ADOPTION_ACTIVATED_RUNTIME_RECOVERY_READY`

All four frozen P0 capabilities, local recovery/upgrade fixtures, schema compatibility, affected regression, full canonical gate, and read-only Jingwei compatibility preview pass. This status describes local implementation readiness, not authorization to mutate Jingwei or publish v1.5.2.

## 17. GIT_STATUS

- Worktree contains only uncommitted implementation/report changes plus the pre-existing audit report under `.agent-reports/`.
- No commit, reset, clean, rebase, push, PR, tag, or release was performed.

## 18. RELEASE_NOT_AUTHORIZED

`RELEASE_NOT_AUTHORIZED`

Stop after this report and wait for the 卫兵 main-thread acceptance.
