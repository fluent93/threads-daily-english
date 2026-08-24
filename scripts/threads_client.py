#!/usr/bin/env python3
"""
Threads Client with Image Post Support (Meta Graph API)
"""

import os
import sys
import json
import time
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


class ThreadsClient:
    def __init__(self, access_token: str = None):
        self.access_token = access_token or os.environ.get("THREADS_ACCESS_TOKEN", "").strip()
        if not self.access_token:
            raise ValueError(
                "THREADS_ACCESS_TOKEN이 설정되지 않았습니다. .env 파일에 토큰을 설정하거나 환경변수를 지정해주세요."
            )

    def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None) -> dict:
        url = f"{THREADS_API_BASE}/{endpoint.lstrip('/')}"
        
        query_params = params.copy() if params else {}
        query_params["access_token"] = self.access_token
        url = f"{url}?{urllib.parse.urlencode(query_params)}"

        headers = {"User-Agent": "ThreadsDailyEnglish/1.0"}
        body = None

        if data is not None:
            data_with_token = data.copy()
            data_with_token["access_token"] = self.access_token
            body = urllib.parse.urlencode(data_with_token).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_text = resp.read().decode("utf-8")
                return json.loads(resp_text)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_body)
                err_msg = err_json.get("error", {}).get("message", err_body)
            except Exception:
                err_msg = err_body
            raise RuntimeError(f"Threads API Error ({e.code}): {err_msg}") from e
        except Exception as e:
            raise RuntimeError(f"Request failed: {e}") from e

    def get_me(self) -> dict:
        return self._request("GET", "/me", params={"fields": "id,username,name,threads_profile_picture_url"})

    def create_container(self, text: str, image_url: str = None, reply_to_id: str = None) -> str:
        """텍스트 또는 이미지 컨테이너 생성"""
        payload = {}
        if image_url:
            payload["media_type"] = "IMAGE"
            payload["image_url"] = image_url
            if text:
                payload["text"] = text
        else:
            payload["media_type"] = "TEXT"
            payload["text"] = text

        if reply_to_id:
            payload["reply_to_id"] = reply_to_id

        res = self._request("POST", "/me/threads", data=payload)
        return res.get("id")

    def publish_container(self, container_id: str) -> str:
        """생성된 컨테이너 게시"""
        payload = {"creation_id": container_id}
        res = self._request("POST", "/me/threads_publish", data=payload)
        return res.get("id")

    def post(self, text: str, image_url: str = None, reply_to_id: str = None) -> str:
        """컨테이너 생성 후 게시까지 원스톱 실행"""
        container_id = self.create_container(text, image_url=image_url, reply_to_id=reply_to_id)
        # 이미지 업로드/처리 대기 (이미지는 3초, 텍스트는 1.5초)
        time.sleep(3.0 if image_url else 1.5)
        thread_id = self.publish_container(container_id)
        return thread_id
