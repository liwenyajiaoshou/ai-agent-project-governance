"""Evidence object models and non-persistent Phase 1 store interfaces."""

from .core import EvidenceStore, InMemoryEvidenceStore
from .models import EvidenceIntegrityError, EvidenceObject, EvidenceReference, digest_bytes, verify_digest
from .resolver import EvidenceBinding, EvidenceResolutionError, EvidenceResolver, VerifiedEvidence

__all__ = [
    "EvidenceIntegrityError", "EvidenceObject", "EvidenceReference", "EvidenceStore", "InMemoryEvidenceStore",
    "EvidenceBinding", "EvidenceResolutionError", "EvidenceResolver", "VerifiedEvidence",
    "digest_bytes", "verify_digest",
]
