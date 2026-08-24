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


if __name__ == "__main__":
    unittest.main()
