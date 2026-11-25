#!/usr/bin/env python3
"""Append one or more approved monthly batches to the production queue."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from build_pilot_queue import build_queue
from validate_expression_selection import validate_selection
from validate_pilot_copy import validate_copy


def atomic_write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(".json.tmp")
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--replace-from", type=int, help="Replace existing queue items from this Day")
    parser.add_argument("--batch", action="append", nargs=2, metavar=("SELECTION", "COPY"), required=True)
    args = parser.parse_args()
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    if args.replace_from is not None:
        if args.replace_from < 1 or args.replace_from > queue[-1]["day"] + 1:
            raise SystemExit("--replace-from 범위가 운영 큐와 맞지 않습니다.")
        queue = [item for item in queue if item["day"] < args.replace_from]
    next_day = queue[-1]["day"] + 1
    additions: list[dict] = []
    errors: list[str] = []
    for selection_name, copy_name in args.batch:
        selection = json.loads(Path(selection_name).read_text(encoding="utf-8"))
        copy = json.loads(Path(copy_name).read_text(encoding="utf-8"))
        errors.extend(validate_selection(selection))
        errors.extend(validate_copy(selection, copy))
        if selection and selection[0].get("day") != next_day:
            errors.append(f"다음 Day는 {next_day}여야 합니다: {selection_name}")
        additions.extend(build_queue(selection, copy, card_prefix="REAL", quality_version=3, review_status="approved"))
        next_day += len(selection)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    merged = queue + additions
    if [item["day"] for item in merged] != list(range(1, len(merged) + 1)):
        print("ERROR: 운영 큐 Day가 연속적이지 않습니다.")
        return 1
    atomic_write_json(args.queue, merged)
    print(f"운영 큐 병합 완료: Day 1-{merged[-1]['day']} ({len(additions)}개 추가)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
