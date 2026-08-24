#!/usr/bin/env python3
"""
Daily Threads Expression Auto-Publisher (with Image Support)
- data/threads_daily_queue.json 에서 다음 Day 표현을 꺼내어
  [1] 카드뉴스 이미지 + 메인 텍스트 포스팅
  [2] 타래 답글 (발음 꿀팁 & 1초 영작 퀴즈)
  순서로 Threads API에 자동 발행합니다.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

from threads_client import ThreadsClient, load_env
from release_control import require_publishing_enabled
from content_validation import (
    build_answer_post,
    build_quiz_prompt,
    get_quiz_spec,
    print_report,
    validate_item,
    uses_delayed_answer,
)

BASE_DIR = Path(__file__).resolve().parent.parent
load_env(BASE_DIR / ".env")

QUEUE_FILE = BASE_DIR / "data" / "threads_daily_queue.json"
STATE_FILE = BASE_DIR / "data" / "threads_post_state.json"
IMAGES_DIR = BASE_DIR / "images"

# GitHub Raw Image Base URL (레포지토리가 push되면 공개 CDN으로 사용됨)
GITHUB_IMAGE_BASE = os.environ.get(
    "GITHUB_IMAGE_BASE",
    "https://raw.githubusercontent.com/fluent93/threads-daily-english/master/images"
)

KST = timezone(timedelta(hours=9))


def get_answer_due_at(published_at: datetime) -> datetime:
    """Use the daily reveal window, with a six-hour delay for late manual posts."""
    reveal_window = published_at.replace(hour=14, minute=0, second=0, microsecond=0)
    if published_at < reveal_window:
        return reveal_window
    return published_at + timedelta(hours=6)


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {
            "last_published_day": 0,
            "last_published_at": None,
            "history": [],
            "in_progress": None,
        }
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    state.setdefault("last_published_day", 0)
    state.setdefault("last_published_at", None)
    state.setdefault("history", [])
    state.setdefault("in_progress", None)
    return state


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = STATE_FILE.with_suffix(".json.tmp")
    with open(temporary_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary_file, STATE_FILE)


def get_queue() -> list[dict]:
    if not QUEUE_FILE.exists():
        raise FileNotFoundError(f"큐 파일이 없습니다: {QUEUE_FILE}")
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def publish_item(
    item: dict,
    state: dict,
    client: ThreadsClient,
    image_url: str,
    *,
    now_kst: datetime,
    save_callback=save_state,
) -> tuple[str, str]:
    """Publish or resume one item, saving progress after every external write."""
    target_day = item["day"]
    phrase = item["phrase"]
    meaning = item["meaning_ko"]
    main_post = next(p for p in item["posts"] if p.get("type") == "main")
    sub_post = next(p for p in item["posts"] if p.get("type") == "sub")
    delayed_answer = uses_delayed_answer(item)
    now_iso = now_kst.isoformat()

    progress = state.get("in_progress")
    if progress and progress.get("day") != target_day:
        raise RuntimeError(
            f"Day {progress.get('day')} 게시가 미완료 상태라 Day {target_day}를 시작할 수 없습니다."
        )
    if not progress:
        progress = {
            "day": target_day,
            "phrase": phrase,
            "started_at": now_iso,
            "image_url": image_url,
            "main_thread_id": None,
            "sub_thread_id": None,
        }
        state["in_progress"] = progress
        save_callback(state)

    main_thread_id = progress.get("main_thread_id")
    if not main_thread_id:
        if delayed_answer:
            quiz_spec = get_quiz_spec(item)
            post_text = build_quiz_prompt(item)
            alt_text = (
                f"미드 실전 영어 Day {target_day} 퀴즈. "
                f"질문: {quiz_spec['quiz_ko']}."
            )
            if quiz_spec["mode"] == "choice":
                alt_text += (
                    f" 선택지 A: {quiz_spec['choice_a']}."
                    f" 선택지 B: {quiz_spec['choice_b']}."
                )
        else:
            post_text = main_post["text"]
            alt_text = f"미드 실전 영어 Day {target_day}: {phrase}. 뜻: {meaning}"
        topic_tag = os.environ.get("THREADS_TOPIC_TAG", "").strip() or None
        print(f"[1/2] 메인 카드뉴스 이미지 포스팅 중... ({image_url})")
        main_thread_id = client.post(
            text=post_text,
            image_url=image_url,
            alt_text=alt_text,
            topic_tag=topic_tag,
        )
        progress["main_thread_id"] = main_thread_id
        save_callback(state)
        print(f"  ✅ 메인 글 발행 완료 (Thread ID: {main_thread_id})")
    else:
        print(f"[1/2] 기존 메인 글에서 재개합니다. (Thread ID: {main_thread_id})")

    sub_thread_id = progress.get("sub_thread_id")
    if delayed_answer:
        print("[2/2] 정답 지연 공개형: 오전에는 추가 답글을 게시하지 않습니다.")
    elif not sub_thread_id:
        print("[2/2] 발음 팁 & 영작 퀴즈 타래 답글 연결 중...")
        sub_thread_id = client.post(
            text=sub_post["text"],
            reply_to_id=main_thread_id,
        )
        progress["sub_thread_id"] = sub_thread_id
        save_callback(state)
        print(f"  ✅ 타래 답글 발행 완료 (Thread ID: {sub_thread_id})")
    else:
        print(f"[2/2] 기존 답글을 확인했습니다. (Thread ID: {sub_thread_id})")

    published_at_dt = now_kst
    published_at = published_at_dt.isoformat()
    state["last_published_day"] = target_day
    state["last_published_at"] = published_at
    if not any(
        entry.get("day") == target_day and entry.get("main_thread_id") == main_thread_id
        for entry in state["history"]
    ):
        state["history"].append({
            "day": target_day,
            "phrase": phrase,
            "published_at": published_at,
            "main_thread_id": main_thread_id,
            "sub_thread_id": sub_thread_id,
            "image_url": image_url,
            "answer_due_at": (
                get_answer_due_at(published_at_dt).isoformat()
                if delayed_answer
                else None
            ),
            "answer_thread_id": None,
            "answer_detail_thread_id": None,
        })
    state["in_progress"] = None
    save_callback(state)
    return main_thread_id, sub_thread_id


def main():
    parser = argparse.ArgumentParser(description="Threads Daily Expression Publisher with Cards")
    parser.add_argument("--dry-run", action="store_true", help="실제 발행하지 않고 오늘 발행될 내용과 이미지 URL 미리보기")
    parser.add_argument("--publish", action="store_true", help="다음 Day 표현을 실제로 Threads에 발행")
    parser.add_argument("--day", type=int, help="특정 Day 번호를 지정하여 발행 (예: --day 1)")
    parser.add_argument("--force", action="store_true", help="당일 중복 발행 제한 무시하고 강제 발행")
    parser.add_argument("--status", action="store_true", help="현재 발행 현황 및 다음 예정 Day 확인")

    args = parser.parse_args()

    state = load_state()
    queue = get_queue()
    total_days = len(queue)

    if args.status:
        last_day = state.get("last_published_day", 0)
        last_time = state.get("last_published_at", "없음")
        next_day = last_day + 1
        print("=" * 50)
        print("📊 [Threads 1일 1표현 카드뉴스 발행 현황]")
        print(f" - 전체 큐: 총 {total_days}일치 준비됨 (이미지 176장 완비)")
        print(f" - 마지막 발행: Day {last_day} ({last_time})")
        print(f" - 다음 발행 예정: Day {next_day}")
        if state.get("in_progress"):
            progress = state["in_progress"]
            print(
                f" - 복구 대기: Day {progress.get('day')} "
                f"(main={bool(progress.get('main_thread_id'))}, "
                f"sub={bool(progress.get('sub_thread_id'))})"
            )
        print("=" * 50)
        return

    # 타겟 Day 결정
    progress = state.get("in_progress")
    if args.day:
        target_day = args.day
        if progress and progress.get("day") != target_day:
            print(
                f"❌ Day {progress.get('day')} 게시가 미완료 상태입니다. "
                "먼저 해당 게시를 복구해야 합니다."
            )
            sys.exit(1)
    elif progress:
        target_day = progress["day"]
    else:
        target_day = state.get("last_published_day", 0) + 1

    item = next((x for x in queue if x.get("day") == target_day), None)
    if not item:
        print(f"❌ Day {target_day} 항목을 찾을 수 없습니다.")
        sys.exit(1)

    posts = item.get("posts", [])
    phrase = item.get("phrase", "")
    meaning = item.get("meaning_ko", "")
    image_url = f"{GITHUB_IMAGE_BASE}/day_{target_day:03d}.png"

    main_post = next((p for p in posts if p.get("type") == "main"), None)
    sub_post = next((p for p in posts if p.get("type") == "sub"), None)

    validation_errors, validation_warnings = validate_item(
        item,
        images_dir=IMAGES_DIR,
        require_editorial_approval=True,
        require_card_fingerprint=True,
    )
    if validation_warnings:
        print_report([], validation_warnings)
    if validation_errors:
        print_report(validation_errors, [])
        print("❌ 콘텐츠 검증 실패로 발행을 중단합니다.")
        sys.exit(1)

    if args.dry_run or (not args.publish):
        print("=" * 60)
        print(f"👀 [DRY-RUN] Day {target_day:03d} 카드뉴스 미리보기")
        print(f"🖼️ 카드 이미지 URL: {image_url}")
        print("=" * 60)
        if uses_delayed_answer(item):
            print("\n[오전 08:07] 정답 없는 참여형 문제 (이미지 첨부):")
            print("-" * 50)
            print(build_quiz_prompt(item))
            print("-" * 50)
            print("\n[오후 14:07] 같은 타래의 정답·뉘앙스:")
            print("-" * 50)
            print(build_answer_post(item, main_post.get("text", "")))
            print("-" * 50)
            print("\n[정답 상세 답글] 발음·복습:")
            print("-" * 50)
            print(sub_post.get("text") if sub_post else "")
            print("-" * 50)
        else:
            print("\n[1/2] 메인 포스트 (이미지 첨부):")
            print("-" * 50)
            print(main_post.get("text") if main_post else "")
            print("-" * 50)
            print("\n[2/2] 타래 답글 (발음 & 1초 영작 퀴즈):")
            print("-" * 50)
            print(sub_post.get("text") if sub_post else "")
            print("-" * 50)
        if not args.publish:
            print("\n💡 실제 발행 명령: python3 scripts/publish_daily_expression.py --publish")
        return

    if args.publish:
        try:
            require_publishing_enabled()
        except RuntimeError as exc:
            print(f"❌ {exc}")
            sys.exit(1)
        now_kst = datetime.now(KST)
        today_str = now_kst.strftime("%Y-%m-%d")

        last_at = state.get("last_published_at")
        if (
            last_at
            and last_at.startswith(today_str)
            and not args.force
            and not args.day
            and not state.get("in_progress")
        ):
            print(f"⚠️ 오늘({today_str})은 이미 Day {state.get('last_published_day')} 표현이 발행되었습니다.")
            print("강제 발행을 원하시면 --force 옵션을 사용하세요.")
            sys.exit(0)

        client = ThreadsClient()
        me = client.get_me()
        print(f"👤 계정: @{me.get('username')} ({me.get('name')})")
        print(f"🚀 Day {target_day:03d} - \"{phrase}\" 카드뉴스 발행 시작...\n")

        publish_item(
            item,
            state,
            client,
            image_url,
            now_kst=now_kst,
        )

        print(f"\n🎉 [발행 성공] Day {target_day:03d} 카드뉴스가 정상 게시되었습니다!")


if __name__ == "__main__":
    main()
