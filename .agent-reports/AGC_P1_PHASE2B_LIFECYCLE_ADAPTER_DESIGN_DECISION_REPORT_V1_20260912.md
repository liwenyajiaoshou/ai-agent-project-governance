# AGC P1 Phase 2B Lifecycle Adapter Design Decision Report V1

Date: 2026-09-12

## Decision status

`P1_PHASE2B_LIFECYCLE_ADAPTER_DESIGN_READY`

This report completes design only. It does not authorize or perform lifecycle integration, source or schema changes, migration, Existing Project Adoption enablement, installation, activation, upgrade, recovery, Jingwei work, Git operations, or release work.

The design is `ready_for_owner_confirmation`. Phase 2B implementation is **not authorized by this report**.

## Task envelope and baseline checks

- Project mode: `ADAPTATION`.
- Task class and execution level: `B / Level 2`, bounded architecture design and one report write.
- Allowed write: only this report under `.agent-reports/`.
- Forbidden write: all source, test, schema, lifecycle, install, activation, upgrade, recovery, registry, task/changelog, migration, adoption-target, and Jingwei files.
- Rules read: `AGENTS.md`, `agent_rules/RULES_INDEX.yaml`, `agent_rules/00_rule_router.md`, `agent_rules/15_plan_adaptation_rules.md`, `agent_rules/01_task_classification.md`, `agent_rules/task_cards/B_standard_task.md`, `agent_rules/02_architecture_rules.md`, `agent_rules/04_trace_and_index_rules.md`, `agent_rules/06_data_safety_rules.md`, `agent_rules/07_testing_rules.md`, and `docs/VERSIONING.md`.
- `agent_rules/11_project_specific_rules.md` is referenced by the rule index but is absent in this template repository. That pre-existing governance gap is not repaired or expanded into this task.
- The requested repository plan path `.agent-plans/AGC_P1_PHASE2B_LIFECYCLE_ADAPTER_DESIGN_PLAN_V1_20260912.md` does not exist. The Owner-provided attachment at `C:/Users/范德彪/Downloads/AGC_P1_PHASE2B_LIFECYCLE_ADAPTER_DESIGN_PLAN_V1_20260912.md` was read as the explicitly named task plan; it was not copied into the repository.
- Current HEAD: `53018127440370a74a63378513db572e4ba2388e`, matching the stated Phase 2A baseline.
- Ancestors inspected: v1.5.2 closure `b9023c5e131088115b1c9e704a27be6c232d6cb7`; Phase 1 `b3f84d011384e778b15ac3213d9374114eebef8b`.
- Starting worktree contained multiple pre-existing untracked reports, including the Phase 1 and Phase 2A reports. They were treated as Owner assets and left unchanged.
- Phase 2A status: resolver contracts exist at the stated commit; `EvidenceResolver` is reference-only, store-injected, immutable on success, and fail-closed with stable error codes. It intentionally has no lifecycle, filesystem discovery, fallback, or migration behavior.

## Phase 2B goal

Design the narrow boundary through which the existing Adoption lifecycle can consume either:

1. a legacy, explicitly supplied lifecycle evidence file; or
2. an explicitly supplied durable `EvidenceBinding` resolved by `EvidenceResolver`.

Both inputs must produce one equivalent, already-verified lifecycle evidence value before any ProjectState mutation is eligible. Phase 2B must preserve existing state-edge rules, target binding, previous-state binding, upstream-chain ordering, CAS semantics, atomic state writes, and non-production closure semantics.

## Current lifecycle gap

The current lifecycle is path-only:

- `transition_project_state` requires an `evidence_path`.
- `validate_evidence_file` reads and schema-validates that path, checks edge type/status, target identity, previous-state digest, and ordered upstream digests.
- ProjectState records `evidence_digest`, optional-equivalent `evidence_file_digest`, and `evidence_file` for new path-backed transitions.
- `upstream_digests` re-reads every recorded legacy file when a path exists and blocks if the file is missing, unsafe, or changed.

