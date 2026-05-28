from pathlib import Path

import pytest

from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.session_state_repository import (
    SessionTransitionError,
    interrupt_session,
    pause_session,
    resume_session,
    start_session,
    stop_session,
)
from worktrace_agent.domain.session_state import SessionStatus

STARTED_AT = "2026-05-06T09:14:00+05:30"
PAUSED_AT = "2026-05-06T09:20:00+05:30"
STOPPED_AT = "2026-05-06T09:30:00+05:30"
INTERRUPTED_AT = "2026-05-06T09:18:00+05:30"


def test_start_session_persists_recording_status(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        session = start_session(
            connection,
            session_id="sess_state_001",
            started_at=STARTED_AT,
            title="State machine smoke",
            goal="Finish API tests",
            project_label="workaudit-ai",
            tags=["coding", "tests", "coding"],
            storage_path="~/.worktrace/sessions/sess_state_001",
            privacy_mode="standard",
        )

        row = connection.execute(
            "SELECT id, started_at, ended_at, status, title, goal, project_label, tags_json, "
            "storage_path, privacy_mode "
            "FROM sessions WHERE id = ?",
            ("sess_state_001",),
        ).fetchone()

        assert session.status is SessionStatus.RECORDING
        assert row["status"] == "recording"
        assert row["started_at"] == STARTED_AT
        assert row["ended_at"] is None
        assert row["title"] == "State machine smoke"
        assert row["goal"] == "Finish API tests"
        assert row["project_label"] == "workaudit-ai"
        assert row["tags_json"] == '["coding","tests"]'
        assert session.tags == ("coding", "tests")
    finally:
        connection.close()


def test_pause_and_stop_session_persist_transitions(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id="sess_state_001", started_at=STARTED_AT)

        paused = pause_session(connection, session_id="sess_state_001", occurred_at=PAUSED_AT)
        stopped = stop_session(connection, session_id="sess_state_001", occurred_at=STOPPED_AT)

        row = connection.execute(
            "SELECT status, started_at, ended_at FROM sessions WHERE id = ?",
            ("sess_state_001",),
        ).fetchone()

        assert paused.status is SessionStatus.PAUSED
        assert stopped.status is SessionStatus.STOPPED
        assert row["status"] == "stopped"
        assert row["started_at"] == STARTED_AT
        assert row["ended_at"] == STOPPED_AT
    finally:
        connection.close()


def test_resume_session_persists_recording_status_without_ending_session(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id="sess_state_001", started_at=STARTED_AT)
        pause_session(connection, session_id="sess_state_001", occurred_at=PAUSED_AT)

        resumed = resume_session(connection, session_id="sess_state_001", occurred_at=PAUSED_AT)

        row = connection.execute(
            "SELECT status, started_at, ended_at FROM sessions WHERE id = ?",
            ("sess_state_001",),
        ).fetchone()

        assert resumed.status is SessionStatus.RECORDING
        assert resumed.ended_at is None
        assert row["status"] == "recording"
        assert row["started_at"] == STARTED_AT
        assert row["ended_at"] is None
    finally:
        connection.close()


def test_interrupt_session_persists_interrupted_status(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id="sess_state_001", started_at=STARTED_AT)

        interrupted = interrupt_session(
            connection,
            session_id="sess_state_001",
            occurred_at=INTERRUPTED_AT,
        )

        row = connection.execute(
            "SELECT status, ended_at FROM sessions WHERE id = ?",
            ("sess_state_001",),
        ).fetchone()

        assert interrupted.status is SessionStatus.INTERRUPTED
        assert row["status"] == "interrupted"
        assert row["ended_at"] == INTERRUPTED_AT
    finally:
        connection.close()


def test_duplicate_start_does_not_corrupt_active_session(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        original = start_session(
            connection,
            session_id="sess_state_001",
            started_at=STARTED_AT,
            title="Original title",
        )

        duplicate = start_session(
            connection,
            session_id="sess_state_001",
            started_at="2026-05-06T10:00:00+05:30",
            title="Should not replace",
        )

        session_count = connection.execute(
            "SELECT COUNT(*) FROM sessions WHERE id = ?",
            ("sess_state_001",),
        ).fetchone()[0]
        row = connection.execute(
            "SELECT started_at, status, title FROM sessions WHERE id = ?",
            ("sess_state_001",),
        ).fetchone()

        assert duplicate == original
        assert session_count == 1
        assert row["started_at"] == STARTED_AT
        assert row["status"] == "recording"
        assert row["title"] == "Original title"
    finally:
        connection.close()


def test_duplicate_stop_is_idempotent(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id="sess_state_001", started_at=STARTED_AT)
        first_stop = stop_session(connection, session_id="sess_state_001", occurred_at=STOPPED_AT)

        second_stop = stop_session(
            connection,
            session_id="sess_state_001",
            occurred_at="2026-05-06T11:00:00+05:30",
        )

        assert second_stop == first_stop
    finally:
        connection.close()


def test_invalid_transitions_are_rejected(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        with pytest.raises(SessionTransitionError, match="Unknown session"):
            pause_session(connection, session_id="sess_missing", occurred_at=PAUSED_AT)

        start_session(connection, session_id="sess_state_001", started_at=STARTED_AT)
        stop_session(connection, session_id="sess_state_001", occurred_at=STOPPED_AT)

        with pytest.raises(SessionTransitionError, match="Cannot pause"):
            pause_session(connection, session_id="sess_state_001", occurred_at=PAUSED_AT)

        with pytest.raises(SessionTransitionError, match="Cannot resume"):
            resume_session(connection, session_id="sess_state_001", occurred_at=PAUSED_AT)

        with pytest.raises(SessionTransitionError, match="Cannot start"):
            start_session(connection, session_id="sess_state_001", started_at=STARTED_AT)
    finally:
        connection.close()
