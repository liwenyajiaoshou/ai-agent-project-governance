import unittest
from governance.workspace.lifecycle import AssetCategory, GitPolicy

class TestAssetLifecycle(unittest.TestCase):
    def test_asset_lifecycle_unknown_fails_closed(self):
        with self.assertRaises(ValueError):
            AssetCategory.UNKNOWN.get_policy()

    def test_asset_lifecycle_git_policy(self):
        self.assertEqual(AssetCategory.RUNTIME_EVIDENCE.get_policy().git_policy, GitPolicy.EXCLUDE)
        self.assertEqual(AssetCategory.SOURCE.get_policy().git_policy, GitPolicy.INCLUDE)

    def test_asset_lifecycle_retention_policy(self):
        policy = AssetCategory.TEMPORARY.get_policy()
        self.assertEqual(policy.retention_policy, "session")
        self.assertEqual(policy.cleanup_policy, "automatic_on_exit")

    def test_serialization(self):
        policy = AssetCategory.SOURCE.get_policy()
        serialized = policy.to_dict()
        self.assertEqual(serialized["git_policy"], "include")
