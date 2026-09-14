# AGC P1 Phase 2 Evidence Store Integration Design Decision Report V1

Date: 2026-09-12

## 1. Decision Status

`P1_PHASE2_EVIDENCE_STORE_INTEGRATION_DESIGN_READY`

This report is a design decision only. It does not authorize or perform lifecycle integration, install, activation, upgrade, recovery, Existing Project Adoption, Jingwei, migration, real evidence writes, commit, push, or release.

The integration design below is `proposed` pending Owner approval. Existing repository behavior and the Phase 1 contracts are recorded as `confirmed` facts.

## 2. Governance and Preflight

- Mode / level / class: `ADAPTATION` / Level 2 / B-class bounded design task.
- Allowed write: this report only.
- Repository: `/home/liyouran1997/projects/ai-agent-project-governance`.
- Branch / HEAD: `main` / `b3f84d011384e778b15ac3213d9374114eebef8b`.
- v1.5.2 closure commit: `b9023c5e131088115b1c9e704a27be6c232d6cb7`; present and immediately precedes the Phase 1 commit.
- Phase 1 result: `P1_PHASE1_EVIDENCE_STORE_CORE_IMPLEMENTATION_PASS`; 13 focused tests and 225 unit tests passed in the recorded Phase 1 execution.
- Worktree status before this report: `main` was ahead of `origin/main` by two commits and contained nine pre-existing untracked reports. They were not modified.
- The requested plan was absent from repository `.agent-plans/`; the attached same-named Downloads file was read as task guidance and was not copied into the repository.
- `agent_rules/11_project_specific_rules.md` is indexed but absent; only its template exists. This task does not create or repair it.

Rules read: `AGENTS.md`, `RULES_INDEX.yaml`, rule router, plan adaptation/execution envelope, task classification, B task card, architecture, traceability, data safety, testing, and cost-aware testing rules.

## 3. Current Problem

Confirmed current behavior has two disconnected evidence contracts:

1. Phase 1 defines immutable `EvidenceObject`, path-free `EvidenceReference`, digest verification, an `EvidenceStore` protocol, and a non-persistent `InMemoryEvidenceStore`. It deliberately has no lifecycle integration or durable backend.
2. The v1.5.2 Adoption lifecycle accepts evidence as filesystem paths. `ProjectState.lifecycle_evidence` records `evidence_file` plus digests, and the registry reopens every historical path when calculating upstream evidence. Installation, activation, upgrade, and recovery likewise accept or emit receipt paths.

Consequently, a digest can prove whether available bytes match, but it cannot discover or restore missing original bytes. Absolute paths are machine-specific and may disappear. Directly replacing paths with new references would also break existing `1.0` schemas, callers, tests, and activated Runtime state.

The integration problem is therefore to make Phase 1 references resolvable and consumable while preserving all existing schema, provenance, identity, approval, ordering, replay, and fail-closed checks.

## 4. Phase 2 Goal and Non-Goal

The proposed Phase 2 goal is a narrow compatibility layer between Phase 1 evidence primitives and the existing Adoption/lifecycle consumers:

- resolve original bytes from an `EvidenceReference` through an injected store;
- verify reference structure, object metadata, byte length, SHA-256, expected evidence type, schema identity/version, and domain schema before consumption;
- let lifecycle state edges bind stable references without making object metadata or indexes substitutes for original bytes;
- preserve a bounded legacy-path read mode for existing Runtime data;
- define explicit behavior for new, existing-complete, and existing-incomplete projects.

Phase 2 is not a durable filesystem store, lifecycle mutation, migration engine, backup system, relocation mechanism, signing system, Jingwei recovery, or production deployment.

## 5. Lifecycle Integration Design

### 5.1 Events that require evidence

The following authority-bearing events must have resolvable original evidence before they may be accepted:

