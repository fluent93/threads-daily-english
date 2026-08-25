#!/usr/bin/env python3
"""
Threads Client with Image Post Support (Meta Graph API)
"""

import os
import sys
import json
import time
import random
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error

def load_env(env_path: Path):
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and val and key not in os.environ:
                os.environ[key] = val

BASE_DIR = Path(__file__).resolve().parent.parent
load_env(BASE_DIR / ".env")

THREADS_API_BASE = "https://graph.threads.net/v1.0"
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}
READY_STATUSES = {"FINISHED"}
FAILED_STATUSES = {"ERROR", "EXPIRED"}


class ThreadsClient:
    def __init__(
        self,
        access_token: str = None,
        *,
        opener=None,
        sleep=None,
        clock=None,
        max_retries: int = 3,
    ):
        self.access_token = access_token or os.environ.get("THREADS_ACCESS_TOKEN", "").strip()
        if not self.access_token:
            raise ValueError(
                "THREADS_ACCESS_TOKEN이 설정되지 않았습니다. .env 파일에 토큰을 설정하거나 환경변수를 지정해주세요."
            )
        self._opener = opener or urllib.request.urlopen
        self._sleep = sleep or time.sleep
        self._clock = clock or time.monotonic
        self.max_retries = max_retries

    def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None) -> dict:
        url = f"{THREADS_API_BASE}/{endpoint.lstrip('/')}"
        
        query_params = params.copy() if params else {}
        if query_params:
            url = f"{url}?{urllib.parse.urlencode(query_params)}"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "ThreadsDailyEnglish/2.0",
        }
        body = None

        if data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        for attempt in range(self.max_retries + 1):
            try:
                with self._opener(req, timeout=30) as resp:
                    resp_text = resp.read().decode("utf-8")
                    return json.loads(resp_text)
            except urllib.error.HTTPError as exc:
                err_body = exc.read().decode("utf-8")
                try:
                    err_json = json.loads(err_body)
                    err_msg = err_json.get("error", {}).get("message", err_body)
                except Exception:
                    err_msg = err_body

                if exc.code in RETRYABLE_HTTP_CODES and attempt < self.max_retries:
                    retry_after = exc.headers.get("Retry-After") if exc.headers else None
                    try:
                        delay = float(retry_after) if retry_after else 2**attempt
                    except ValueError:
                        delay = 2**attempt
                    self._sleep(delay + random.uniform(0, 0.25))
                    continue
                raise RuntimeError(f"Threads API Error ({exc.code}): {err_msg}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt < self.max_retries:
                    self._sleep((2**attempt) + random.uniform(0, 0.25))
                    continue
                raise RuntimeError(f"Request failed after retries: {exc}") from exc
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise RuntimeError(f"Threads API returned an invalid response: {exc}") from exc

        raise RuntimeError("Threads API request exhausted retries")

    def get_me(self) -> dict:
        return self._request("GET", "/me", params={"fields": "id,username,name,threads_profile_picture_url"})

    def get_thread(self, thread_id: str) -> dict:
        """Return a published Threads post owned by, or visible to, this token."""
        return self._request(
            "GET",
            f"/{thread_id}",
            params={"fields": "id,permalink,timestamp"},
        )

    def debug_access_token(self) -> dict:
        result = self._request(
            "GET",
            "/debug_token",
            params={"input_token": self.access_token},
        )
        return result.get("data", result)

    def create_container(
        self,
        text: str,
        image_url: str = None,
        reply_to_id: str = None,
        alt_text: str = None,
        topic_tag: str = None,
    ) -> str:
        """텍스트 또는 이미지 컨테이너 생성"""
        payload = {}
        if image_url:
            payload["media_type"] = "IMAGE"
            payload["image_url"] = image_url
            if text:
                payload["text"] = text
            if alt_text:
                payload["alt_text"] = alt_text
        else:
            payload["media_type"] = "TEXT"
            payload["text"] = text

        if reply_to_id:
            payload["reply_to_id"] = reply_to_id
        if topic_tag:
            payload["topic_tag"] = topic_tag

        res = self._request("POST", "/me/threads", data=payload)
        container_id = res.get("id")
        if not container_id:
            raise RuntimeError("Threads API did not return a container id")
        return container_id

    def get_container_status(self, container_id: str) -> dict:
        return self._request(
            "GET",
            f"/{container_id}",
            params={"fields": "id,status,error_message"},
        )

    def wait_until_ready(
        self,
        container_id: str,
        *,
        timeout_seconds: float = 90,
        poll_interval: float = 1,
    ) -> None:
        """Poll a media container until Meta reports it is publishable."""
        deadline = self._clock() + timeout_seconds
        interval = poll_interval

        while self._clock() < deadline:
            result = self.get_container_status(container_id)
            status = str(result.get("status") or result.get("status_code") or "").upper()
            if status in READY_STATUSES:
                return
            if status in FAILED_STATUSES:
                error_message = result.get("error_message") or "원인을 제공하지 않았습니다."
                raise RuntimeError(f"Container {container_id} is {status}: {error_message}")
            self._sleep(interval)
            interval = min(interval * 1.5, 5)

        raise TimeoutError(
            f"Container {container_id} was not ready within {timeout_seconds} seconds"
        )

    def publish_container(self, container_id: str) -> str:
        """생성된 컨테이너 게시"""
        payload = {"creation_id": container_id}
        res = self._request("POST", "/me/threads_publish", data=payload)
        thread_id = res.get("id")
        if not thread_id:
            raise RuntimeError("Threads API did not return a published thread id")
        return thread_id

    def post(
        self,
        text: str,
        image_url: str = None,
        reply_to_id: str = None,
        alt_text: str = None,
        topic_tag: str = None,
    ) -> str:
        """컨테이너 생성 후 게시까지 원스톱 실행"""
        container_id = self.create_container(
            text,
            image_url=image_url,
            reply_to_id=reply_to_id,
            alt_text=alt_text,
            topic_tag=topic_tag,
        )
        self.wait_until_ready(container_id)
        thread_id = self.publish_container(container_id)
        return thread_id
