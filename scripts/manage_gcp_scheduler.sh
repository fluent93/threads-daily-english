#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-apply}"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-}"
GCP_SCHEDULER_LOCATION="${GCP_SCHEDULER_LOCATION:-asia-northeast3}"
GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-fluent93/threads-daily-english}"
GITHUB_BRANCH="${GITHUB_BRANCH:-master}"
GITHUB_WORKFLOW_FILE="${GITHUB_WORKFLOW_FILE:-threads-daily-publish.yml}"
QUESTION_JOB="${QUESTION_JOB:-threads-daily-question}"
ANSWER_JOB="${ANSWER_JOB:-threads-daily-answer}"

usage() {
  echo "Usage: GCP_PROJECT_ID=... GITHUB_DISPATCH_TOKEN=... $0 [apply|verify|pause|resume]"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: '$1' 명령을 찾을 수 없습니다."
    exit 1
  fi
}

require_project() {
  if [[ -z "$GCP_PROJECT_ID" ]]; then
    echo "ERROR: GCP_PROJECT_ID가 필요합니다."
    usage
    exit 1
  fi
}

dispatch_uri() {
  echo "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/workflows/${GITHUB_WORKFLOW_FILE}/dispatches"
}

upsert_job() {
  local job_name="$1"
  local schedule="$2"
  local workflow_mode="$3"
  local body
  local headers
  local operation

  body="{\"ref\":\"${GITHUB_BRANCH}\",\"inputs\":{\"mode\":\"${workflow_mode}\"}}"
  headers="Accept=application/vnd.github+json,Authorization=Bearer ${GITHUB_DISPATCH_TOKEN},X-GitHub-Api-Version=2026-03-10,Content-Type=application/json"

  if gcloud scheduler jobs describe "$job_name" \
    --project "$GCP_PROJECT_ID" \
    --location "$GCP_SCHEDULER_LOCATION" >/dev/null 2>&1; then
    operation="update"
  else
    operation="create"
  fi

  gcloud scheduler jobs "$operation" http "$job_name" \
    --project "$GCP_PROJECT_ID" \
    --location "$GCP_SCHEDULER_LOCATION" \
    --schedule "$schedule" \
    --time-zone "Asia/Seoul" \
    --uri "$(dispatch_uri)" \
    --http-method POST \
    --headers "$headers" \
    --message-body "$body" \
    --attempt-deadline "60s" \
    --max-retry-attempts 3 \
    --min-backoff "30s" \
    --max-backoff "300s" \
    --max-doublings 3 \
    --max-retry-duration "900s" \
    --description "Threads Daily English: ${workflow_mode} via GitHub workflow_dispatch"
}

show_job() {
  gcloud scheduler jobs describe "$1" \
    --project "$GCP_PROJECT_ID" \
    --location "$GCP_SCHEDULER_LOCATION" \
    --format="yaml(name,state,schedule,timeZone,httpTarget.uri,retryConfig)"
}

require_command gcloud
require_project

case "$MODE" in
  apply)
    if [[ -z "${GITHUB_DISPATCH_TOKEN:-}" ]]; then
      echo "ERROR: GITHUB_DISPATCH_TOKEN이 필요합니다."
      usage
      exit 1
    fi
    gcloud services enable cloudscheduler.googleapis.com --project "$GCP_PROJECT_ID"
    upsert_job "$QUESTION_JOB" "7 8 * * *" "publish"
    upsert_job "$ANSWER_JOB" "7 14 * * *" "answer"
    show_job "$QUESTION_JOB"
    show_job "$ANSWER_JOB"
    echo "Google Cloud Scheduler 작업 2개를 생성 또는 갱신했습니다."
    ;;
  verify)
    show_job "$QUESTION_JOB"
    show_job "$ANSWER_JOB"
    ;;
  pause|resume)
    gcloud scheduler jobs "$MODE" "$QUESTION_JOB" \
      --project "$GCP_PROJECT_ID" \
      --location "$GCP_SCHEDULER_LOCATION"
    gcloud scheduler jobs "$MODE" "$ANSWER_JOB" \
      --project "$GCP_PROJECT_ID" \
      --location "$GCP_SCHEDULER_LOCATION"
    ;;
  *)
    usage
    exit 1
    ;;
esac
