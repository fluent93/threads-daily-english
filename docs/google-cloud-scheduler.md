# Google Cloud Scheduler 운영

## 구성

Google Cloud Scheduler가 GitHub의 `workflow_dispatch` API를 호출하고, 기존
GitHub Actions가 검증·Threads 게시·상태 저장을 담당한다.

| 작업 | KST | GitHub 입력 |
| --- | --- | --- |
| `threads-daily-question` | 매일 08:07 | `mode=publish` |
| `threads-daily-answer` | 매일 14:07 | `mode=answer` |

Scheduler는 GitHub API 호출이 실패하면 15분 동안 최대 세 번 재시도한다.
Threads API의 일시 오류는 기존 Python 클라이언트가 별도로 재시도하며,
`data/threads_post_state.json`이 부분 실패 복구와 중복 방지를 담당한다.

## 준비

1. 기존 성경 알림과 같은 Google 결제 계정의 프로젝트를 사용한다.
2. Google Cloud CLI를 설치하고 로그인한다.

   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. GitHub fine-grained personal access token을 만든다.

   - Repository access: `fluent93/threads-daily-english`만 선택
   - Repository permissions: `Actions: Read and write`
   - 만료일을 지정하고 갱신 알림을 설정

## 생성

토큰을 파일에 저장하지 않고 현재 셸 환경에만 넣는다.

```bash
export GCP_PROJECT_ID=YOUR_PROJECT_ID
export GITHUB_DISPATCH_TOKEN=YOUR_FINE_GRAINED_TOKEN
bash scripts/manage_gcp_scheduler.sh apply
unset GITHUB_DISPATCH_TOKEN
```

기본 리전은 서울 `asia-northeast3`이다. 기존 Scheduler 리전이 다르면
`GCP_SCHEDULER_LOCATION`으로 지정한다.

```bash
export GCP_SCHEDULER_LOCATION=YOUR_EXISTING_LOCATION
```

## 확인과 전환

```bash
bash scripts/manage_gcp_scheduler.sh verify
```

두 작업을 만든 직후에는 GitHub cron을 안전망으로 유지한다. 다음 날
오전 문제와 오후 답안이 Google Scheduler가 만든 `workflow_dispatch` 실행으로
정상 게시되는 것을 확인한 후 GitHub workflow의 `schedule` 항목만 제거한다.
`workflow_dispatch`는 계속 유지해야 한다.

Google Scheduler가 호출한 실행은 GitHub Actions 화면에서 이벤트가
`workflow_dispatch`로 표시된다.

## 중지·재개

```bash
bash scripts/manage_gcp_scheduler.sh pause
bash scripts/manage_gcp_scheduler.sh resume
```

일시중지된 작업도 Google Scheduler 작업 수에는 포함된다. 더 이상 쓰지 않는
작업은 Google Cloud Console에서 삭제한다.

## 비용

Google 결제 계정당 Scheduler 작업 세 개가 무료다. 기존 성경 알림 한 개와
이 프로젝트 두 개만 있다면 무료 범위다. 무료 작업 수는 프로젝트가 아니라
결제 계정 전체를 합산한다.

## 보안

- Scheduler 작업의 HTTP 헤더에는 GitHub 토큰이 저장된다. 해당 Google
  프로젝트에서 Scheduler 작업을 조회할 수 있는 IAM 권한을 최소화한다.
- 전체 계정용 classic token 대신 이 저장소만 허용한 fine-grained token을 쓴다.
- 토큰을 터미널 기록이나 저장소에 입력하지 않는다.
- 토큰 폐기 시 새 토큰으로 `apply`를 다시 실행하면 두 작업의 헤더가 갱신된다.
