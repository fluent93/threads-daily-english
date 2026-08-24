import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from publish_daily_expression import publish_item


def item() -> dict:
    return {
        "day": 1,
        "phrase": "Sounds good.",
        "meaning_ko": "좋아요.",
        "posts": [
            {"type": "main", "text": "main"},
            {"type": "sub", "text": "sub"},
        ],
    }


class FakeClient:
    def __init__(self):
        self.calls = []

    def post(self, **kwargs):
        self.calls.append(kwargs)
        return f"thread-{len(self.calls)}"


class PublishRecoveryTests(unittest.TestCase):
    def test_saves_progress_after_each_external_write(self):
        state = {
            "last_published_day": 0,
            "last_published_at": None,
            "history": [],
            "in_progress": None,
        }
        snapshots = []
        client = FakeClient()
        publish_item(
            item(),
            state,
            client,
            "https://example.com/day.png",
            now_kst=datetime.now(timezone.utc),
            save_callback=lambda value: snapshots.append(repr(value)),
        )
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(len(snapshots), 4)
        self.assertIsNone(state["in_progress"])
        self.assertEqual(state["last_published_day"], 1)

    def test_resumes_at_reply_without_reposting_main(self):
        state = {
            "last_published_day": 0,
            "last_published_at": None,
            "history": [],
            "in_progress": {
                "day": 1,
                "phrase": "Sounds good.",
                "image_url": "https://example.com/day.png",
                "main_thread_id": "existing-main",
                "sub_thread_id": None,
            },
        }
        client = FakeClient()
        publish_item(
            item(),
            state,
            client,
            "https://example.com/day.png",
            now_kst=datetime.now(timezone.utc),
            save_callback=lambda _: None,
        )
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["reply_to_id"], "existing-main")


if __name__ == "__main__":
    unittest.main()
