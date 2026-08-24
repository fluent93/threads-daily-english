#!/usr/bin/env python3
"""Apply reviewed editorial overrides and approval status to the queue."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
QUEUE_FILE = BASE_DIR / "data" / "threads_daily_queue.json"
OVERRIDES_FILE = BASE_DIR / "data" / "editorial_overrides.json"
REQUIRED_REWRITE_FIELDS = {
    "phrase",
    "meaning_ko",
    "hook_ko",
    "context_ko",
    "quiz_ko",
    "answer_example_en",
    "nuance_ko",
    "example_en",
    "example_ko",
    "pronunciation_ko",
}
REQUIRED_POLISH_FIELDS = {"hook_ko", "context_ko"}


def apply_override(item: dict, override: dict) -> None:
    missing = REQUIRED_REWRITE_FIELDS - set(override)
    if missing:
        raise ValueError(
            f"Day {item['day']}: 수동 교체 필드가 부족합니다: {', '.join(sorted(missing))}"
        )
    for field in (
        "phrase",
        "meaning_ko",
        "hook_ko",
        "context_ko",
        "quiz_ko",
        "answer_example_en",
    ):
        item[field] = override[field]
    item["quiz_mode"] = "free"
    item["delayed_answer"] = True
    main_post = next(post for post in item["posts"] if post.get("type") == "main")
    sub_post = next(post for post in item["posts"] if post.get("type") == "sub")
    main_post["text"] = (
        f"📌 {override['phrase']}\n{override['meaning_ko']}\n\n"
        f"💡 뉘앙스\n{override['nuance_ko']}\n\n"
        f"🗣 \"{override['example_en']}\"\n{override['example_ko']}"
    )
    sub_post["text"] = (
        f"🗣️ 발음 포인트\n\n{override['pronunciation_ko']}\n\n"
        f"✍️ 10초 복습\n\"{override['quiz_ko']}\"\n\n"
        f"{override['answer_example_en']}"
    )


def apply_editorial_data(queue: list[dict], editorial: dict) -> list[dict]:
    by_day = {item["day"]: item for item in queue}
    approved_days = editorial.get("approved_days", [])
    polish = editorial.get("polish", {})
    overrides = editorial.get("items", {})
    for day_text, fields in polish.items():
        day = int(day_text)
        if day not in by_day:
            raise ValueError(f"Day {day}: 큐에 없는 다듬기 항목입니다.")
        missing = REQUIRED_POLISH_FIELDS - set(fields)
        if missing:
            raise ValueError(
                f"Day {day}: 다듬기 필드가 부족합니다: {', '.join(sorted(missing))}"
            )
        by_day[day]["hook_ko"] = fields["hook_ko"]
        by_day[day]["context_ko"] = fields["context_ko"]
    for day_text, override in overrides.items():
        day = int(day_text)
        if day not in by_day:
            raise ValueError(f"Day {day}: 큐에 없는 항목입니다.")
        apply_override(by_day[day], override)
    for day in approved_days:
        if day not in by_day:
            raise ValueError(f"Day {day}: 승인 대상이 큐에 없습니다.")
        by_day[day]["quality_version"] = 3
    unapproved_overrides = sorted(set(map(int, overrides)) - set(approved_days))
    if unapproved_overrides:
        raise ValueError(f"교체됐지만 승인 목록에 없는 Day: {unapproved_overrides}")
    return queue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    editorial = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    apply_editorial_data(queue, editorial)
    if not args.apply:
        print(
            f"편집 승인 {len(editorial.get('approved_days', []))}개, "
            f"훅 다듬기 {len(editorial.get('polish', {}))}개, "
            f"수동 교체 {len(editorial.get('items', {}))}개 적용 가능"
        )
        return
    temporary = QUEUE_FILE.with_suffix(".json.tmp")
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(queue, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, QUEUE_FILE)
    print("편집 승인·교체 반영 완료")


if __name__ == "__main__":
    main()