Phase 2A adds verified reference resolution, but no Adoption consumer can use it. Passing resolved JSON directly to the current transition would bypass the single evidence registry. Materializing reference bytes as a temporary file would misrepresent provenance and weaken restart behavior. Adding fallback inside `EvidenceResolver` would violate its reference-only contract and invert ownership.

There is also a persistence boundary: current ProjectState can retain a digest-only lifecycle entry, but—without a ProjectState schema change—it cannot retain a complete `EvidenceReference`. Therefore a later process cannot reconstruct reference provenance from state alone. Phase 2B must not hide this limitation.

## Adapter design

### Ownership and dependency direction

The adapter belongs to `governance.adoption`, adjacent to the existing Adoption evidence registry. It is an anti-corruption boundary between lifecycle semantics and evidence transport.

Dependency direction is strictly:

```text
governance.adoption.lifecycle
    -> governance.adoption.lifecycle_evidence_adapter
        -> governance.adoption.evidence_registry   (edge and lifecycle checks)
        -> governance.evidence                     (binding/resolver contracts)
```

`governance.evidence` must not import Adoption, ProjectState, lifecycle stages, or filesystem policy. `EvidenceResolver` remains unchanged and receives no path discovery or legacy fallback behavior.

### Proposed consumer contract

The lifecycle adapter should accept one explicit discriminated source, never two optional competing inputs:

- `LegacyEvidenceFile(path)`; or
- `ReferenceEvidence(binding, resolver)`.

It returns an immutable normalized result conceptually containing:

- parsed lifecycle evidence content;
- canonical evidence digest (SHA-256 of the exact validated bytes);
- source kind (`legacy_file` or `reference`);
- legacy path only for a legacy source;
- the verified reference only in the in-process result;
- evidence type, status, target identity, prior-state digest, and ordered upstream digests already checked against the requested edge.

The normalized result is not authority by itself. It is valid only for the exact current state bytes, target identity, requested edge, and expected upstream chain used during validation.

### Validation sequence

Inside the same lifecycle lock used by `transition_project_state`, and before constructing or writing updated state:

1. Read current ProjectState bytes and compute the current digest.
2. Enforce expected state digest and the one-step `NEXT` edge.
3. Revalidate the ordered upstream chain using the source-aware registry adapter.
4. For a legacy source, retain current safety checks: explicit path, regular file, no symlink, exact bytes, lifecycle schema, and recomputed digest.
5. For a reference source, call the injected `EvidenceResolver.resolve_verified` with the exact expected lifecycle evidence type, `adoption_lifecycle_evidence.schema.json`, and schema version `1.0`.
6. Independently apply the existing lifecycle checks to normalized content: required edge type/status, target identity, current ProjectState digest, and exact ordered upstream digests.
7. Reconfirm that normalized bytes hash to the reference/file digest.
8. Only after all checks pass, construct the next state, validate it, and use the existing atomic writer.

This keeps transport verification and lifecycle authorization distinct: resolver success proves object integrity and declared schema; it does not authorize a lifecycle edge.

### Registry behavior and upstream evidence

The existing `EDGE_REQUIREMENTS` remains the sole edge-to-type/status truth. The new adapter must reuse it rather than duplicate it.

For compatibility without changing ProjectState schema:

- legacy entries continue to be re-read through their recorded `evidence_file`;
- reference-backed entries may be recorded using the existing required `evidence_digest` and existing provenance fields, with no fabricated `evidence_file`;
- every operation involving a state whose chain contains reference-backed entries must receive an explicit, exact reference-binding set from the caller and re-resolve each reference in lifecycle order;
- each supplied binding digest must equal the corresponding ProjectState entry digest; missing, extra, reordered, duplicated, or mismatched bindings fail closed;
- no store discovery, digest-to-reference guessing, global singleton, environment lookup, or filesystem scan is allowed.

This is a bounded compatibility bridge, not durable self-description. Restart-safe reference reconstruction requires a later Owner decision: either authorize an additive ProjectState/reference-registry contract or require an external provenance manifest whose lifecycle and authority are separately defined. That decision is outside the current schema prohibition.

## Legacy compatibility decision

