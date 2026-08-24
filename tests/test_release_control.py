import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from release_control import require_publishing_enabled


class ReleaseControlTests(unittest.TestCase):
    def test_blocks_when_review_is_in_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "status.json"
            path.write_text(
                json.dumps({"publishing_enabled": False, "reason": "재검토 중"}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "재검토 중"):
                require_publishing_enabled(path)

    def test_allows_only_explicit_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "status.json"
            path.write_text(json.dumps({"publishing_enabled": True}), encoding="utf-8")
            require_publishing_enabled(path)


if __name__ == "__main__":
    unittest.main()
