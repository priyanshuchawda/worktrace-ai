from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Literal

from worktrace_agent.db.session_state_repository import (
    ACTIVE_STATUSES,
    interrupt_session,
    list_sessions_by_status,
)
from worktrace_agent.domain.session_state import SessionRecord, SessionStatus, require_iso_datetime

type RecoveryAction = Literal["review", "export", "delete"]
RECOVERY_ACTIONS: tuple[RecoveryAction, ...] = ("review", "export", "delete")


@dataclass(frozen=True)
class InterruptedSessionSummary:
    id: str
    started_at: str
    interrupted_at: str | None
    title: str | None
    event_count: int
    available_actions: tuple[RecoveryAction, ...]


@dataclass(frozen=True)
class RecoveryBanner:
    has_interrupted_sessions: bool
    message: str
    sessions: list[InterruptedSessionSummary]


def mark_active_sessions_interrupted(
    connection: sqlite3.Connection,
    *,
    occurred_at: str,
) -> list[SessionRecord]:
    require_iso_datetime(occurred_at, "occurred_at")
    active_sessions = list_sessions_by_status(connection, ACTIVE_STATUSES)

    return [
        interrupt_session(connection, session_id=session.id, occurred_at=occurred_at)
        for session in active_sessions
    ]


def list_interrupted_sessions(connection: sqlite3.Connection) -> list[InterruptedSessionSummary]:
    sessions = list_sessions_by_status(connection, (SessionStatus.INTERRUPTED,))
    event_counts = _count_events_by_session(connection, [session.id for session in sessions])

    return [
        InterruptedSessionSummary(
            id=session.id,
            started_at=session.started_at,
            interrupted_at=session.ended_at,
            title=session.title,
            event_count=event_counts.get(session.id, 0),
            available_actions=RECOVERY_ACTIONS,
        )
        for session in sessions
    ]


def build_recovery_banner(connection: sqlite3.Connection) -> RecoveryBanner:
    sessions = list_interrupted_sessions(connection)
    count = len(sessions)
    if count == 0:
        return RecoveryBanner(
            has_interrupted_sessions=False,
            message="No interrupted sessions found.",
            sessions=[],
        )

    noun = "session" if count == 1 else "sessions"
    return RecoveryBanner(
        has_interrupted_sessions=True,
        message=f"{count} interrupted {noun} can be reviewed, exported, or deleted.",
        sessions=sessions,
    )


def _count_events_by_session(
    connection: sqlite3.Connection,
    session_ids: list[str],
) -> dict[str, int]:
    if not session_ids:
        return {}

    counts: dict[str, int] = {}
    for session_id in session_ids:
        row = connection.execute(
            "SELECT COUNT(*) AS event_count FROM raw_events WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is not None and int(row["event_count"]) > 0:
            counts[session_id] = int(row["event_count"])
    return counts
