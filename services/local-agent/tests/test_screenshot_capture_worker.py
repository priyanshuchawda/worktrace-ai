from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from worktrace_agent.capture.screenshot_capture import (
    ScreenshotCaptureWorker,
    ScreenshotProvider,
)
from worktrace_agent.capture.screenshot_sampler import ScreenshotFrame
from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.raw_events_repository import append_raw_event
from worktrace_agent.db.screenshots_repository import list_screenshots
from worktrace_agent.db.session_state_repository import start_session
from worktrace_agent.domain.raw_event import build_raw_event
from worktrace_agent.privacy.policy import PrivacyPolicy

SESSION_ID = "sess_real_screenshot_001"
STARTED_AT = "2026-05-07T09:14:00+05:30"
SECOND_FRAME_AT = "2026-05-07T09:14:05+05:30"


class StaticScreenshotProvider(ScreenshotProvider):
    def __init__(self, frames: list[ScreenshotFrame]) -> None:
        self.frames = frames
        self.calls = 0

    def capture_frame(self, *, session_id: str, timestamp: str) -> ScreenshotFrame | None:
        self.calls += 1
        if not self.frames:
            return None
        frame = self.frames.pop(0)
        return ScreenshotFrame(
            session_id=session_id,
            timestamp=timestamp,
            width=frame.width,
            height=frame.height,
            rgb_bytes=frame.rgb_bytes,
        )


def frame(*, width: int, height: int, value: int) -> ScreenshotFrame:
    return ScreenshotFrame(
        session_id=SESSION_ID,
        timestamp=STARTED_AT,
        width=width,
        height=height,
        rgb_bytes=bytes([value, value, value]) * width * height,
    )


def save_active_window_event(connection: sqlite3.Connection) -> str:
    event = build_raw_event(
        event_id="evt_active_window_001",
        session_id=SESSION_ID,
        timestamp=STARTED_AT,
        source="active_window",
        event_type="active_window_changed",
        privacy_level="safe",
        confidence=0.98,
        metadata={
            "app": "VS Code",
            "window_title": "screen-ai - Visual Studio Code",
            "process_name": "Code.exe",
        },
    )
    append_raw_event(connection, event)
    return event.id


def test_capture_worker_writes_downscaled_artifact_and_metadata(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    artifact_root = tmp_path / "session-artifacts"
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        source_event_id = save_active_window_event(connection)
        worker = ScreenshotCaptureWorker(
            connection=connection,
            session_id=SESSION_ID,
            artifact_root=artifact_root,
            provider=StaticScreenshotProvider([frame(width=2560, height=1440, value=90)]),
        )

        artifact = worker.poll_once(timestamp=STARTED_AT, active_process_name="Code.exe")

        screenshots = list_screenshots(connection, SESSION_ID)
        assert artifact is not None
        assert screenshots == [artifact]
        assert artifact.source_event_id == source_event_id
        assert artifact.stored_width == 1280
        assert artifact.stored_height == 720
        written = artifact_root / artifact.storage_path
        assert written.exists()
        assert written.suffix == ".png"
        assert written.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert artifact.byte_size == written.stat().st_size
        assert artifact.byte_size < 1280 * 720 * 3
    finally:
        connection.close()


def test_capture_worker_skips_duplicate_frame_without_writing(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    artifact_root = tmp_path / "session-artifacts"
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        provider = StaticScreenshotProvider(
            [
                frame(width=8, height=8, value=40),
                frame(width=8, height=8, value=40),
            ]
        )
        worker = ScreenshotCaptureWorker(
            connection=connection,
            session_id=SESSION_ID,
            artifact_root=artifact_root,
            provider=provider,
        )

        first = worker.poll_once(timestamp=STARTED_AT, active_process_name="Code.exe")
        second = worker.poll_once(timestamp=SECOND_FRAME_AT, active_process_name="Code.exe")

        assert first is not None
        assert second is None
        assert len(list_screenshots(connection, SESSION_ID)) == 1
        assert len(list((artifact_root / "screenshots").glob("*.png"))) == 1
    finally:
        connection.close()


def test_capture_worker_degrades_safely_when_artifact_write_fails(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    artifact_root = tmp_path / "session-artifacts"
    artifact_root.write_text("not a directory", encoding="utf-8")
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        worker = ScreenshotCaptureWorker(
            connection=connection,
            session_id=SESSION_ID,
            artifact_root=artifact_root,
            provider=StaticScreenshotProvider([frame(width=8, height=8, value=40)]),
        )

        artifact = worker.poll_once(timestamp=STARTED_AT, active_process_name="Code.exe")

        assert artifact is None
        assert worker.last_error == "screenshot_storage_error"
        assert list_screenshots(connection, SESSION_ID) == []
    finally:
        connection.close()


def test_capture_worker_respects_private_mode_and_blocklist(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    artifact_root = tmp_path / "session-artifacts"
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        private_worker = ScreenshotCaptureWorker(
            connection=connection,
            session_id=SESSION_ID,
            artifact_root=artifact_root,
            provider=StaticScreenshotProvider([frame(width=8, height=8, value=40)]),
            privacy_policy=PrivacyPolicy(private_mode=True),
        )
        blocklisted_worker = ScreenshotCaptureWorker(
            connection=connection,
            session_id=SESSION_ID,
            artifact_root=artifact_root,
            provider=StaticScreenshotProvider([frame(width=8, height=8, value=80)]),
            privacy_policy=PrivacyPolicy(blocklist=("Code.exe",)),
        )

        assert (
            private_worker.poll_once(timestamp=STARTED_AT, active_process_name="Code.exe") is None
        )
        assert (
            blocklisted_worker.poll_once(timestamp=STARTED_AT, active_process_name="Code.exe")
            is None
        )
        assert list_screenshots(connection, SESSION_ID) == []
    finally:
        connection.close()


def test_capture_worker_stops_cleanly(tmp_path: Path) -> None:
    async def run_worker() -> None:
        connection = initialize_database(tmp_path / "worktrace.sqlite")
        try:
            start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
            worker = ScreenshotCaptureWorker(
                connection=connection,
                session_id=SESSION_ID,
                artifact_root=tmp_path / "session-artifacts",
                provider=StaticScreenshotProvider([frame(width=8, height=8, value=40)]),
                interval_seconds=0.01,
            )

            task = asyncio.create_task(worker.run(active_process_name="Code.exe"))
            while worker.poll_count < 1:
                await asyncio.sleep(0)
            await worker.stop()
            await task

            assert len(list_screenshots(connection, SESSION_ID)) == 1
        finally:
            connection.close()

    asyncio.run(run_worker())
