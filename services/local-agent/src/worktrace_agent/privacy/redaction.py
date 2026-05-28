from __future__ import annotations

import json
import re
from typing import Any, cast

PRIVACY_TEST_CORPUS = (
    "OPENAI_API_KEY=sk-test",
    "GITHUB_TOKEN=ghp_test",
    "AWS_SECRET_ACCESS_KEY=test",
    "password=mysecret",
    "email@example.com",
    "+91 9876543210",
    "-----BEGIN PRIVATE KEY-----",
)

SECRET_VALUES = (
    "sk-test",
    "ghp_test",
    "mysecret",
)

REDACTION_TOKEN = "[REDACTED]"  # nosec B105

SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD|PASS|KEY)[A-Z0-9_]*=)([^\s;&|]+)"
)
JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
GITHUB_TOKEN_PATTERN = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
)
GOOGLE_API_KEY_PATTERN = re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")
AWS_ACCESS_KEY_PATTERN = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
PRIVATE_KEY_BLOCK_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")


def redact_text(value: str, *, redact_contact_info: bool = False) -> str:
    redacted = value
    for secret in PRIVACY_TEST_CORPUS + SECRET_VALUES:
        redacted = redacted.replace(secret, REDACTION_TOKEN)
    redacted = PRIVATE_KEY_BLOCK_PATTERN.sub(REDACTION_TOKEN, redacted)
    redacted = SECRET_ASSIGNMENT_PATTERN.sub(rf"\1{REDACTION_TOKEN}", redacted)
    redacted = JWT_PATTERN.sub(REDACTION_TOKEN, redacted)
    redacted = GITHUB_TOKEN_PATTERN.sub(REDACTION_TOKEN, redacted)
    redacted = GOOGLE_API_KEY_PATTERN.sub(REDACTION_TOKEN, redacted)
    redacted = AWS_ACCESS_KEY_PATTERN.sub(REDACTION_TOKEN, redacted)
    if redact_contact_info:
        redacted = EMAIL_PATTERN.sub(REDACTION_TOKEN, redacted)
        redacted = PHONE_PATTERN.sub(REDACTION_TOKEN, redacted)
    return redacted


def redact_json_value(value: Any, *, redact_contact_info: bool = False) -> Any:
    if isinstance(value, str):
        return redact_text(value, redact_contact_info=redact_contact_info)
    if isinstance(value, list):
        return [
            redact_json_value(item, redact_contact_info=redact_contact_info)
            for item in cast(list[object], value)
        ]
    if isinstance(value, dict):
        return {
            str(key): redact_json_value(item, redact_contact_info=redact_contact_info)
            for key, item in cast(dict[object, object], value).items()
        }
    return value


def redact_for_prompt(value: Any, *, redact_contact_info: bool = False) -> Any:
    return redact_json_value(value, redact_contact_info=redact_contact_info)


def redact_for_export(value: Any, *, redact_contact_info: bool = False) -> Any:
    return redact_json_value(value, redact_contact_info=redact_contact_info)


def redact_for_log(value: str, *, redact_contact_info: bool = False) -> str:
    return redact_text(value, redact_contact_info=redact_contact_info)


def count_privacy_leaks(value: Any) -> int:
    serialized = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
    literal_leaks = sum(secret in serialized for secret in PRIVACY_TEST_CORPUS + SECRET_VALUES)
    pattern_leaks = sum(
        bool(pattern.search(serialized))
        for pattern in (
            JWT_PATTERN,
            GITHUB_TOKEN_PATTERN,
            GOOGLE_API_KEY_PATTERN,
            AWS_ACCESS_KEY_PATTERN,
            PRIVATE_KEY_BLOCK_PATTERN,
        )
    )
    return literal_leaks + pattern_leaks
