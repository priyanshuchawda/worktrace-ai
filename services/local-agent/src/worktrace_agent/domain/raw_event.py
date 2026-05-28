from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

PRIVACY_LEVELS: Final = {"safe", "sensitive", "secret", "redacted", "unknown"}


class RawEventValidationError(ValueError):
    pass


@dataclass(frozen=True)
class RawEvent:
    id: str
    session_id: str
    timestamp: str
    source: str
    type: str
    privacy_level: str
    confidence: float
    metadata: dict[str, object]


def build_raw_event(
    *,
    event_id: str,
    session_id: str,
    timestamp: str,
    source: str,
    event_type: str,
    privacy_level: str,
    confidence: float,
    metadata: dict[str, object] | None = None,
) -> RawEvent:
    return RawEvent(
        id=require_non_empty_string(event_id, "event_id"),
        session_id=require_non_empty_string(session_id, "session_id"),
        timestamp=require_iso_datetime(timestamp, "timestamp"),
        source=require_non_empty_string(source, "source"),
        type=require_non_empty_string(event_type, "event_type"),
        privacy_level=require_privacy_level(privacy_level),
        confidence=require_confidence(confidence),
        metadata=dict(metadata or {}),
    )


def require_non_empty_string(value: str, field_name: str) -> str:
    if not value.strip():
        raise RawEventValidationError(f"{field_name} must be a non-empty string")
    return value


def require_iso_datetime(value: str, field_name: str) -> str:
    require_non_empty_string(value, field_name)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RawEventValidationError(f"{field_name} must include a timezone offset")
    return value


def require_privacy_level(value: str) -> str:
    if value not in PRIVACY_LEVELS:
        raise RawEventValidationError(f"privacy_level must be one of {sorted(PRIVACY_LEVELS)}")
    return value


def require_confidence(value: float) -> float:
    if value < 0 or value > 1:
        raise RawEventValidationError("confidence must be between 0 and 1")
    return value
