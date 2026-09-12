from __future__ import annotations

import unittest

from governance.evidence import EvidenceIntegrityError, EvidenceObject, EvidenceReference, InMemoryEvidenceStore


class EvidenceStoreCoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.value = b'{"receipt":"original bytes"}'
        self.object = EvidenceObject.from_bytes(
            self.value, evidence_type="InstallationReceipt", schema_id="adoption_installation_receipt.schema.json",
            metadata={"retention_class": "A"}, created_at="2026-09-12T00:00:00+00:00",
        )

    def test_object_and_reference_schema_round_trip(self) -> None:
        restored = EvidenceObject.from_mapping(self.object.to_mapping())
        reference = EvidenceReference.from_mapping(restored.reference().to_mapping())
        self.assertEqual(reference.sha256, self.object.sha256)
        self.assertEqual(reference.byte_length, len(self.value))

    def test_store_resolves_original_bytes_after_integrity_verification(self) -> None:
        store = InMemoryEvidenceStore()
        reference = store.publish(self.value, self.object)
        self.assertEqual(self.value, store.resolve(reference))
        self.assertEqual(self.object, store.verify(reference))

    def test_corrupted_evidence_fails_closed(self) -> None:
        store = InMemoryEvidenceStore()
        reference = store.publish(self.value, self.object)
        store._objects[reference.sha256] = (self.object, b"corrupted")
        with self.assertRaisesRegex(EvidenceIntegrityError, "digest"):
            store.resolve(reference)

    def test_reference_mismatch_and_unknown_schema_fail_closed(self) -> None:
        store = InMemoryEvidenceStore()
        reference = store.publish(self.value, self.object)
        mismatched = EvidenceReference.from_mapping({**reference.to_mapping(), "evidence_type": "ActivationReceipt"})
        with self.assertRaisesRegex(EvidenceIntegrityError, "metadata"):
            store.resolve(mismatched)
        with self.assertRaises(Exception):
            EvidenceObject.from_mapping({**self.object.to_mapping(), "schema_version": "2.0"})


if __name__ == "__main__":
    unittest.main()
