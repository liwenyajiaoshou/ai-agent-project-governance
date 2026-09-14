# AGC P1 Phase 1 Evidence Store Core Implementation Report V1

Date: 2026-09-12

## Result

`P1_PHASE1_EVIDENCE_STORE_CORE_IMPLEMENTATION_PASS`

The authorized Phase 1 core has been added without lifecycle integration, a filesystem-backed store, migration, or any Jingwei work.

## Authorization and Boundary

- Baseline checked: `main` at `b9023c5e131088115b1c9e704a27be6c232d6cb7`.
- Execution mode: `EXECUTION`; Level 2, B-class bounded extension of the existing `governance.evidence` package.
- Read for this task: `AGENTS.md`, `RULES_INDEX.yaml`, rule router, classification, cost-aware testing, plan-adaptation execution envelope, B task card, architecture, traceability, data-safety, testing, code-quality, versioning rules, the Owner authorization plan, and directly related evidence/schema/test assets.
- The pre-existing seven untracked reports were observed before implementation and left unchanged.

## Modified Files

- `governance/evidence/models.py`: immutable `EvidenceObject` and `EvidenceReference` models, JSON-safe detached metadata, SHA-256 helper, and fail-closed digest/reference validation.
- `governance/evidence/core.py`: `EvidenceStore` protocol and process-local `InMemoryEvidenceStore` test double. It is deliberately non-persistent and creates no real Evidence Store.
- `governance/evidence/__init__.py`: Phase 1 public exports.
- `schemas/durable_evidence_object.schema.json` and `schemas/durable_evidence_reference.schema.json`: additive `1.0` contracts; unsupported versions are rejected.
- `tests/unit/evidence/test_core.py`: object/reference schema, integrity, corruption, reference-mismatch, and incompatible-schema tests.
- `tests/unit/test_schema_contracts.py`: registered the two additive schemas in the schema inventory assertion.

## Verification Evidence

Working directory for every command: `/home/liyouran1997/projects/ai-agent-project-governance`.

| Level | Command | Result |
| --- | --- | --- |
| 1 (attempt) | `python -m unittest tests.unit.evidence.test_core tests.unit.evidence.test_manifest tests.unit.test_schema_contracts` | Did not start: `/bin/bash: python: command not found`; no tests ran. |
| 1 | `python3 -m unittest tests.unit.evidence.test_core tests.unit.evidence.test_manifest tests.unit.test_schema_contracts` | PASS — 13 tests in 0.287s. This covers schema validation, object/reference validation, digest verification, and corrupted evidence rejection. |
| 2 | `python3 -m unittest discover -s tests/unit -p 'test_*.py'` | PASS — 225 tests in 50.714s. |
| static | `git diff --check` | PASS — no whitespace errors. |
| environment | `python3 --version` | `Python 3.12.3`. |
| dependency | `python3 -c "import jsonschema; print('jsonschema=' + jsonschema.__version__)"` | `jsonschema=4.10.3`; command emitted Python's deprecation warning for `jsonschema.__version__`, but exited successfully. |

No environment variables, markers, basetemp, JUnit output, network calls, external writes, database writes, or migrations were used.

## Safety and Non-Scope Confirmation

- No install, activation, upgrade, recovery, Adoption, or Jingwei source was modified.
- No existing authority contract was modified.
- No real filesystem/production Evidence Store, evidence migration, external access, commit, push, tag, release, or PR was performed.
- Remaining limitation by design: durable filesystem publication, enrollment, indexes, lifecycle consumption, backup/restore, and migration remain outside Phase 1 authorization.

## Acceptance

All required Phase 1 capabilities and regression checks passed within scope. Stop here for Owner acceptance; no Git operation was performed.
