#!/usr/bin/env python3
"""
Generate 1080x1080 Card News Images for Threads Daily Posts
- NotoSansCJK-Bold 폰트를 사용하여 모던 다크 미니멀 스타일의 카드뉴스 이미지 생성
- 176개 전체 일괄 생성 및 개별 생성 지원
"""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
from content_validation import card_fingerprint, get_quiz_spec, uses_delayed_answer

BASE_DIR = Path(__file__).resolve().parent.parent
QUEUE_FILE = BASE_DIR / "data" / "threads_daily_queue.json"
IMAGES_DIR = BASE_DIR / "images"

# 폰트 경로 (시스템 폰트)
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
if not Path(FONT_PATH).exists():
    FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """긴 텍스트를 이미지 너비에 맞춰 자동 줄바꿈합니다."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        test_line = " ".join(current_line)
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w > max_width:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(test_line)
                current_line = []

    if current_line:
        lines.append(" ".join(current_line))
    return lines if lines else [text]


def create_card_image(
    day_num: int,
    phrase: str,
    meaning_ko: str,
    output_path: Path,
    *,
    hook_ko: str = "",
    context_ko: str = "",
    source_label: str = "",
    delayed_answer: bool = False,
    quiz_ko: str = "",
    choice_a: str = "",
    choice_b: str = "",
    quiz_mode: str = "choice",
    content_fingerprint: str = "",
):
    width, height = 1080, 1080
    img = Image.new("RGB", (width, height), color="#0F172A") # 딥 다크 네이비/차콜
    draw = ImageDraw.Draw(img)

    # 폰트 로드
    font_badge = ImageFont.truetype(FONT_PATH, 28)
    font_quote = ImageFont.truetype(FONT_PATH, 72)
    font_main = ImageFont.truetype(FONT_PATH, 54)
    font_meaning = ImageFont.truetype(FONT_PATH, 38)
    font_hook = ImageFont.truetype(FONT_PATH, 42)
    font_context = ImageFont.truetype(FONT_PATH, 28)
    font_source = ImageFont.truetype(FONT_PATH, 22)
    font_footer = ImageFont.truetype(FONT_PATH, 24)
    font_quiz = ImageFont.truetype(FONT_PATH, 38)
    font_choice = ImageFont.truetype(FONT_PATH, 27)
    font_reveal = ImageFont.truetype(FONT_PATH, 27)

    # 1. 내부 카드 프레임 (모던 글래스모피즘 느낌의 라운드 사각형)
    card_margin = 60
    card_rect = [card_margin, card_margin, width - card_margin, height - card_margin]
    draw.rounded_rectangle(card_rect, radius=32, fill="#1E293B", outline="#334155", width=2)

    # 2. 상단 뱃지 (#Day001 • 미드 실전 영어)
    badge_text = f"미드 실전 영어  •  #DAY {day_num:03d}"
    badge_bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    bw = badge_bbox[2] - badge_bbox[0]
    bh = badge_bbox[3] - badge_bbox[1]
    bx = (width - bw) // 2
    by = card_margin + 60

    # 뱃지 배경 캡슐
    pad_x, pad_y = 24, 12
    draw.rounded_rectangle(
        [bx - pad_x, by - pad_y, bx + bw + pad_x, by + bh + pad_y],
        radius=20,
        fill="#0284C7" # 스카이블루 포인트
    )
    draw.text((bx, by - 2), badge_text, font=font_badge, fill="#FFFFFF")

    if source_label:
        source_bbox = draw.textbbox((0, 0), source_label, font=font_source)
        source_width = source_bbox[2] - source_bbox[0]
        draw.text(
            ((width - source_width) // 2, by + bh + 34),
            source_label,
            font=font_source,
            fill="#64748B",
        )

    # 오전 퀴즈 카드는 영어 정답과 한국어 뜻을 모두 숨깁니다.
    if delayed_answer:
        hook_lines = wrap_text(hook_ko, font=font_hook, max_width=780, draw=draw)
        hook_start_y = 245
        for i, line in enumerate(hook_lines):
            bbox = draw.textbbox((0, 0), line, font=font_hook)
            draw.text(
                ((width - (bbox[2] - bbox[0])) // 2, hook_start_y + (i * 58)),
                line,
                font=font_hook,
                fill="#FBBF24",
            )

        quiz_lines = wrap_text(f"Q. {quiz_ko}", font=font_quiz, max_width=790, draw=draw)
        quiz_start_y = hook_start_y + (len(hook_lines) * 58) + 50
        for i, line in enumerate(quiz_lines):
            bbox = draw.textbbox((0, 0), line, font=font_quiz)
            draw.text(
                ((width - (bbox[2] - bbox[0])) // 2, quiz_start_y + (i * 52)),
                line,
                font=font_quiz,
                fill="#F8FAFC",
            )

        option_y = quiz_start_y + (len(quiz_lines) * 52) + 38
        options = (("A", choice_a), ("B", choice_b)) if quiz_mode == "choice" else ()
        for label, option in options:
            option_lines = wrap_text(option, font=font_choice, max_width=720, draw=draw)
            box_height = max(94, 42 + (len(option_lines) * 39))
            draw.rounded_rectangle(
                [135, option_y, width - 135, option_y + box_height],
                radius=22,
                fill="#27364A",
                outline="#475569",
                width=2,
            )
            draw.rounded_rectangle(
                [165, option_y + 24, 213, option_y + 72],
                radius=14,
                fill="#0284C7",
            )
            label_bbox = draw.textbbox((0, 0), label, font=font_choice)
            draw.text(
                (
                    189 - ((label_bbox[2] - label_bbox[0]) // 2),
                    option_y + 25,
                ),
                label,
                font=font_choice,
                fill="#FFFFFF",
            )
            for i, line in enumerate(option_lines):
                draw.text(
                    (240, option_y + 24 + (i * 39)),
                    line,
                    font=font_choice,
                    fill="#E2E8F0",
                )
            option_y += box_height + 22

        if quiz_mode == "free":
            draw.rounded_rectangle(
                [175, option_y + 10, width - 175, option_y + 135],
                radius=24,
                fill="#27364A",
                outline="#475569",
                width=2,
            )
            response_text = "영어 한 문장으로 댓글 도전"
            response_bbox = draw.textbbox((0, 0), response_text, font=font_quiz)
            draw.text(
                ((width - (response_bbox[2] - response_bbox[0])) // 2, option_y + 48),
                response_text,
                font=font_quiz,
                fill="#E2E8F0",
            )
            option_y += 155

        reveal_text = (
            "A/B 댓글로  ·  정답은 오후 2:07"
            if quiz_mode == "choice"
            else "정답 예시는 오후 2:07"
        )
        reveal_bbox = draw.textbbox((0, 0), reveal_text, font=font_reveal)
        reveal_width = reveal_bbox[2] - reveal_bbox[0]
        reveal_y = min(max(option_y + 18, 860), 915)
        draw.text(
            ((width - reveal_width) // 2, reveal_y),
            reveal_text,
            font=font_reveal,
            fill="#38BDF8",
        )

        footer_text = "@fluent93  |  Daily English"
        footer_bbox = draw.textbbox((0, 0), footer_text, font=font_footer)
        footer_width = footer_bbox[2] - footer_bbox[0]
        draw.text(
            ((width - footer_width) // 2, height - card_margin - 60),
            footer_text,
            font=font_footer,
            fill="#64748B",
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        png_info = PngImagePlugin.PngInfo()
        png_info.add_text("content_fingerprint", content_fingerprint)
        img.save(output_path, "PNG", quality=95, pnginfo=png_info)
        return

    # 획득형 카드는 먼저 사용 상황을 보여주고 표현을 보상으로 제시합니다.
    if hook_ko:
        hook_lines = wrap_text(hook_ko, font=font_hook, max_width=760, draw=draw)
        hook_start_y = 245
        for i, hook_line in enumerate(hook_lines):
            hook_bbox = draw.textbbox((0, 0), hook_line, font=font_hook)
            hook_width = hook_bbox[2] - hook_bbox[0]
            draw.text(
                ((width - hook_width) // 2, hook_start_y + (i * 58)),
                hook_line,
                font=font_hook,
                fill="#FBBF24",
            )

    # 3. 중앙 영어 메인 표현 (큰 따옴표 + 자동 줄바꿈)
    max_text_width = width - (card_margin * 2) - 120
    lines = wrap_text(f'"{phrase}"', font=font_main, max_width=max_text_width, draw=draw)

    # 줄 간격 계산 및 중앙 정렬
    line_height = 76
    total_main_height = len(lines) * line_height
    main_center_y = 500 if hook_ko else 380
    start_y = main_center_y - (total_main_height // 2)

    for i, line in enumerate(lines):
        l_bbox = draw.textbbox((0, 0), line, font=font_main)
        lw = l_bbox[2] - l_bbox[0]
        lx = (width - lw) // 2
        ly = start_y + (i * line_height)
        draw.text((lx, ly), line, font=font_main, fill="#F8FAFC")

    # 구분선
    div_y = start_y + total_main_height + 40
    draw.line([(width // 2) - 80, div_y, (width // 2) + 80, div_y], fill="#38BDF8", width=4)

    # 4. 한국어 뜻 박스
    meaning_lines = wrap_text(meaning_ko, font=font_meaning, max_width=max_text_width, draw=draw)
    m_start_y = div_y + 50
    m_line_height = 54

    for i, m_line in enumerate(meaning_lines):
        m_bbox = draw.textbbox((0, 0), m_line, font=font_meaning)
        mw = m_bbox[2] - m_bbox[0]
        mx = (width - mw) // 2
        my = m_start_y + (i * m_line_height)
        draw.text((mx, my), m_line, font=font_meaning, fill="#94A3B8")

    if context_ko:
        context_bbox = draw.textbbox((0, 0), context_ko, font=font_context)
        context_width = context_bbox[2] - context_bbox[0]
        context_x = (width - context_width) // 2
        context_y = m_start_y + (len(meaning_lines) * m_line_height) + 45
        draw.rounded_rectangle(
            [context_x - 22, context_y - 10, context_x + context_width + 22, context_y + 40],
            radius=18,
            fill="#334155",
        )
        draw.text((context_x, context_y - 3), context_ko, font=font_context, fill="#CBD5E1")

    # 5. 하단 푸터 (@fluent93 • Seinfeld English)
    footer_text = "@fluent93  |  Daily English"
    f_bbox = draw.textbbox((0, 0), footer_text, font=font_footer)
    fw = f_bbox[2] - f_bbox[0]
    fx = (width - fw) // 2
    fy = height - card_margin - 60
    draw.text((fx, fy), footer_text, font=font_footer, fill="#64748B")

    # 이미지 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    png_info = PngImagePlugin.PngInfo()
    png_info.add_text("content_fingerprint", content_fingerprint)
    img.save(output_path, "PNG", quality=95, pnginfo=png_info)


def generate_all():
    if not QUEUE_FILE.exists():
        print(f"❌ 큐 파일을 찾을 수 없습니다: {QUEUE_FILE}")
        return

    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        queue = json.load(f)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"🎨 총 {len(queue)}개의 카드뉴스 이미지 생성을 시작합니다...")

    for item in queue:
        day = item.get("day")
        phrase = item.get("phrase", "")
        meaning = item.get("meaning_ko", "")
        hook = item.get("hook_ko", "")
        context = item.get("context_ko", "")
        source_label = item.get("source_label", "")
        quiz_spec = get_quiz_spec(item) if uses_delayed_answer(item) else {}
        img_path = IMAGES_DIR / f"day_{day:03d}.png"
        create_card_image(
            day,
            phrase,
            meaning,
            img_path,
            hook_ko=quiz_spec.get("hook_ko", hook),
            context_ko=context,
            source_label=source_label,
            delayed_answer=uses_delayed_answer(item),
            quiz_ko=quiz_spec.get("quiz_ko", ""),
            choice_a=quiz_spec.get("choice_a", ""),
            choice_b=quiz_spec.get("choice_b", ""),
            quiz_mode=quiz_spec.get("mode", "choice"),
            content_fingerprint=card_fingerprint(item),
        )

    print(f"✅ 176개 카드뉴스 이미지 생성 완료! 위치: {IMAGES_DIR}")


if __name__ == "__main__":
    generate_all()
