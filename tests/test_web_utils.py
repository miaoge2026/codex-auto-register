import json
import time
from pathlib import Path

import pytest
from flask import Flask, request

from web_utils import (
    build_file_listing,
    mask_sensitive_info,
    parse_json_request,
    resolve_safe_path,
)


def test_resolve_safe_path_rejects_path_traversal(tmp_path: Path):
    with pytest.raises(ValueError, match="非法文件名"):
        resolve_safe_path("../secrets.json", tmp_path)


def test_resolve_safe_path_rejects_disallowed_suffix(tmp_path: Path):
    with pytest.raises(ValueError, match="不支持的文件类型"):
        resolve_safe_path("script.py", tmp_path)


def test_resolve_safe_path_accepts_allowed_file(tmp_path: Path):
    file_path = resolve_safe_path("accounts.json", tmp_path)
    assert file_path == tmp_path / "accounts.json"


def test_mask_sensitive_info_supports_json_lines():
    raw = '\n'.join([
        json.dumps({"email": "a@example.com", "access_token": "abcdefghijklmnop", "nested": {"refresh_token": "qrstuvwxyz123456"}}),
        json.dumps({"token": "zyxwvutsrqponmlk"}),
    ])

    masked = mask_sensitive_info(raw).splitlines()
    first = json.loads(masked[0])
    second = json.loads(masked[1])

    assert first["access_token"].startswith("abcdef...")
    assert first["nested"]["refresh_token"].endswith("3456")
    assert second["token"] == "zyxwvu...nmlk"


def test_build_file_listing_sorts_newest_first(tmp_path: Path):
    older = tmp_path / "older.json"
    older.write_text("{}")
    time.sleep(0.01)
    newer = tmp_path / "newer.log"
    newer.write_text("log")

    files = build_file_listing(tmp_path)
    assert [item["name"] for item in files] == ["newer.log", "older.json"]


def test_parse_json_request_returns_empty_dict_for_invalid_payload():
    app = Flask(__name__)
    with app.test_request_context("/", method="POST", data="not-json", content_type="application/json"):
        assert parse_json_request(request) == {}
