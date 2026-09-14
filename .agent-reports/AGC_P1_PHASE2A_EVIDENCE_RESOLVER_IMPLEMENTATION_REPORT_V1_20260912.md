# AGC P1 Phase 2A Evidence Resolver Implementation Report V1

## Acceptance conclusion

`P1_PHASE2A_EVIDENCE_RESOLVER_IMPLEMENTATION_PASS`

The authorized Phase 2A resolver contracts are implemented and verified. The
change is limited to `governance.evidence` and focused in-memory unit tests.

## Baseline and task envelope

- v1.5.2 closure baseline checked: `b9023c5e131088115b1c9e704a27be6c232d6cb7`.
- Phase 1 baseline and task starting HEAD: `b3f84d011384e778b15ac3213d9374114eebef8b`.
- Starting branch: `main`.
- Execution mode: `EXECUTION`; task class: B / Level 2.
- No external access, real evidence write, database write, migration, or irreversible operation was performed.

## Actual modifications

- `governance/evidence/resolver.py`: added reference-only `EvidenceBinding`, immutable `VerifiedEvidence`, injected-store `EvidenceResolver`, and stable `EvidenceResolutionError` codes. The resolver validates the reference, store metadata, bytes/digest/length, expected evidence contract, and declared JSON schema before returning a result. It has no lifecycle, filesystem, discovery, or fallback behavior.
- `governance/evidence/__init__.py`: exported the Phase 2A public contracts.
- `tests/unit/evidence/test_resolver.py`: added focused resolver contract tests.

## Verification evidence

Level 1 command (working directory: `/home/liyouran1997/projects/ai-agent-project-governance`):

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.unit.evidence.test_core tests.unit.evidence.test_resolver -v
```

Result: 10 passed, 0 failed, 0 skipped.

Level 2 command (working directory: `/home/liyouran1997/projects/ai-agent-project-governance`):

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/unit/evidence -p 'test_*.py' -v
```

Result: 13 passed, 0 failed, 0 skipped. Python: `3.12.3`. No markers,
environment variables beyond `PYTHONDONTWRITEBYTECODE`, basetemp, or JUnit file
were used. `git diff --check` passed. No Level 3 full regression was required
because no cross-module or architecture-level behavior changed.

Required Phase 2A test outcomes:

- EvidenceBinding and immutable VerifiedEvidence: passed.
- Resolver success: passed.
- Missing object: `EVIDENCE_OBJECT_MISSING`, passed.
- Digest mismatch: `EVIDENCE_INTEGRITY_FAILED`, passed.
- Reference mismatch: `EVIDENCE_REFERENCE_MISMATCH`, passed.
- Unsupported reference schema/version: `EVIDENCE_REFERENCE_INVALID`, passed.
- Fail-closed expected-contract mismatch: `EVIDENCE_CONTRACT_MISMATCH`, passed.

## Scope and safety result

Not modified: install, activation, Adoption lifecycle, ProjectState schema,
upgrade, recovery, durable filesystem storage, migration, Jingwei, schemas,
or existing lifecycle consumer paths. No real evidence was published or written.
No commit, push, tag, release, or PR was performed.

Existing untracked reports were preserved. The only new report from this task is
this file. Stop here for Owner acceptance; Phase 2B and later remain out of
scope.
