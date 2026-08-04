import unittest
from governance.runtime.bundle import build_runtime_bundle

class TestBundle(unittest.TestCase):
    def test_bundle_deterministic_identity(self):
        artifacts = [{"path": "file1.py", "digest": "aaa"}]
        bundle1 = build_runtime_bundle("b1", "e1", "commit1", artifacts)
        bundle2 = build_runtime_bundle("b1", "e1", "commit1", artifacts)
        self.assertEqual(bundle1["bundle_id"], bundle2["bundle_id"])
        self.assertEqual(bundle1["bundle_digest"], bundle2["bundle_digest"])

    def test_bundle_identity_changes_on_artifact_change(self):
        artifacts1 = [{"path": "file1.py", "digest": "aaa"}]
        artifacts2 = [{"path": "file1.py", "digest": "bbb"}]
        bundle1 = build_runtime_bundle("b1", "e1", "commit1", artifacts1)
        bundle2 = build_runtime_bundle("b1", "e1", "commit1", artifacts2)
        self.assertNotEqual(bundle1["bundle_id"], bundle2["bundle_id"])

    def test_bundle_binds_baseline_environment_source_commit(self):
        artifacts = [{"path": "file1.py", "digest": "aaa"}]
        bundle1 = build_runtime_bundle("b1", "e1", "commit1", artifacts)
        bundle2 = build_runtime_bundle("b2", "e1", "commit1", artifacts)
        bundle3 = build_runtime_bundle("b1", "e2", "commit1", artifacts)
        bundle4 = build_runtime_bundle("b1", "e1", "commit2", artifacts)
        self.assertNotEqual(bundle1["bundle_id"], bundle2["bundle_id"])
        self.assertNotEqual(bundle1["bundle_id"], bundle3["bundle_id"])
        self.assertNotEqual(bundle1["bundle_id"], bundle4["bundle_id"])

if __name__ == "__main__":
    unittest.main()
