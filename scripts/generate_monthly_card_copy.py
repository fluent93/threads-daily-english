#!/usr/bin/env python3
"""Generate consistent monthly card copy from an approved expression selection."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


ALTERNATIVES = {
    "It's freezing out.": "It's bitterly cold outside.",
    "The temperature dropped overnight.": "It got much colder overnight.",
    "I can barely feel my fingers.": "My fingers are almost numb.",
    "Let's warm up inside.": "Let's go inside and get warm.",
    "The heater is acting up.": "The heater isn't working properly.",
    "I'm swamped right now.": "I'm really busy at the moment.",
    "I have a lot on my plate.": "I'm juggling a lot right now.",
    "Can we move this up?": "Could we bring this forward?",
    "Let's get the ball rolling.": "Let's get started.",
    "I'll take care of it.": "I'll handle it.",
    "We're running behind.": "We're a little late.",
    "We're falling behind schedule.": "We're getting off schedule.",
    "Let's stick to the plan.": "Let's follow the original plan.",
    "We may need a backup plan.": "We might need another option.",
    "Let's figure out the details.": "Let's work out the specifics.",
    "I'm just browsing.": "I'm just looking around.",
    "I'm looking for something practical.": "I'd like something useful.",
    "This is out of my budget.": "This costs more than I can spend.",
    "Do you have this in a different size?": "Does this come in another size?",
    "I'll think about it.": "Let me give it some thought.",
    "It comes with a warranty.": "A warranty is included.",
    "Can I get a gift receipt?": "Could I have a receipt for the gift?",
    "It's the thought that counts.": "What matters is the thought behind it.",
    "You shouldn't have!": "That was so thoughtful of you!",
    "I hope you like it.": "I hope it's your style.",
    "Make yourself at home.": "Please make yourself comfortable.",
    "Can I get you anything?": "Would you like something to drink?",
    "Help yourself.": "Please take whatever you'd like.",
    "There's plenty to go around.": "There's enough for everyone.",
    "I'm glad you could make it.": "It's great to have you here.",
    "I need a few days to recharge.": "I need a short break to reset.",
    "I'm taking some time off.": "I'm going to take a few days off.",
    "Let's keep things low-key.": "Let's keep it simple and relaxed.",
    "I really needed that.": "That was exactly what I needed.",
    "The year flew by.": "This year went by so fast.",
    "It's been quite a year.": "What a year it's been.",
    "I'm ready for a fresh start.": "I'm ready to begin again.",
    "I want to get back on track.": "I want to return to my routine.",
    "I'm setting realistic goals.": "I'm choosing goals I can actually reach.",
    "I'm starting small.": "I'm taking one small step at a time.",
    "I want to build a better routine.": "I want to create healthier daily habits.",
    "I'm trying to be more consistent.": "I'm working on sticking with it.",
    "I fell out of the habit.": "I stopped doing it regularly.",
    "I need to get back into the habit.": "I need to make it part of my routine again.",
    "I'm making steady progress.": "I'm moving forward little by little.",
    "I'm not there yet.": "I still have a way to go.",
    "I hit a roadblock.": "I ran into a problem.",
    "Let's try a different approach.": "Let's look at this another way.",
    "I need to rethink this.": "I need to reconsider my plan.",
    "I'm open to suggestions.": "I'd be happy to hear your ideas.",
    "Could you give me some feedback?": "I'd appreciate your thoughts on this.",
    "That's good to know.": "That's useful information.",
    "I'll take that into account.": "I'll keep that in mind.",
    "That makes sense.": "I can see why you think that.",
    "I hadn't thought of it that way.": "That's a perspective I hadn't considered.",
    "Let's see how it goes.": "Let's try it and see what happens.",
    "So far, so good.": "Everything is going well up to now.",
    "I'm looking forward to it.": "I can't wait for it.",
    "It gives me something to look forward to.": "It gives me something positive to anticipate.",
    "Let's start off on the right foot.": "Let's make a good start.",
}


def clean_phrase(phrase: str) -> str:
    return phrase.rstrip(".!?")


def clean_meaning(meaning: str) -> str:
    return meaning.rstrip(".!?。！？")


def stress_word(phrase: str) -> str:
    words = re.findall(r"[A-Za-z]+", phrase)
    stop = {"a", "an", "the", "to", "of", "it", "i", "we", "you", "this", "that"}
    return next((word for word in reversed(words) if word.casefold() not in stop), words[-1])


def build(selection: list[dict]) -> list[dict]:
    copy: list[dict] = []
    for item in selection:
        phrase = item["phrase"]
        meaning = item["meaning_ko"]
        display_meaning = clean_meaning(meaning)
        category = item["category"]
        alternative = ALTERNATIVES[phrase]
        core = clean_phrase(phrase)
        copy.append({
            "day": item["day"],
            "hook_ko": f"{category} 상황에서 '{display_meaning}'라고 말하고 싶을 때",
            "quiz_ko": f"'{display_meaning}'를 자연스러운 영어 한마디로 말해 보세요.",
            "answer_example_en": phrase,
            "alternative_en": alternative,
            "alternative_note_ko": f"둘 다 '{display_meaning}'라는 뜻이다. 첫 표현은 일상 대화에서 짧고 자연스럽고, 대안은 뜻을 조금 더 직접 풀어 말한다.",
            "nuance_ko": f"'{core}'는 '{display_meaning}'라는 뜻으로, {category} 상황에서 바로 꺼내 쓰기 좋은 자연스러운 회화 표현이다.",
            "example_en": phrase,
            "example_ko": display_meaning + ".",
            "pronunciation_ko": f"문장을 한 덩어리로 자연스럽게 잇고, 핵심어 {stress_word(phrase)}에 힘을 준다.",
        })
    return copy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    missing = [item["phrase"] for item in selection if item["phrase"] not in ALTERNATIVES]
    if missing:
        raise SystemExit(f"대체 표현이 없습니다: {missing}")
    value = build(selection)
    temporary = args.output.with_suffix(".json.tmp")
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, args.output)
    print(f"카드 문안 생성: {len(value)}개 → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
