#!/usr/bin/env python3
"""Hard release switch shared by every external publishing entrypoint."""

from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
STATUS_FILE = BASE_DIR / "data" / "release_status.json"


def load_release_status(path: Path = STATUS_FILE) -> dict:
    if not path.is_file():
        return {
            "publishing_enabled": False,
            "library_status": "unknown",
            "reason": "release_status.json이 없습니다.",
        }
    return json.loads(path.read_text(encoding="utf-8"))


def require_publishing_enabled(path: Path = STATUS_FILE) -> None:
    status = load_release_status(path)
    if status.get("publishing_enabled") is not True:
        reason = status.get("reason") or "콘텐츠 출시 승인이 없습니다."
        raise RuntimeError(f"Threads 게시가 중지되어 있습니다: {reason}")
