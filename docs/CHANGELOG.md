# Changelog

## [1.3.0] - 2026-08-03

### Added

- Optional Context Handoff extension with a current project state view, multi-task document index, and a new-thread handoff entry.
- Safe preview, enable, disable, and uninstall lifecycle commands for Context Handoff.

### Compatibility

- Core-only behavior remains unchanged.
- Context Handoff is disabled by default.

## Unreleased

### Added

- Added the v1.5.2 Existing Project Adoption recovery patch: lifecycle viability checks before compile/install/activation, exact approved recovery for `ACTIVATED_NOT_PREFLIGHTED`, a canonical adoption-preflight command, and a bounded changed-only `v1.5.1 → v1.5.2` framework upgrade.

### Security

- Recovery and upgrade remain local-only, approval-bound, digest-bound, state-limited, and fail closed on drift; neither path authorizes business-data writes, network access, Git writes, or release operations.

## [1.5.1] - 2026-09-10

### Changed

- Finalized TestPlan runtime/schema/public-persistence parity and VerificationResult canonical normalization/schema parity.
- Added compact task-relevant Closure evidence; separated `task_type`, `risk_kinds`, and `governance_level`; wired the ordinary Owner Gate / SideEffectGate and Closure Window / Autonomous Repair Boundary.
- Corrected C05 requirement definition: no ordinary TaskContract stage model was added.

## [1.4.0] - 2026-08-04

### Added

- Added Phase 1: Workspace Foundation with workspace isolation and baseline snapshotting.
- Added Phase 2: Runtime & Manifest Foundation with environment bundles and evidence manifests.
- Added Phase 3: Authorization & Autonomy with side-effect gates and autonomous remediation budgets.
- Added Phase 4: Context Handoff integration ensuring `extensions/context-handoff` compatibility with the new schemas.
- Added Phase 5: CI and syntax validations including extension directories and schema compatibilities.


- Added a provenance-bound adoption lifecycle foundation: formal Preflight bridging, CAS ProjectState transitions, confirmed-candidate test selection, workspace snapshots, fresh-evidence verification, and non-production closure semantics.

- Added provenance-bound `activate-approved` for Existing Project Adoption. It can only transition an installed Runtime to `ACTIVATED_NOT_PREFLIGHTED`; it does not run Preflight, tests, verification, closure, network, Git, or production operations.

- Added public-facing README files, Quickstart, adoption and demo guides, examples, community files, Issue/PR templates, compatibility evidence, and repository-settings checklist for GOV-OSS-GROWTH-01.

- Added P2 local-state, approval-freshness, Guard baseline and acceptance tests; approval-to-Guard enforcement remains incomplete.
- Added deterministic TaskRequest/ProjectState to TaskContract Preflight models, CLI, fixtures, and tests; persistence, guards, test execution, and automatic closure remain unimplemented.
- Added the governance runtime target architecture, module registry, core Schema contracts, baseline validator, and baseline tests. Runtime behavior remains disabled in P0.
- 鍦?`agent_rules/14_cost_aware_testing_rules.md` 澧炲姞 Token-Efficient Execution Contract锛岃鐩?Gate 0銆佺‘璁ゅ鐢ㄣ€佹渶灏忚鍙栥€佽祫浜у鐢ㄣ€佸垎灞傛祴璇曘€佸浠芥椂鏈恒€侀樆濉?checkpoint銆佽緭鍑哄帇缂╁拰鎶ュ憡鍘嬬缉銆?
- 鍦?`agent_rules/RULES_INDEX.yaml` 澧炲姞 token-efficient execution 鍚堝悓鍏ュ彛锛屾槑纭Е鍙戞潯浠跺拰 Gate 0 鍓嶇疆浜嬮」銆?

### Changed

- 鏇存柊 `agent_rules/00_rule_router.md` 鍜?`AGENTS.md`锛屽皢楂樻垚鏈€佽仈缃戙€佹寮忓啓鍏ャ€佷笉鍙€嗘搷浣滅瓑浠诲姟鐨勪汉宸ュ墠缃棬鍓嶇Щ鍒版墿灞曡鍙栧拰鏂藉伐涔嬪墠銆?

### Fixed

- Added P3 allowlisted verification, closure, isolated CLI acceptance, and compact reporting; adapters, CI, and multi-agent remain disabled.

## [1.2.0] - 2026-07-22

### Added

- Added formal project-defined adoption scopes through `--scope-file`, enforced across planning, confirmation, export, Runtime compilation, approval, and installation.
- Added one canonical install writeset plus pre-install hashes and a manual rollback manifest, all generated before target writes.
- Added explicit, authorization-neutral confirmation and installation approval candidates. Preview generation does not grant installation or activation authority.

### Changed

- Upgraded Toolchain Provenance Binding to v2. Generator identity now binds clean Git `HEAD` blobs, rejects modified or staged generator inputs, and remains deterministic across LF/CRLF checkouts.
- Made formal artifact writing byte-stable through UTF-8/LF normalization, exclusive creation, and atomic replacement where applicable.
- Replaced the fixed release-test timeout with a bounded, auditable 600-second default configurable from 60 through 3600 seconds.
- Preserved the public Coding Agent Governance presentation, controlled distribution materials, and target-review tracking added on `main` after v1.1.0.

### Fixed

- Kept generated draft summaries authorization-neutral until an Owner explicitly confirms the unchanged artifacts.
- Made the provenance LF/CRLF fixture self-contained so Windows and Linux validate the same Git-blob contract.

### Performance

- Cached immutable Git `HEAD` blob digests and batched Git validation/blob reads without weakening dirty or staged fail-closed checks.

### Security

- Artifacts created before v1.2.0 do not contain provenance v2 fields and are rejected by the formal downstream flow. Regenerate the adoption Preview instead of editing an old receipt.
- Installation and activation remain separate, explicit Owner decisions. A Preview is never installation or activation authorization.

## [1.1.0] - 2026-07-16

### Added

- Added workflow-agnostic positioning, a documented Superpowers mapping, an offline TaskContract example, a reproducible synthetic case study, and public share/release materials.

### Changed

- Repositioned the public entry points around deterministic scope checks, evidence freshness, and Closure; clarified that the bounded adoption lifecycle is the recommended existing-project path.

### Security

- No remote workflow integration, external API, publishing automation, production operation, or official third-party compatibility claim was added.

## GOV-RUNTIME-P5
- Added self-validation, schema compatibility, isolated bootstrap checks, a fixed local release gate, and least-privilege GitHub Actions CI.

## GOV-RUNTIME-P4
- Added deterministic generic, Python, Node and WeChat Mini Program adapters, adapter detection, bootstrap configuration, adapter-aware test planning and guard classification.


## GOV-RUNTIME-P6
- Added deterministic local multi-agent orchestration, handoff freshness, ownership checks and CLI entry points.


## [1.0.0] - 2026-07-13

### Added

- Deterministic governance runtime V1: Preflight, local state/approval/guard, allowlisted verification/closure, adapters/bootstrap, read-only CI gate, and local multi-agent orchestration contracts.

### Security

- Runtime and CI remain local/read-only by default: no remote Agent/API invocation, automatic worktree, Git write, Secret use, deployment, or publishing.

### Known limits

- Prompt bundles are manually distributed to Agent threads. GitHub Actions configuration is locally validated only; V1 has not been committed, pushed, tagged, or remotely executed from this checkout.
