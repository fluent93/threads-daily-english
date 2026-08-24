#!/usr/bin/env python3
"""Build a non-publishable review queue from the approved pilot selection and copy."""

from __future__ import annotations

import json
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SELECTION_FILE = BASE_DIR / "data" / "pilot_expression_selection.json"
COPY_FILE = BASE_DIR / "data" / "pilot_card_copy.json"
OUTPUT_FILE = BASE_DIR / "data" / "pilot_threads_queue.json"


def build_queue(selection: list[dict], copy_items: list[dict]) -> list[dict]:
    copy_by_day = {item["day"]: item for item in copy_items}
    queue: list[dict] = []
    for selected in selection:
        day = selected["day"]
        copy = copy_by_day[day]
        main_text = (
            f"📌 {selected['phrase']}\n{selected['meaning_ko']}\n\n"
            f"💡 뉘앙스\n{copy['nuance_ko']}\n\n"
            f"🗣 \"{copy['example_en']}\"\n{copy['example_ko']}\n\n"
            f"🔄 함께 가능한 표현\n\"{copy['alternative_en']}\"\n"
            f"{copy['alternative_note_ko']}"
        )
        sub_text = (
            f"🗣️ 발음 포인트\n\n{copy['pronunciation_ko']}\n\n"
            f"✍️ 10초 복습\n\"{copy['quiz_ko']}\"\n\n"
            f"{copy['answer_example_en']}"
        )
        queue.append(
            {
                "day": day,
                "card_id": f"PILOT-{day:03d}",
                "episode": "REAL-LIFE",
                "phrase": selected["phrase"],
                "meaning_ko": selected["meaning_ko"],
                "posts": [
                    {"index": 1, "type": "main", "text": main_text},
                    {"index": 2, "type": "sub", "text": sub_text},
                ],
                "hook_ko": copy["hook_ko"],
                "context_ko": selected["category"],
                "source_label": "REAL-LIFE ENGLISH · 상황 기반",
                "delayed_answer": True,
                "quality_version": 0,
                "quiz_mode": "free",
                "quiz_ko": copy["quiz_ko"],
                "answer_example_en": copy["answer_example_en"],
                "review_status": "pilot",
            }
        )
    return queue


def main() -> None:
    selection = json.loads(SELECTION_FILE.read_text(encoding="utf-8"))
    copy_items = json.loads(COPY_FILE.read_text(encoding="utf-8"))
    queue = build_queue(selection, copy_items)
    temporary = OUTPUT_FILE.with_suffix(".json.tmp")
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(queue, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, OUTPUT_FILE)
    print(f"파일럿 검토 큐 생성: {len(queue)}개 → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
