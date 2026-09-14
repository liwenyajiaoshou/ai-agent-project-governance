# AGC P1 Phase 2B.2 Lifecycle Consumer Integration Design Decision Report V1

Date: 2026-09-12

## Decision status

`P1_PHASE2B2_LIFECYCLE_CONSUMER_INTEGRATION_DESIGN_READY`

This is a design-only decision. It does not authorize or perform lifecycle
integration, source or schema changes, installation, activation, upgrade,
recovery, migration, Adoption rollout, Jingwei work, Git operations, or release.
Implementation status remains `NOT_AUTHORIZED` pending the Owner decision listed
below.

## Task envelope and baseline

- Project mode: `ADAPTATION`.
- Task class and level: `B / Level 2`; bounded consumer-integration design and one
  report write.
- Allowed write: only this report.
- Forbidden write: source, tests, schemas, lifecycle/runtime state, formal
  registries/changelog, install/activation/upgrade/recovery/migration/Jingwei, and
  Git history or remotes.
- Rules read: `AGENTS.md`, `agent_rules/RULES_INDEX.yaml`,
  `agent_rules/00_rule_router.md`, `agent_rules/15_plan_adaptation_rules.md`,
  `agent_rules/01_task_classification.md`,
  `agent_rules/task_cards/B_standard_task.md`,
  `agent_rules/02_architecture_rules.md`,
  `agent_rules/04_trace_and_index_rules.md`,
  `agent_rules/06_data_safety_rules.md`,
  `agent_rules/07_testing_rules.md`, and `docs/VERSIONING.md`.
- `agent_rules/11_project_specific_rules.md`, referenced by the rule index, is
  absent. This pre-existing gap is outside the task and was not repaired.
- The requested `.agent-plans/...` repository copy is absent. The identically
  named Owner attachment under `C:/Users/范德彪/Downloads/` was read as the
  explicitly authorized plan and was not copied into the repository.
- Current branch/HEAD: `main` at
  `6d8d6621b58bb832121afee944c80526f7385a71`, matching Phase 2B.1 and ahead of
  `origin/main` by four commits.
- Verified ancestors: v1.5.2
  `b9023c5e131088115b1c9e704a27be6c232d6cb7`, Phase 1
  `b3f84d011384e778b15ac3213d9374114eebef8b`, and Phase 2A
  `53018127440370a74a63378513db572e4ba2388e`.
- The starting worktree contained pre-existing untracked reports. They were
  preserved unchanged.

## Phase 2B.1 state and Phase 2B.2 goal

Phase 2B.1 is present and verified by its implementation report: it introduced
`LegacyEvidenceFile`, `ReferenceEvidence`, immutable
`NormalizedVerifiedEvidence`, and `LifecycleEvidenceAdapter`, while preserving
`EDGE_REQUIREMENTS` as the lifecycle semantic authority. It did not read or
write ProjectState and did not connect to a lifecycle consumer.

Phase 2B.2 should later connect that adapter to the existing
`transition_project_state` flow so a caller can explicitly choose legacy-file or
reference evidence. The integration must preserve the existing transition graph,
CAS semantics, ProjectState schema and legacy output, and must prove:

```text
any validation/integration failure
    => identical ProjectState bytes and digest
```

## Consumer integration decision

### Ownership

- `transition_project_state` remains the sole mutation coordinator and the only
  ProjectState write site.
- `LifecycleEvidenceAdapter` owns current-source transport verification and
  normalization. It never mutates state or an evidence store.
- `evidence_registry` owns edge/type/status, target, previous-state, and ordered
  upstream-chain semantics. `EDGE_REQUIREMENTS` must not be duplicated.
- `EvidenceResolver` owns reference/object integrity and declared schema
  verification only. Resolver success does not authorize a lifecycle edge.

Dependency direction remains:

```text
governance.adoption.lifecycle
  -> governance.adoption.lifecycle_evidence_adapter
      -> governance.adoption.evidence_registry
      -> governance.evidence
```

`governance.evidence` must not import Adoption or lifecycle concepts.

### Proposed public boundary

Preserve the current `evidence_path` call form without behavior change. Add an
explicit opt-in `evidence_source` for the Phase 2B.1 discriminated source and an
explicit prior-reference binding collection for mixed-chain validation. Exactly
one current source is legal:

- legacy: the existing `evidence_path`, internally wrapped as
  `LegacyEvidenceFile`;
- reference: `ReferenceEvidence(binding, resolver)` supplied explicitly by the
  caller.

Both, neither, an unrecognized source, duplicate prior bindings, an unused
binding, or a binding whose reference digest differs from the matching state
entry must fail closed. There is no environment/global resolver, store lookup,
filesystem scan, temporary-file conversion, digest-to-reference guessing, or
cross-source fallback.

