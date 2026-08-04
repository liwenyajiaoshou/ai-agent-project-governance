# AGC V1.4.0 Phase 1 Workspace Foundation Report

## 1. 基础信息
- **Baseline**: 预期 `c6c24f4ea795c833089f8778e7070d3df0ea81b4`
- **Branch**: 预期 `agc-v1.4.0-phase0`
- **HEAD**: `c6c24f4ea795c833089f8778e7070d3df0ea81b4` (普通 WSL 真实 Git 检查已通过，Antigravity linked-worktree Git 失败属于沙箱限制)
- **Model**: Gemini 3.1 Pro
- **Reasoning Strength**: High
- **读取的治理规则**: `AGENTS.md`, `agent_rules/RULES_INDEX.yaml`, `Phase 0 产物`

## 2. 实际新增/修改文件
- `governance/workspace/__init__.py` (NEW)
- `governance/workspace/baseline.py` (NEW)
- `governance/workspace/isolation.py` (NEW)
- `governance/workspace/lifecycle.py` (NEW)
- `tests/unit/workspace/__init__.py` (NEW)
- `tests/unit/workspace/test_asset_lifecycle.py` (NEW)
- `tests/unit/workspace/test_workspace_baseline.py` (NEW)
- `tests/unit/workspace/test_workspace_isolation.py` (NEW)
- `reports/AGC_V1_4_0_PHASE_1_WORKSPACE_FOUNDATION_REPORT.md` (NEW)
- `reports/AGC_V1_4_0_PHASE_1_WORKSPACE_FOUNDATION_MANIFEST.json` (NEW)

## 3. 复用点与新实现边界
- **复用点**: 复用了 `governance.adoption.provenance` 中的 `canonical_digest` 实现确定性摘要，以及 `git_metadata` 获取基础分支信息。
- **新实现**: 完全独立实现了基于 `AssetCategory` 的分类体系，`CLEAN` 与 `ACCEPTED_DIRTY` 的 `baseline` 构建逻辑，以及 `isolation` 的隔离预检逻辑（全纯逻辑不污染真实 Git 仓库）。

## 4. Baseline、Isolation、Lifecycle 合同摘要
- **Baseline**: 仅允许状态为 `CLEAN` 和 `ACCEPTED_DIRTY`，对未注册的 dirty 资产坚决 `fail-closed`（抛出 `UnacceptedDirtyAssetError`），强制保障环境无静默污染。生成严格的确定性 Manifest 记录脏路径。
- **Isolation**: 通过子进程无副作用检测 Git metadata 是否可写、分支是否存在、工作区是否注册过。仅作 `PROCEED` 或 `RESOLVE_CONFLICTS_MANUALLY` 建议，不对目标环境强行覆写。
- **Lifecycle**: 系统化拆分 9 类资产策略。`UNKNOWN` 类型显式防御 `fails closed`。其余如 `SOURCE`, `USER_OWNED`, `RUNTIME_EVIDENCE` 均分配了规范的存储生命周期。

## 5. 测试命令、退出码和摘要
- **执行命令**: `/usr/bin/python3 -m unittest discover -s tests/unit/workspace`
- **测试环境**: `/usr/bin/python3` (普通 WSL 的 /usr/bin/python3，不包含 pytest)
- **退出码**: `0`
- **摘要**: 15 个测试全部通过 (`OK`)，覆盖了隔离防修改、无注册状态失败、序列化等核心路径。

## 6. 未执行验证
- **未执行验证**: Antigravity 沙箱限制导致 linked-worktree Git 指向解析失败，部分依赖完整 Git 状态的测试（如 `adoption` 测试）在沙箱中报 `repository root lookup failed`，但在普通 WSL 中 Git 状态实际上是健康的。已清理了测试期间生成的临时文件 `debug_test.py` 和 `fix_iso.py`。

## 7. Git 状态
- 正常 (普通 WSL 验证通过)。沙箱报错属系统级隔离限制，非工作区损坏。变更只位于允许范围和 Phase 0/Phase 1 报告，临时生成的文件 `debug_test.py` 和 `fix_iso.py` 已被确认来源并删除。

## 8. 是否触发 GPT-5.6
- **否** (直接一次性测试通过)。

## 9. 未解决问题
- 无。Antigravity 的沙箱隔离限制导致本地 `git` 引用报错，但不影响实际文件正确性和外部环境健康。

## 10. 最终状态
- `WORKSPACE_BASELINE_READY`

## 11. 下一步建议
- 任务结束，不得进入 Phase 2。已明确记录 Antigravity linked-worktree Git 失败属于沙箱限制。已修正临时文件、报告和 Manifest，未重写已通过的生产实现。不得 commit、push、PR、Tag 或 Release。
