#!/usr/bin/env python3
"""Build a non-publishable review queue from a monthly selection and copy file."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from build_pilot_queue import build_queue
from validate_expression_selection import validate_selection
from validate_pilot_copy import validate_copy


def atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--copy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    copy_items = json.loads(args.copy.read_text(encoding="utf-8"))
    errors = validate_selection(selection) + validate_copy(selection, copy_items)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    queue = build_queue(
        selection,
        copy_items,
        card_prefix="REVIEW",
        quality_version=0,
        review_status="review",
    )
    atomic_write_json(args.output, queue)
    print(
        f"검토 큐 생성: Day {queue[0]['day']}-{queue[-1]['day']} "
        f"({len(queue)}개) → {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
