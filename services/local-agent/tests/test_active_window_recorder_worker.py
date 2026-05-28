from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path

from worktrace_agent.capture.active_window import (
    ActiveWindowRecorder,
    ActiveWindowSnapshot,
)
from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.raw_events_repository import list_raw_events
from worktrace_agent.db.session_state_repository import start_session, stop_session
from worktrace_agent.privacy.policy import PrivacyPolicy
from worktrace_agent.privacy.redaction import PRIVACY_TEST_CORPUS, REDACTION_TOKEN

SESSION_ID = "sess_live_window_001"
STARTED_AT = "2026-05-06T09:14:00+05:30"
STOPPED_AT = "2026-05-06T09:16:00+05:30"


class SequenceActiveWindowProvider:
    def __init__(self, snapshots: Sequence[ActiveWindowSnapshot | Exception]) -> None:
        self._snapshots = list(snapshots)
        self.calls = 0

    def get_active_window(self) -> ActiveWindowSnapshot | None:
        self.calls += 1
        next_value = self._snapshots.pop(0)
        if isinstance(next_value, Exception):
            raise next_value
        return next_value


def snapshot(
    *,
    app: str = "VS Code",
    title: str = "workaudit-ai - App.tsx",
    process: str = "Code.exe",
    timestamp: str = STARTED_AT,
) -> ActiveWindowSnapshot:
    return ActiveWindowSnapshot(
        app=app,
        window_title=title,
        process_name=process,
        timestamp=timestamp,
        confidence=0.98,
    )


def test_fake_provider_emits_first_event(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        recorder = ActiveWindowRecorder(
            connection=connection,
            session_id=SESSION_ID,
            provider=SequenceActiveWindowProvider([snapshot()]),
        )

        saved = recorder.poll_once()

        events = list_raw_events(connection, SESSION_ID)
        assert saved is not None
        assert events == [saved]
        assert events[0].type == "active_window_changed"
        assert events[0].metadata["app"] == "VS Code"
        assert events[0].metadata["window_title"] == "workaudit-ai - App.tsx"
        assert events[0].metadata["process_name"] == "Code.exe"
    finally:
        connection.close()


def test_duplicate_active_window_is_skipped(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        recorder = ActiveWindowRecorder(
            connection=connection,
            session_id=SESSION_ID,
            provider=SequenceActiveWindowProvider([snapshot(), snapshot()]),
        )

        first = recorder.poll_once()
        second = recorder.poll_once()

        assert first is not None
        assert second is None
        assert len(list_raw_events(connection, SESSION_ID)) == 1
    finally:
        connection.close()


def test_changed_active_window_is_persisted(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        recorder = ActiveWindowRecorder(
            connection=connection,
            session_id=SESSION_ID,
            provider=SequenceActiveWindowProvider(
                [
                    snapshot(),
                    snapshot(
                        app="Chrome",
                        title=f"Issue #51 {PRIVACY_TEST_CORPUS[1]}",
                        process="chrome.exe",
                        timestamp="2026-05-06T09:15:00+05:30",
                    ),
                ]
            ),
        )

        recorder.poll_once()
        recorder.poll_once()

        events = list_raw_events(connection, SESSION_ID)
        assert len(events) == 2
        assert events[1].metadata["app"] == "Chrome"
        assert events[1].metadata["window_title"] == f"Issue #51 {REDACTION_TOKEN}"
    finally:
        connection.close()


def test_provider_error_does_not_corrupt_session(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        session = start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        recorder = ActiveWindowRecorder(
            connection=connection,
            session_id=SESSION_ID,
            provider=SequenceActiveWindowProvider([RuntimeError("Windows API unavailable")]),
        )

        saved = recorder.poll_once()

        row = connection.execute(
            "SELECT status FROM sessions WHERE id = ?", (SESSION_ID,)
        ).fetchone()
        assert saved is None
        assert recorder.last_error == "active_window_provider_error"
        assert row["status"] == session.status.value
        assert list_raw_events(connection, SESSION_ID) == []
    finally:
        connection.close()


def test_active_window_recorder_respects_private_mode_and_blocklist(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        private_recorder = ActiveWindowRecorder(
            connection=connection,
            session_id=SESSION_ID,
            provider=SequenceActiveWindowProvider([snapshot(app="VS Code", process="Code.exe")]),
            privacy_policy=PrivacyPolicy(private_mode=True),
        )
        blocklisted_recorder = ActiveWindowRecorder(
            connection=connection,
            session_id=SESSION_ID,
            provider=SequenceActiveWindowProvider([snapshot(app="Chrome", process="chrome.exe")]),
            privacy_policy=PrivacyPolicy(blocklist=("chrome.exe",)),
        )

        assert private_recorder.poll_once() is None
        assert blocklisted_recorder.poll_once() is None
        assert list_raw_events(connection, SESSION_ID) == []
    finally:
        connection.close()


def test_worker_stops_cleanly_and_session_stop_flushes_events(tmp_path: Path) -> None:
    async def run_worker() -> None:
        connection = initialize_database(tmp_path / "worktrace.sqlite")
        try:
            start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
            provider = SequenceActiveWindowProvider(
                [
                    snapshot(),
                    snapshot(
                        app="Chrome",
                        title="Issue #51",
                        process="chrome.exe",
                        timestamp="2026-05-06T09:15:00+05:30",
                    ),
                ]
            )
            recorder = ActiveWindowRecorder(
                connection=connection,
                session_id=SESSION_ID,
                provider=provider,
                poll_interval_seconds=0.01,
            )

            task = asyncio.create_task(recorder.run())
            while provider.calls < 2:
                await asyncio.sleep(0)

            await recorder.stop()
            await task
            stop_session(connection, session_id=SESSION_ID, occurred_at=STOPPED_AT)

            assert len(list_raw_events(connection, SESSION_ID)) == 2
            row = connection.execute(
                "SELECT status, ended_at FROM sessions WHERE id = ?",
                (SESSION_ID,),
            ).fetchone()
            assert row["status"] == "stopped"
            assert row["ended_at"] == STOPPED_AT
        finally:
            connection.close()

    asyncio.run(run_worker())
