#!/usr/bin/env python3
"""Validate expression selection before any card copy is written."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SCORE_FIELDS = {"frequency", "transfer", "learning_value", "memorability"}


def normalize(value: str) -> str:
    return re.sub(r"\W+", " ", value.casefold()).strip()


def validate_selection(items: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(items, list) or not items:
        return ["선정 목록은 비어 있지 않은 배열이어야 합니다."]

    seen: dict[str, int] = {}
    for index, item in enumerate(items, start=1):
        label = f"항목 {index}"
        if not isinstance(item, dict):
            errors.append(f"{label}: 객체가 아닙니다.")
            continue
        day = item.get("day")
        label = f"Day {day}" if isinstance(day, int) else label
        if day != index:
            errors.append(f"{label}: day는 파일 순서대로 1부터 연속이어야 합니다.")
        for field in ("phrase", "meaning_ko", "category", "selection_reason", "register_note"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{label}: {field}가 비어 있습니다.")

        phrase = item.get("phrase")
        if isinstance(phrase, str) and phrase.strip():
            key = normalize(phrase)
            if key in seen:
                errors.append(f"{label}: Day {seen[key]}와 표현이 중복됩니다: {phrase}")
            seen[key] = day

        scores = item.get("scores")
        if not isinstance(scores, dict) or set(scores) != SCORE_FIELDS:
            errors.append(f"{label}: 네 가지 선정 점수가 정확히 필요합니다.")
            continue
        if any(not isinstance(value, int) or not 1 <= value <= 5 for value in scores.values()):
            errors.append(f"{label}: 선정 점수는 1~5의 정수여야 합니다.")
            continue
        if scores["frequency"] < 4 or scores["transfer"] < 4:
            errors.append(f"{label}: 빈도와 전이성은 각각 4점 이상이어야 합니다.")
        if sum(scores.values()) < 16:
            errors.append(f"{label}: 선정 총점이 16/20 미만입니다.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "pilot_expression_selection.json",
    )
    args = parser.parse_args()
    items = json.loads(args.path.read_text(encoding="utf-8"))
    errors = validate_selection(items)
    for error in errors:
        print(f"ERROR: {error}")
    print(f"표현 선정 검증: {len(items)}개, 오류 {len(errors)}건")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
