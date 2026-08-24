import tempfile
import unittest
from pathlib import Path

from PIL import Image

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from content_validation import validate_queue


def make_item(day: int, phrase: str = "Sounds good.", main_text: str = "Main") -> dict:
    return {
        "day": day,
        "card_id": f"TEST-{day}",
        "episode": "TEST",
        "phrase": phrase,
        "meaning_ko": "좋아요.",
        "posts": [
            {"index": 1, "type": "main", "text": main_text},
            {"index": 2, "type": "sub", "text": "Sub"},
        ],
    }


def make_delayed_item(day: int = 1) -> dict:
    value = make_item(day)
    value.update(
        {
            "hook_ko": "이 둘 중 자연스러운 문장은?",
            "delayed_answer": True,
            "quiz_ko": "좋은 것 같아.",
            "choice_a": "Sounds good.",
            "choice_b": "Sounds well.",
            "answer_choice": "A",
            "answer_explanation_ko": "good은 형용사이고 well은 보통 부사입니다.",
        }
    )
    return value


class ContentValidationTests(unittest.TestCase):
    def test_valid_queue_and_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            images_dir = Path(tmp)
            Image.new("RGB", (1080, 1080)).save(images_dir / "day_001.png")
            errors, warnings = validate_queue([make_item(1)], images_dir)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_rejects_long_post_duplicate_and_typo(self):
        queue = [
            make_item(1, phrase="Same", main_text="x" * 501),
            make_item(2, phrase="same", main_text="초근무"),
        ]
        errors, _ = validate_queue(queue)
        report = "\n".join(errors)
        self.assertIn("501자", report)
        self.assertIn("중복 표현", report)
        self.assertIn("초근무", report)

    def test_warns_on_card_placeholder(self):
        errors, warnings = validate_queue([make_item(1, "What does [someone] do?")])
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)

    def test_validates_delayed_quiz_fields_and_answer_length(self):
        item = make_delayed_item()
        item["answer_choice"] = "C"
        errors, _ = validate_queue([item])
        self.assertIn("answer_choice는 A 또는 B", "\n".join(errors))

        item = make_delayed_item()
        item["posts"][0]["text"] = "x" * 495
        errors, _ = validate_queue([item])
        self.assertIn("오후 정답 글", "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
