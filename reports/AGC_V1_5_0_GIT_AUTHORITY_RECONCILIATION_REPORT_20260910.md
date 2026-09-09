# AGC v1.5.0 Git Authority Reconciliation Report

## Scope and result

- Task: read-only reconciliation of `agc-v1.5.0-development`, local `main`, and locally recorded `origin/main`.
- No merge, cherry-pick, rebase, reset, clean, stash, checkout/switch, branch operation, commit, push, fetch/pull, tag, release, or source-file change was performed.
- Authority worktree: `/home/liyouran1997/projects/agc-v1.5.0-development`.
- Authority branch / HEAD: `agc-v1.5.0-development` / `5e836156856eb8f1280bdb256dc9531fde7d711c`.
- Authority worktree status: clean.

## Reproducible read-only commands

```bash
git show -s --format='%H %cs %s' main origin/main agc-v1.5.0-development
git merge-base --all main origin/main agc-v1.5.0-development
git merge-base --octopus main origin/main agc-v1.5.0-development
git merge-base --is-ancestor main agc-v1.5.0-development
git merge-base --is-ancestor origin/main agc-v1.5.0-development
git merge-base --is-ancestor agc-v1.5.0-development main
git merge-base --is-ancestor agc-v1.5.0-development origin/main
git rev-list --left-right --count main...origin/main
git rev-list --left-right --count main...agc-v1.5.0-development
git rev-list --left-right --count origin/main...agc-v1.5.0-development
git log --left-right --cherry-pick --decorate --date=short --format='%m %H %cs %s' origin/main...agc-v1.5.0-development
git for-each-ref --sort=creatordate --format='%(refname:strip=2)|%(objectname)|%(creatordate:short)|%(subject)' refs/tags
git worktree list --porcelain
git -C <each-worktree> status --short
```

## Commit relation

| Ref | HEAD | Version | Relation to v1.5 |
| --- | --- | --- | --- |
| `main` | `74d90e68339daba7011d784a6ee0affa72611d25` | `1.1.0` | ancestor; v1.5 contains all of it |
| `origin/main` (local tracking ref; no fetch performed) | `fc7fbe993d5adf05faa99c43e601cecc31ed381a` | `1.3.0` | diverged; two commits absent from v1.5 |
| `agc-v1.5.0-development` | `5e836156856eb8f1280bdb256dc9531fde7d711c` | `1.5.0` | proposed future development authority |

- Three-way common merge-base: `74d90e68339daba7011d784a6ee0affa72611d25` (`v1.1.0`).
- `main...origin/main`: `0 27`; local main has no unique commits, while origin/main has 27 commits after main.
- `main...agc-v1.5.0-development`: `0 27`; local main can fast-forward to v1.5 because it is an ancestor.
- `origin/main...agc-v1.5.0-development`: `2 2`; neither is an ancestor of the other, so neither direction can fast-forward.
- Pairwise merge-base for `origin/main` and v1.5: `c6c24f4ea795c833089f8778e7070d3df0ea81b4` (`v1.3.0` tag commit). This is a normal, small post-v1.3 branch fork, not unrelated history.

## Divergence assessment

`origin/main`-only commits are:

1. `4a4123699329b7d0817d46ac7a6ef66f4617170d` — `docs(release): record v1.3.0 publication`.
2. `fc7fbe993d5adf05faa99c43e601cecc31ed381a` — merge of that release-record commit.

Their effective changes are four documentation lines across `docs/TASK_REGISTRY.yaml` and `reports/AGC_V1_3_0_CONTEXT_HANDOFF_PUBLIC_RELEASE_REPORT.md`. They are formal release-history evidence and are not present in v1.5's ancestry. They should be explicitly preserved before future main convergence; this is not a feature-code omission.

v1.5-only commits are:

1. `6cedc70629930fcb95aabbf829ede7a708967791` — v1.4.0 release candidate.
2. `5e836156856eb8f1280bdb256dc9531fde7d711c` — v1.5.0 governance compression closure.

Thus v1.5 already contains every local-main commit and the tagged v1.2/v1.3 history, but not the two origin/main post-v1.3 release-record commits.

## Tags

| Tag | Target commit | Contained by v1.5 |
| --- | --- | --- |
| `v1.0.0` | `5024b4c6f0c9b50ddc973ce1e3b3843e2e6aa26` | yes |
| `v1.1.0` | `74d90e68339daba7011d784a6ee0affa72611d25` | yes |
| `v1.2.0` | `7e8493ed0cb24ff523422487f0d5657ceea7fa98` | yes |
| `v1.3.0` | `c6c24f4ea795c833089f8778e7070d3df0ea81b4` | yes |

No v1.4 or v1.5 tag exists. No tag was created or altered.

## Worktree protection

All registered local worktrees were inspected with `git status --short` only. The protected legacy worktree `/home/liyouran1997/projects/ai-agent-project-governance` remains untouched and has 33 dirty paths. No operation was performed in it.

## Recommendation

`ROUTE_B`

Make `5e836156856eb8f1280bdb256dc9531fde7d711c` the future single development authority, but first integrate and verify the two origin/main-only v1.3.0 release-history commits (or their exact effective documentation content) into the v1.5 authority branch. Only after that separate, explicitly authorized integration may main/origin-main converge on the resulting authority commit. This task performed none of those actions.

## Post-Audit Authority Update

- 本报告主体审计执行时的 authority HEAD 为
  `5e836156856eb8f1280bdb256dc9531fde7d711c`。
- 随后根据本报告 ROUTE_B 建议及 Owner 授权，
  `4a4123699329b7d0817d46ac7a6ef66f4617170d` 的 v1.3 发布历史证据被单独 cherry-pick。
- 新 authority HEAD 为
  `e5f6ab8f64cb591e5df7e67b61cbf88882d0c40d`。
- 未整合 merge-only commit `fc7fbe99...`。
- 该操作仅补齐发布历史证据，没有改变 v1.5 Final Manifest 中 20 个功能路径的内容。
- 因此：
  - 本报告中的 `5e836...` 应理解为 audit-time authority；
  - `e5f6ab8...` 是 post-reconciliation current authority。
