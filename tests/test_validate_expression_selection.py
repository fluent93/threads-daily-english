import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from validate_expression_selection import validate_selection


def make_item(day=1, phrase="It slipped my mind."):
    return {
        "day": day,
        "phrase": phrase,
        "meaning_ko": "깜빡했어.",
        "category": "기억",
        "scores": {
            "frequency": 5,
            "transfer": 5,
            "learning_value": 5,
            "memorability": 4,
        },
        "selection_reason": "여러 상황에서 실수를 자연스럽게 설명한다.",
        "register_note": "중립적인 일상 표현이다.",
    }


class SelectionValidationTests(unittest.TestCase):
    def test_accepts_high_value_selection(self):
        self.assertEqual(validate_selection([make_item()]), [])

    def test_rejects_duplicate_and_low_value_selection(self):
        first = make_item()
        second = make_item(day=2, phrase="it slipped my mind")
        second["scores"]["frequency"] = 2
        second["scores"]["learning_value"] = 2
        errors = "\n".join(validate_selection([first, second]))
        self.assertIn("중복", errors)
        self.assertIn("빈도와 전이성", errors)
        self.assertIn("16/20 미만", errors)


if __name__ == "__main__":
    unittest.main()
