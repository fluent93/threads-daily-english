#!/usr/bin/env python3
"""
Generate 1080x1080 Card News Images for Threads Daily Posts
- NotoSansCJK-Bold 폰트를 사용하여 모던 다크 미니멀 스타일의 카드뉴스 이미지 생성
- 176개 전체 일괄 생성 및 개별 생성 지원
"""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

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
    img.save(output_path, "PNG", quality=95)


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
        img_path = IMAGES_DIR / f"day_{day:03d}.png"
        create_card_image(
            day,
            phrase,
            meaning,
            img_path,
            hook_ko=hook,
            context_ko=context,
            source_label=source_label,
        )

    print(f"✅ 176개 카드뉴스 이미지 생성 완료! 위치: {IMAGES_DIR}")


if __name__ == "__main__":
    generate_all()
