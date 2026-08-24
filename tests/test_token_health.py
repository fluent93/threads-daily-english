import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_threads_access import evaluate_token


class TokenHealthTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.scopes = [
            "threads_basic",
            "threads_content_publish",
            "threads_manage_replies",
        ]

    def test_accepts_healthy_token(self):
        info = {
            "is_valid": True,
            "scopes": self.scopes,
            "expires_at": int(self.now.timestamp()) + (30 * 86400),
        }
        errors, _ = evaluate_token(info, now=self.now)
        self.assertEqual(errors, [])

    def test_rejects_expiring_and_under_scoped_token(self):
        info = {
            "is_valid": True,
            "scopes": ["threads_basic"],
            "expires_at": int(self.now.timestamp()) + (2 * 86400),
        }
        errors, _ = evaluate_token(info, now=self.now)
        self.assertEqual(len(errors), 2)


if __name__ == "__main__":
    unittest.main()
