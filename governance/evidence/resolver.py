"""Reference-backed, fail-closed evidence resolution contracts for Phase 2A.

This module intentionally has no lifecycle, filesystem, migration, or store
discovery behavior.  A caller supplies both the store and the expected evidence
contract; successful resolution returns detached immutable values only.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from types import MappingProxyType
from typing import Any, Mapping

from governance.schema_loader import validate_mapping

from .core import EvidenceStore
from .models import EvidenceIntegrityError, EvidenceObject, EvidenceReference, verify_digest


class EvidenceResolutionError(ValueError):
    """A stable, non-mutating failure while resolving evidence."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class EvidenceBinding:
    """A named, reference-backed evidence input for a future consumer."""

    role: str
    reference: EvidenceReference

    def __post_init__(self) -> None:
        if not self.role:
            raise ValueError("evidence binding role must not be empty")
        if not isinstance(self.reference, EvidenceReference):
            raise ValueError("evidence binding reference must be an EvidenceReference")


@dataclass(frozen=True)
class VerifiedEvidence:
    """Immutable evidence returned only after reference, bytes, and schema checks."""

    binding: EvidenceBinding
    reference: EvidenceReference
    object: EvidenceObject
    value: bytes
    content: Mapping[str, Any]

    @classmethod
    def create(
        cls,
        binding: EvidenceBinding,
        object: EvidenceObject,
        value: bytes,
        content: Mapping[str, Any],
    ) -> "VerifiedEvidence":
        return cls(binding, object.reference(), object, bytes(value), MappingProxyType(dict(content)))


class EvidenceResolver:
    """Resolve one reference through an injected ``EvidenceStore`` without fallback."""

    def __init__(self, store: EvidenceStore) -> None:
        self._store = store

    def resolve_verified(
        self,
        binding: EvidenceBinding,
        expected_type: str,
        expected_schema_id: str,
        expected_schema_version: str,
    ) -> VerifiedEvidence:
        reference = self._validate_binding(binding)
        object = self._verify(reference)
        self._require_metadata(object, reference, expected_type, expected_schema_id, expected_schema_version)
        value = self._resolve(reference)
        self._verify_bytes(value, reference)
        content = self._parse_and_validate(value, object.schema_id)
        return VerifiedEvidence.create(binding, object, value, content)

    @staticmethod
    def _validate_binding(binding: EvidenceBinding) -> EvidenceReference:
        if not isinstance(binding, EvidenceBinding):
            raise EvidenceResolutionError("EVIDENCE_REFERENCE_INVALID", "evidence binding is invalid")
        try:
            return EvidenceReference.from_mapping(binding.reference.to_mapping())
        except Exception as exc:
            raise EvidenceResolutionError("EVIDENCE_REFERENCE_INVALID", "evidence reference is invalid") from exc

    def _verify(self, reference: EvidenceReference) -> EvidenceObject:
        try:
            object = self._store.verify(reference)
        except EvidenceIntegrityError as exc:
            raise self._store_error(exc) from exc
        except Exception as exc:
            raise EvidenceResolutionError("EVIDENCE_STORE_UNAVAILABLE", "evidence store verification failed") from exc
        if object.reference() != reference:
            raise EvidenceResolutionError("EVIDENCE_REFERENCE_MISMATCH", "verified object metadata does not match reference")
        return object

    def _resolve(self, reference: EvidenceReference) -> bytes:
        try:
            return self._store.resolve(reference)
        except EvidenceIntegrityError as exc:
            raise self._store_error(exc) from exc
        except Exception as exc:
            raise EvidenceResolutionError("EVIDENCE_STORE_UNAVAILABLE", "evidence store resolution failed") from exc

    @staticmethod
    def _store_error(exc: EvidenceIntegrityError) -> EvidenceResolutionError:
        message = str(exc)
        if "missing" in message:
            return EvidenceResolutionError("EVIDENCE_OBJECT_MISSING", message)
        if "metadata" in message or "reference does not match" in message:
            return EvidenceResolutionError("EVIDENCE_REFERENCE_MISMATCH", message)
        return EvidenceResolutionError("EVIDENCE_INTEGRITY_FAILED", message)

    @staticmethod
    def _require_metadata(
        object: EvidenceObject,
        reference: EvidenceReference,
        expected_type: str,
        expected_schema_id: str,
        expected_schema_version: str,
    ) -> None:
        if object.reference() != reference:
            raise EvidenceResolutionError("EVIDENCE_REFERENCE_MISMATCH", "object metadata does not match reference")
        if (object.evidence_type, object.schema_id, object.schema_version) != (
            expected_type, expected_schema_id, expected_schema_version,
        ):
            raise EvidenceResolutionError("EVIDENCE_CONTRACT_MISMATCH", "evidence does not match the expected contract")

    @staticmethod
    def _verify_bytes(value: bytes, reference: EvidenceReference) -> None:
        try:
            verify_digest(value, reference.sha256)
        except EvidenceIntegrityError as exc:
            raise EvidenceResolutionError("EVIDENCE_INTEGRITY_FAILED", str(exc)) from exc
        if len(value) != reference.byte_length:
            raise EvidenceResolutionError("EVIDENCE_INTEGRITY_FAILED", "evidence byte length does not match reference")

    @staticmethod
    def _parse_and_validate(value: bytes, schema_id: str) -> Mapping[str, Any]:
        try:
            content = json.loads(value.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvidenceResolutionError("EVIDENCE_SCHEMA_INVALID", "evidence bytes are not valid UTF-8 JSON") from exc
        if not isinstance(content, dict):
            raise EvidenceResolutionError("EVIDENCE_SCHEMA_INVALID", "evidence JSON must be an object")
        try:
            validate_mapping(content, schema_id)
        except Exception as exc:
            raise EvidenceResolutionError("EVIDENCE_SCHEMA_INVALID", "evidence content does not satisfy its declared schema") from exc
        return content