| Event | Required evidence role | Binding rule |
| --- | --- | --- |
| Enrollment / import | identity/enrollment record and imported originals | Bind project instance, observed target identity, source classification, and every imported original digest |
| Install | plan, confirmation, provenance/manifests, final approval, installation or partial receipt | Receipt becomes the install event result and retains all existing upstream digest bindings |
| Activation | installation chain, activation approval, activation receipt | Activation receipt is a child of the verified installation evidence |
| Lifecycle state edge | the registered `Preflight`, `Guard`, `TestPlan`, `TestRun`, `Verification`, or `Closure` evidence | Reference is bound to previous state digest, target identity, exact edge, and ordered upstream references |
| Upgrade | upgrade manifest, approval, receipt | Append a new event; never replace install/activation history |
| Recovery | original install/activation receipts, recovery manifest, fresh approval, recovery evidence | Resolve and revalidate originals before compiling and again before writing |

The event record should carry the existing semantic fields plus an `EvidenceReference`; no event may treat an object ID, index entry, digest-only record, or reconstructed document as original evidence.

### 5.2 Binding and ordering

- `EvidenceReference.sha256` remains the byte-integrity anchor and must equal `object_id` under the Phase 1 `1.0` contract.
- Domain bindings remain authoritative: target identity, previous state digest, upstream evidence digests, manifest/approval/receipt links, Runtime before/after digests, and lifecycle edge type/status.
- The resolver must not invent a new ordering model in Phase 2. Existing ordered `lifecycle_evidence` remains the compatibility source; future durable event/index ordering is a later store capability.
- A lifecycle transition is eligible only after all prior references and the candidate evidence resolve and validate. The transition must re-check the current ProjectState digest under the existing compare-and-swap behavior.
- A newly created authority result must be durably published before a successful operation exposes its reference or leaves Runtime state dependent on it. Because no durable backend exists in Phase 1, this rule is an interface contract for later implementation, not executable Phase 2 behavior.

### 5.3 Backward-compatible state representation

Do not mutate `project_state.schema.json` in the first integration slice. Introduce a versioned adapter-domain record outside ProjectState:

```text
EvidenceBindingV1
  role
  reference: EvidenceReference
  legacy_path: optional read-only locator
  binding_status: REFERENCE | LEGACY_ORIGINAL
```

Compatibility rules:

- Existing `evidence_file` + digest entries remain readable as `LEGACY_ORIGINAL` only when the original regular, non-symlink file still exists and its digest and domain schema validate.
- New reference-aware consumers operate on `EvidenceBindingV1`; they do not branch throughout install/activation/lifecycle code on path versus store.
- New successful writes must produce a reference-backed binding once a durable store is separately implemented and authorized.
- No silent in-place conversion of existing ProjectState, no schema-version masquerading, and no automatic deletion of legacy paths.
- A later schema proposal may add `evidence_reference` as an additive alternative to `evidence_file`, but it requires a separate compatibility decision and migration plan.

## 6. Resolver Design

### 6.1 Public responsibility

Define one narrow resolver abstraction owned by `governance.evidence`, not by Adoption:

```text
EvidenceResolver.resolve_verified(
    binding,
    expected_type,
    expected_schema_id,
    expected_schema_version,
) -> VerifiedEvidence
```

`VerifiedEvidence` should expose immutable bytes, the validated `EvidenceObject`, its `EvidenceReference`, and parsed domain content only after all checks pass. Callers must not receive unverified bytes.

The resolver may depend on the Phase 1 `EvidenceStore`; the Phase 1 store protocol must not import Adoption or lifecycle modules. Adoption supplies expected domain constraints through the call, preserving dependency direction:

```text
adoption/lifecycle consumer -> evidence resolver -> EvidenceStore
                                  |
                                  -> Phase 1 object/reference validation
```

### 6.2 Resolution and verification sequence

For a reference-backed binding, fail closed unless every step passes:

