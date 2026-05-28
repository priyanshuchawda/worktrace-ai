from pathlib import Path

from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.raw_events_repository import append_raw_event, list_raw_events
from worktrace_agent.db.session_state_repository import pause_session, start_session, stop_session
from worktrace_agent.domain.raw_event import build_raw_event
from worktrace_agent.domain.session_state import SessionStatus
from worktrace_agent.exporters.raw_json import export_redacted_raw_json
from worktrace_agent.recovery.crash_recovery import (
    build_recovery_banner,
    list_interrupted_sessions,
    mark_active_sessions_interrupted,
)

STARTED_AT = "2026-05-06T09:14:00+05:30"
PAUSED_AT = "2026-05-06T09:20:00+05:30"
STOPPED_AT = "2026-05-06T09:30:00+05:30"
CRASHED_AT = "2026-05-06T09:24:00+05:30"


def test_sidecar_crash_marks_recording_session_interrupted_and_keeps_events(
    tmp_path: Path,
) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    export_path = tmp_path / "exports" / "sess_recovery_001.raw.json"
    try:
        start_session(connection, session_id="sess_recovery_001", started_at=STARTED_AT)
        append_raw_event(
            connection,
            build_raw_event(
                event_id="evt_recovery_001",
                session_id="sess_recovery_001",
                timestamp="2026-05-06T09:18:00+05:30",
                source="active_window_tracker",
                event_type="active_window_changed",
                privacy_level="safe",
                confidence=0.98,
                metadata={"app": "VS Code", "window_title": "crash_recovery.py"},
            ),
        )

        interrupted = mark_active_sessions_interrupted(connection, occurred_at=CRASHED_AT)

        assert [session.id for session in interrupted] == ["sess_recovery_001"]
        assert interrupted[0].status is SessionStatus.INTERRUPTED
        assert interrupted[0].ended_at == CRASHED_AT
        assert [event.id for event in list_raw_events(connection, "sess_recovery_001")] == [
            "evt_recovery_001"
        ]

        written_path = export_redacted_raw_json(connection, "sess_recovery_001", export_path)
        assert written_path.read_text(encoding="utf-8").find("evt_recovery_001") != -1
    finally:
        connection.close()


def test_app_crash_marks_paused_session_interrupted(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id="sess_paused_001", started_at=STARTED_AT)
        pause_session(connection, session_id="sess_paused_001", occurred_at=PAUSED_AT)

        interrupted = mark_active_sessions_interrupted(connection, occurred_at=CRASHED_AT)

        assert [session.id for session in interrupted] == ["sess_paused_001"]
        assert interrupted[0].status is SessionStatus.INTERRUPTED
    finally:
        connection.close()


def test_recovery_does_not_change_stopped_sessions(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id="sess_stopped_001", started_at=STARTED_AT)
        stop_session(connection, session_id="sess_stopped_001", occurred_at=STOPPED_AT)

        interrupted = mark_active_sessions_interrupted(connection, occurred_at=CRASHED_AT)
        row = connection.execute(
            "SELECT status, ended_at FROM sessions WHERE id = ?",
            ("sess_stopped_001",),
        ).fetchone()

        assert interrupted == []
        assert row["status"] == "stopped"
        assert row["ended_at"] == STOPPED_AT
    finally:
        connection.close()


def test_recovery_banner_lists_interrupted_sessions_with_actions(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(
            connection,
            session_id="sess_banner_001",
            started_at=STARTED_AT,
            title="Interrupted review",
        )
        append_raw_event(
            connection,
            build_raw_event(
                event_id="evt_banner_001",
                session_id="sess_banner_001",
                timestamp="2026-05-06T09:19:00+05:30",
                source="terminal_command_detector",
                event_type="terminal_command",
                privacy_level="safe",
                confidence=0.9,
                metadata={"command": "uv run --python 3.13 pytest"},
            ),
        )
        mark_active_sessions_interrupted(connection, occurred_at=CRASHED_AT)

        interrupted = list_interrupted_sessions(connection)
        banner = build_recovery_banner(connection)

        assert len(interrupted) == 1
        assert interrupted[0].id == "sess_banner_001"
        assert interrupted[0].event_count == 1
        assert interrupted[0].available_actions == ("review", "export", "delete")
        assert banner.has_interrupted_sessions
        assert banner.sessions == interrupted
        assert "interrupted session" in banner.message
    finally:
        connection.close()
