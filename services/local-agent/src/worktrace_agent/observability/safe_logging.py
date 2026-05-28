from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Literal, cast

from worktrace_agent.privacy.redaction import redact_for_log

LogLevel = Literal["debug", "info", "warning", "error"]

DEFAULT_LOG_FILENAME = "worktrace.log"
DEFAULT_MAX_BYTES = 1_048_576
DEFAULT_BACKUP_COUNT = 3
OMITTED_PRIVATE_FIELD_COUNT_KEY = "omitted_private_field_count"

PRIVATE_FIELD_FRAGMENTS = (
    "screenshot",
    "clipboard",
    "prompt",
    "raw_ocr",
    "ocr_text",
    "image_bytes",
    "image_data",
    "audio_bytes",
)

LOG_LEVELS: dict[LogLevel, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def setup_rotating_local_logger(
    log_dir: Path,
    *,
    logger_name: str = "worktrace_agent",
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> logging.Logger:
    resolved_dir = Path(log_dir)
    resolved_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    handler = RotatingFileHandler(
        resolved_dir / DEFAULT_LOG_FILENAME,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def write_safe_log(
    logger: logging.Logger,
    *,
    level: LogLevel,
    category: str,
    message: str,
    metadata: Mapping[str, object] | None = None,
) -> None:
    safe_metadata = sanitize_for_log(dict(metadata or {}))
    payload: dict[str, object] = {
        "category": redact_for_log(category),
        "message": redact_for_log(message),
        "metadata": safe_metadata,
    }

    logger.log(LOG_LEVELS[level], json.dumps(payload, sort_keys=True, default=str))


def sanitize_for_log(value: object) -> object:
    sanitized, omitted_count = _sanitize_value(value)
    if omitted_count == 0 or not isinstance(sanitized, dict):
        return sanitized

    sanitized_mapping = cast(dict[str, object], sanitized)
    existing_count = sanitized_mapping.get(OMITTED_PRIVATE_FIELD_COUNT_KEY, 0)
    if isinstance(existing_count, int):
        sanitized_mapping[OMITTED_PRIVATE_FIELD_COUNT_KEY] = existing_count + omitted_count
    else:
        sanitized_mapping[OMITTED_PRIVATE_FIELD_COUNT_KEY] = omitted_count
    return sanitized_mapping


def _sanitize_value(value: object) -> tuple[object, int]:
    if isinstance(value, str):
        return redact_for_log(value), 0
    if isinstance(value, bytes | bytearray | memoryview):
        return "[OMITTED_BINARY]", 1
    if isinstance(value, Mapping):
        return _sanitize_mapping(cast(Mapping[object, object], value))
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return _sanitize_sequence(cast(Sequence[object], value))
    return value, 0


def _sanitize_mapping(value: Mapping[object, object]) -> tuple[dict[str, object], int]:
    sanitized: dict[str, object] = {}
    omitted_count = 0

    for key, item in value.items():
        key_text = str(key)
        if _is_private_field(key_text):
            omitted_count += 1
            continue

        safe_item, child_omitted_count = _sanitize_value(item)
        sanitized[key_text] = safe_item
        omitted_count += child_omitted_count

    return sanitized, omitted_count


def _sanitize_sequence(value: Sequence[object]) -> tuple[list[object], int]:
    sanitized: list[object] = []
    omitted_count = 0

    for item in value:
        safe_item, child_omitted_count = _sanitize_value(item)
        sanitized.append(safe_item)
        omitted_count += child_omitted_count

    return sanitized, omitted_count


def _is_private_field(key: str) -> bool:
    normalized_key = key.lower()
    return any(fragment in normalized_key for fragment in PRIVATE_FIELD_FRAGMENTS)
