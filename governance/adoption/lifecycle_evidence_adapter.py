"""Pure source-to-verified-value contracts for Adoption lifecycle evidence.

This Phase 2B.1 boundary neither reads or writes ProjectState nor invokes a
lifecycle transition.  It deliberately accepts one explicit source at a time
and performs no source discovery or fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from governance.evidence import EvidenceBinding, EvidenceReference, EvidenceResolutionError, EvidenceResolver
from governance.schema_loader import load_mapping

from .evidence_registry import file_digest, required_for, validate_evidence_content


LIFECYCLE_EVIDENCE_SCHEMA_ID = "adoption_lifecycle_evidence.schema.json"
LIFECYCLE_EVIDENCE_SCHEMA_VERSION = "1.0"


class LifecycleEvidenceAdapterError(ValueError):
    """Stable, non-mutating adapter failure with an optional source error code."""

    def __init__(self, code: str, message: str, *, source_code: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.source_code = source_code


@dataclass(frozen=True)
class LegacyEvidenceFile:
    """One caller-supplied legacy lifecycle evidence path."""

    path: Path

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            raise LifecycleEvidenceAdapterError("LIFECYCLE_EVIDENCE_SOURCE_INVALID", "legacy evidence path must be a Path")


@dataclass(frozen=True)
class ReferenceEvidence:
    """One caller-supplied durable reference and its injected resolver."""

    binding: EvidenceBinding
    resolver: EvidenceResolver

    def __post_init__(self) -> None:
        if not isinstance(self.binding, EvidenceBinding) or not isinstance(self.resolver, EvidenceResolver):
            raise LifecycleEvidenceAdapterError("LIFECYCLE_EVIDENCE_SOURCE_INVALID", "reference evidence requires a binding and resolver")


@dataclass(frozen=True)
class NormalizedVerifiedEvidence:
    """Immutable lifecycle evidence whose transport and meaning both verified."""

    content: Mapping[str, Any]
    evidence_digest: str
    source_kind: str
    legacy_path: Path | None = None
    reference: EvidenceReference | None = None

    @classmethod
    def create(
        cls,
        content: Mapping[str, Any],
        evidence_digest: str,
        source_kind: str,
        *,
        legacy_path: Path | None = None,
        reference: EvidenceReference | None = None,
    ) -> "NormalizedVerifiedEvidence":
        return cls(MappingProxyType(dict(content)), evidence_digest, source_kind, legacy_path, reference)


class LifecycleEvidenceAdapter:
    """Resolve exactly one source into verified, lifecycle-valid evidence."""

    def resolve(
        self,
        source: LegacyEvidenceFile | ReferenceEvidence,
        *,
        previous_stage: str,
        next_stage: str,
        target_identity_digest: str,
        previous_state_digest: str,
        expected_upstream: list[str],
    ) -> NormalizedVerifiedEvidence:
        if isinstance(source, LegacyEvidenceFile):
            content, digest = self._legacy(source)
            reference = None
            legacy_path = source.path
            source_kind = "legacy_file"
        elif isinstance(source, ReferenceEvidence):
            content, digest, reference = self._reference(source, previous_stage, next_stage)
            legacy_path = None
            source_kind = "reference"
        else:
            raise LifecycleEvidenceAdapterError("LIFECYCLE_EVIDENCE_SOURCE_INVALID", "exactly one recognized evidence source is required")
        try:
            validate_evidence_content(
                content,
                previous_stage=previous_stage,
                next_stage=next_stage,
                target_identity_digest=target_identity_digest,
                previous_state_digest=previous_state_digest,
                expected_upstream=expected_upstream,
            )
        except Exception as exc:
            raise LifecycleEvidenceAdapterError("LIFECYCLE_EVIDENCE_INVALID", "evidence does not satisfy the lifecycle contract") from exc
        return NormalizedVerifiedEvidence.create(
            content, digest, source_kind, legacy_path=legacy_path, reference=reference,
        )

    @staticmethod
    def _legacy(source: LegacyEvidenceFile) -> tuple[dict[str, Any], str]:
        path = source.path
        if not path.is_file() or path.is_symlink():
            raise LifecycleEvidenceAdapterError("LIFECYCLE_EVIDENCE_LEGACY_UNAVAILABLE", "legacy lifecycle evidence file is missing or unsafe")
        try:
            return load_mapping(path), file_digest(path)
        except Exception as exc:
            raise LifecycleEvidenceAdapterError("LIFECYCLE_EVIDENCE_LEGACY_INVALID", "legacy lifecycle evidence cannot be read") from exc

    @staticmethod
    def _reference(
        source: ReferenceEvidence, previous_stage: str, next_stage: str,
    ) -> tuple[Mapping[str, Any], str, EvidenceReference]:
        required_type, _ = required_for(previous_stage, next_stage)
        try:
            verified = source.resolver.resolve_verified(
                source.binding, required_type, LIFECYCLE_EVIDENCE_SCHEMA_ID, LIFECYCLE_EVIDENCE_SCHEMA_VERSION,
            )
        except EvidenceResolutionError as exc:
            raise LifecycleEvidenceAdapterError(
                "LIFECYCLE_EVIDENCE_REFERENCE_FAILED", "reference lifecycle evidence could not be resolved", source_code=exc.code,
            ) from exc
        except Exception as exc:
            raise LifecycleEvidenceAdapterError("LIFECYCLE_EVIDENCE_REFERENCE_FAILED", "reference lifecycle evidence could not be resolved") from exc
        return verified.content, verified.reference.sha256, verified.reference
