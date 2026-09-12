# AGC v1.5.2 Local Git Closure Candidate Report

Date: 2026-09-12

## Status

`V1_5_2_LOCAL_CLOSURE_CANDIDATE_READY`

The local P0 implementation boundary, version identity, required targeted and compatibility checks, canonical governance gate, and whitespace check all pass. This is local Git-closure readiness only. It does not authorize a commit, push, PR, tag, release, network access, Provider/API use, or any Jingwei action.

## Repository Identity

- Repository: `/home/liyouran1997/projects/ai-agent-project-governance`
- Branch: `main`
- Current and baseline HEAD: `3e9a01fe40435fdb1bd3bff3181f1cd5dcb9da26`
- VERSION: `1.5.2`
- Index: clean; all candidate changes remain unstaged.
- Worktree: primary worktree plus existing sibling worktrees; no worktree was created, moved, or modified by this closure prep.

## Exact Changed-File Inventory

### Proposed v1.5.2 candidate (28 paths)

```text
VERSION
docs/CHANGELOG.md
docs/EXISTING_PROJECT_ADOPTION.md
docs/GOVERNANCE_RUNTIME_MODULE_REGISTRY.yaml
docs/TASK_REGISTRY.yaml
governance/adoption/activation.py
governance/adoption/contract_viability.py
governance/adoption/framework_upgrade.py
governance/adoption/installer.py
governance/adoption/planner.py
governance/adoption/recovery.py
governance/adoption/runtime_artifact_compiler.py
governance/cli.py
schemas/adoption_lifecycle_evidence.schema.json
schemas/adoption_plan.schema.json
schemas/adoption_recovery_approval.schema.json
schemas/adoption_recovery_manifest.schema.json
schemas/framework_upgrade_approval.schema.json
schemas/framework_upgrade_manifest.schema.json
scripts/agent_adopt.py
scripts/validate_governance.py
tests/fixtures/compatibility/schema_baseline.json
tests/unit/adoption_flow.py
tests/unit/test_case001_minimum_unblock.py
tests/unit/test_schema_contracts.py
tests/unit/test_v1_5_2_p0.py
.agent-reports/AGC_V1_5_2_P0_EXISTING_PROJECT_ADOPTION_RECOVERY_IMPLEMENTATION_REPORT_V1_20260912.md
.agent-reports/AGC_V1_5_2_LOCAL_CLOSURE_CANDIDATE_REPORT_V1_20260912.md
```

### Explicitly preserved and excluded from the candidate

```text
.agent-reports/AGC_EXISTING_PROJECT_ADOPTION_REAL_WORLD_DEPLOYMENT_FAILURE_AUDIT_V1_20260912.md
.agent-reports/AGC_V1_5_2_JINGWEI_REAL_RECOVERY_PREPARATION_REPORT_V1_20260912.md
.agent-reports/AGC_V1_5_2_JINGWEI_RECOVERY_PROVENANCE_BLOCKER_DECISION_DELTA_V1_20260912.md
.agent-reports/AGC_V1_5_2_TO_JINGWEI_REAL_RECOVERY_PREP_HANDOFF_V1_20260912.md
```

The excluded Jingwei artifacts remain unmodified. Recovery is stopped with `ORIGINAL_RECEIPT_EVIDENCE_NOT_RECOVERED`; no receipt was reconstructed.

## Required Validation

All commands ran from the repository root, using local fixtures only and `PYTHONDONTWRITEBYTECODE=1` where applicable.

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.unit.test_v1_5_2_p0 tests.integration.test_agent_preflight_cli` | PASS; 7 tests |
| affected adoption regression (11 named unit modules, including P0) | PASS; 66 tests |
| `python3 scripts/check_schema_compatibility.py` | PASS; 43 schemas, stable fields/enums |
| `python3 scripts/run_governance_ci.py` | PASS; terminal exit 0, 8/8 gates; test gate 57.2 seconds |
| `git diff --check` | PASS; exit 0, no output |

## Warnings and Boundaries

- The canonical quality gate passed with the existing soft warning that `scripts/agent_adopt.py::build_parser` is 90 lines; no out-of-scope refactor was made.
- `README.md` still displays a `1.3.0` badge while `VERSION` is `1.5.2`. This pre-existing version-presentation mismatch is not part of frozen P0 scope and was not changed.
- The indexed project-specific rule file is absent; only `agent_rules/11_project_specific_rules.template.md` exists. It was not created during this bounded closure task.
- No commit, push, PR, tag, release, reset, clean, rebase, force operation, network access, Provider/API operation, or Jingwei modification occurred.

## Commit Candidate

- Proposed commit message: `fix(adoption): add activated runtime recovery and controlled v1.5.2 upgrade`
- Commit executed: **No**.
- Authorization status: wait for explicit Owner authorization before any Git write.

## Closure Conclusion

`V1_5_2_LOCAL_CLOSURE_CANDIDATE_READY`

Stop here and await Owner authorization.