The prior-reference collection is request-scoped and read-only. It is not a new
registry of authority. It may satisfy only lifecycle entries whose recorded
evidence type is one of the registered transition evidence types and which have
no `evidence_file`. Existing activation/recovery provenance entries remain under
their current digest-only/path-backed behavior. If an entry cannot be classified
unambiguously from the baseline invariants, integration must stop in
`ADAPTATION`; it must not infer provenance.

### Lock, CAS, and validation order

All state-dependent work occurs inside the existing per-ProjectState lifecycle
lock. The required order is:

1. Acquire the existing lifecycle lock.
2. Read the exact current ProjectState bytes once and compute their SHA-256.
3. Compare that digest with `expected_current_state_digest`; stale state fails
   before any evidence resolution.
4. Parse and validate ProjectState, then verify the expected current stage and
   the single registered `NEXT` edge.
5. Validate the complete ordered historical chain against a source-aware helper:
   re-read and hash path-backed entries; resolve every required reference-backed
   entry from the exact supplied binding; reject missing, extra, duplicate,
   reordered, mismatched, unsafe, or changed sources.
6. Freeze the resulting ordered digest list and reuse it. Do not call a second
   helper that re-reads historical evidence between current-evidence validation
   and state construction.
7. Invoke `LifecycleEvidenceAdapter.resolve` for the current explicit source,
   binding it to the requested edge, target identity, current state digest, and
   the frozen upstream digest list.
8. Construct the next state in memory from the normalized result. Validate it
   through the unchanged ProjectState schema and model.
9. Use the existing atomic writer as the sole mutation point.

No resolver or adapter work may happen before the lock/CAS check, because evidence
validated against a stale state must never become eligible to advance a newer
state. Holding the state lock does not lock external evidence files or a store;
therefore exact bytes/digests returned by the successful validation pass must be
reused without a second source read.

### State recording with unchanged ProjectState schema

- Legacy success must append exactly the existing entry shape, including
  `evidence_digest`, `evidence_file_digest`, and canonical `evidence_file`.
- Reference success may append only fields already accepted by the current
  schema: stage, type, exact byte digest, previous-state digest, target identity,
  and ordered upstream digests. It must not fabricate `evidence_file` or add a
  reference field.
- The canonical chain identity remains SHA-256 of the exact validated evidence
  bytes, independent of transport.
- No existing entry is rewritten. Mixed mode is validation at read time, not
  migration.

This is intentionally an in-process compatibility bridge. Current ProjectState
cannot persist a complete `EvidenceReference`, so a later process cannot rebuild
reference provenance from state alone. Restart-safe discovery, a durable
reference manifest/registry, or an additive ProjectState contract requires a
separate Owner decision and is outside Phase 2B.2.

## Compatibility and mixed-chain rules

- Legacy-only callers and chains require no resolver or reference bindings and
  must produce byte-equivalent state output to the Phase 2B.1 baseline.
- A reference-backed current transition never falls back to a path. A path-backed
  transition never searches a store.
- A mixed chain preserves state order exactly. Path-backed entries are verified
  from their recorded paths; reference-backed lifecycle entries are resolved from
  the exact request-scoped bindings; existing non-transition provenance entries
  retain baseline treatment.
- Every current evidence document must name the frozen ordered digest list. A
  different order, missing/extra digest, target mismatch, stale
  `previous_state_digest`, or wrong edge type/status blocks the transition.
- The unchanged schema limitation means mixed reference chains are supported only
  when the caller can supply complete provenance explicitly. No rollout claim may
  describe this as durable or restart-self-contained.

## Failure and rollback decision

Adapter, resolver, registry, schema, CAS, state-model, and unexpected integration
exceptions must propagate as a blocked transition before the atomic writer. The
ProjectState file must remain byte-identical; the adapter must not publish,
delete, or rewrite evidence; and no alternate source may be attempted. The
existing lock file may be opened as part of the current locking protocol, so the
no-mutation guarantee is specifically ProjectState and evidence-store/content
mutation, not lock-file metadata.

For later implementation:

- integration failure: preserve the legacy public path route as the default and
  do not enable the reference route outside direct tests;
- adapter/resolver failure: fail the edge without fallback or retry against a
  different source;
- regression failure: stop, leave Phase 2B.2 unaccepted, and restore the two
  affected production files to the accepted Phase 2B.1 behavior using a
  recoverable review/revert process; do not proceed to rollout or Phase 2B.3.

Rollback cannot make already-recorded reference entries legacy-readable because
they have no path. Therefore Phase 2B.2 implementation tests may use temporary
state only, and any real lifecycle consumption remains forbidden until a later
rollout authorization defines durable provenance and rollback.

## Proposed implementation boundary

The smallest later write scope is:

- modify `governance/adoption/lifecycle.py` only to select the explicit source,
  enforce the lock/CAS sequence, invoke the adapter, and retain one atomic write;
