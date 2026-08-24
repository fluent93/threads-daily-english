#!/usr/bin/env python3
"""Validation rules shared by CI and the publisher."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from PIL import Image


MAX_POST_CHARS = 500
EXPECTED_IMAGE_SIZE = (1080, 1080)
MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_QUIZ_FOCUS = {"context", "nuance", "register", "collocation", "grammar"}
KNOWN_TYPO_TOKENS = ("쯙", "살짙", "초근무")
GENERIC_HOOKS = {
    "힌트 없이 먼저 떠올려보세요",
    "이 상황, 영어로 어떻게 말할까요?",
}
PLACEHOLDER_RE = re.compile(
    r"\[[^\]]+\]|~(?:ing)?|\((?:someone|something|one's|my/your|it/that)[^)]*\)",
    re.IGNORECASE,
)
QUIZ_LINE_RE = re.compile(r"Q\.\s*(.+?)(?:\n|$)")


def uses_delayed_answer(item: dict) -> bool:
    """Delayed reveal is the service default; explicit false is legacy opt-out."""
    return item.get("delayed_answer") is not False


def _clean_quiz_text(value: str) -> str:
    value = value.strip()
    if value.startswith('""') and value.endswith('""'):
        return value[1:-1]
    return value.strip('"“”')


def get_quiz_spec(item: dict) -> dict:
    """Return explicit A/B quiz data or derive a free-response quiz from the sub post."""
    if all(item.get(field) for field in ("quiz_ko", "choice_a", "choice_b")):
        return {
            "mode": "choice",
            "hook_ko": item.get("hook_ko", "이 상황, 영어로 어떻게 말할까요?"),
            "quiz_ko": item["quiz_ko"],
            "choice_a": item["choice_a"],
            "choice_b": item["choice_b"],
        }
    if item.get("quiz_mode") == "free" and item.get("quiz_ko"):
        return {
            "mode": "free",
            "hook_ko": item.get("hook_ko", "힌트 없이 먼저 떠올려보세요"),
            "quiz_ko": item["quiz_ko"],
            "choice_a": "",
            "choice_b": "",
        }

    posts = item.get("posts") if isinstance(item.get("posts"), list) else []
    sub_text = next(
        (
            post.get("text", "")
            for post in posts
            if isinstance(post, dict) and post.get("type") == "sub"
        ),
        "",
    )
    match = QUIZ_LINE_RE.search(sub_text)
    quiz_ko = _clean_quiz_text(match.group(1)) if match else ""
    return {
        "mode": "free",
        "hook_ko": item.get("hook_ko", "힌트 없이 먼저 떠올려보세요"),
        "quiz_ko": quiz_ko,
        "choice_a": "",
        "choice_b": "",
    }


def build_quiz_prompt(item: dict) -> str:
    """Build the answer-free morning prompt for delayed-reveal lessons."""
    spec = get_quiz_spec(item)
    if spec["mode"] == "free":
        return (
            "🎬 오늘의 10초 미드 영어\n\n"
            f"{spec['hook_ko']}\n\n"
            f"Q. {spec['quiz_ko']}\n\n"
            "영어 한 문장으로 댓글에 도전해보세요.\n"
            "정답 예시·뉘앙스·발음은 오후 2:07에 이 타래에서 공개합니다."
        )
    return (
        "🎬 오늘의 10초 미드 영어\n\n"
        f"{spec['hook_ko']}\n\n"
        f"Q. {spec['quiz_ko']}\n\n"
        f"A. {spec['choice_a']}\n"
        f"B. {spec['choice_b']}\n\n"
        "A/B만 댓글로 남겨도 좋아요. 이유나 다른 표현도 환영합니다.\n"
        "정답·뉘앙스·발음은 오후 2:07에 이 타래에서 공개합니다."
    )


def build_answer_post(item: dict, main_text: str) -> str:
    """Build the delayed answer reply with a diagnostic explanation."""
    if get_quiz_spec(item)["mode"] == "free":
        return f"✅ 정답 예시\n\n{main_text}"
    return (
        f"✅ 정답: {item['answer_choice']}\n"
        f"🔎 {item['answer_explanation_ko']}\n\n"
        f"{main_text}"
    )


def card_fingerprint(item: dict) -> str:
    """Hash every field that affects the rendered morning card."""
    spec = get_quiz_spec(item) if uses_delayed_answer(item) else {}
    payload = {
        "day": item.get("day"),
        "phrase": item.get("phrase", ""),
        "meaning_ko": item.get("meaning_ko", ""),
        "hook_ko": spec.get("hook_ko", item.get("hook_ko", "")),
        "context_ko": item.get("context_ko", ""),
        "source_label": item.get("source_label", ""),
        "delayed_answer": uses_delayed_answer(item),
        "quiz_ko": spec.get("quiz_ko", ""),
        "choice_a": spec.get("choice_a", ""),
        "choice_b": spec.get("choice_b", ""),
        "quiz_mode": spec.get("mode", "choice"),
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalized_phrase(value: str) -> str:
    return re.sub(r"\W+", " ", value.casefold()).strip()


def _validate_choice_quiz(item: dict, label: str, by_type: dict) -> list[str]:
    errors: list[str] = []
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
    quiz_focus = item.get("quiz_focus")
    if quiz_focus not in ALLOWED_QUIZ_FOCUS:
        errors.append(
            f"{label}: quiz_focus는 {', '.join(sorted(ALLOWED_QUIZ_FOCUS))} 중 하나여야 합니다."
        )
    explanation = item.get("answer_explanation_ko")
    if isinstance(explanation, str) and not all(
        marker in explanation for marker in ("A는", "B는")
    ):
        errors.append(f"{label}: 해설은 A와 B의 차이를 모두 설명해야 합니다.")
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
    return errors


def validate_item(
    item: object,
    images_dir: Path | None = None,
    *,
    require_editorial_approval: bool = False,
    require_card_fingerprint: bool = False,
) -> tuple[list[str], list[str]]:
    """Validate one queue item and return (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(item, dict):
        return ["항목이 객체가 아닙니다."], warnings

    day = item.get("day")
    label = f"Day {day}" if isinstance(day, int) else "Day ?"
    if not isinstance(day, int) or day < 1:
        errors.append(f"{label}: day는 1 이상의 정수여야 합니다.")

    if require_editorial_approval:
        if item.get("quality_version") != 3:
            errors.append(f"{label}: 최종 편집 승인(quality_version 3)이 없습니다.")
        hook = item.get("hook_ko")
        context = item.get("context_ko")
        if not isinstance(hook, str) or not hook.strip():
            errors.append(f"{label}: 상황형 훅이 비어 있습니다.")
        elif hook.strip() in GENERIC_HOOKS:
            errors.append(f"{label}: 범용 훅 대신 표현별 상황형 훅이 필요합니다.")
        if not isinstance(context, str) or not context.strip():
            errors.append(f"{label}: 사용 맥락이 비어 있습니다.")

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

    if uses_delayed_answer(item):
        spec = get_quiz_spec(item)
        if not spec["quiz_ko"]:
            errors.append(f"{label}: 오전에 사용할 영작 질문을 추출할 수 없습니다.")
        if spec["mode"] == "free":
            if build_quiz_prompt(item) and len(build_quiz_prompt(item)) > MAX_POST_CHARS:
                errors.append(f"{label}: 오전 자유 영작 퀴즈가 500자를 초과합니다.")
            main_matches = by_type.get("main", [])
            if len(main_matches) == 1:
                answer_text = build_answer_post(item, main_matches[0].get("text", ""))
                if len(answer_text) > MAX_POST_CHARS:
                    errors.append(f"{label}: 오후 정답 글이 500자를 초과합니다.")
        else:
            errors.extend(_validate_choice_quiz(item, label, by_type))

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
                    if require_card_fingerprint:
                        actual_fingerprint = image.info.get("content_fingerprint")
                        expected_fingerprint = card_fingerprint(item)
                        if actual_fingerprint != expected_fingerprint:
                            errors.append(
                                f"{label}: 카드 이미지가 현재 콘텐츠와 일치하지 않습니다. "
                                "이미지를 다시 생성하세요."
                            )
                    image.verify()
            except Exception as exc:
                errors.append(f"{label}: 이미지를 열 수 없습니다: {exc}")

    return errors, warnings


def validate_queue(
    queue: object,
    images_dir: Path | None = None,
    *,
    require_editorial_approval: bool = False,
) -> tuple[list[str], list[str]]:
    """Validate the complete publishing queue."""
    if not isinstance(queue, list) or not queue:
        return ["큐는 비어 있지 않은 배열이어야 합니다."], []

    errors: list[str] = []
    warnings: list[str] = []
    days: list[int] = []
    phrases: dict[str, list[int]] = defaultdict(list)
    choice_answers: list[str] = []
    choice_focuses: list[str] = []
    hooks: dict[str, list[int]] = defaultdict(list)

    for item in queue:
        item_errors, item_warnings = validate_item(
            item,
            images_dir=images_dir,
            require_editorial_approval=require_editorial_approval,
            require_card_fingerprint=require_editorial_approval,
        )
        errors.extend(item_errors)
        warnings.extend(item_warnings)
        if isinstance(item, dict) and isinstance(item.get("day"), int):
            day = item["day"]
            days.append(day)
            if require_editorial_approval:
                hook = item.get("hook_ko")
                if isinstance(hook, str) and hook.strip() and hook.strip() not in GENERIC_HOOKS:
                    hooks[hook.strip()].append(day)
            phrase = item.get("phrase")
            if isinstance(phrase, str) and phrase.strip():
                phrases[normalized_phrase(phrase)].append(day)
            if get_quiz_spec(item)["mode"] == "choice":
                choice_answers.append(str(item.get("answer_choice")))
                choice_focuses.append(str(item.get("quiz_focus")))

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

    if require_editorial_approval:
        for hook, duplicate_days in hooks.items():
            if len(duplicate_days) > 1:
                errors.append(
                    f"중복 훅이 있습니다: Day {', '.join(map(str, duplicate_days))} ({hook})"
                )

    if choice_answers:
        answer_gap = abs(choice_answers.count("A") - choice_answers.count("B"))
        if answer_gap > 2:
            errors.append(
                "A/B 정답 위치가 편향되어 있습니다 "
                f"(A {choice_answers.count('A')}개, B {choice_answers.count('B')}개)."
            )
        grammar_ratio = choice_focuses.count("grammar") / len(choice_focuses)
        if len(choice_focuses) >= 10 and grammar_ratio > 0.2:
            errors.append(
                f"단순 문법형 A/B 문제가 {grammar_ratio:.0%}로 20%를 초과합니다."
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
