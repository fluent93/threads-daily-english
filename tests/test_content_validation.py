import tempfile
import unittest
from pathlib import Path

from PIL import Image

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from content_validation import build_quiz_prompt, card_fingerprint, get_quiz_spec, validate_queue


def make_item(day: int, phrase: str = "Sounds good.", main_text: str = "Main") -> dict:
    return {
        "day": day,
        "card_id": f"TEST-{day}",
        "episode": "TEST",
        "phrase": phrase,
        "meaning_ko": "좋아요.",
        "delayed_answer": False,
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
            "quiz_focus": "nuance",
            "answer_explanation_ko": "A는 평가를 말하고, B는 행동 방식을 말합니다.",
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

    def test_derives_free_response_quiz_and_preserves_dialogue_quotes(self):
        item = make_item(1)
        item.pop("delayed_answer")
        item["posts"][1]["text"] = (
            '✍️ 퀴즈\nQ. ""일이 끝이 없어." "내 말이.""\n(정답: sample)'
        )
        spec = get_quiz_spec(item)
        self.assertEqual(spec["mode"], "free")
        self.assertEqual(spec["quiz_ko"], '"일이 끝이 없어." "내 말이."')
        self.assertNotIn("sample", build_quiz_prompt(item))
        errors, _ = validate_queue([item])
        self.assertEqual(errors, [])

    def test_rejects_one_sided_choice_explanation(self):
        item = make_delayed_item()
        item["answer_explanation_ko"] = "A가 맞습니다."
        errors, _ = validate_queue([item])
        self.assertIn("A와 B의 차이", "\n".join(errors))

    def test_release_gate_requires_editorial_approval_and_specific_hooks(self):
        item = make_delayed_item()
        item["hook_ko"] = "힌트 없이 먼저 떠올려보세요"
        errors, _ = validate_queue([item], require_editorial_approval=True)
        report = "\n".join(errors)
        self.assertIn("최종 편집 승인", report)
        self.assertIn("범용 훅", report)

        item["quality_version"] = 3
        item["hook_ko"] = "추천받은 영화를 오늘 가볍게 확인해볼 때"
        item["context_ko"] = "부담 없이 한번 살펴보겠다고 할 때"
        errors, _ = validate_queue([item], require_editorial_approval=True)
        self.assertEqual(errors, [])

    def test_release_gate_rejects_stale_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            images_dir = Path(tmp)
            item = make_delayed_item()
            item["quality_version"] = 3
            item["context_ko"] = "상대 제안에 동의할 때"
            Image.new("RGB", (1080, 1080)).save(images_dir / "day_001.png")

            errors, _ = validate_queue(
                [item], images_dir, require_editorial_approval=True
            )
            self.assertIn("현재 콘텐츠와 일치하지 않습니다", "\n".join(errors))
            self.assertEqual(len(card_fingerprint(item)), 64)


if __name__ == "__main__":
    unittest.main()
