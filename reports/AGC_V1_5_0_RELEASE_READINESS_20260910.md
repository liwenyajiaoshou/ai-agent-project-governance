# AGC v1.5.0 Release Readiness Check

## Decision

`RELEASE_BLOCKED`

The local v1.5.0 authority is complete and clean, but the local `origin/main` tracking ref has a non-fast-forward history divergence. A safe `push main` path therefore requires a separate Owner-authorized remote-history reconciliation decision.

## Read-only scope

- No fetch, pull, network access, push, tag, release, PR, merge, rebase, cherry-pick, reset, clean, stash, or branch/worktree deletion was performed.
- Evidence was read from existing local refs and committed reports only.

## Main and version checks

| Check | Result |
| --- | --- |
| Primary branch | `main` |
| Current main HEAD | `d229bda758584fe2200c312aa1bcd76360102c65` |
| Primary status before this report | clean |
| `VERSION` | `1.5.0` |
| Existing `v1.5.0` tag | absent |
| Existing version tags | `v1.0.0`, `v1.1.0`, `v1.2.0`, `v1.3.0` |
| `git diff --check` | PASS |

## Local origin/main relation

- Local tracking ref: `origin/main` at `fc7fbe993d5adf05faa99c43e601cecc31ed381a`.
- Common merge-base: `c6c24f4ea795c833089f8778e7070d3df0ea81b4` (`v1.3.0`).
- `git rev-list --left-right --count main...origin/main`: `4 2`.
- `origin/main` is not an ancestor of `main`; `main` is not an ancestor of `origin/main`.
- Existing local history shows `origin/main` retains the merge-only v1.3 publication-history commit `fc7fbe99...`, while main contains the v1.5 authority line and the effective v1.3 evidence cherry-pick.

This divergence means a normal `push main` would not be a fast-forward based on the local tracking ref. No force push or merge was attempted.

## v1.5 canonical evidence

The following committed reports are present:

- `reports/AGC_V1_5_0_FINAL_MANIFEST_20260910.json`
- `reports/AGC_V1_5_0_REALITY_CHECK_AND_IMPLEMENTATION_REPORT_20260910.md`
- `reports/AGC_V1_5_0_REUSE_MATRIX_20260910.json`
- `reports/AGC_V1_5_0_GIT_AUTHORITY_RECONCILIATION_REPORT_20260910.md`

The Final Manifest records `AGC_V1_5_0_LOCAL_CLOSURE_PASS`, canonical gate exit code `0`, and `8/8 PASS`; the Reality Check report records the same gate result and `git diff --check: PASS`. The Final Manifest lists 20 final changed paths.

## Independent protected assets

- Inspector archive: `/home/liyouran1997/projects/agc-inspector-build-week-archive`, HEAD `06b9576df512a94a68db3914b72e501420fba8b4`, clean. Its commit is not an ancestor of main.
- Legacy recovery branch: `codex/repository-rename-distribution`, quarantine commit `f02fdeeb329b0237294a2b2f5379cefadee2011d`, both retained and reachable. The quarantine commit is not an ancestor of main.
- No Inspector archive or legacy recovery asset is implicitly included by the main release line.

## Release action envelope (not executed)

Once the remote-history blocker is resolved by Owner decision, a release would consist of:

1. push `main`;
2. create and push tag `v1.5.0` at the approved release commit;
3. create a GitHub release from that tag, if applicable.

## Blocker and recommended next Owner action

**Blocker:** `origin/main` and local `main` have a normal post-v1.3 history fork (`4` local-only commits vs `2` origin-only commits), so publishing main cannot safely proceed as a fast-forward from the known local ref.

**Recommended next action:** decide and authorize a non-force remote-history reconciliation that preserves the existing v1.3 publication evidence; then rerun this read-only readiness check before push/tag/release.