- Existing callers that explicitly provide `evidence_path` retain byte-for-byte path validation and current state-entry behavior.
- Legacy and reference-backed entries may coexist in one ordered chain. Each item is validated according to its recorded source evidence: path-backed entries by exact file; reference-backed entries by an explicitly supplied binding matched to the recorded digest.
- The canonical chain identity remains the SHA-256 of exact evidence bytes. Downstream `upstream_evidence_digests` ordering does not change.
- A reference-backed request must never fall back to a legacy file when resolution, integrity, metadata, or schema validation fails.
- A missing legacy path must never trigger store discovery.
- The adapter must reject ambiguous inputs, including both path and reference, neither input, or a digest collision/mismatch across sources.
- Temporary-file conversion, implicit path derivation from metadata, symlink acceptance, unverified cached JSON, and “parse first, verify later” are forbidden.

## Lifecycle safety decision

Every adapter/resolver failure blocks the state edge. The externally observable invariant is:

```text
failure => no ProjectState write and identical ProjectState bytes/digest
```

The invariant applies to missing objects/files, unavailable stores, unsafe paths, reference or metadata mismatch, digest/length corruption, invalid UTF-8/JSON/schema, wrong type/status, target mismatch, stale previous-state digest, upstream-chain mismatch, incomplete reference bindings, invalid edge, and any unexpected adapter exception.

CAS remains authoritative. Evidence resolution must occur after the lifecycle lock and current-state digest check so the verified content is bound to the state that may advance. The adapter must not write state, publish evidence, mutate the store, alter evidence content, or retry against a different source. `transition_project_state` remains the sole state mutation coordinator and retains atomic write behavior.

Existing state digest semantics remain unchanged: the exact current ProjectState bytes are hashed before validation; evidence must name that digest; the next state is validated before atomic replacement. No schema field, stage, edge, or closure meaning changes in Phase 2B.

## Proposed file boundary for later implementation

The smallest implementation boundary is:

- New `governance/adoption/lifecycle_evidence_adapter.py`: discriminated source types, immutable normalized result, source-aware validation orchestration, and stable adapter error translation.
- Modify `governance/adoption/evidence_registry.py`: expose reusable content/edge validation and source-aware upstream validation without duplicating `EDGE_REQUIREMENTS`; keep the legacy public path validator compatible.
- Modify `governance/adoption/lifecycle.py`: accept or invoke the adapter within the existing lock/CAS flow while keeping one state-write site.
- New focused unit tests under `tests/unit/` for adapter contracts; extend existing adoption lifecycle tests only where needed for consumer/CAS regression.

Explicitly outside that implementation boundary: `governance/evidence/resolver.py`, evidence store discovery or persistence, ProjectState schema, lifecycle evidence schema, install/activation/upgrade/recovery paths, migration, CLI enablement, Existing Project Adoption rollout, Jingwei, docs/registries/changelog, and release artifacts.

If implementation cannot support mixed-chain revalidation without adding persistent reference provenance, it must stop and return to ADAPTATION; it must not silently broaden the schema or introduce an implicit registry.

## Testing strategy for authorized implementation

### Adapter contract tests

- reference success returns immutable normalized evidence with exact content digest;
- every Phase 2A stable resolver error blocks with no alternate-source lookup;
- wrong lifecycle type/status, target identity, previous-state digest, schema version, or upstream order blocks;
- ambiguous source construction blocks;
- resolver and store are injected; no discovery or writes occur.

### Legacy parity tests

- existing legacy-file success produces the same state transition and lifecycle entry as the pre-adapter path;
- missing, symlinked, changed, malformed, wrong-edge, stale-state, and wrong-upstream legacy evidence remains blocked;
- legacy-only chains require no reference registry;
- mixed chains preserve digest order and validate each prior item through its own source path.

### Failure and no-mutation tests

For every adapter, resolver, registry, schema, CAS, and unexpected failure class, capture ProjectState bytes and digest before the call and assert they are identical afterward. Also assert that no evidence publish/store mutation and no fallback lookup occurred.

Include race tests showing that a stale expected digest blocks before state replacement and that evidence validated for one state cannot advance a concurrently changed state.

