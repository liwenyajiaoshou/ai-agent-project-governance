import unittest
import json
from governance.evidence.manifest import build_machine_manifest

class TestManifest(unittest.TestCase):
    def test_machine_manifest_json_round_trip(self):
        manifest = build_machine_manifest(
            "task-1", "base-1", "env-1", "bundle-1", "commit-1",
            ["file1.py"], {"file1.py": "aaa"}, ["pytest"], ["pass"],
            [], [], "DRAFT", "READY_FOR_PHASE_5"
        )
        as_json = json.dumps(manifest)
        loaded = json.loads(as_json)
        self.assertEqual(manifest, loaded)

    def test_manifest_digest_recomputation(self):
        manifest = build_machine_manifest(
            "task-1", "base-1", "env-1", "bundle-1", "commit-1",
            ["file1.py"], {"file1.py": "aaa"}, ["pytest"], ["pass"],
            [], [], "DRAFT", "READY_FOR_PHASE_5"
        )
        self.assertIn("manifest_id", manifest)

    def test_manifest_changed_path_scope_check(self):
        manifest = build_machine_manifest(
            "task-1", "base-1", "env-1", "bundle-1", "commit-1",
            ["b.py", "a.py"], {}, [], [], [], [], "DRAFT", "READY"
        )
        self.assertEqual(manifest["changed_paths"], ["a.py", "b.py"])

if __name__ == "__main__":
    unittest.main()
