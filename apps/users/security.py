"""Small security helpers for request throttling and input validation."""
import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils.crypto import constant_time_compare

from .utils import get_client_ip


SAFE_TEXT_RE = re.compile(r"^[\w\s.,:;@#/+()\-_'&\[\]]*$", re.UNICODE)
SAFE_NAME_RE = re.compile(r"^[\w\s.,@#\-_'()]{1,255}$", re.UNICODE)
ALLOWED_UPLOAD_EXTENSIONS = {
    ".pdf", ".txt", ".csv", ".json", ".log", ".png", ".jpg", ".jpeg",
    ".doc", ".docx", ".xls", ".xlsx", ".zip"
}
ALLOWED_UPLOAD_MIME_PREFIXES = (
    "text/", "image/", "application/pdf", "application/json",
    "application/zip", "application/vnd.openxmlformats-officedocument",
    "application/msword", "application/vnd.ms-excel"
)


def sanitize_text(value, max_length=500, field_name="value", allow_empty=True):
    value = (value or "").strip()
    if not value and allow_empty:
        return value
    if len(value) > max_length:
        raise ValidationError(f"{field_name} is too long.")
    if not SAFE_TEXT_RE.match(value):
        raise ValidationError(f"{field_name} contains unsupported characters.")
    return value


def sanitize_name(value, field_name="name"):
    value = (value or "").strip()
    if not SAFE_NAME_RE.match(value):
        raise ValidationError(f"{field_name} contains unsupported characters.")
    return value


def validate_uploaded_file(file_obj, max_mb=None):
    if not file_obj:
        raise ValidationError("A file is required.")
    max_mb = max_mb or settings.TAPDEV_CONFIG.get("MAX_UPLOAD_SIZE_MB", 50)
    if file_obj.size > max_mb * 1024 * 1024:
        raise ValidationError(f"File too large. Max {max_mb} MB.")
    original_name = Path(file_obj.name).name
    if original_name != file_obj.name or ".." in file_obj.name.replace("\\", "/"):
        raise ValidationError("Invalid file name.")
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError(f"File type {extension or '(none)'} is not allowed.")
    content_type = getattr(file_obj, "content_type", "") or "application/octet-stream"
    if not any(content_type.startswith(prefix) for prefix in ALLOWED_UPLOAD_MIME_PREFIXES):
        raise ValidationError("File MIME type is not allowed.")
    return file_obj


def rate_limit(request, scope, limit=5, window=300, identity=None):
    ip = get_client_ip(request) or "unknown"
    identity = identity or ""
    raw_key = f"{scope}:{ip}:{identity}".lower()
    key = "rl:" + hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    count = cache.get(key, 0)
    if count >= limit:
        return False
    if count == 0:
        cache.set(key, 1, window)
    else:
        cache.incr(key)
    return True


def parse_json_body(request, max_bytes=256 * 1024):
    content_type = request.headers.get("Content-Type", "")
    if content_type and "application/json" not in content_type:
        raise ValueError("Content-Type must be application/json.")
    if len(request.body) > max_bytes:
        raise ValueError("JSON payload too large.")
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        raise ValueError("Malformed JSON.")


def json_error(message, status=400):
    return JsonResponse({"error": message}, status=status)


def verify_hmac_signature(secret, message, supplied_signature):
    if not supplied_signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return constant_time_compare(digest, supplied_signature)


def validate_replay_nonce(scope, nonce, window=300):
    nonce = (nonce or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9._:-]{12,128}", nonce):
        return False
    key = "nonce:" + hashlib.sha256(f"{scope}:{nonce}".encode("utf-8")).hexdigest()
    if cache.get(key):
        return False
    cache.set(key, "1", window)
    return True


def require_production_secret(value, name):
    if not settings.DEBUG and (not value or value in {"change-me", "dev-only-change-me-not-for-production"}):
        raise RuntimeError(f"{name} must be configured for production.")
    return value
