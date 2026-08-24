#!/usr/bin/env python3
"""Validation rules shared by CI and the publisher."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from PIL import Image


MAX_POST_CHARS = 500
EXPECTED_IMAGE_SIZE = (1080, 1080)
MAX_IMAGE_BYTES = 8 * 1024 * 1024
KNOWN_TYPO_TOKENS = ("쯙", "살짙", "초근무")
PLACEHOLDER_RE = re.compile(
    r"\[[^\]]+\]|~(?:ing)?|\((?:someone|something|one's|my/your|it/that)[^)]*\)",
    re.IGNORECASE,
)


def build_quiz_prompt(item: dict) -> str:
    """Build the answer-free morning prompt for delayed-reveal lessons."""
    return (
        "🎬 오늘의 10초 미드 영어\n\n"
        f"{item['hook_ko']}\n\n"
        f"Q. {item['quiz_ko']}\n\n"
        f"A. {item['choice_a']}\n"
        f"B. {item['choice_b']}\n\n"
        "A/B만 댓글로 남겨도 좋아요. 이유나 다른 표현도 환영합니다.\n"
        "정답·뉘앙스·발음은 오후 2:07에 이 타래에서 공개합니다."
    )


def build_answer_post(item: dict, main_text: str) -> str:
    """Build the delayed answer reply with a diagnostic explanation."""
    return (
        f"✅ 정답: {item['answer_choice']}\n"
        f"🔎 {item['answer_explanation_ko']}\n\n"
        f"{main_text}"
    )


def normalized_phrase(value: str) -> str:
    return re.sub(r"\W+", " ", value.casefold()).strip()


def validate_item(item: object, images_dir: Path | None = None) -> tuple[list[str], list[str]]:
    """Validate one queue item and return (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(item, dict):
        return ["항목이 객체가 아닙니다."], warnings

    day = item.get("day")
    label = f"Day {day}" if isinstance(day, int) else "Day ?"
    if not isinstance(day, int) or day < 1:
        errors.append(f"{label}: day는 1 이상의 정수여야 합니다.")

    for field in ("card_id", "episode", "phrase", "meaning_ko"):
        if not isinstance(item.get(field), str) or not item[field].strip():
            errors.append(f"{label}: {field}가 비어 있습니다.")

    posts = item.get("posts")
    if not isinstance(posts, list):
        errors.append(f"{label}: posts는 배열이어야 합니다.")
        posts = []

    by_type: dict[str, list[dict]] = defaultdict(list)
    for post in posts:
        if not isinstance(post, dict):
            errors.append(f"{label}: post 항목이 객체가 아닙니다.")
            continue
        by_type[str(post.get("type"))].append(post)

    for post_type in ("main", "sub"):
        matches = by_type.get(post_type, [])
        if len(matches) != 1:
            errors.append(f"{label}: {post_type} post는 정확히 1개여야 합니다.")
            continue
        text = matches[0].get("text")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{label}: {post_type} text가 비어 있습니다.")
        elif len(text) > MAX_POST_CHARS:
            errors.append(
                f"{label}: {post_type} text가 {len(text)}자로 "
                f"Threads 한도 {MAX_POST_CHARS}자를 초과합니다."
            )

    if item.get("delayed_answer"):
        for field in (
            "hook_ko",
            "quiz_ko",
            "choice_a",
            "choice_b",
            "answer_explanation_ko",
        ):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{label}: 지연 공개용 {field}가 비어 있습니다.")
        answer_choice = item.get("answer_choice")
        if answer_choice not in {"A", "B"}:
            errors.append(f"{label}: answer_choice는 A 또는 B여야 합니다.")
        required = all(
            isinstance(item.get(field), str) and item[field].strip()
            for field in ("hook_ko", "quiz_ko", "choice_a", "choice_b")
        )
        if required:
            quiz_prompt = build_quiz_prompt(item)
            if len(quiz_prompt) > MAX_POST_CHARS:
                errors.append(
                    f"{label}: 오전 퀴즈가 {len(quiz_prompt)}자로 "
                    f"Threads 한도 {MAX_POST_CHARS}자를 초과합니다."
                )
        main_matches = by_type.get("main", [])
        if (
            len(main_matches) == 1
            and answer_choice in {"A", "B"}
            and isinstance(item.get("answer_explanation_ko"), str)
            and item["answer_explanation_ko"].strip()
        ):
            answer_text = build_answer_post(item, main_matches[0].get("text", ""))
            if len(answer_text) > MAX_POST_CHARS:
                errors.append(
                    f"{label}: 오후 정답 글이 {len(answer_text)}자로 "
                    f"Threads 한도 {MAX_POST_CHARS}자를 초과합니다."
                )

    serialized = repr(item)
    for typo in KNOWN_TYPO_TOKENS:
        if typo in serialized:
            errors.append(f"{label}: 알려진 오타 '{typo}'가 있습니다.")

    phrase = item.get("phrase")
    if isinstance(phrase, str) and PLACEHOLDER_RE.search(phrase):
        warnings.append(f"{label}: 카드 표현에 플레이스홀더가 있습니다: {phrase}")

    if images_dir is not None and isinstance(day, int):
        image_path = images_dir / f"day_{day:03d}.png"
        if not image_path.is_file():
            errors.append(f"{label}: 이미지가 없습니다: {image_path.name}")
        else:
            if image_path.stat().st_size > MAX_IMAGE_BYTES:
                errors.append(f"{label}: 이미지가 8MB를 초과합니다.")
            try:
                with Image.open(image_path) as image:
                    if image.size != EXPECTED_IMAGE_SIZE:
                        errors.append(
                            f"{label}: 이미지 크기가 {image.size}입니다. "
                            f"예상 크기는 {EXPECTED_IMAGE_SIZE}입니다."
                        )
                    image.verify()
            except Exception as exc:
                errors.append(f"{label}: 이미지를 열 수 없습니다: {exc}")

    return errors, warnings


def validate_queue(
    queue: object, images_dir: Path | None = None
) -> tuple[list[str], list[str]]:
    """Validate the complete publishing queue."""
    if not isinstance(queue, list) or not queue:
        return ["큐는 비어 있지 않은 배열이어야 합니다."], []

    errors: list[str] = []
    warnings: list[str] = []
    days: list[int] = []
    phrases: dict[str, list[int]] = defaultdict(list)

    for item in queue:
        item_errors, item_warnings = validate_item(item, images_dir=images_dir)
        errors.extend(item_errors)
        warnings.extend(item_warnings)
        if isinstance(item, dict) and isinstance(item.get("day"), int):
            day = item["day"]
            days.append(day)
            phrase = item.get("phrase")
            if isinstance(phrase, str) and phrase.strip():
                phrases[normalized_phrase(phrase)].append(day)

    expected_days = list(range(1, len(queue) + 1))
    if days != expected_days:
        errors.append(
            "day 번호는 파일 순서대로 1부터 연속이어야 합니다 "
            f"(실제 {days[:5]}...{days[-5:] if days else []})."
        )

    for normalized, duplicate_days in phrases.items():
        if normalized and len(duplicate_days) > 1:
            errors.append(
                f"중복 표현이 있습니다: Day {', '.join(map(str, duplicate_days))}"
            )

    return errors, warnings


def print_report(errors: Iterable[str], warnings: Iterable[str]) -> None:
    errors = list(errors)
    warnings = list(warnings)
    for message in errors:
        print(f"ERROR: {message}")
    for message in warnings:
        print(f"WARNING: {message}")
    print(f"검증 결과: 오류 {len(errors)}건, 경고 {len(warnings)}건")
