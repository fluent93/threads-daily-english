# Threads Daily English (미드 실전 영어 1일 1카드 자동 발행 봇)

Threads(@fluent93)에 매일 오전 08:07 (KST) 정답 없는 실전 영어 퀴즈를 올리고, 오후 14:07 같은 타래에 정답·뉘앙스·발음을 자동 공개합니다.

---

## 🎨 주요 기능

1. **1080x1080 고해상도 카드뉴스 이미지 자동 생성**: Pillow 기반 다크 미니멀 카드 이미지 (총 176일치 사전 렌더링)
2. **시간차 타래(Thread) 자동 게시**:
   - **[오전 08:07]**: 정답이 보이지 않는 A/B 또는 자유 영작 상황 퀴즈 카드
   - **[오후 14:07]**: 원글 답글로 정답 + 핵심 표현 + 뉘앙스 + 실전 예문
   - **[정답 상세 답글]**: 발음 포인트 + 10초 복습 영작
3. **안전한 자동화 (GitHub Actions & Cron)**:
   - 매일 오전 08:07 문제, 오후 14:07 정답 자동 실행
   - 게시 전 500자·중복·오타·이미지 검증
   - Meta 미디어 처리 상태 확인 및 일시 오류 재시도
   - 부분 실패 시 마지막 완료 단계부터 이어서 게시
   - 구형 큐도 영작 질문을 추출해 정답 비노출 형식으로 강제 전환
   - 토큰 권한과 만료일 사전 점검
   - 발행 이력 자동 관리 (`data/threads_post_state.json`)

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
