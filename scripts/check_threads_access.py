#!/usr/bin/env python3
"""Fail early when the Threads token is invalid, under-scoped, or near expiry."""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from threads_client import ThreadsClient


REQUIRED_SCOPES = {
    "threads_basic",
    "threads_content_publish",
    "threads_manage_replies",
}
MINIMUM_REMAINING_DAYS = 7


def evaluate_token(info: dict, now: datetime | None = None) -> tuple[list[str], list[str]]:
    now = now or datetime.now(timezone.utc)
    errors: list[str] = []
    warnings: list[str] = []

    if not info.get("is_valid"):
        errors.append("Threads access token이 유효하지 않습니다.")

    scopes = set(info.get("scopes") or [])
    missing_scopes = sorted(REQUIRED_SCOPES - scopes)
    if missing_scopes:
        errors.append(f"필수 권한이 없습니다: {', '.join(missing_scopes)}")

    expires_at = info.get("expires_at")
    if not isinstance(expires_at, (int, float)) or expires_at <= 0:
        warnings.append("토큰 만료 시각을 확인할 수 없습니다.")
    else:
        expiry = datetime.fromtimestamp(expires_at, timezone.utc)
        remaining = expiry - now
        remaining_days = remaining.total_seconds() / 86400
        print(f"토큰 만료: {expiry.isoformat()} ({remaining_days:.1f}일 남음)")
        if remaining_days < MINIMUM_REMAINING_DAYS:
            errors.append(
                f"토큰 만료까지 {remaining_days:.1f}일 남았습니다. 갱신 후 게시하세요."
            )
        elif remaining_days < 14:
            warnings.append(f"토큰 만료까지 {remaining_days:.1f}일 남았습니다.")

    return errors, warnings


def main() -> int:
    try:
        client = ThreadsClient()
        me = client.get_me()
        info = client.debug_access_token()
    except Exception as exc:
        print(f"ERROR: Threads 접근 사전 점검 실패: {exc}")
        return 1

    print(f"Threads 계정 확인: @{me.get('username')}")
    errors, warnings = evaluate_token(info)
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
