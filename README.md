# Threads Daily English (미드 실전 영어 1일 1카드 자동 발행 봇)

> **현재 게시 중지:** 기존 176일 큐는 폐기 예정이며 실제 영미권 일상 회화 중심으로 전면 재구축 중입니다. 예약·수동 게시 경로는 모두 잠겨 있습니다.

검증 완료 후 Threads(@fluent93)에 매일 오전 08:07 (KST) 답이 보이지 않는 실전 영어 퀴즈를 올리고, 오후 14:07 같은 타래에 추천 답안·뉘앙스·발음을 공개하는 것을 목표로 합니다.

---

## 🎨 주요 기능

1. **1080x1080 고해상도 카드뉴스 이미지 자동 생성**: Pillow 기반 다크 미니멀 카드 이미지 (총 176일치 사전 렌더링)
2. **시간차 타래(Thread) 자동 게시**:
   - **[오전 08:07]**: 답이 보이지 않는 A/B 또는 자유 영작 상황 퀴즈 카드
   - **[오후 14:07]**: 원글 답글로 상황별 추천 + 핵심 표현 + 뉘앙스 + 실전 예문
   - **[정답 상세 답글]**: 발음 포인트 + 10초 복습 영작
3. **안전한 자동화 (GitHub Actions & Cron)**:
   - 콘텐츠 검증 완료 전에는 예약·수동 게시 모두 차단
   - 게시 전 500자·중복·오타·이미지 검증
   - 176개 전 항목의 최종 편집 승인과 고유 상황형 훅 검증
   - PNG 콘텐츠 지문으로 문안과 카드 이미지 불일치 차단
   - Meta 미디어 처리 상태 확인 및 일시 오류 재시도
   - 부분 실패 시 마지막 완료 단계부터 이어서 게시
   - 구형 큐도 영작 질문을 추출해 정답 비노출 형식으로 강제 전환
   - 토큰 권한과 만료일 사전 점검
   - 발행 이력 자동 관리 (`data/threads_post_state.json`)

### A/B 문항 품질 원칙

- 두 선택지 모두 실제로 성립하는 자연스러운 영어를 사용합니다.
- A/B는 정답·오답이 아니라 주어진 상황에 더 잘 맞는 표현을 고르는 방식입니다.
- 철자·관사·전치사 하나를 틀리게 만든 오답보다 상황·뉘앙스·말투 차이를 묻습니다.
- 해설은 A와 B가 각각 언제 맞는지 비교합니다.
- 정답 위치는 A/B 한쪽으로 편향되지 않게 검증합니다.
- 단순 문법형 문항은 전체 A/B 문항의 20%를 넘으면 검증에 실패합니다.
- 억지 오답을 만들기 어려운 표현은 A/B 대신 자유 영작으로 발행합니다.
- 모든 문항은 표현별 상황형 훅과 오후 지연 정답을 가져야 배포됩니다.

---

## 🚀 빠른 시작

### 1. 환경 변수 설정
`.env` 파일에 발급받은 Threads 토큰을 입력합니다.
```env
THREADS_ACCESS_TOKEN=your_token_here
```

### 2. 명령어

```bash
# 발행 현황 확인
python3 scripts/publish_daily_expression.py --status

# 전체 콘텐츠 및 카드 품질 검증
python3 scripts/validate_content.py

# 176일 라이브러리의 객관 지표 확인
python3 scripts/report_content_quality.py

# Threads 계정, 권한, 토큰 만료 점검
python3 scripts/check_threads_access.py

# 단위 테스트
python3 -m unittest discover -s tests -v

# 오늘 발행될 카드뉴스 및 타래 미리보기 (Dry-run)
python3 scripts/publish_daily_expression.py --dry-run

# 즉시 1개 카드뉴스 발행
python3 scripts/publish_daily_expression.py --publish

# 공개 시각이 지난 정답을 원래 문제 타래에 게시
python3 scripts/publish_delayed_answer.py
```
