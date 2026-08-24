#!/usr/bin/env python3
"""Print reproducible release-readiness metrics for the 176-day library."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from content_validation import build_quiz_prompt, get_quiz_spec


BASE_DIR = Path(__file__).resolve().parent.parent
QUEUE_FILE = BASE_DIR / "data" / "threads_daily_queue.json"
EDITORIAL_FILE = BASE_DIR / "data" / "editorial_overrides.json"


def main() -> None:
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    editorial = json.loads(EDITORIAL_FILE.read_text(encoding="utf-8"))
    specs = [get_quiz_spec(item) for item in queue]
    choice_items = [item for item, spec in zip(queue, specs) if spec["mode"] == "choice"]
    prompt_lengths = [(len(build_quiz_prompt(item)), item["day"]) for item in queue]

    print("콘텐츠 품질 리포트")
    print(f"- 전체 라이브러리: {len(queue)}개")
    print(
        "- 최종 편집 승인: "
        f"{sum(item.get('quality_version') == 3 for item in queue)}/{len(queue)}개"
    )
    print(f"- 정답 지연 공개: {sum(item.get('delayed_answer') is True for item in queue)}/{len(queue)}개")
    print(f"- 문항 구성: A/B {len(choice_items)}개, 자유 영작 {len(queue) - len(choice_items)}개")
    print(f"- A/B 정답 분포: {dict(Counter(item['answer_choice'] for item in choice_items))}")
    print(f"- A/B 초점 분포: {dict(Counter(item['quiz_focus'] for item in choice_items))}")
    print(f"- 고유 상황형 훅: {len({item['hook_ko'] for item in queue})}/{len(queue)}개")
    print(f"- 전면 교체 문항: {len(editorial.get('items', {}))}개")
    longest_length, longest_day = max(prompt_lengths)
    print(f"- 최장 오전 게시물: Day {longest_day}, {longest_length}/500자")


if __name__ == "__main__":
    main()
