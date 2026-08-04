from enum import Enum
from dataclasses import dataclass
from typing import Any

class GitPolicy(Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    CONDITIONAL = "conditional"

@dataclass(frozen=True)
class AssetLifecyclePolicy:
    git_policy: GitPolicy
    retention_policy: str
    write_location: str
    ownership: str
    cleanup_policy: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "git_policy": self.git_policy.value,
            "retention_policy": self.retention_policy,
            "write_location": self.write_location,
            "ownership": self.ownership,
            "cleanup_policy": self.cleanup_policy,
        }

class AssetCategory(Enum):
    SOURCE = "SOURCE"
    GOVERNANCE = "GOVERNANCE"
    USER_OWNED = "USER_OWNED"
    TASK_OWNED = "TASK_OWNED"
    RUNTIME_EVIDENCE = "RUNTIME_EVIDENCE"
    GENERATED_REPORT = "GENERATED_REPORT"
    TEMPORARY = "TEMPORARY"
    ARCHIVE = "ARCHIVE"
    UNKNOWN = "UNKNOWN"

    def get_policy(self) -> AssetLifecyclePolicy:
        if self == AssetCategory.SOURCE:
            return AssetLifecyclePolicy(GitPolicy.INCLUDE, "permanent", "src_or_equivalent", "repository", "manual")
        elif self == AssetCategory.GOVERNANCE:
            return AssetLifecyclePolicy(GitPolicy.INCLUDE, "permanent", "governance_dir", "framework", "manual")
        elif self == AssetCategory.USER_OWNED:
            return AssetLifecyclePolicy(GitPolicy.CONDITIONAL, "user_defined", "any", "user", "never")
        elif self == AssetCategory.TASK_OWNED:
            return AssetLifecyclePolicy(GitPolicy.INCLUDE, "task_duration", "task_dir", "task", "task_completion")
        elif self == AssetCategory.RUNTIME_EVIDENCE:
            return AssetLifecyclePolicy(GitPolicy.EXCLUDE, "audit_duration", "evidence_dir", "runtime", "archival")
        elif self == AssetCategory.GENERATED_REPORT:
            return AssetLifecyclePolicy(GitPolicy.INCLUDE, "permanent", "reports_dir", "runtime", "manual")
        elif self == AssetCategory.TEMPORARY:
            return AssetLifecyclePolicy(GitPolicy.EXCLUDE, "session", "tmp_dir", "runtime", "automatic_on_exit")
        elif self == AssetCategory.ARCHIVE:
            return AssetLifecyclePolicy(GitPolicy.EXCLUDE, "permanent", "archive_dir", "framework", "manual")
        elif self == AssetCategory.UNKNOWN:
            raise ValueError("UNKNOWN asset category fails closed")
        raise ValueError(f"No policy for {self}")
