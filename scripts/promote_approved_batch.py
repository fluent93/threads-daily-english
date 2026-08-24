#!/usr/bin/env python3
"""Promote the user-approved Day 1-14 pilot into the production queue."""

from __future__ import annotations

import json
import os
from pathlib import Path

from build_pilot_queue import build_queue
from validate_expression_selection import validate_selection
from validate_pilot_copy import validate_copy


BASE_DIR = Path(__file__).resolve().parent.parent
SELECTION_FILE = BASE_DIR / "data" / "pilot_expression_selection.json"
COPY_FILE = BASE_DIR / "data" / "pilot_card_copy.json"
OUTPUT_FILE = BASE_DIR / "data" / "threads_daily_queue.json"
APPROVED_DAYS = list(range(1, 15))


def atomic_write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(".json.tmp")
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main() -> int:
    selection = json.loads(SELECTION_FILE.read_text(encoding="utf-8"))
    copy_items = json.loads(COPY_FILE.read_text(encoding="utf-8"))
    days = [item.get("day") for item in selection]
    errors = validate_selection(selection) + validate_copy(selection, copy_items)
    if days != APPROVED_DAYS:
        errors.append(f"승인 범위가 Day 1-14와 다릅니다: {days}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    queue = build_queue(
        selection,
        copy_items,
        card_prefix="REAL",
        quality_version=3,
        review_status="approved",
    )
    atomic_write_json(OUTPUT_FILE, queue)
    print(f"운영 큐 승격 완료: Day 1-{len(queue)} → {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