### Lifecycle regression scope

Run focused evidence core/resolver tests, adapter tests, current lifecycle foundation tests, activation lifecycle tests, and v1.5.2 recovery tests. The recovery suite is regression-only: Phase 2B must not modify recovery behavior. Then run the bounded unit suite because the consumer boundary crosses `governance.evidence` and `governance.adoption`. No real network, filesystem Evidence Store, production data, migration, install, activation, upgrade, recovery execution against a real target, or full external adoption run is permitted.

Verification evidence must record command, working directory, Python/dependency versions, environment variable names, test count/failures, and baseline HEAD in accordance with `GOV-EVIDENCE-001`. Exact commands should be finalized in the implementation authorization plan after the Owner selects the reference-provenance option.

## Risks and controls

| Risk | Required control |
| --- | --- |
| Reference provenance cannot be reconstructed from current ProjectState alone | Require explicit complete binding injection for reference-backed chain entries; obtain a separate Owner decision before durable/restart-safe rollout. |
| Resolver success is mistaken for lifecycle authority | Always run edge, status, target, prior-state, and upstream checks after resolution. |
| Silent fallback masks corruption or outage | No cross-source fallback under any error. |
| TOCTOU between evidence validation and state mutation | Resolve and validate under the existing lifecycle lock, then retain CAS and atomic replacement. |
| Duplicate edge logic diverges | Keep `EDGE_REQUIREMENTS` in the existing Adoption evidence registry as the single truth. |
| Adapter accidentally publishes or mutates evidence | Consumer interface is resolve/validate-only; use read-only/failing test doubles to prove no publish call. |
| Legacy behavior regresses | Preserve the legacy validator as a compatible wrapper and require parity tests. |
| “Compatibility” becomes migration | No rewriting of prior ProjectState entries or evidence files; mixed mode is read-time validation only. |

## Proposed implementation split

1. **Phase 2B.1 — adapter contracts:** add the Adoption-owned discriminated source and normalized verified result; refactor reusable registry validation; unit-test without lifecycle mutation.
2. **Phase 2B.2 — lifecycle consumer integration:** call the adapter inside the existing transition lock, preserve legacy entry output, add reference-backed and mixed-chain behavior, and prove no mutation on failure.
3. **Phase 2B.3 — bounded regression:** run focused Evidence, Adoption lifecycle, activation, and v1.5.2 recovery regression plus the unit suite; produce an implementation report only.
4. **Later, separately authorized durability decision:** choose additive state/reference provenance or an external formal reference manifest before any restart-safe rollout, migration, Existing Project Adoption use, or Jingwei integration.

Each split requires an explicit Owner authorization retaining the forbidden scope. Phase 2B.2 is lifecycle integration and is therefore expressly outside the current task.

## Implementation authorization readiness

The architecture boundary is sufficiently defined for Owner review, but the conditions for Phase 2B implementation authorization are **not yet complete**.

Before implementation, the Owner must explicitly confirm:

1. the proposed dependency direction and four-file/test boundary;
2. whether Phase 2B is limited to an in-process explicit reference-binding registry under the unchanged ProjectState schema;
3. that restart-safe reference reconstruction, schema evolution, migration, rollout, and actual Existing Project Adoption consumption remain deferred;
4. the exact allowed source/test files, forbidden files, required regression commands, report path, and baseline commit;
5. whether Phase 2B.1 and Phase 2B.2 are separately authorized, because Phase 2B.2 is lifecycle integration currently forbidden.

Until those points are confirmed, status remains `ready_for_owner_confirmation`, not `confirmed`, and no implementation may start.

## Verification and stop condition

Manual read-only checks were used to inspect governance rules, Git status/history, the Phase 1 and Phase 2A reports, Evidence Store/Resolver contracts, Adoption evidence registry and lifecycle transition logic, ProjectState and lifecycle evidence schemas, and relevant lifecycle tests/docs. No automated tests were run because this task made no runtime or source change; the later implementation test plan is defined above.

Only this report was created. Runtime behavior is unchanged. Stop here and wait for Owner direction.
