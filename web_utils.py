"""Shared helpers for the Flask web interfaces."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from flask import Request

SENSITIVE_TOKEN_KEYS = {"access_token", "refresh_token", "id_token", "token"}
ALLOWED_FILE_SUFFIXES = {".json", ".log", ".txt", ".yaml", ".yml"}


def parse_json_request(request: Request) -> Dict[str, Any]:
    """Safely parse a JSON request body, returning an empty dict for invalid payloads."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def resolve_safe_path(filename: str, base_dir: Path) -> Path:
    """Resolve a user supplied file path inside base_dir.

    Raises:
        ValueError: If the filename is empty, outside base_dir, or has a disallowed suffix.
    """
    cleaned = (filename or "").strip()
    if not cleaned:
        raise ValueError("文件名不能为空")

    candidate = (base_dir / cleaned).resolve()
    allowed_root = base_dir.resolve()

    try:
        candidate.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError("非法文件名") from exc

    if candidate.suffix.lower() not in ALLOWED_FILE_SUFFIXES:
        raise ValueError("不支持的文件类型")

    return candidate


def build_file_listing(base_dir: Path, patterns: Optional[Iterable[str]] = None) -> list[Dict[str, Any]]:
    """Build a sorted list of files for the file manager endpoints."""
    search_patterns = tuple(patterns or ("*.json", "*.log", "*.txt"))
    files = []
    seen = set()

    for pattern in search_patterns:
        for file_path in base_dir.glob(pattern):
            if not file_path.is_file() or file_path in seen:
                continue
            seen.add(file_path)
            stat = file_path.stat()
            files.append(
                {
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )

    files.sort(key=lambda item: item["modified"], reverse=True)
    for item in files:
        item["modified"] = datetime.fromtimestamp(item["modified"]).isoformat()
    return files


def mask_token(token: str) -> str:
    """Mask sensitive token values while keeping them identifiable."""
    if len(token) <= 12:
        return "***"
    return f"{token[:6]}...{token[-4:]}"


def _mask_sensitive_data(value: Any) -> Any:
    if isinstance(value, dict):
        masked = {}
        for key, item in value.items():
            if key in SENSITIVE_TOKEN_KEYS and isinstance(item, str):
                masked[key] = mask_token(item)
            else:
                masked[key] = _mask_sensitive_data(item)
        return masked
    if isinstance(value, list):
        return [_mask_sensitive_data(item) for item in value]
    return value


def mask_sensitive_info(content: str) -> str:
    """Mask sensitive fields in JSON or JSON-lines content."""
    stripped = content.strip()
    if not stripped:
        return content

    try:
        parsed = json.loads(content)
        return json.dumps(_mask_sensitive_data(parsed), ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        lines = [line for line in content.splitlines() if line.strip()]
        if not lines:
            return content

        masked_lines = []
        for line in lines:
            try:
                masked_lines.append(json.dumps(_mask_sensitive_data(json.loads(line)), ensure_ascii=False))
            except json.JSONDecodeError:
                return content
        return "\n".join(masked_lines)