1. Parse and validate the `EvidenceReference` schema/version.
2. Ask the store to `verify(reference)` and require exact metadata equality.
3. Ask the store to `resolve(reference)`; rehash bytes and verify byte length again at the resolver boundary.
4. Require object/reference evidence type, schema ID, and schema version to match caller expectations.
5. Parse the original bytes using the declared media/domain format; reject ambiguous or non-canonical inputs where the existing contract requires canonical form.
6. Validate the parsed value against its existing domain schema.
7. Apply existing Adoption checks for lifecycle edge, status, target identity, previous state, ordered upstream digests, approvals, receipts, and Runtime bindings.

For a legacy-path binding, use the same domain checks after the existing safe-file and raw-byte digest checks. Legacy mode must never publish a reference implicitly during a read operation.

### 6.3 Failure semantics

All resolver failures are hard, non-mutating failures for the current operation:

| Condition | Proposed stable outcome |
| --- | --- |
| Reference malformed or unsupported version | `EVIDENCE_REFERENCE_INVALID` |
| Object absent | `EVIDENCE_OBJECT_MISSING` |
| Metadata/reference mismatch | `EVIDENCE_REFERENCE_MISMATCH` |
| Digest or byte-length mismatch | `EVIDENCE_INTEGRITY_FAILED` |
| Evidence type/schema mismatch | `EVIDENCE_CONTRACT_MISMATCH` |
| Domain schema invalid | `EVIDENCE_SCHEMA_INVALID` |
| Store unavailable | `EVIDENCE_STORE_UNAVAILABLE` |
| Legacy original missing | preserve `ORIGINAL_RECEIPT_EVIDENCE_NOT_RECOVERED` where already established; otherwise `LEGACY_EVIDENCE_MISSING` |
| Multiple candidate bindings/head ambiguity | `EVIDENCE_RESOLUTION_AMBIGUOUS` |

No fallback from a failed reference to a same-digest path, no search of arbitrary filesystem locations, no remote retrieval, no reconstruction, and no automatic repair. Resolver errors must occur before dependent Runtime mutation whenever possible; post-mutation publication failure remains a separately designed rollback/manual-review concern.

## 7. Existing Project Adoption Paths

### 7.1 New projects

- Require evidence-store capability/configuration during preflight, before installation writes.
- Publish and verify every required original authority object, then pass only verified bindings to lifecycle consumers.
- Record stable references for install, activation, later lifecycle events, upgrade, and recovery.
- Do not allow a successful new lifecycle operation to depend only on a temporary or caller-selected path.

This path cannot be enabled until a durable store and atomic publication semantics are separately authorized and implemented.

### 7.2 Existing projects with complete original evidence

- Continue to accept existing external paths read-only under current v1.5.2 validators.
- A future import/enrollment flow must be separate from ordinary lifecycle consumption: preview exact bytes and digests, validate the full chain, show proposed bindings, obtain explicit Owner approval, then publish originals without rewriting historical content.
- Imported objects must be classified `LEGACY_IMPORTED_ORIGINAL`; import time is not historical creation time, and imported status must not imply cryptographic authorship.
- Until that separate import capability exists, the project remains in legacy-path compatibility mode.

### 7.3 Existing projects missing historical evidence

- Remain blocked. Digests, current Runtime files, regenerated receipts, semantic equivalents, reports, or timestamps cannot replace missing original bytes.
- Do not manufacture enrollment history or mark a partial chain complete.
- A project may be explicitly re-adopted only through a future Owner-designed clean-start policy that does not claim continuity with missing history; that policy is outside Phase 2.
- Jingwei remains unchanged and blocked under the current facts.

## 8. Upgrade and Recovery Boundary

Phase 2 should provide interfaces and validation semantics only:

- resolver and verified-result types;
- binding adapter for reference-backed and validated legacy-path inputs;
- lifecycle consumer ports that request evidence by role and expected contract;
- stable error taxonomy;
- contract tests using `InMemoryEvidenceStore` and fixtures only.

