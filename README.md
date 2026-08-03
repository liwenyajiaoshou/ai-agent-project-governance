# Coding Agent Governance

> A governance layer for AI coding agents that keeps changes scoped, evidence-bound, reviewable, and explicitly closed.

Repository-slug migration from `ai-agent-project-governance` is pending.

[![Python](https://img.shields.io/badge/runtime-Python-blue)](requirements-governance.txt)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)](VERSION)

[English](README.md) | [简体中文](README.zh-CN.md)

## Keep an AI coding task bounded and provable

## Optional: make long-running projects easier to resume

When you often switch Codex threads, you can enable Context Handoff. It generates a short project state, task index, and handoff entry. When you do not need it, the Core governance workflow stays unchanged.

It is disabled by default. From the repository root, you can safely preview the files it would create, then enable it for a target project:

```bash
python3 extensions/context-handoff/manage.py context-handoff preview --target /path/to/project --project-id PROJECT_A --task-id TASK_1
python3 extensions/context-handoff/manage.py context-handoff enable --target /path/to/project --project-id PROJECT_A --task-id TASK_1 --event TASK_STARTED
python3 extensions/context-handoff/manage.py context-handoff disable --target /path/to/project
python3 extensions/context-handoff/manage.py context-handoff uninstall --target /path/to/project --apply
```

Disable preserves generated history. Uninstall only removes the extension's unmodified control files; it preserves generated history and user-modified files. See the [Context Handoff extension guide](extensions/context-handoff/README.md) for details.

Planning and coding workflows can help an agent decide what to build. This project independently checks whether the resulting work stayed in scope, used relevant evidence, and can safely close.

It is for the moments when an agent:

- edits a file outside the authorized TaskContract;
- runs an unrelated or missing test;
- reuses verification after the workspace changed; or
- reports completion without an evidence-backed handoff.

Run the offline proof now:

```bash
python3 examples/demo/run_visual_proof.py
```

On Windows PowerShell, use `python` instead. The command creates only a temporary synthetic repository and demonstrates an out-of-scope block, a stale-verification block, and a successful closure. See the [Demo](docs/DEMO.md).

## Where it fits

This is not a replacement for [Superpowers](docs/SUPERPOWERS_COMPATIBILITY.md), `AGENTS.md`, TDD practices, a general development methodology, or a sub-agent orchestrator.

| Upper workflow layer | This governance layer |
| --- | --- |
| Clarifies requirements, designs work, plans implementation, and may coordinate agents | Maps a bounded task to a TaskContract, checks actual scope, records test evidence, rejects stale verification, and produces Closure/Handoff records |

The relationship is complementary and workflow-agnostic. The repository provides a documented, offline mapping example; it does **not** claim an official Superpowers integration, a plugin, or end-to-end compatibility. See the [compatibility statement](docs/SUPERPOWERS_COMPATIBILITY.md) and [minimal workflow mapping](docs/WORKFLOW_INTEGRATION.md).

## Why this exists

When agents change a repository, the difficult part is often not generating code. It is keeping the change inside its intended scope, selecting meaningful tests, avoiding unsupported completion claims, coordinating concurrent work, and retaining evidence for handoff.

This repository provides a local governance runtime for that work:

- explicit task scope and protected paths;
- task-relevant test planning and verification evidence;
- closure that detects stale validation; and
- structured handoff with single-writer protection for multi-agent work.

### More than an `AGENTS.md` or prompt

An `AGENTS.md` file or prompt can guide an agent. This project adds executable checks around that guidance: contracts, scope guards, test planning, verification, and closure records. It reduces common failure modes; it does not claim to prevent every agent error or provide an official third-party product integration.

## Verify it locally

Run the existing local gate after cloning the repository:

```powershell
git clone https://github.com/vanlew1/ai-agent-project-governance.git
cd ai-agent-project-governance
python -m pip install -r requirements-governance.txt
python scripts/run_governance_ci.py
```

The final command runs the repository's existing governance checks and reports the result in the terminal.

## Status and boundaries at a glance

| Area | Current, cautious statement |
| --- | --- |
| Version | `1.2.0` |
| Automation | The repository includes the `Governance CI` GitHub Actions workflow. |
| Release | `v1.2.0` is the current release. See the [release notes](docs/releases/v1.2.0.md) and [migration guide](docs/migrations/v1.1.0-to-v1.2.0.md). |
| Runtime coverage | Python, Node.js, WeChat Mini Program, and the generic fallback have local adapter acceptance evidence. See [compatibility](docs/COMPATIBILITY.md). |
| Agent compatibility | Codex is instruction-compatible only. Claude Code, Cursor, and GitHub Copilot have no recorded end-to-end validation. |

By default, the runtime does not automatically access production systems, write production data, call remote APIs, start third-party agents, install dependencies, create worktrees, commit, push, deploy, or publish. The local audit is read-only unless you explicitly pass `--output`.

## What it helps prevent

- Changes outside a TaskContract scope.
- Tests that are unrelated to the change, or skipped required checks.
- Claims of completion without verification evidence.
- Closure that reuses validation after the workspace has changed.
- Multiple agents writing the same file without single-writer protection.

## How it works

![Governance runtime architecture](docs/assets/architecture-overview.svg)

| Static guidance alone | This governance runtime adds |
| --- | --- |
| Tells an agent what not to change | Guard checks the actual change scope |
| Asks an agent to run tests | TestPlan selects registered commands |
| Relies on a completion claim | Verification and Closure decide completion |
| Leaves handoff in prose | Structured Handoff records ownership and results |
| Coordinates manually | DAG and single-writer protection expose conflicts |

## Continue by intent

| If you want to… | Start here |
| --- | --- |
| Run a short local introduction | [Demo](docs/DEMO.md), then [Getting started](docs/GETTING_STARTED.md) |
| Choose a setup level | [Preset guide](docs/PRESETS.md) |
| Adopt the runtime in an existing repository | [Existing-project adoption](docs/EXISTING_PROJECT_ADOPTION.md) — the `agent_adopt.py` lifecycle is the recommended path; manual copying is recovery-only |
| Activate an adopted Runtime | Use `scripts/agent_state.py activate-approved`; activation is separately approved and does not run Preflight, tests, verification, or closure |
| Review compatibility evidence | [Compatibility](docs/COMPATIBILITY.md) |
| Understand the audit and safety model | [Audit details](docs/ADOPTION_AUDIT.md) |
| Explore a concrete path | [Demo](docs/DEMO.md) — see an out-of-scope block, stale-verification block, and successful closure — plus [examples](examples/README.md) |
| Reuse an upper workflow plan | [Workflow integration](docs/WORKFLOW_INTEGRATION.md) and the [offline mapping example](examples/superpowers_compat/README.md) |
| Prepare a public launch | [Share kit](docs/SHARE_KIT.md), [launch copy](docs/LAUNCH_COPY.md), and [repository metadata](docs/GITHUB_TOPICS.md) |
| Contribute or get help | [Contributing](CONTRIBUTING.md), [Security](SECURITY.md), and [Support](SUPPORT.md) |

For repository-maintenance checks, see the [GitHub settings checklist](docs/GITHUB_REPOSITORY_SETTINGS_CHECKLIST.md). The runtime itself does not modify those remote settings.

## License

MIT. See [LICENSE](LICENSE).
