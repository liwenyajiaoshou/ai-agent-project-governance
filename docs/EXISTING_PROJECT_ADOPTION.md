# Adopt an Existing Project

## Recommended path: use the bounded lifecycle

For an existing repository, use `scripts/agent_adopt.py` as the single recommended adoption path: start with `dry-run`, review/export drafts outside the target, compile a Runtime preview, and only then use separately approved installation and activation steps. It is local-only and does not download dependencies.

Manual copying of templates is intentionally not a normal adoption path. Keep it only as an advanced, user-managed recovery option when the bounded lifecycle cannot be used; it does not replace its provenance or approval checks.

The lifecycle coexists with Superpowers, `AGENTS.md`, CI, hooks, and other workflows: those tools may provide task intent, while this runtime accepts only a bounded TaskContract and records its own local evidence. No external workflow receives a special trust exemption.

You do not need to rebuild a business application.

- The runtime does not automatically install dependencies, overwrite files, commit, or push.
- Adapter detection is marker-based advice, not migration or authorization.

## Plan before changing a project

Start with the local, read-only planner. It detects local markers, reuses the configuration audit, proposes a Preset, lists test candidates and prospective governance assets, and embeds untrusted configuration drafts. It does not copy assets, create configuration, activate state, run tests, or modify the target project.

```bash
python3 scripts/agent_adopt.py --project-root /path/to/project --format markdown dry-run
python3 scripts/agent_adopt.py --project-root /path/to/project --format json --output /tmp/adoption-plan.json --scope-file /tmp/adoption_scope_input.yaml --scope-copy-output /tmp/formal-scope.yaml --provenance-output /tmp/adoption-provenance.json dry-run
python3 scripts/agent_adopt.py confirmation-candidate --plan /tmp/adoption-plan.json --output /tmp/adoption-confirmations.yaml --target-project-root /path/to/project
```

`--output` is optional and must point outside the target project. A formal downstream flow requires `--scope-file`; private `build_plan(...)` calls and scope-less plans cannot masquerade as public CLI generation. A confirmation candidate remains unapproved unless the Owner separately invokes the explicit confirmation command with `--confirm-owner`. A detected Adapter, Preset recommendation, scope candidate, or test candidate is never authorization by itself.

Note: Artifacts generated before `v1.2.0` do not carry the Git-HEAD-blob provenance contract and are no longer supported. Re-run `dry-run` to generate a fresh, compatible draft bundle.

1. Make a normal local backup or branch.
2. Run `python <runtime-root>/scripts/agent_detect_adapter.py --root . detect`.
3. Copy only governance assets you intend to own: `governance/`, `schemas/`, `config/`, required `scripts/`, `AGENTS.md`, and `agent_rules/`.
4. Create project-specific `task.yaml` and `project_state.yaml` with narrow write scope and known-safe commands.
5. Run Preflight, activate State, then Guard before accepting a test plan.
6. Start with one reversible task; deny production data, credentials, generated output, and deployment paths until reviewed.

`dry-run` is the only planner mode. The separate export and installation commands below require explicit, digest-bound inputs; there is no one-click adoption or automatic activation. `scripts/init_new_project.py` is not an in-place adoption shortcut.

## Command surface

`python3 scripts/agent_adopt.py --help` lists the complete local-only command surface:

| Command | Boundary |
| --- | --- |
| `dry-run` | Analyze an existing project without writing to it. |
| `export-drafts` | Write reviewed drafts only outside the target project. |
| `compile-runtime-artifacts` | Build an external Runtime preview; it does not install. |
| `install-approved` | Copy exact approved bytes; it does not activate. |
| `assess-rollback` | Produce a read-only manual recovery assessment. |
| `rollback-install` | Reject automatic rollback; it never deletes target files. |
| `compile-contract-recovery` / `approve-contract-recovery` / `recover-approved` | Preview, explicitly approve, then atomically rebind only an `ACTIVATED_NOT_PREFLIGHTED` Runtime. |
| `adoption-preflight` | Run the canonical adoption-aware bridge and record the `PREFLIGHT_PASSED` transition. |
| `compile-framework-upgrade` / `approve-framework-upgrade` / `upgrade-approved` | Apply only an exact approved, drift-free `v1.5.1 → v1.5.2` changed-asset writeset. |

All commands are local-only and do not authorize network access, Git writes, production actions, or deployment.

