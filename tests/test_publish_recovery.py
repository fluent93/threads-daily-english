import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from publish_daily_expression import publish_item


def item() -> dict:
    return {
        "day": 1,
        "phrase": "Sounds good.",
        "meaning_ko": "좋아요.",
        "delayed_answer": False,
        "posts": [
            {"type": "main", "text": "main"},
            {"type": "sub", "text": "sub"},
        ],
    }


def delayed_item() -> dict:
    value = item()
    value.update(
        {
            "hook_ko": "둘 중 자연스러운 문장은?",
            "delayed_answer": True,
            "quiz_ko": "좋은 것 같아.",
            "choice_a": "Sounds good.",
            "choice_b": "Sounds well.",
            "answer_choice": "A",
            "quiz_focus": "nuance",
            "answer_explanation_ko": "A는 자연스럽고, B는 다른 뜻입니다.",
        }
    )
    return value


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

    def test_delayed_lesson_posts_only_answer_free_morning_quiz(self):
        state = {
            "last_published_day": 0,
            "last_published_at": None,
            "history": [],
            "in_progress": None,
        }
        client = FakeClient()
        now = datetime.now(timezone.utc)
        publish_item(
            delayed_item(),
            state,
            client,
            "https://example.com/day.png",
            now_kst=now,
            save_callback=lambda _: None,
        )
        self.assertEqual(len(client.calls), 1)
        self.assertNotIn("정답", client.calls[0]["alt_text"])
        self.assertNotIn("main", client.calls[0]["text"])
        expected = now.replace(hour=14, minute=7, second=0, microsecond=0)
        if now >= expected:
            expected = now + timedelta(hours=6)
        self.assertEqual(state["history"][0]["answer_due_at"], expected.isoformat())

    def test_delayed_reveal_is_default_for_legacy_queue_items(self):
        legacy = item()
        legacy.pop("delayed_answer")
        legacy["posts"][1]["text"] = '퀴즈\nQ. "좋은 것 같아."\n(정답: Sounds good.)'
        state = {
            "last_published_day": 0,
            "last_published_at": None,
            "history": [],
            "in_progress": None,
        }
        client = FakeClient()
        publish_item(
            legacy,
            state,
            client,
            "https://example.com/day.png",
            now_kst=datetime.now(timezone.utc),
            save_callback=lambda _: None,
        )
        self.assertEqual(len(client.calls), 1)
        self.assertNotIn("Sounds good.", client.calls[0]["text"])


if __name__ == "__main__":
    unittest.main()