- modify `governance/adoption/evidence_registry.py` only for a source-aware,
  read-only historical-chain validation result that returns one frozen digest
  sequence while preserving `upstream_digests` compatibility;
- extend `tests/unit/test_adoption_lifecycle_foundation.py` for consumer, CAS,
  legacy-parity, mixed-chain, and no-mutation behavior;
- extend `tests/unit/adoption/test_lifecycle_evidence_adapter.py` only if an
  integration-discovered contract gap cannot be tested at the consumer boundary.

Not required by the current design and therefore forbidden in the later bounded
implementation unless separately authorized: new production modules,
`governance/adoption/lifecycle_evidence_adapter.py`,
`governance/evidence/**`, ProjectState or lifecycle-evidence schemas,
activation/install/upgrade/recovery modules, migrations, CLI/rollout paths,
Jingwei, registries/changelog, release artifacts, and real target data.

If the implementation needs any of those items, or cannot classify historical
reference entries without inference, it must stop and return to ADAPTATION.

## Test strategy for a separately authorized implementation

Focused Level 1:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.unit.adoption.test_lifecycle_evidence_adapter \
  tests.unit.test_adoption_lifecycle_foundation -v
```

Required cases:

- unchanged legacy API and byte-equivalent appended legacy entry;
- successful reference current transition with no fabricated path;
- legacy -> reference, reference -> legacy, and multiple-reference ordered chains;
- absent/extra/duplicate/reordered/mismatched prior bindings;
- unsafe/changed/missing legacy files and missing/corrupt reference objects;
- wrong type/status/schema/target/previous-state/upstream digest;
- stale CAS blocks before resolver invocation;
- every failure leaves exact ProjectState bytes/digest unchanged;
- resolver/store doubles prove no publish, discovery, or fallback;
- historical sources are each validated once and the frozen digest list is reused;
- `CLOSED` flag behavior and invalid-edge behavior remain unchanged.

Bounded Level 2 regression:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.unit.evidence.test_core \
  tests.unit.evidence.test_resolver \
  tests.unit.adoption.test_lifecycle_evidence_adapter \
  tests.unit.test_adoption_lifecycle_foundation \
  tests.unit.test_agent_adopt_activation \
  tests.unit.test_adoption_remediation_security \
  tests.unit.test_v1_5_2_p0 -v
```

Then run the bounded unit suite only if explicitly included in the implementation
authorization. Recovery/activation tests are regression-only; no real install,
activation, upgrade, recovery, migration, network, durable store, Adoption target,
or Jingwei execution is permitted. Evidence must record the exact command,
working directory, Python/dependency versions, environment variable names, test
counts/failures, and baseline HEAD under `GOV-EVIDENCE-001`.

No automated tests were run for this design-only task because runtime and source
were not changed. Validation here consists of read-only rule, baseline, contract,
schema, source, and existing-test inspection.

## Risks

| Risk | Control |
| --- | --- |
| Current schema cannot reconstruct references after restart | Require exact request-scoped bindings and prohibit rollout/durability claims; obtain a separate Owner decision. |
| Missing provenance is mistaken for a reference | Classify only from accepted baseline invariants; ambiguity returns to ADAPTATION. |
| Resolver success is treated as transition authority | Always run registry lifecycle checks against the current locked state. |
| Evidence changes between reads | Validate each historical source once and reuse the frozen digest sequence. |
| Stale state advances | CAS and edge validation occur before evidence resolution under the same lock. |
| Silent fallback masks corruption/outage | Exactly one explicit current source; no discovery or fallback. |
| Legacy output changes | Preserve the public path form and require byte-equivalent state-entry regression. |
| Rollback strands reference-backed state | Limit implementation to temporary test state; defer real consumption to rollout authorization. |

## Implementation authorization readiness

The design is ready for Owner review, but Phase 2B.2 implementation is **not
authorized** by this report. Authorization conditions are not complete until the
Owner explicitly confirms all of the following:

1. the ownership, dependency, lock/CAS sequence, and frozen-chain decisions;
2. the proposed two-production-file and bounded-test write scope;
3. the exact backward-compatible public call shape and prior-reference binding
   collection shape;
4. the baseline classification rule for path-backed, reference-backed lifecycle,
   and existing activation/recovery provenance entries;
5. that Phase 2B.2 is temporary/in-process only and that restart-safe provenance,
   schema evolution, migration, rollout, and real adoption consumption remain
   deferred;
6. the exact required commands, bounded-unit-suite decision, implementation
   report path, baseline commit, and unchanged forbidden scope.

Until those decisions are confirmed in a separate implementation authorization,
status is `DESIGN_READY / IMPLEMENTATION_NOT_AUTHORIZED`.

## Stop condition

Only this report was created. No source, test, schema, Runtime, lifecycle state,
formal registry, or Git history was changed. Stop here and wait for Owner.
