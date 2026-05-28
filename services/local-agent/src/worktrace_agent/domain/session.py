from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

type JsonObject = dict[str, Any]

SESSION_STATUSES = {"recording", "paused", "stopped", "interrupted"}
PRIVACY_LEVELS = {"safe", "sensitive", "secret", "redacted", "unknown"}


@dataclass(frozen=True)
class FakeSession:
    session: JsonObject
    events: list[JsonObject]


def validate_fake_session(raw: object) -> FakeSession:
    root = _require_object(raw, "session_fixture")
    session = _validate_session(_require_object(root.get("session"), "session"))
    events = _require_list(root.get("events"), "events")
    validated_events = [
        _validate_event(event, f"events[{index}]", str(session["id"]))
        for index, event in enumerate(events)
    ]

    return FakeSession(session=session, events=validated_events)


def _validate_session(raw: JsonObject) -> JsonObject:
    session = {
        "id": _require_non_empty_string(raw.get("id"), "session.id"),
        "started_at": _require_iso_datetime(raw.get("started_at"), "session.started_at"),
        "ended_at": _optional_iso_datetime(raw.get("ended_at"), "session.ended_at"),
        "status": _require_choice(raw.get("status"), "session.status", SESSION_STATUSES),
        "title": _optional_non_empty_string(raw.get("title"), "session.title"),
        "goal": _optional_non_empty_string(raw.get("goal"), "session.goal"),
        "project_label": _optional_non_empty_string(
            raw.get("project_label"), "session.project_label"
        ),
        "tags": _optional_string_list(raw.get("tags"), "session.tags"),
        "storage_path": _optional_non_empty_string(raw.get("storage_path"), "session.storage_path"),
        "privacy_mode": _require_non_empty_string(raw.get("privacy_mode"), "session.privacy_mode"),
    }
    return {key: value for key, value in session.items() if value is not None}


def _validate_event(raw: object, path: str, session_id: str) -> JsonObject:
    event = _require_object(raw, path)
    event_session_id = _require_non_empty_string(event.get("session_id"), f"{path}.session_id")
    if event_session_id != session_id:
        raise ValueError(f"{path}.session_id must match session.id")

    metadata = event.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError(f"{path}.metadata must be an object")
    metadata_object = cast(JsonObject, metadata)

    return {
        "id": _require_non_empty_string(event.get("id"), f"{path}.id"),
        "session_id": event_session_id,
        "timestamp": _require_iso_datetime(event.get("timestamp"), f"{path}.timestamp"),
        "source": _require_non_empty_string(event.get("source"), f"{path}.source"),
        "type": _require_non_empty_string(event.get("type"), f"{path}.type"),
        "privacy_level": _require_choice(
            event.get("privacy_level"), f"{path}.privacy_level", PRIVACY_LEVELS
        ),
        "confidence": _require_confidence(event.get("confidence"), f"{path}.confidence"),
        "metadata": metadata_object.copy(),
    }


def _require_object(value: object, path: str) -> JsonObject:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    return cast(JsonObject, value).copy()


def _require_list(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be a list")
    return cast(list[object], value).copy()


def _optional_string_list(value: object, path: str) -> list[str]:
    if value is None:
        return []
    values = _require_list(value, path)
    return [
        _require_non_empty_string(item, f"{path}[{index}]") for index, item in enumerate(values)
    ]


def _require_non_empty_string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value


def _optional_non_empty_string(value: object, path: str) -> str | None:
    if value is None:
        return None
    return _require_non_empty_string(value, path)


def _require_iso_datetime(value: object, path: str) -> str:
    value = _require_non_empty_string(value, path)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{path} must include a timezone offset")
    return value


def _optional_iso_datetime(value: object, path: str) -> str | None:
    if value is None:
        return None
    return _require_iso_datetime(value, path)


def _require_choice(value: object, path: str, choices: set[str]) -> str:
    value = _require_non_empty_string(value, path)
    if value not in choices:
        raise ValueError(f"{path} must be one of: {', '.join(sorted(choices))}")
    return value


def _require_confidence(value: object, path: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{path} must be a number")
    confidence = float(value)
    if confidence < 0 or confidence > 1:
        raise ValueError(f"{path} must be between 0 and 1")
    return confidence
