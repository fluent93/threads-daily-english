#!/usr/bin/env python3
"""Validate all queued posts and rendered cards before publishing."""

import argparse
import json
import sys
from pathlib import Path

from content_validation import print_report, validate_queue


BASE_DIR = Path(__file__).resolve().parent.parent
QUEUE_FILE = BASE_DIR / "data" / "threads_daily_queue.json"
IMAGES_DIR = BASE_DIR / "images"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=QUEUE_FILE)
    parser.add_argument("--images", type=Path, default=IMAGES_DIR)
    parser.add_argument(
        "--review",
        action="store_true",
        help="연속 Day 검토 큐를 검사하되 최종 편집 승인은 요구하지 않음",
    )
    args = parser.parse_args()
    try:
        with open(args.queue, "r", encoding="utf-8") as handle:
            queue = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: 큐 파일을 읽을 수 없습니다: {exc}")
        return 1

    errors, warnings = validate_queue(
        queue,
        images_dir=args.images,
        require_editorial_approval=not args.review,
        require_card_fingerprint=True,
    )
    print_report(errors, warnings)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
