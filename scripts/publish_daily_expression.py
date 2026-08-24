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


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {
            "last_published_day": 0,
            "last_published_at": None,
            "history": []
        }
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_queue() -> list[dict]:
    if not QUEUE_FILE.exists():
        raise FileNotFoundError(f"큐 파일이 없습니다: {QUEUE_FILE}")
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


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
        print("=" * 50)
        return

    # 타겟 Day 결정
    if args.day:
        target_day = args.day
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

    if args.dry_run or (not args.publish):
        print("=" * 60)
        print(f"👀 [DRY-RUN] Day {target_day:03d} 카드뉴스 미리보기")
        print(f"🖼️ 카드 이미지 URL: {image_url}")
        print("=" * 60)
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
        now_kst = datetime.now(KST)
        today_str = now_kst.strftime("%Y-%m-%d")

        last_at = state.get("last_published_at")
        if last_at and last_at.startswith(today_str) and not args.force and not args.day:
            print(f"⚠️ 오늘({today_str})은 이미 Day {state.get('last_published_day')} 표현이 발행되었습니다.")
            print("강제 발행을 원하시면 --force 옵션을 사용하세요.")
            sys.exit(0)

        client = ThreadsClient()
        me = client.get_me()
        print(f"👤 계정: @{me.get('username')} ({me.get('name')})")
        print(f"🚀 Day {target_day:03d} - \"{phrase}\" 카드뉴스 발행 시작...\n")

        # 1. 메인 포스트 (카드 이미지 + 텍스트)
        print(f"[1/2] 메인 카드뉴스 이미지 포스팅 중... ({image_url})")
        main_thread_id = client.post(
            text=main_post.get("text", "") if main_post else "",
            image_url=image_url
        )
        print(f"  ✅ 메인 글 발행 완료 (Thread ID: {main_thread_id})")

        # 2. 타래 답글 연결
        print("[2/2] 발음 팁 & 영작 퀴즈 타래 답글 연결 중...")
        sub_thread_id = client.post(
            text=sub_post.get("text", "") if sub_post else "",
            reply_to_id=main_thread_id
        )
        print(f"  ✅ 타래 답글 발행 완료 (Thread ID: {sub_thread_id})")

        # State 업데이트
        now_iso = now_kst.isoformat()
        state["last_published_day"] = target_day
        state["last_published_at"] = now_iso
        state["history"].append({
            "day": target_day,
            "phrase": phrase,
            "published_at": now_iso,
            "main_thread_id": main_thread_id,
            "sub_thread_id": sub_thread_id,
            "image_url": image_url
        })
        save_state(state)

        print(f"\n🎉 [발행 성공] Day {target_day:03d} 카드뉴스가 정상 게시되었습니다!")


if __name__ == "__main__":
    main()
