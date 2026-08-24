#!/usr/bin/env python3
"""Normalize legacy Day 29+ copy into the current concise lesson format."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from content_validation import PLACEHOLDER_RE


BASE_DIR = Path(__file__).resolve().parent.parent
QUEUE_FILE = BASE_DIR / "data" / "threads_daily_queue.json"

NUANCE_RE = re.compile(r"💡(?: 원어민)? 뉘앙스\n(.+?)(?=\n\n🔥)", re.S)
EXAMPLE_RE = re.compile(r'•\s+"(.*?)"\n\s*\((.*?)\)', re.S)
PRONUNCIATION_RE = re.compile(
    r"🗣️ 발음 (?:꿀팁|포인트):\n(.+?)(?=\n\n✍️)", re.S
)
QUESTION_RE = re.compile(r"Q\.\s*(.+?)(?=\n\(정답:)", re.S)
ANSWER_RE = re.compile(r"\(정답:\s*(.+?)\)\s*(?:\n|$)", re.S)
NORMALIZED_REVIEW_RE = re.compile(
    r"✍️ 10초 복습\n[\"“](.+?)[\"”]\n\n(.+)$", re.S
)


def _extract(pattern: re.Pattern, text: str, day: int, field: str) -> str:
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Day {day}: {field}를 추출할 수 없습니다.")
    return match.group(1).strip()


def _clean_wrapping_quotes(value: str) -> str:
    value = value.strip()
    if value.startswith('""') and value.endswith('""'):
        return value[1:-1]
    return value.strip('"“”')


def _concrete_phrase(item: dict, answer: str) -> str:
    phrase = item["phrase"].strip()
    if not PLACEHOLDER_RE.search(phrase):
        return phrase
    candidate = _clean_wrapping_quotes(answer)
    # Dialogue answers are too long for a card title; their source phrase is fixed manually later.
    if len(candidate) <= 90 and '" "' not in candidate:
        return candidate
    return phrase


def normalize_item(item: dict) -> dict:
    day = item["day"]
    main_post = next(post for post in item["posts"] if post.get("type") == "main")
    sub_post = next(post for post in item["posts"] if post.get("type") == "sub")
    main_text = main_post["text"]
    sub_text = sub_post["text"]

    if item.get("quality_version") == 2:
        review_match = NORMALIZED_REVIEW_RE.search(sub_text)
        if not review_match:
            raise ValueError(f"Day {day}: 정규화된 복습 문장을 복구할 수 없습니다.")
        item["quiz_mode"] = "free"
        item["quiz_ko"] = review_match.group(1).strip()
        item["answer_example_en"] = review_match.group(2).strip()
        return item

    nuance = _extract(NUANCE_RE, main_text, day, "뉘앙스")
    example_match = EXAMPLE_RE.search(main_text)
    if not example_match:
        raise ValueError(f"Day {day}: 예문을 추출할 수 없습니다.")
    example_en = example_match.group(1).strip()
    example_ko = example_match.group(2).strip()
    pronunciation = _extract(PRONUNCIATION_RE, sub_text, day, "발음")
    question = _clean_wrapping_quotes(_extract(QUESTION_RE, sub_text, day, "질문"))
    answer = _clean_wrapping_quotes(_extract(ANSWER_RE, sub_text, day, "정답"))
    phrase = _concrete_phrase(item, answer)

    item["phrase"] = phrase
    item.setdefault("hook_ko", "힌트 없이 먼저 떠올려보세요")
    item.setdefault("context_ko", "한국어 상황을 자연스러운 영어로 바꿀 때")
    item.setdefault(
        "source_label",
        f"SEINFELD {item['episode'].replace('S', 'S').replace('E', 'E')} · 대사 기반",
    )
    item["delayed_answer"] = True
    item["quiz_mode"] = "free"
    item["quiz_ko"] = question
    item["answer_example_en"] = answer
    item["quality_version"] = 2

    main_post["text"] = (
        f"📌 {phrase}\n{item['meaning_ko']}\n\n"
        f"💡 뉘앙스\n{nuance}\n\n"
        f"🗣 \"{example_en}\"\n{example_ko}"
    )
    sub_post["text"] = (
        f"🗣️ 발음 포인트\n\n{pronunciation}\n\n"
        f"✍️ 10초 복습\n\"{question}\"\n\n{answer}"
    )
    return item


def normalize_queue(queue: list[dict]) -> list[dict]:
    for item in queue:
        if item.get("day", 0) >= 29:
            normalize_item(item)
    return queue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="정규화 결과를 큐 파일에 저장")
    args = parser.parse_args()
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    normalize_queue(queue)
    if not args.apply:
        print(f"정규화 가능: Day 29~{queue[-1]['day']} ({len(queue) - 28}개)")
        return
    temporary = QUEUE_FILE.with_suffix(".json.tmp")
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(queue, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, QUEUE_FILE)
    print(f"정규화 완료: Day 29~{queue[-1]['day']}")


if __name__ == "__main__":
    main()