Defer to later phases:

- durable filesystem store, configuration, permissions, locking, atomic object/index publication, and crash recovery;
- actual changes to install, activation, lifecycle transitions, framework upgrade, or recovery;
- ProjectState/schema evolution;
- legacy import/migration execution;
- event indexes, project identity enrollment/relocation, backup/restore, integrity audit, garbage collection, signing/PKI, and network/cloud stores.

Upgrade and recovery must not be the first integration consumers. The lowest-risk first consumer is read-only lifecycle evidence validation in a compatibility adapter; mutation-bearing install/activation, then upgrade/recovery, follow only after durable publication and rollback semantics are approved.

## 9. File and Module Boundary Proposal

Proposed later implementation ownership; no file is created or changed by this report:

| Boundary | Responsibility | Must not own |
| --- | --- | --- |
| `governance/evidence/models.py` | Phase 1 immutable object/reference contracts | Adoption stages or filesystem policy |
| `governance/evidence/core.py` | Minimal store protocol and test double | Durable backend or lifecycle branching |
| `governance/evidence/resolver.py` (proposed) | Binding parsing, store/path adapter, byte/object/domain prevalidation, stable resolver errors | Runtime mutation, store discovery, migration |
| `governance/adoption/evidence_registry.py` | Edge/type/status/domain rules; consume verified evidence | Object storage or arbitrary path search |
| `governance/adoption/lifecycle.py` | State-edge CAS after verified evidence | Direct store implementation or migration |
| `governance/adoption/installer.py`, `activation.py`, `framework_upgrade.py`, `recovery.py` | Existing operation semantics; later accept injected verified evidence ports | Store construction, implicit import, compatibility policy |
| `schemas/` | Explicit future versioned binding/state contracts | Silent reinterpretation of `1.0` fields |
| `tests/unit/evidence/` | resolver/store contract tests | production durability claims |
| Adoption tests | consumer compatibility, fail-closed and no-mutation assertions | real project migration or Jingwei fixtures |

Dependency rules:

- `governance.evidence` remains independent of `governance.adoption`.
- Durable backend selection is injected at the application/CLI composition boundary.
- There is one resolver; lifecycle consumers must not each implement their own path/reference logic.
- Existing validators are reused after resolution; Phase 2 does not duplicate or weaken them.

## 10. Risks and Required Controls

1. **False durability:** `InMemoryEvidenceStore` can validate integration contracts but cannot support production claims. Control: label it test-only and block mutation-bearing production integration without an approved durable backend.
2. **Split authority:** accepting both paths and references could create divergent originals. Control: a binding has one authority mode; reference failure never falls back, and import is explicit.
3. **Schema break:** replacing `evidence_file` in `project_state.schema.json` would invalidate existing Runtime state. Control: adapter-first design and separately versioned schema decision.
4. **TOCTOU:** evidence may change between validation and mutation. Control: consumers use resolved immutable bytes/results, revalidate state/head freshness immediately before mutation, and publish results atomically in a later store phase.
5. **Dependency inversion:** Adoption-specific semantics could leak into the store core. Control: caller-supplied expected contracts and one-way dependency from Adoption to evidence.
6. **Ambiguous identity/head:** digest-valid evidence may belong to another project or competing history. Control: retain `target_identity_digest`, require explicit project-instance/head design before durable enrollment, and fail on ambiguity.
7. **Error compatibility:** new generic errors could hide established recovery blockers. Control: stable resolver taxonomy with preservation of `ORIGINAL_RECEIPT_EVIDENCE_NOT_RECOVERED` where applicable.
8. **Metadata overclaim:** a digest verifies integrity, not authorship or historical truth. Control: reports and APIs must not claim signing/non-forgery without a separate trust model.
9. **Project rule gap:** the indexed project-specific rule file is absent. Control: Owner decides whether it must be restored before implementation authorization.

