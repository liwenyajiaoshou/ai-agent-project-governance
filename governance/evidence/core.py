"""Non-persistent Evidence Store Core interfaces for Phase 1.

This module deliberately provides no filesystem, network, migration, or lifecycle
integration. ``InMemoryEvidenceStore`` is a deterministic test implementation.
"""
from __future__ import annotations

from typing import Protocol

from .models import EvidenceIntegrityError, EvidenceObject, EvidenceReference, verify_digest


class EvidenceStore(Protocol):
    """Minimal immutable object interface; implementations must verify on reads."""

    def publish(self, value: bytes, object: EvidenceObject) -> EvidenceReference: ...

    def resolve(self, reference: EvidenceReference) -> bytes: ...

    def verify(self, reference: EvidenceReference) -> EvidenceObject: ...


class InMemoryEvidenceStore:
    """Process-local test double, not a durable or production Evidence Store."""

    def __init__(self) -> None:
        self._objects: dict[str, tuple[EvidenceObject, bytes]] = {}

    def publish(self, value: bytes, object: EvidenceObject) -> EvidenceReference:
        verify_digest(value, object.sha256)
        if len(value) != object.byte_length:
            raise EvidenceIntegrityError("evidence byte length does not match its declaration")
        existing = self._objects.get(object.sha256)
        if existing is not None and existing[1] != value:
            raise EvidenceIntegrityError("immutable object key is already bound to different bytes")
        self._objects.setdefault(object.sha256, (object, bytes(value)))
        return object.reference()

    def resolve(self, reference: EvidenceReference) -> bytes:
        object = self.verify(reference)
        stored_object, value = self._objects[object.sha256]
        if stored_object != object:
            raise EvidenceIntegrityError("stored object metadata does not match the referenced object")
        return bytes(value)

    def verify(self, reference: EvidenceReference) -> EvidenceObject:
        if reference.object_id != reference.sha256:
            raise EvidenceIntegrityError("evidence reference identity must equal its SHA-256")
        try:
            object, value = self._objects[reference.sha256]
        except KeyError as exc:
            raise EvidenceIntegrityError("referenced evidence object is missing") from exc
        if object.reference() != reference:
            raise EvidenceIntegrityError("evidence reference does not match stored object metadata")
        verify_digest(value, reference.sha256)
        if len(value) != reference.byte_length:
            raise EvidenceIntegrityError("stored evidence byte length does not match its reference")
        return object
