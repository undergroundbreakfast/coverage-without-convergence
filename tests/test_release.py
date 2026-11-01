"""Check that the software inventory rejects modified or extra public files."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_release


class ReleaseInventory(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        data = b"Example software description\n"
        (self.root / "README.md").write_bytes(data)
        manifest = {
            "version": "test",
            "files": [
                {
                    "path": "README.md",
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            ],
        }
        (self.root / "release_manifest.json").write_text(json.dumps(manifest))
        self.patch = patch.object(verify_release, "ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_changed_file_is_rejected(self):
        (self.root / "README.md").write_text("Changed content")
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            verify_release.verify()

    def test_uninventoried_file_is_rejected(self):
        (self.root / "unexpected.txt").write_text("Extra content")
        with self.assertRaisesRegex(ValueError, "Inventory differs"):
            verify_release.verify()

    def test_runtime_data_is_not_in_software_inventory(self):
        (self.root / "data").mkdir()
        (self.root / "data/example.csv").write_text("synthetic\n1\n")
        manifest = verify_release.verify()
        self.assertEqual([r["path"] for r in manifest["files"]], ["README.md"])

    def test_inventory_rejects_path_traversal(self):
        self.assertFalse(verify_release.valid_path("../README.md"))
        self.assertFalse(verify_release.valid_path("/README.md"))
        self.assertFalse(verify_release.valid_path("data/example.py"))


if __name__ == "__main__":
    unittest.main()
