"""Immutable, schema-bound evidence object and reference value types."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from governance.schema_loader import validate_mapping


OBJECT_SCHEMA = "durable_evidence_object.schema.json"
REFERENCE_SCHEMA = "durable_evidence_reference.schema.json"
SCHEMA_VERSION = "1.0"


class EvidenceIntegrityError(ValueError):
    """Raised when evidence bytes or their declared binding do not match."""


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def verify_digest(value: bytes, expected_digest: str) -> None:
    if digest_bytes(value) != expected_digest:
        raise EvidenceIntegrityError("evidence digest does not match the declared SHA-256")


def _immutable_metadata(metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    """Accept JSON metadata only and detach it from the caller's mutable mapping."""
    try:
        copied = json.loads(json.dumps(dict(metadata), ensure_ascii=False, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError("evidence metadata must be JSON-serializable") from exc
    return MappingProxyType(copied)


@dataclass(frozen=True)
class EvidenceObject:
    """Description of immutable bytes; the bytes themselves remain store-owned."""

    object_id: str
    sha256: str
    byte_length: int
    evidence_type: str
    schema_id: str
    schema_version: str
    metadata: Mapping[str, Any]
    created_at: str

    @classmethod
    def from_bytes(
        cls,
        value: bytes,
        *,
        evidence_type: str,
        schema_id: str,
        metadata: Mapping[str, Any] | None = None,
        created_at: str | None = None,
    ) -> "EvidenceObject":
        digest = digest_bytes(value)
        instance = cls(
            object_id=digest,
            sha256=digest,
            byte_length=len(value),
            evidence_type=evidence_type,
            schema_id=schema_id,
            schema_version=SCHEMA_VERSION,
            metadata=_immutable_metadata(metadata or {}),
            created_at=created_at or datetime.now(timezone.utc).isoformat(),
        )
        validate_mapping(instance.to_mapping(), OBJECT_SCHEMA)
        return instance

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EvidenceObject":
        validate_mapping(value, OBJECT_SCHEMA)
        if value["object_id"] != value["sha256"]:
            raise EvidenceIntegrityError("evidence object identity must equal its SHA-256")
        return cls(
            object_id=value["object_id"], sha256=value["sha256"], byte_length=value["byte_length"],
            evidence_type=value["evidence_type"], schema_id=value["schema_id"],
            schema_version=value["schema_version"], metadata=_immutable_metadata(value["metadata"]),
            created_at=value["created_at"],
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id, "sha256": self.sha256, "byte_length": self.byte_length,
            "evidence_type": self.evidence_type, "schema_id": self.schema_id,
            "schema_version": self.schema_version, "metadata": dict(self.metadata), "created_at": self.created_at,
        }

    def reference(self) -> "EvidenceReference":
        return EvidenceReference(
            object_id=self.object_id, sha256=self.sha256, byte_length=self.byte_length,
            evidence_type=self.evidence_type, schema_id=self.schema_id, schema_version=self.schema_version,
        )


@dataclass(frozen=True)
class EvidenceReference:
    """Stable digest binding used to resolve an EvidenceObject through a store."""

    object_id: str
    sha256: str
    byte_length: int
    evidence_type: str
    schema_id: str
    schema_version: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EvidenceReference":
        validate_mapping(value, REFERENCE_SCHEMA)
        if value["object_id"] != value["sha256"]:
            raise EvidenceIntegrityError("evidence reference identity must equal its SHA-256")
        return cls(**dict(value))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id, "sha256": self.sha256, "byte_length": self.byte_length,
            "evidence_type": self.evidence_type, "schema_id": self.schema_id,
            "schema_version": self.schema_version,
        }
