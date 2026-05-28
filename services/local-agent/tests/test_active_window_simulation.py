from pathlib import Path

from worktrace_agent.capture.active_window import (
    build_fake_active_window_events,
    save_fake_active_window_recording,
)
from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.raw_events_repository import list_raw_events
from worktrace_agent.db.session_state_repository import start_session, stop_session

SESSION_ID = "sess_active_window_001"
STARTED_AT = "2026-05-06T09:14:00+05:30"
STOPPED_AT = "2026-05-06T09:24:00+05:30"


def test_ten_minute_fake_active_window_recording_persists_ordered_events(
    tmp_path: Path,
) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(
            connection,
            session_id=SESSION_ID,
            started_at=STARTED_AT,
            title="Active window simulation",
        )

        saved_events = save_fake_active_window_recording(
            connection,
            session_id=SESSION_ID,
            started_at=STARTED_AT,
            duration_minutes=10,
        )
        stop_session(connection, session_id=SESSION_ID, occurred_at=STOPPED_AT)

        loaded_events = list_raw_events(connection, SESSION_ID)

        assert saved_events == loaded_events
        assert [event.metadata["app"] for event in loaded_events] == [
            "VS Code",
            "Chrome",
            "Windows Terminal",
            "VS Code",
            "File Explorer",
        ]
        assert [event.timestamp for event in loaded_events] == sorted(
            event.timestamp for event in loaded_events
        )
        assert loaded_events[0].timestamp == STARTED_AT
        assert loaded_events[-1].timestamp == STOPPED_AT
        assert all(event.source == "active_window" for event in loaded_events)
        assert all(event.type == "active_window_changed" for event in loaded_events)
        assert all(event.privacy_level == "safe" for event in loaded_events)
        assert all(event.confidence == 1 for event in loaded_events)
    finally:
        connection.close()


def test_fake_active_window_events_are_deterministic() -> None:
    first = build_fake_active_window_events(
        session_id=SESSION_ID,
        started_at=STARTED_AT,
        duration_minutes=10,
    )
    second = build_fake_active_window_events(
        session_id=SESSION_ID,
        started_at=STARTED_AT,
        duration_minutes=10,
    )

    assert first == second
    assert [event.id for event in first] == [
        "sess_active_window_001-active-window-000",
        "sess_active_window_001-active-window-001",
        "sess_active_window_001-active-window-002",
        "sess_active_window_001-active-window-003",
        "sess_active_window_001-active-window-004",
    ]