Full lifecycle adoption requires explicit write authority for `project_state.yaml`; the planner diagnoses missing authority and compile, install, and activation reject it with stable reason codes. Generic discovery contracts may remain zero-write because this gate is adoption-specific and never widens scope automatically.

Recovery preserves the installed/activation evidence chain and existing ProjectState history. It never overwrites without a fresh exact Owner approval and its writeset is fixed to `task.yaml` plus `project_state.yaml`. The controlled upgrade similarly excludes those Runtime files and refuses unknown local framework drift. Use generic `agent_preflight.py` only for generic TaskRequest input; an activated adoption TaskContract returns `USE_ADOPTION_LIFECYCLE_BRIDGE`.

## Export reviewed configuration drafts

After reviewing a JSON dry-run plan, a user may provide a separately authored confirmation file and export an untrusted draft bundle outside the target project:

```bash
python3 scripts/agent_adopt.py export-drafts \
  --plan /path/to/adoption-plan.json \
  --confirmations /path/to/adoption-confirmations.yaml \
  --target-project-root /path/to/project \
  --output-dir /external/path/adoption-drafts
```

The target-root argument is a safety boundary: the exporter recomputes a privacy-preserving target identity and rejects a Plan made for a different project, as well as internal or symlinked output paths. It never writes the target. The export contains `task.yaml.draft`, `project_state.yaml.draft`, a confirmation summary, and a manifest. These are `UNTRUSTED_DRAFT`, `NOT_INSTALLED`, `NOT_ACTIVATED`, and require final review. This command does not install assets, activate state, or execute any runtime command.

## Compile Runtime preview before final approval

The reviewed draft bundle is compiled once into an external, immutable preview bundle before final approval:

```bash
python3 scripts/agent_adopt.py compile-runtime-artifacts \
  --plan /path/to/adoption-plan.json \
  --confirmations /path/to/adoption-confirmations.yaml \
  --draft-bundle /external/path/adoption-drafts \
  --target-project-root /path/to/project \
  --output-dir /external/path/runtime-artifact-preview
```

The preview contains `task_contract.runtime.yaml`, `project_state.runtime.yaml`, `RUNTIME_ARTIFACT_MANIFEST.json`, `INSTALL_WRITESET.json`, `PRE_INSTALL_HASHES.json`, and `ROLLBACK_MANIFEST.json`. The manifest records exact file-byte digests, canonical scope, pre-write sidecar digests, Toolchain Provenance Binding, and a reproducible compiler identity. Runtime 正式产物必须在最终批准前生成。最终批准绑定精确的 Runtime 文件摘要、scope、pre-write sidecar 与编译器身份。

## Approved installation (synthetic validation only)

`approval-candidate` creates an exact-byte candidate with `approved_by_user=false`, `install_approved=false`, and `activate_approved=false`. It grants no authority. If an Owner later explicitly approves the unchanged candidate, `install-approved` receives the reviewed draft bundle and precompiled Runtime preview. The installer revalidates target branch/HEAD, framework commit, scope equality, Runtime bytes, and all three sidecars before target writes; it never regenerates sidecars after writing or substitutes Runtime artifacts.

The provenance receipt is a `TOOLCHAIN_PROVENANCE_BINDING`: generator source digest v2 binds fixed generator-input blobs from the framework Git `HEAD`, not LF/CRLF checkout bytes. Any modified or staged generator input blocks formal generation; a non-Git framework source is unsupported. Because it has no secret key, HMAC, or external signature, it is not cryptographic anti-forgery and must not be described as such.

```bash
python3 scripts/agent_adopt.py install-approved \
  --target-project-root /path/to/project \
  --draft-bundle /external/path/adoption-drafts \
  --runtime-artifact-bundle /external/path/runtime-artifact-preview \
  --final-approval /external/path/final-approval.yaml \
  --receipt-output /external/path/installation-receipt.json \
  --plan /path/to/adoption-plan.json \
  --confirmations /path/to/adoption-confirmations.yaml
```

安装阶段直接使用已批准文件，不重新编译替换。 It refuses conflicts, does not activate state or run tests, and writes an external installation receipt containing both source-draft and Runtime digests. If a later write fails, it preserves the already-created files and issues a manual-recovery receipt; `rollback-install` is fixed to reject automatic deletion. Real projects require separate review and authorization; 04E does not run Guard, Verification, Closure, Git, or network operations.

