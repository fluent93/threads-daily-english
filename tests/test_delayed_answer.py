import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from publish_delayed_answer import publish_due_answers


def queue_item() -> dict:
    return {
        "day": 1,
        "delayed_answer": True,
        "answer_choice": "B",
        "answer_explanation_ko": "B가 자연스럽습니다.",
        "posts": [
            {"type": "main", "text": "answer and nuance"},
            {"type": "sub", "text": "pronunciation"},
        ],
    }


def state_entry(now: datetime) -> dict:
    return {
        "history": [
            {
                "day": 1,
                "main_thread_id": "morning-root",
                "answer_due_at": (now - timedelta(minutes=1)).isoformat(),
                "answer_thread_id": None,
                "answer_detail_thread_id": None,
            }
        ]
    }


class FakeClient:
    def __init__(self):
        self.calls = []

    def post(self, **kwargs):
        self.calls.append(kwargs)
        return f"answer-{len(self.calls)}"


class DelayedAnswerTests(unittest.TestCase):
    def test_posts_answer_then_detail_and_saves_each_write(self):
        now = datetime(2026, 8, 24, 14, 7, tzinfo=timezone(timedelta(hours=9)))
        state = state_entry(now)
        client = FakeClient()
        snapshots = []
        completed = publish_due_answers(
            state,
            [queue_item()],
            client,
            now_kst=now,
            save_callback=lambda value: snapshots.append(repr(value)),
        )
        self.assertEqual(completed, 1)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0]["reply_to_id"], "morning-root")
        self.assertEqual(client.calls[1]["reply_to_id"], "answer-1")
        self.assertEqual(len(snapshots), 2)

    def test_resumes_at_detail_without_reposting_answer(self):
        now = datetime(2026, 8, 24, 14, 7, tzinfo=timezone(timedelta(hours=9)))
        state = state_entry(now)
        state["history"][0]["answer_thread_id"] = "existing-answer"
        client = FakeClient()
        publish_due_answers(
            state,
            [queue_item()],
            client,
            now_kst=now,
            save_callback=lambda _: None,
        )
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["reply_to_id"], "existing-answer")

    def test_skips_not_yet_due_answer(self):
        now = datetime(2026, 8, 24, 14, 7, tzinfo=timezone(timedelta(hours=9)))
        state = state_entry(now)
        state["history"][0]["answer_due_at"] = (now + timedelta(minutes=1)).isoformat()
        client = FakeClient()
        completed = publish_due_answers(
            state,
            [queue_item()],
            client,
            now_kst=now,
            save_callback=lambda _: None,
        )
        self.assertEqual(completed, 0)
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
