import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from normalize_legacy_content import normalize_item


class NormalizeLegacyContentTests(unittest.TestCase):
    def test_extracts_learning_content_and_removes_promotional_copy(self):
        item = {
            "day": 29,
            "episode": "S03E04",
            "phrase": "fall for it",
            "meaning_ko": "속다",
            "posts": [
                {
                    "type": "main",
                    "text": (
                        '[미드]\n📌 "fall for it"\n(속다)\n\n'
                        "💡 원어민 뉘앙스\n가벼운 속임수에 넘어갈 때 쓴다.\n\n"
                        '🔥 실전 예문:\n• "I fell for it."\n  (나 속았어.)\n\n'
                        "👇 발음·퀴즈는 답글에!"
                    ),
                },
                {
                    "type": "sub",
                    "text": (
                        "🗣️ 발음 꿀팁:\nfall에 강세가 온다.\n\n"
                        '✍️ 퀴즈:\nQ. "나 속았어."\n(정답: I fell for it.)\n\n'
                        "저장하고 팔로우하세요!"
                    ),
                },
            ],
        }
        normalize_item(item)
        self.assertEqual(item["quality_version"], 2)
        self.assertEqual(item["quiz_mode"], "free")
        self.assertEqual(item["quiz_ko"], "나 속았어.")
        self.assertNotIn("팔로우", item["posts"][1]["text"])
        self.assertIn("💡 뉘앙스", item["posts"][0]["text"])
        self.assertIn("I fell for it.", item["posts"][1]["text"])


if __name__ == "__main__":
    unittest.main()
