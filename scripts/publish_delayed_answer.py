#!/usr/bin/env python3
"""Publish due answers as replies to morning quiz posts."""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from publish_daily_expression import KST, get_queue, load_state, save_state
from content_validation import build_answer_post, uses_delayed_answer
from release_control import require_publishing_enabled
from threads_client import ThreadsClient


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"시간대가 없는 시각은 사용할 수 없습니다: {value}")
    return parsed


def next_pending_due_at(state: dict, *, now_kst: datetime) -> datetime | None:
    """Return the nearest unanswered reveal time that is still in the future."""
    due_times = []
    for entry in state.get("history", []):
        due_at = entry.get("answer_due_at")
        if due_at and not entry.get("answer_detail_thread_id"):
            parsed = _parse_datetime(due_at)
            if parsed > now_kst:
                due_times.append(parsed)
    return min(due_times) if due_times else None


def publish_due_answers(
    state: dict,
    queue: list[dict],
    client: ThreadsClient,
    *,
    now_kst: datetime,
    save_callback=save_state,
) -> int:
    """Publish every due answer, resuming safely after partial failures."""
    if now_kst.tzinfo is None:
        raise ValueError("now_kst에는 시간대 정보가 필요합니다.")

    items_by_day = {item["day"]: item for item in queue}
    due_entries = []
    for entry in state.get("history", []):
        due_at = entry.get("answer_due_at")
        if not due_at or entry.get("answer_detail_thread_id"):
            continue
        if _parse_datetime(due_at) <= now_kst:
            due_entries.append(entry)

    due_entries.sort(key=lambda entry: entry["answer_due_at"])
    completed = 0

    for entry in due_entries:
        day = entry.get("day")
        item = items_by_day.get(day)
        if not item or not uses_delayed_answer(item):
            raise RuntimeError(f"Day {day}의 지연 공개 콘텐츠를 찾을 수 없습니다.")
        root_thread_id = entry.get("main_thread_id")
        if not root_thread_id:
            raise RuntimeError(f"Day {day}의 오전 원글 ID가 없습니다.")

        root_thread = client.get_thread(str(root_thread_id))
        if str(root_thread.get("id")) != str(root_thread_id):
            raise RuntimeError(f"Day {day}의 오전 원글을 확인할 수 없습니다.")

        main_post = next(post for post in item["posts"] if post.get("type") == "main")
        sub_post = next(post for post in item["posts"] if post.get("type") == "sub")
        answer_thread_id = entry.get("answer_thread_id")

        if not answer_thread_id:
            answer_text = build_answer_post(item, main_post["text"])
            print(f"[Day {day:03d}] 정답·뉘앙스 답글 게시 중...")
            answer_thread_id = client.post(
                text=answer_text,
                reply_to_id=root_thread_id,
            )
            entry["answer_thread_id"] = answer_thread_id
            save_callback(state)
            print(f"  ✅ 정답 답글 완료 (Thread ID: {answer_thread_id})")
        else:
            print(f"[Day {day:03d}] 기존 정답 답글에서 재개합니다.")

        if not entry.get("answer_detail_thread_id"):
            print(f"[Day {day:03d}] 발음·복습 답글 게시 중...")
            detail_thread_id = client.post(
                text=sub_post["text"],
                reply_to_id=answer_thread_id,
            )
            entry["answer_detail_thread_id"] = detail_thread_id
            entry["answer_published_at"] = now_kst.isoformat()
            save_callback(state)
            print(f"  ✅ 발음·복습 답글 완료 (Thread ID: {detail_thread_id})")
        completed += 1

    return completed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wait-until-due",
        action="store_true",
        help="공개 시각 전에 시작된 예약 실행은 답글 공개 시각까지 대기합니다.",
    )
    args = parser.parse_args()
    require_publishing_enabled()
    state = load_state()
    queue = get_queue()
    now_kst = datetime.now(KST)
    if args.wait_until_due:
        due_at = next_pending_due_at(state, now_kst=now_kst)
        if due_at:
            wait_seconds = (due_at - now_kst).total_seconds()
            print(f"⏳ 답글 공개 시각({due_at.isoformat()})까지 {wait_seconds:.0f}초 대기합니다.")
            time.sleep(wait_seconds)
    client = ThreadsClient()
    me = client.get_me()
    print(f"👤 계정: @{me.get('username')} ({me.get('name')})")
    completed = publish_due_answers(
        state,
        queue,
        client,
        now_kst=datetime.now(KST),
    )
    if completed:
        print(f"🎉 공개 시각이 지난 정답 {completed}개를 게시했습니다.")
    else:
        print("ℹ️ 지금 공개할 정답이 없습니다.")


if __name__ == "__main__":
    main()
