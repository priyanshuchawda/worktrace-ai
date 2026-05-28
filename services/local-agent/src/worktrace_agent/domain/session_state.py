from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SessionStatus(StrEnum):
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"
    INTERRUPTED = "interrupted"


class SessionTransitionError(ValueError):
    pass


@dataclass(frozen=True)
class SessionRecord:
    id: str
    started_at: str
    ended_at: str | None
    status: SessionStatus
    title: str | None
    goal: str | None
    project_label: str | None
    tags: tuple[str, ...]
    storage_path: str | None
    privacy_mode: str


def require_non_empty_string(value: str, field_name: str) -> str:
    if not value.strip():
        raise SessionTransitionError(f"{field_name} must be a non-empty string")
    return value


def require_iso_datetime(value: str, field_name: str) -> str:
    require_non_empty_string(value, field_name)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SessionTransitionError(f"{field_name} must include a timezone offset")
    return value


def optional_non_empty_string(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return require_non_empty_string(value, field_name)


def normalized_tags(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()

    tags: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = require_non_empty_string(raw_value, "tag").strip()
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        tags.append(value)
    return tuple(tags)


def build_recording_session(
    *,
    session_id: str,
    started_at: str,
    title: str | None = None,
    goal: str | None = None,
    project_label: str | None = None,
    tags: tuple[str, ...] | list[str] | None = None,
    storage_path: str | None = None,
    privacy_mode: str = "standard",
) -> SessionRecord:
    return SessionRecord(
        id=require_non_empty_string(session_id, "session_id"),
        started_at=require_iso_datetime(started_at, "started_at"),
        ended_at=None,
        status=SessionStatus.RECORDING,
        title=optional_non_empty_string(title, "title"),
        goal=optional_non_empty_string(goal, "goal"),
        project_label=optional_non_empty_string(project_label, "project_label"),
        tags=normalized_tags(tags),
        storage_path=optional_non_empty_string(storage_path, "storage_path"),
        privacy_mode=require_non_empty_string(privacy_mode, "privacy_mode"),
    )


def transition_session(
    session: SessionRecord,
    *,
    status: SessionStatus,
    occurred_at: str | None,
) -> SessionRecord:
    ended_at = require_iso_datetime(occurred_at, "occurred_at") if occurred_at else None
    return SessionRecord(
        id=session.id,
        started_at=session.started_at,
        ended_at=ended_at,
        status=status,
        title=session.title,
        goal=session.goal,
        project_label=session.project_label,
        tags=session.tags,
        storage_path=session.storage_path,
        privacy_mode=session.privacy_mode,
    )
