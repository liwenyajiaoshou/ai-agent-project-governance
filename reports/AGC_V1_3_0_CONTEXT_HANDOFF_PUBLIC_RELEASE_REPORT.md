# AGC v1.3.0 Context Handoff Public Release Report

## Release inputs

- Pre-release `origin/main`: `7e8493e`
- RC source: `aea5ed7`
- Release branch: `release/v1.3.0-context-handoff`
- Product version: `1.3.0`
- Extension version: `0.1.0`

## Imported public assets

- `extensions/context-handoff/`
- `profiles/multi-agent-context/profile.yaml`
- `tests/unit/test_context_handoff_extension.py`

## Publicization

- Removed release-candidate and local-only distribution wording.
- Confirmed the extension manifest and optional profile have `default_enabled: false`.
- Performed one targeted check for credentials, user state, local worktree names, and `/home/liyouran1997` paths; none were found in release assets.

## Validation

- PASS: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.unit.test_context_handoff_extension` — 13 tests.
- PASS: lifecycle smoke: preview zero-write; enable; disable preserves history; uninstall preserves history.
- PASS: `PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_governance_ci.py` — 8/8 gates.
- PASS: `git diff --check` and `git diff --cached --check`.
- PASS: PR [#9](https://github.com/vanlew1/ai-agent-project-governance/pull/9) merged at `c6c24f4ea795c833089f8778e7070d3df0ea81b4`.
- PASS: annotated tag `v1.3.0` created and pushed at `c6c24f4ea795c833089f8778e7070d3df0ea81b4`.
- PASS: [GitHub Release v1.3.0](https://github.com/vanlew1/ai-agent-project-governance/releases/tag/v1.3.0) published.

## Compatibility

- Core-only behavior remains unchanged: the Core does not import or depend on Context Handoff.
- Context Handoff remains optional and disabled by default.
