#!/usr/bin/env python3
"""Verify that the latest recorded Threads root post still exists."""

from __future__ import annotations

from publish_daily_expression import load_state
from threads_client import ThreadsClient


def main() -> int:
    state = load_state()
    history = state.get("history") or []
    if not history:
        raise RuntimeError("확인할 게시 이력이 없습니다.")

    entry = history[-1]
    thread_id = entry.get("main_thread_id")
    if not thread_id:
        raise RuntimeError("최신 게시 이력에 원글 ID가 없습니다.")

    thread = ThreadsClient().get_thread(str(thread_id))
    if str(thread.get("id")) != str(thread_id):
        raise RuntimeError("원글 조회 결과의 ID가 기록과 일치하지 않습니다.")

    print(f"원글 확인 완료: Day {entry.get('day')} / {thread.get('permalink', thread_id)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
