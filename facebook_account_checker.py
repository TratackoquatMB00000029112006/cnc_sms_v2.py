#!/usr/bin/env python3
"""
facebook_account_checker.py
===========================

Tool dòng lệnh kiểm tra nhanh một (hoặc nhiều) tài khoản Facebook còn hoạt động
hay đã bị khóa/vô hiệu hóa dựa trên UID. Script ưu tiên sử dụng Graph API nếu có
access token hợp lệ, sau đó fallback sang kiểm tra trang web công khai.

Kết quả được phân loại theo các trạng thái:
    - ALIVE: tài khoản tồn tại và có thể truy cập.
    - NOT_FOUND: không tìm thấy tài khoản (UID sai hoặc đã bị xóa/vô hiệu hóa).
    - LOGIN_REQUIRED: cần đăng nhập mới xem được (không kết luận chắc chắn).
    - PERMISSION_DENIED: token không đủ quyền truy cập thông tin người dùng.
    - INVALID_TOKEN: token hết hạn hoặc sai định dạng.
    - UNKNOWN: không thể xác định (lỗi khác, bị chặn, captcha,...).

Ví dụ:
    python facebook_account_checker.py --uid 1000123456789
    python facebook_account_checker.py --uids 10001 10002 10003 --access-token <TOKEN>
    python facebook_account_checker.py --input-file list_uid.txt --json
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
from typing import Any, Dict, Iterable, List, Optional, Sequence


DEFAULT_GRAPH_VERSION = "v19.0"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


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


@dataclass
class AccountResult:
    uid: str
    status: str
    reason: Optional[str] = None
    name: Optional[str] = None
    source: Optional[str] = None  # "graph" hoặc "web"


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


def check_via_graph(uid: str, access_token: str, version: str) -> AccountResult:
    payload = call_graph(
        uid,
        params={
            "fields": "id,name",
            "access_token": access_token,
        },
        version=version,
    )
    return AccountResult(uid=uid, status="ALIVE", name=payload.get("name"), source="graph")


def interpret_graph_error(uid: str, error: GraphAPIError) -> AccountResult:
    error_info = error.payload.get("error") if isinstance(error.payload, dict) else None
    if isinstance(error_info, dict):
        code = error_info.get("code")
        subcode = error_info.get("error_subcode")
        message = error_info.get("message") or error_info.get("error_user_msg")
        if code == 190:
            return AccountResult(uid=uid, status="INVALID_TOKEN", reason=message, source="graph")
        if code == 200:
            return AccountResult(uid=uid, status="PERMISSION_DENIED", reason=message, source="graph")
        if code == 803 or (code == 100 and subcode == 33):
            return AccountResult(uid=uid, status="NOT_FOUND", reason=message, source="graph")
    return AccountResult(uid=uid, status="UNKNOWN", reason=error.pretty(), source="graph")


def check_via_web(uid: str, user_agent: str) -> AccountResult:
    url = f"https://m.facebook.com/profile.php?id={urllib.parse.quote(uid)}"
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status_code = response.getcode()
            html = response.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return AccountResult(uid=uid, status="NOT_FOUND", reason="Trang trả về 404.", source="web")
        return AccountResult(uid=uid, status="UNKNOWN", reason=f"HTTP {exc.code}", source="web")
    except urllib.error.URLError as exc:
        return AccountResult(uid=uid, status="UNKNOWN", reason=f"Lỗi mạng: {exc}", source="web")

    text = html.lower()
    unavailable_markers = [
        "content isn't available",
        "this content isn't available",
        "content not found",
        "liên kết có thể đã bị hỏng",
        "nội dung này hiện không khả dụng",
        "the link you followed may be broken",
    ]
    login_markers = [
        "log into facebook",
        "đăng nhập facebook",
        "you must log in",
    ]

    if any(marker in text for marker in unavailable_markers):
        return AccountResult(uid=uid, status="NOT_FOUND", reason="Trang thông báo nội dung không khả dụng.", source="web")
    if any(marker in text for marker in login_markers):
        return AccountResult(uid=uid, status="LOGIN_REQUIRED", reason="Cần đăng nhập để xác minh chính xác.", source="web")

    if status_code in (301, 302):
        return AccountResult(uid=uid, status="ALIVE", reason="Redirect tới trang hồ sơ.", source="web")

    return AccountResult(uid=uid, status="ALIVE", reason="Trang phản hồi hợp lệ.", source="web")


def check_account(uid: str, access_token: Optional[str], version: str, user_agent: str) -> AccountResult:
    uid = uid.strip()
    if not uid:
        return AccountResult(uid=uid, status="UNKNOWN", reason="UID trống.")

    if access_token:
        try:
            return check_via_graph(uid, access_token, version)
        except GraphAPIError as exc:
            result = interpret_graph_error(uid, exc)
            if result.status in {"UNKNOWN", "PERMISSION_DENIED", "INVALID_TOKEN"}:
                return result
            if result.status == "NOT_FOUND":
                return result
            # Nếu lỗi do quyền, thử fallback web
            if result.status in {"PERMISSION_DENIED"}:
                fallback = check_via_web(uid, user_agent)
                if fallback.status == "ALIVE":
                    fallback.reason = "Graph API bị hạn chế nhưng trang web hiển thị."
                return fallback
            return result

    return check_via_web(uid, user_agent)


def parse_uid_inputs(args: argparse.Namespace) -> List[str]:
    uids: List[str] = []
    if args.uid:
        uids.append(args.uid)
    if args.uids:
        uids.extend(args.uids)
    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith("#"):
                    uids.append(line)
    deduped = []
    seen = set()
    for uid in uids:
        if uid not in seen:
            deduped.append(uid)
            seen.add(uid)
    return deduped


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kiểm tra trạng thái tài khoản Facebook bằng UID.")
    parser.add_argument("--uid", help="UID cá nhân để kiểm tra.")
    parser.add_argument("--uids", nargs="+", help="Danh sách UID (cách nhau bằng khoảng trắng).")
    parser.add_argument("--input-file", help="Đường dẫn file chứa danh sách UID (mỗi dòng một UID).")
    parser.add_argument("--access-token", help="Access token Graph API (tùy chọn).")
    parser.add_argument(
        "--graph-version",
        default=DEFAULT_GRAPH_VERSION,
        help=f"Phiên bản Graph API (mặc định: {DEFAULT_GRAPH_VERSION}).",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent dùng khi truy cập phiên bản web di động (mặc định: Chrome trên Linux).",
    )
    parser.add_argument("--json", action="store_true", help="Xuất kết quả dạng JSON.")
    args = parser.parse_args(argv)

    if not (args.uid or args.uids or args.input_file):
        parser.error("Cần cung cấp ít nhất một UID (qua --uid, --uids hoặc --input-file).")

    return args


def resolve_access_token(cli_token: Optional[str]) -> Optional[str]:
    return cli_token or os.getenv("FACEBOOK_ACCESS_TOKEN")


def results_to_table(results: Sequence[AccountResult]) -> str:
    headers = ["UID", "STATUS", "NAME/REASON"]
    rows = [headers]
    for item in results:
        note = item.name or item.reason or ""
        rows.append([item.uid, item.status, note])

    col_widths = [max(len(str(row[idx])) for row in rows) for idx in range(len(headers))]

    lines = []
    for ridx, row in enumerate(rows):
        line = " | ".join(str(cell).ljust(col_widths[idx]) for idx, cell in enumerate(row))
        lines.append(line)
        if ridx == 0:
            lines.append("-+-".join("-" * width for width in col_widths))
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    access_token = resolve_access_token(args.access_token)
    uids = parse_uid_inputs(args)
    if not uids:
        print("Không tìm thấy UID hợp lệ trong đầu vào.", file=sys.stderr)
        return 1

    results = []
    for uid in uids:
        result = check_account(uid, access_token, args.graph_version, args.user_agent)
        results.append(result)

    if args.json:
        print(json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2))
    else:
        print(results_to_table(results))

    unresolved = [res for res in results if res.status in {"UNKNOWN", "LOGIN_REQUIRED"}]
    if unresolved:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
