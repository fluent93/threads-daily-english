import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from apply_editorial_overrides import apply_editorial_data


class ApplyEditorialOverridesTests(unittest.TestCase):
    def test_applies_complete_override_and_marks_approval(self):
        queue = [
            {
                "day": 29,
                "posts": [{"type": "main", "text": "old"}, {"type": "sub", "text": "old"}],
            }
        ]
        value = {
            "phrase": "Count me in.",
            "meaning_ko": "나도 할게.",
            "hook_ko": "함께하고 싶을 때",
            "context_ko": "참여 의사를 밝힐 때",
            "quiz_ko": "나도 할게.",
            "answer_example_en": "Count me in.",
            "nuance_ko": "적극적인 참여 의사입니다.",
            "example_en": "Count me in for dinner.",
            "example_ko": "저녁 식사에 나도 낄게.",
            "pronunciation_ko": "count와 in에 힘을 줍니다.",
        }
        apply_editorial_data(queue, {"approved_days": [29], "items": {"29": value}})
        self.assertEqual(queue[0]["quality_version"], 3)
        self.assertIn("Count me in.", queue[0]["posts"][0]["text"])

    def test_applies_hook_polish_without_rewriting_lesson(self):
        queue = [
            {
                "day": 1,
                "posts": [
                    {"type": "main", "text": "original main"},
                    {"type": "sub", "text": "original sub"},
                ],
            }
        ]
        original_post = queue[0]["posts"][0]["text"]
        editorial = {
            "approved_days": [1],
            "polish": {
                "1": {
                    "hook_ko": "민감한 문제를 처음 꺼내야 할 때",
                    "context_ko": "회의에서 조심스럽게 화제를 제시할 때",
                }
            },
            "items": {},
        }

        apply_editorial_data(queue, editorial)

        self.assertEqual(queue[0]["hook_ko"], "민감한 문제를 처음 꺼내야 할 때")
        self.assertEqual(queue[0]["posts"][0]["text"], original_post)
        self.assertEqual(queue[0]["quality_version"], 3)


if __name__ == "__main__":
    unittest.main()
