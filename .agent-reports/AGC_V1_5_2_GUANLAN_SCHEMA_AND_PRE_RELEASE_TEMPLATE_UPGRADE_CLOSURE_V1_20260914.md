# AGC v1.5.2 观澜 Schema 与 Pre-release Template Upgrade 收口 V1

日期：2026-09-14
任务：`AGC-V1.5.2-GUANLAN-SCHEMA-PRE-RELEASE-TEMPLATE-UPGRADE`
基线：`6743aa454440ff67e16386651cb5f7a766c5928a`

## 完成内容

- 将 governance schema 基线从 43 对齐到 45，并登记 Durable Evidence object/reference contracts。
- 新增专用 `PRE_RELEASE_GENERATED_TEMPLATE_UPGRADE`：它只处理 `scripts/validate_governance.py` 与 `tests/fixtures/compatibility/schema_baseline.json` 两个已知 v1.5.2 pre-fix generated-template 文件。
- Preview、Owner-bound Approval、零写入 Preflight、Execute 与 machine-readable receipt 均绑定：目标/来源版本 `1.5.2`、`6743aa4` source baseline commit、baseline digest、每项 expected-old hash、changed-only writeset。
- 任何未知目标 drift 均以 `UPGRADE_UNKNOWN_LOCAL_DRIFT` 在写入前整体停止；已是当前内容时生成空 writeset 的 NO_OP receipt。

这不是通用 same-version source-overwrites-target 能力。

## Remote normalization

`origin` 已从 redirect 旧地址改为：

`https://github.com/liwenyajiaoshou/ai-agent-project-governance.git`

只读回查的 live `origin/main`：

`6743aa454440ff67e16386651cb5f7a766c5928a`

未执行 fetch、pull、reset、rebase、push、tag 或 GitHub Release。

## Dirty attribution

开始时仅有两项 tracked 修改，且无额外 tracked drift：

- `scripts/validate_governance.py`：预期 schema 数及 PASS 文案 `43 → 45`。
- `tests/fixtures/compatibility/schema_baseline.json`：加入两项 Durable Evidence schema baseline。

## Report attribution

保留为 `CURRENT_V1_5_2_EVIDENCE`：

- `AGC_P1_PHASE1_EVIDENCE_STORE_CORE_IMPLEMENTATION_REPORT_V1_20260912.md`
- `AGC_P1_PHASE2_EVIDENCE_STORE_INTEGRATION_DESIGN_DECISION_REPORT_V1_20260912.md`
- `AGC_P1_PHASE2A_EVIDENCE_RESOLVER_IMPLEMENTATION_REPORT_V1_20260912.md`
- `AGC_P1_PHASE2B_LIFECYCLE_ADAPTER_DESIGN_DECISION_REPORT_V1_20260912.md`
- `AGC_P1_PHASE2B1_LIFECYCLE_ADAPTER_CONTRACTS_IMPLEMENTATION_REPORT_V1_20260912.md`
- `AGC_P1_PHASE2B2_LIFECYCLE_CONSUMER_INTEGRATION_DESIGN_DECISION_REPORT_V1_20260912.md`
- `AGC_P1_PHASE2B2_LIFECYCLE_CONSUMER_INTEGRATION_IMPLEMENTATION_REPORT_V1_20260912.md`

标注为 `HISTORICAL_ALREADY_SUPERSEDED`（仅归因，不删除）：

- `AGC_EXISTING_PROJECT_ADOPTION_REAL_WORLD_DEPLOYMENT_FAILURE_AUDIT_V1_20260912.md`
- `AGC_P1_DURABLE_EVIDENCE_RETENTION_DESIGN_DECISION_REPORT_V1_20260912.md`
- `AGC_P1_DURABLE_EVIDENCE_RETENTION_IMPLEMENTATION_PLAN_V1_20260912.md`
- `AGC_P1_DURABLE_EVIDENCE_RETENTION_OWNER_DECISION_DELTA_V1_20260912.md`
- `AGC_V1_5_2_GIT_RELEASE_CLOSURE_REPORT_V1_20260912.md`
- `AGC_V1_5_2_JINGWEI_REAL_RECOVERY_PREPARATION_REPORT_V1_20260912.md`
- `AGC_V1_5_2_JINGWEI_RECOVERY_PROVENANCE_BLOCKER_DECISION_DELTA_V1_20260912.md`
- `AGC_V1_5_2_TO_JINGWEI_REAL_RECOVERY_PREP_HANDOFF_V1_20260912.md`

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_governance.py` — PASS, 45 schemas.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_schema_compatibility.py` — PASS, 45 schemas.
- Affected Durable Evidence / Existing Project Adoption suite — PASS, 55 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_governance_ci.py` — PASS, 8/8 gates; its tests gate passed in 60.3 seconds.
- `git diff --check` — PASS.

## Limits

- No target Runtime, production data, external API, Git remote content, tag, or release was written.
- The quality gate reports the pre-existing soft warning that `scripts/agent_adopt.py::build_parser` is 98 lines; the canonical gate classifies it as PASS with warnings.
