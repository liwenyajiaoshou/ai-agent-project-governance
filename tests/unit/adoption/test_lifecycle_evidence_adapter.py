from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from governance.adoption.lifecycle_evidence_adapter import (
    LegacyEvidenceFile, LifecycleEvidenceAdapter, LifecycleEvidenceAdapterError, ReferenceEvidence,
)
from governance.evidence import EvidenceBinding, EvidenceObject, EvidenceResolver, InMemoryEvidenceStore


class LifecycleEvidenceAdapterContractTest(unittest.TestCase):
    previous_stage = "ACTIVATED_NOT_PREFLIGHTED"
    next_stage = "PREFLIGHT_PASSED"
    target = "a" * 64
    previous_state = "b" * 64

    def setUp(self) -> None:
        self.adapter = LifecycleEvidenceAdapter()
        self.value = self.evidence_bytes()
        self.store = InMemoryEvidenceStore()
        obj = EvidenceObject.from_bytes(self.value, evidence_type="PreflightEvidence", schema_id="adoption_lifecycle_evidence.schema.json")
        self.binding = EvidenceBinding("preflight", self.store.publish(self.value, obj))

    def evidence_bytes(self, **changes: object) -> bytes:
        value = {
            "schema_version": "1.0", "evidence_type": "PreflightEvidence", "status": "PASS",
            "target_identity_digest": self.target, "previous_state_digest": self.previous_state,
            "upstream_evidence_digests": [], "payload": {},
        }
        value.update(changes)
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

    def resolve(self, source: object):
        return self.adapter.resolve(source, previous_stage=self.previous_stage, next_stage=self.next_stage,
            target_identity_digest=self.target, previous_state_digest=self.previous_state, expected_upstream=[])

    def test_reference_source_returns_immutable_normalized_evidence(self) -> None:
        result = self.resolve(ReferenceEvidence(self.binding, EvidenceResolver(self.store)))
        self.assertEqual("reference", result.source_kind)
        self.assertEqual(hashlib.sha256(self.value).hexdigest(), result.evidence_digest)
        self.assertEqual(self.binding.reference, result.reference)
        with self.assertRaises(TypeError):
            result.content["status"] = "FAIL"

    def test_legacy_source_returns_equivalent_normalized_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "preflight.json"
            path.write_bytes(self.value)
            result = self.resolve(LegacyEvidenceFile(path))
        self.assertEqual("legacy_file", result.source_kind)
        self.assertEqual(hashlib.sha256(self.value).hexdigest(), result.evidence_digest)
        self.assertIsNone(result.reference)

    def test_unrecognized_or_ambiguous_source_fails_closed(self) -> None:
        for source in (None, (LegacyEvidenceFile(Path("one.json")), ReferenceEvidence(self.binding, EvidenceResolver(self.store)))):
            with self.assertRaises(LifecycleEvidenceAdapterError) as caught:
                self.resolve(source)
            self.assertEqual("LIFECYCLE_EVIDENCE_SOURCE_INVALID", caught.exception.code)

    def test_legacy_missing_source_fails_closed(self) -> None:
        with self.assertRaises(LifecycleEvidenceAdapterError) as caught:
            self.resolve(LegacyEvidenceFile(Path("/tmp/not-a-phase2b1-evidence.json")))
        self.assertEqual("LIFECYCLE_EVIDENCE_LEGACY_UNAVAILABLE", caught.exception.code)

    def test_reference_resolver_failure_is_translated_without_fallback(self) -> None:
        with self.assertRaises(LifecycleEvidenceAdapterError) as caught:
            self.resolve(ReferenceEvidence(self.binding, EvidenceResolver(InMemoryEvidenceStore())))
        self.assertEqual("LIFECYCLE_EVIDENCE_REFERENCE_FAILED", caught.exception.code)
        self.assertEqual("EVIDENCE_OBJECT_MISSING", caught.exception.source_code)

    def test_wrong_lifecycle_content_fails_after_reference_resolution(self) -> None:
        bad = self.evidence_bytes(status="FAIL")
        store = InMemoryEvidenceStore()
        obj = EvidenceObject.from_bytes(bad, evidence_type="PreflightEvidence", schema_id="adoption_lifecycle_evidence.schema.json")
        binding = EvidenceBinding("preflight", store.publish(bad, obj))
        with self.assertRaises(LifecycleEvidenceAdapterError) as caught:
            self.resolve(ReferenceEvidence(binding, EvidenceResolver(store)))
        self.assertEqual("LIFECYCLE_EVIDENCE_INVALID", caught.exception.code)

    def test_adapter_has_no_mutation_surface(self) -> None:
        before = dict(self.store._objects)
        self.resolve(ReferenceEvidence(self.binding, EvidenceResolver(self.store)))
        self.assertEqual(before, self.store._objects)


if __name__ == "__main__":
    unittest.main()
