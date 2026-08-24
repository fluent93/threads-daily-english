#!/usr/bin/env python3
"""Validate all queued posts and rendered cards before publishing."""

import json
import sys
from pathlib import Path

from content_validation import print_report, validate_queue


BASE_DIR = Path(__file__).resolve().parent.parent
QUEUE_FILE = BASE_DIR / "data" / "threads_daily_queue.json"
IMAGES_DIR = BASE_DIR / "images"


def main() -> int:
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as handle:
            queue = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: 큐 파일을 읽을 수 없습니다: {exc}")
        return 1

    errors, warnings = validate_queue(
        queue,
        images_dir=IMAGES_DIR,
        require_editorial_approval=True,
    )
    print_report(errors, warnings)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