## 11. Proposed Construction Split

Each item requires a separate Owner-authorized execution envelope.

1. **Phase 2A — Resolver contracts:** add resolver/binding/verified-result types and focused in-memory tests; no lifecycle consumer changes.
2. **Phase 2B — Read-only lifecycle adapter:** adapt evidence registry validation to accept injected verified evidence while preserving the existing path API and state schema; prove identical validation outcomes and no mutation on resolver failure.
3. **Phase 2C — Durable store design/implementation:** choose store root, permissions, atomicity, index, identity, backup, and recovery semantics; implement only after those Owner gates close.
4. **Phase 2D — New install/activation integration:** publish authority inputs/results durably and bind references with rollback/manual-review coverage.
5. **Phase 2E — Remaining lifecycle edges:** switch Preflight through Closure to reference-backed evidence with backward compatibility.
6. **Phase 2F — Upgrade/recovery integration:** resolve exact historical receipts and append result evidence; retain all existing approval and stale-state checks.
7. **Phase 2G — Existing-project import:** separately approved preview/approval/import for complete originals only. No automatic migration and no Jingwei work.

Minimum later test gates should include resolver contract tests, corrupted/missing/mismatched object tests, legacy-path parity, unsupported-version rejection, ordered upstream-chain validation, cross-project rejection, ambiguity rejection, no state mutation on failure, and affected Adoption regression. Real stores, migrations, or external projects require their own Gate 0 and authorization.

## 12. Implementation Authorization Readiness

The design is sufficiently bounded to request authorization for **Phase 2A only**, but implementation is not authorized by this report.

Before Phase 2A authorization, the Owner must confirm:

1. adapter-first compatibility and no immediate ProjectState/schema migration;
2. the resolver API ownership under `governance.evidence` and one-way dependency direction;
3. stable failure semantics, including no fallback and preservation of the historical-missing-original blocker;
4. Phase 2A allowed files and tests, with all Adoption mutation paths forbidden;
5. whether the missing `agent_rules/11_project_specific_rules.md` must be restored first.

Authorization for Phase 2B or later additionally requires a dedicated plan for the exact consumer files and regression set. Mutation-bearing phases require Owner decisions on durable store root/permissions, atomic publication, identity/head binding, backup/restore, schema evolution, rollback, legacy import, and production scope.

Decision:

`PHASE2A_IMPLEMENTATION_AUTHORIZATION_REQUEST_READY`

`P1_PHASE2_IMPLEMENTATION_NOT_AUTHORIZED`

## 13. Design Validation and Operations

Read-only design checks performed:

- Phase 1 contract compatibility: PASS. The resolver composes over `EvidenceStore`, `EvidenceObject`, and `EvidenceReference` without changing them.
- Lifecycle semantic preservation: PASS BY DESIGN. Existing edge/type/status, target identity, previous-state, upstream-chain, approval, receipt, and Runtime bindings remain authoritative.
- Backward compatibility: PASS WITH OWNER GATE. Existing path-based state remains readable; schema mutation and automatic migration are deferred.
- Missing evidence behavior: PASS. Missing originals remain blocked and are never reconstructed.
- Runtime impact: NONE. No source or Runtime was modified and no tests were run because this phase is documentation-only.

Created:

- `.agent-reports/AGC_P1_PHASE2_EVIDENCE_STORE_INTEGRATION_DESIGN_DECISION_REPORT_V1_20260912.md`

Not modified or executed:

- source, schemas, install, activation, lifecycle, upgrade, recovery, Adoption, Jingwei, migration, real evidence/store data, existing reports, registries, changelog, versioning, commit, push, release, network, or external API.

## 14. Conclusion and Stop

`P1_PHASE2_EVIDENCE_STORE_INTEGRATION_DESIGN_READY`

The implementation boundary is clear, but no implementation authorization is inferred. Stop here and wait for Owner direction.