## Approved activation (synthetic validation only)

Installation is not activation. A separately authored `activation_approval` binds the current target identity, exact installed Runtime bytes, Runtime manifest, final-install approval, installation receipt, compiler identity, and the current ProjectState digest. Only then may the bounded command below replace `project_state.yaml` from `INSTALLED_NOT_ACTIVATED` to `ACTIVATED_NOT_PREFLIGHTED`:

```bash
python3 scripts/agent_state.py activate-approved \
  --target-project-root /path/to/project \
  --task-contract /path/to/project/task.yaml \
  --project-state /path/to/project/project_state.yaml \
  --runtime-artifact-manifest /external/RUNTIME_ARTIFACT_MANIFEST.json \
  --final-install-approval /external/final-approval.yaml \
  --installation-receipt /external/installation-receipt.json \
  --activation-approval /external/activation-approval.yaml \
  --activation-receipt-output /external/activation-receipt.json
```

The activation receipt is external and new-only. `activation_receipt_digest` in the Runtime state is a deterministic pre-write receipt binding digest, rather than the final receipt-file digest, to avoid an unsafe circular hash dependency between the final state bytes and the receipt's required after-state digest. The legacy `agent_state.py activate` command blocks an adoption Runtime and reports `USE_ACTIVATE_APPROVED`.

安装完成不等于已激活。已激活不等于预检通过。已激活不等于测试、验证或收口完成。 `activate-approved` never runs Preflight, Guard, tests, Verification, Closure, network, Git writes, or production operations.

## Lifecycle foundation

Adoption reuses the formal Runtime lifecycle through a provenance-bound adapter. The adapter maps the approved `TaskContract` to the existing `TaskRequest` input without broadening allowed scope or removing denied scope, then calls formal Preflight. ProjectState transitions use compare-and-swap and atomic writes:

```text
ACTIVATED_NOT_PREFLIGHTED → PREFLIGHT_PASSED → GUARDED → TEST_PLANNED
→ TEST_EXECUTED → VERIFIED → CLOSED
```

No lifecycle stage can be skipped or reversed. Only confirmed test candidates whose command identity exactly matches the local registry are eligible. Verification binds workspace snapshots and provenance; stale, incomplete, blocked, or failed evidence cannot close work. `CLOSED` does not mean production-ready, released, or deployed.

A reviewed Node target may use the exact local `npm test` argv candidate with `shell=False`; it is a test invocation, not package resolution. `npm install`, `npm ci`, `npm add`, `npm update`, `npx`, and download tools are ineligible. Synthetic validation also covers Generic targets and paths containing Unicode or spaces without contacting a registry or other network service.

04D outputs external drafts. 04E compiles and installs Runtime-valid inputs. A future 04F-A activation step may only explicitly activate already-valid Runtime state; it must not convert drafts, run Preflight, run tests, verify, or close work. 安装完成不等于已激活；已激活不等于预检、测试、验证或收口完成。

Automatic rollback is intentionally unsupported: POSIX cannot safely make a content-hash check and file deletion atomic against non-cooperating writers. Use `assess-rollback` only for a read-only, point-in-time manual cleanup assessment. It never deletes target files or emits delete commands; stop editors, Agents, tests, builds, and sync tools, then recheck immediately before any user-managed deletion. Receipts and assessment outputs must be outside the target project. 安全起见，系统不提供自动回滚；它只提供只读人工清理评估，不会删除目标文件。

## Lifecycle evidence and sensitive test output

Raw command stdout and stderr are never stored in lifecycle evidence, reports, or lifecycle debug records. The local command runner computes SHA-256 digests from raw bytes, then stores only bounded redacted tails, the digest values, a redaction count, and the sanitizer rule version. Sanitizer errors fail closed and do not fall back to original output.

Lifecycle context independently reconstructs the Runtime manifest, final-install approval, installation and activation receipts, compiler identity, confirmation, confirmed test candidate, blocked decisions, target identity, and current workspace snapshot. A caller cannot provide an already-resolved candidate list as authority.

Each forward state edge accepts one registered evidence type. The transition re-reads the evidence file, validates its schema, recomputes its file digest, checks target identity, prior-state digest, and every upstream evidence file before using the atomic state writer. Verification and Closure revalidate provenance, current state, target identity, denied-scope status, unresolved blockers, and workspace freshness. `CLOSED` remains neither production-ready, released, nor deployed.
