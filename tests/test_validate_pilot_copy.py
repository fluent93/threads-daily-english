import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from validate_pilot_copy import validate_copy


class PilotCopyValidationTests(unittest.TestCase):
    def test_requires_target_expression_and_distinct_alternative(self):
        selection = [{"day": 1, "phrase": "It slipped my mind."}]
        base = {
            "day": 1,
            "hook_ko": "깜빡했을 때",
            "quiz_ko": "완전히 깜빡했어.",
            "answer_example_en": "Sorry, it slipped my mind.",
            "alternative_en": "Sorry, I completely forgot.",
            "alternative_note_ko": "둘 다 자연스럽지만 뉘앙스가 다르다.",
            "nuance_ko": "의도치 않게 잊었다는 뜻이다.",
            "example_en": "It slipped my mind.",
            "example_ko": "깜빡했어.",
            "pronunciation_ko": "slipped my를 이어 말한다.",
        }
        self.assertEqual(validate_copy(selection, [base]), [])

        base["answer_example_en"] = "I forgot."
        errors = "\n".join(validate_copy(selection, [base]))
        self.assertIn("선정 표현", errors)


if __name__ == "__main__":
    unittest.main()
