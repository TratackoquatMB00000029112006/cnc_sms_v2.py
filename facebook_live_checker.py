#!/usr/bin/env python3
"""
facebook_live_checker.py
=========================

Một công cụ dòng lệnh đơn giản để kiểm tra xem một Trang hoặc một video Facebook
hiện có đang livestream hay không bằng cách sử dụng Facebook Graph API.

Yêu cầu:
    - Python 3.8+
    - Một Facebook Graph API access token còn hiệu lực (app hoặc user token)

Ví dụ:
    python facebook_live_checker.py --page-id <PAGE_ID> --access-token <TOKEN>

Bạn cũng có thể đặt token trong biến môi trường FACEBOOK_ACCESS_TOKEN
và bỏ qua tham số --access-token.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional


DEFAULT_GRAPH_VERSION = "v19.0"


class GraphAPIError(RuntimeError):
    """Lỗi đại diện cho phản hồi lỗi từ Facebook Graph API."""

    def __init__(self, message: str, status_code: int | None = None, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}

    def pretty(self) -> str:
        error_payload = self.payload.get("error") if isinstance(self.payload, dict) else None
        details = []
        if isinstance(error_payload, dict):
            for key in ("type", "code", "error_subcode", "fbtrace_id"):
                if error_payload.get(key) is not None:
                    details.append(f"{key}={error_payload[key]}")
            if error_payload.get("message"):
                details.append(error_payload["message"])
        text = "; ".join(details) if details else str(self)
        if self.status_code is not None:
            return f"HTTP {self.status_code}: {text}"
        return text


def build_url(path: str, params: Dict[str, Any], version: str) -> str:
    query = urllib.parse.urlencode(params)
    return f"https://graph.facebook.com/{version}/{path}?{query}"


def call_graph(path: str, params: Dict[str, Any], version: str) -> Dict[str, Any]:
    url = build_url(path, params, version)
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = {"error": {"message": payload.decode("utf-8", errors="replace")}}
        raise GraphAPIError("Graph API request failed", status_code=exc.code, payload=parsed) from exc
    except urllib.error.URLError as exc:
        raise GraphAPIError(f"Không thể kết nối tới Graph API: {exc}") from exc

    try:
        return json.loads(data)
    except json.JSONDecodeError as exc:
        raise GraphAPIError("Không thể parse phản hồi JSON từ Graph API") from exc


@dataclass
class LiveVideo:
    id: str
    title: Optional[str]
    start_time: Optional[datetime]
    live_views: Optional[int]
    permalink_url: Optional[str]

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "LiveVideo":
        start_time_raw = payload.get("start_time")
        start_time = None
        if isinstance(start_time_raw, str):
            try:
                start_time = datetime.fromisoformat(start_time_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
            except ValueError:
                start_time = None

        live_views = payload.get("live_views")
        if isinstance(live_views, str) and live_views.isdigit():
            live_views = int(live_views)
        elif not isinstance(live_views, int):
            live_views = None

        return cls(
            id=str(payload.get("id")),
            title=payload.get("title"),
            start_time=start_time,
            live_views=live_views,
            permalink_url=payload.get("permalink_url"),
        )


def fetch_live_videos(page_id: str, access_token: str, version: str) -> Iterable[LiveVideo]:
    """
    Lấy danh sách livestream đang diễn ra trên một Trang Facebook.

    Trả về danh sách LiveVideo (có thể rỗng nếu không có livestream).
    """
    payload = call_graph(
        f"{page_id}/live_videos",
        params={
            "status": "LIVE_NOW",
            "fields": "id,title,start_time,live_views,permalink_url",
            "access_token": access_token,
        },
        version=version,
    )
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    return [LiveVideo.from_payload(item) for item in data]


def fetch_video_status(video_id: str, access_token: str, version: str) -> Dict[str, Any]:
    """
    Kiểm tra tình trạng của một video livestream cụ thể.

    Trả về dict chứa các thông tin trạng thái quan trọng.
    """
    payload = call_graph(
        video_id,
        params={
            "fields": "id,status,live_status,publishing_phase,title,start_time,permalink_url,live_views",
            "access_token": access_token,
        },
        version=version,
    )
    return payload


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kiểm tra livestream Facebook qua Graph API.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--page-id", help="ID hoặc tên Trang Facebook cần kiểm tra livestream.")
    group.add_argument("--video-id", help="ID video livestream cụ thể cần kiểm tra.")
    parser.add_argument(
        "--access-token",
        help="Facebook Graph API access token. Có thể đặt qua biến môi trường FACEBOOK_ACCESS_TOKEN.",
    )
    parser.add_argument(
        "--graph-version",
        default=DEFAULT_GRAPH_VERSION,
        help=f"Phiên bản Graph API (mặc định: {DEFAULT_GRAPH_VERSION}).",
    )
    return parser.parse_args(argv)


def resolve_access_token(cli_token: Optional[str]) -> str:
    token = cli_token or os.getenv("FACEBOOK_ACCESS_TOKEN")
    if not token:
        raise GraphAPIError(
            "Thiếu access token. Truyền qua --access-token hoặc đặt biến môi trường FACEBOOK_ACCESS_TOKEN."
        )
    return token


def print_live_videos(videos: Iterable[LiveVideo]) -> None:
    videos = list(videos)
    if not videos:
        print("Không có livestream nào đang diễn ra.")
        return

    print(f"Tìm thấy {len(videos)} livestream đang phát:")
    for idx, video in enumerate(videos, start=1):
        print("-" * 60)
        print(f"[{idx}] Video ID     : {video.id}")
        if video.title:
            print(f"    Tiêu đề       : {video.title}")
        if video.start_time:
            print(f"    Bắt đầu lúc   : {video.start_time.isoformat()}")
        if video.live_views is not None:
            print(f"    Lượt xem live : {video.live_views}")
        if video.permalink_url:
            print(f"    URL           : {video.permalink_url}")


def print_video_status(status_payload: Dict[str, Any]) -> None:
    live_status = status_payload.get("live_status") or status_payload.get("status")
    print(f"Video ID: {status_payload.get('id')}")
    print(f"Trạng thái live: {live_status}")
    if status_payload.get("title"):
        print(f"Tiêu đề: {status_payload['title']}")
    if status_payload.get("publishing_phase"):
        print(f"Publishing phase: {status_payload['publishing_phase']}")
    if status_payload.get("start_time"):
        print(f"Thời gian bắt đầu: {status_payload['start_time']}")
    if status_payload.get("permalink_url"):
        print(f"Liên kết: {status_payload['permalink_url']}")
    if status_payload.get("live_views") is not None:
        print(f"Lượt xem live: {status_payload['live_views']}")


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    try:
        access_token = resolve_access_token(args.access_token)
        if args.page_id:
            live_videos = fetch_live_videos(args.page_id, access_token, args.graph_version)
            print_live_videos(live_videos)
        else:
            status_payload = fetch_video_status(args.video_id, access_token, args.graph_version)
            print_video_status(status_payload)
    except GraphAPIError as exc:
        print(f"Lỗi: {exc.pretty()}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
