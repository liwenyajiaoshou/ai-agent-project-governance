from __future__ import annotations

import unittest

from governance.evidence import (
    EvidenceBinding,
    EvidenceObject,
    EvidenceResolutionError,
    EvidenceResolver,
    EvidenceReference,
    InMemoryEvidenceStore,
)


class EvidenceResolverContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.value = (
            b'{"byte_length":1,"evidence_type":"Reference","object_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
            b'"schema_id":"schema.json","schema_version":"1.0","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
        )
        self.object = EvidenceObject.from_bytes(
            self.value, evidence_type="Reference", schema_id="durable_evidence_reference.schema.json",
            created_at="2026-09-12T00:00:00+00:00",
        )
        self.store = InMemoryEvidenceStore()
        self.reference = self.store.publish(self.value, self.object)
        self.binding = EvidenceBinding(role="installation_receipt", reference=self.reference)
        self.resolver = EvidenceResolver(self.store)

    def resolve(self):
        return self.resolver.resolve_verified(
            self.binding, "Reference", "durable_evidence_reference.schema.json", "1.0",
        )

    def test_binding_and_successful_resolution_return_immutable_verified_result(self) -> None:
        verified = self.resolve()
        self.assertEqual(self.value, verified.value)
        self.assertEqual(self.object, verified.object)
        self.assertEqual(self.reference, verified.reference)
        with self.assertRaises(TypeError):
            verified.content["schema_version"] = "2.0"

    def test_missing_object_fails_closed(self) -> None:
        missing = EvidenceBinding(role="receipt", reference=self.reference)
        with self.assertRaisesRegex(EvidenceResolutionError, "missing") as caught:
            EvidenceResolver(InMemoryEvidenceStore()).resolve_verified(missing, "Reference", "durable_evidence_reference.schema.json", "1.0")
        self.assertEqual("EVIDENCE_OBJECT_MISSING", caught.exception.code)

    def test_digest_mismatch_fails_closed(self) -> None:
        self.store._objects[self.reference.sha256] = (self.object, b"corrupted")
        with self.assertRaises(EvidenceResolutionError) as caught:
            self.resolve()
        self.assertEqual("EVIDENCE_INTEGRITY_FAILED", caught.exception.code)

    def test_reference_mismatch_fails_closed(self) -> None:
        mismatched = EvidenceReference.from_mapping({**self.reference.to_mapping(), "evidence_type": "Other"})
        with self.assertRaises(EvidenceResolutionError) as caught:
            EvidenceResolver(self.store).resolve_verified(EvidenceBinding(role="receipt", reference=mismatched), "Other", "durable_evidence_reference.schema.json", "1.0")
        self.assertEqual("EVIDENCE_REFERENCE_MISMATCH", caught.exception.code)

    def test_unsupported_reference_version_fails_closed(self) -> None:
        unsupported = EvidenceReference(**{**self.reference.to_mapping(), "schema_version": "2.0"})
        with self.assertRaises(EvidenceResolutionError) as caught:
            EvidenceResolver(self.store).resolve_verified(EvidenceBinding(role="receipt", reference=unsupported), "Reference", "durable_evidence_reference.schema.json", "2.0")
        self.assertEqual("EVIDENCE_REFERENCE_INVALID", caught.exception.code)

    def test_expected_contract_mismatch_fails_closed(self) -> None:
        with self.assertRaises(EvidenceResolutionError) as caught:
            self.resolver.resolve_verified(self.binding, "Other", "durable_evidence_reference.schema.json", "1.0")
        self.assertEqual("EVIDENCE_CONTRACT_MISMATCH", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
