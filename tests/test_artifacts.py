import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from grip import __version__
from tools.artifact_manifest import write_manifest


class ArtifactTests(unittest.TestCase):
    def test_checksums_cover_the_complete_bundle_and_detect_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "anki-grip.exe").write_bytes(b"synthetic executable")
            (output / "licenses").mkdir()
            (output / "licenses/NOTICE.txt").write_text("synthetic license")
            with patch("tools.artifact_manifest.version", return_value="test-version"):
                write_manifest(output)
                first = (output / "SHA256SUMS.txt").read_text()
                write_manifest(output)
            self.assertEqual(first, (output / "SHA256SUMS.txt").read_text())
            checksums = dict(line.split("  ", 1)[::-1] for line in first.splitlines())
            self.assertEqual(set(checksums), {"anki-grip.exe", "licenses/NOTICE.txt", "build-info.json"})
            for name, digest in checksums.items():
                self.assertEqual(digest, hashlib.sha256((output / name).read_bytes()).hexdigest())
            (output / "anki-grip.exe").write_bytes(b"changed executable")
            self.assertNotEqual(checksums["anki-grip.exe"], hashlib.sha256((output / "anki-grip.exe").read_bytes()).hexdigest())
            metadata = json.loads((output / "build-info.json").read_text())
            self.assertEqual(metadata["version"], __version__)
            self.assertNotIn(directory, json.dumps(metadata))
