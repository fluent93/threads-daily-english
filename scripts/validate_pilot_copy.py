#!/usr/bin/env python3
"""Cross-check pilot card copy against the approved expression selection."""

from __future__ import annotations

import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SELECTION_FILE = BASE_DIR / "data" / "pilot_expression_selection.json"
COPY_FILE = BASE_DIR / "data" / "pilot_card_copy.json"
REQUIRED_FIELDS = {
    "hook_ko",
    "quiz_ko",
    "answer_example_en",
    "alternative_en",
    "alternative_note_ko",
    "nuance_ko",
    "example_en",
    "example_ko",
    "pronunciation_ko",
}
STOPWORDS = {"i", "it", "a", "an", "the", "am", "is", "are", "to", "for"}


def tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z]+", value.casefold().replace("’", "'"))
        if token not in STOPWORDS and len(token) > 1
    }


def validate_copy(selection: object, copy_items: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(selection, list) or not isinstance(copy_items, list):
        return ["선정표와 문안은 모두 배열이어야 합니다."]
    if len(selection) != len(copy_items):
        errors.append(f"선정 {len(selection)}개와 문안 {len(copy_items)}개의 수가 다릅니다.")

    copy_by_day = {
        item.get("day"): item for item in copy_items if isinstance(item, dict)
    }
    for selected in selection:
        day = selected.get("day")
        label = f"Day {day}"
        item = copy_by_day.get(day)
        if not item:
            errors.append(f"{label}: 카드 문안이 없습니다.")
            continue
        missing = REQUIRED_FIELDS - set(item)
        if missing:
            errors.append(f"{label}: 문안 필드가 부족합니다: {', '.join(sorted(missing))}")
            continue
        for field in REQUIRED_FIELDS:
            if not isinstance(item[field], str) or not item[field].strip():
                errors.append(f"{label}: {field}가 비어 있습니다.")
        target_tokens = tokens(str(selected.get("phrase", "")))
        answer_tokens = tokens(item["answer_example_en"])
        if not target_tokens.issubset(answer_tokens):
            errors.append(f"{label}: 추천 답안에 선정 표현이 온전히 반영되지 않았습니다.")
        if tokens(item["answer_example_en"]) == tokens(item["alternative_en"]):
            errors.append(f"{label}: 추천 답안과 대체 답안이 사실상 같습니다.")
        if len(item["quiz_ko"]) > 100:
            errors.append(f"{label}: 질문이 100자를 초과합니다.")
        if "정답" in item["alternative_note_ko"]:
            errors.append(f"{label}: 가능한 대안을 정답·오답으로 표현하면 안 됩니다.")
    return errors


def main() -> int:
    selection = json.loads(SELECTION_FILE.read_text(encoding="utf-8"))
    copy_items = json.loads(COPY_FILE.read_text(encoding="utf-8"))
    errors = validate_copy(selection, copy_items)
    for error in errors:
        print(f"ERROR: {error}")
    print(f"파일럿 문안 검증: {len(copy_items)}개, 오류 {len(errors)}건")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
