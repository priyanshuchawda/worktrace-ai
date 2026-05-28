from __future__ import annotations

import asyncio
import ctypes
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, cast
from uuid import uuid4

from worktrace_agent.db.raw_events_repository import append_raw_event, append_raw_events
from worktrace_agent.domain.raw_event import RawEvent, build_raw_event
from worktrace_agent.privacy.policy import PrivacyPolicy
from worktrace_agent.privacy.redaction import REDACTION_TOKEN, redact_text

ACTIVE_WINDOW_SOURCE = "active_window"
ACTIVE_WINDOW_CHANGED_TYPE = "active_window_changed"
WINDOWS_API_CONFIDENCE = 0.98
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MAX_PROCESS_IMAGE_PATH = 32_768


@dataclass(frozen=True)
class ActiveWindowSnapshot:
    app: str
    window_title: str
    process_name: str
    timestamp: str
    confidence: float


class ActiveWindowProvider(Protocol):
    def get_active_window(self) -> ActiveWindowSnapshot | None:
        pass


class WindowsActiveWindowProvider:
    def get_active_window(self) -> ActiveWindowSnapshot | None:
        if os.name != "nt":
            return None

        user32 = cast(Any, ctypes.WinDLL("user32", use_last_error=True))
        kernel32 = cast(Any, ctypes.WinDLL("kernel32", use_last_error=True))

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

        title = _get_window_title(user32, hwnd)
        process_id = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        process_name = _get_process_name(kernel32, process_id.value)
        app = Path(process_name).stem or process_name

        return ActiveWindowSnapshot(
            app=app,
            window_title=title,
            process_name=process_name,
            timestamp=datetime.now(UTC).astimezone().isoformat(),
            confidence=WINDOWS_API_CONFIDENCE,
        )


class ActiveWindowRecorder:
    def __init__(
        self,
        *,
        connection: sqlite3.Connection,
        session_id: str,
        provider: ActiveWindowProvider,
        privacy_policy: PrivacyPolicy | None = None,
        poll_interval_seconds: float = 1,
    ) -> None:
        self._connection = connection
        self._session_id = session_id
        self._provider = provider
        self._privacy_policy = privacy_policy or PrivacyPolicy()
        self._poll_interval_seconds = poll_interval_seconds
        self._last_identity: tuple[str, str, str] | None = None
        self._stop_event = asyncio.Event()
        self.last_error: str | None = None

    def poll_once(self) -> RawEvent | None:
        try:
            snapshot = self._provider.get_active_window()
        except Exception:
            self.last_error = "active_window_provider_error"
            return None

        if snapshot is None:
            return None

        if not self._privacy_policy.should_capture_source(ACTIVE_WINDOW_SOURCE):
            return None
        if not self._privacy_policy.should_capture_app_identity(
            app_name=snapshot.app,
            process_name=snapshot.process_name,
        ):
            return None

        event = self._event_from_snapshot(snapshot)
        identity = _event_identity(event)
        if identity == self._last_identity:
            return None

        append_raw_event(self._connection, event)
        self._last_identity = identity
        self.last_error = None
        return event

    async def run(self) -> None:
        while not self._stop_event.is_set():
            self.poll_once()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._poll_interval_seconds,
                )
            except TimeoutError:
                continue

    async def stop(self) -> None:
        self._stop_event.set()
        await asyncio.sleep(0)

    def _event_from_snapshot(self, snapshot: ActiveWindowSnapshot) -> RawEvent:
        title = redact_text(snapshot.window_title)
        app = redact_text(snapshot.app)
        process_name = redact_text(snapshot.process_name)
        privacy_level = "redacted" if REDACTION_TOKEN in f"{title} {app} {process_name}" else "safe"

        return build_raw_event(
            event_id=f"{self._session_id}-active-window-{uuid4().hex[:12]}",
            session_id=self._session_id,
            timestamp=snapshot.timestamp,
            source=ACTIVE_WINDOW_SOURCE,
            event_type=ACTIVE_WINDOW_CHANGED_TYPE,
            privacy_level=privacy_level,
            confidence=snapshot.confidence,
            metadata={
                "app": app,
                "window_title": title,
                "process_name": process_name,
            },
        )


@dataclass(frozen=True)
class ActiveWindowFixture:
    offset_ratio: float
    app: str
    window_title: str
    process_name: str


ACTIVE_WINDOW_FIXTURE: tuple[ActiveWindowFixture, ...] = (
    ActiveWindowFixture(
        offset_ratio=0,
        app="VS Code",
        window_title="workaudit-ai - App.tsx",
        process_name="Code.exe",
    ),
    ActiveWindowFixture(
        offset_ratio=0.2,
        app="Chrome",
        window_title="Issue #9 - GitHub",
        process_name="chrome.exe",
    ),
    ActiveWindowFixture(
        offset_ratio=0.5,
        app="Windows Terminal",
        window_title="uv run --python 3.13 pytest",
        process_name="WindowsTerminal.exe",
    ),
    ActiveWindowFixture(
        offset_ratio=0.8,
        app="VS Code",
        window_title="raw_events_repository.py",
        process_name="Code.exe",
    ),
    ActiveWindowFixture(
        offset_ratio=1,
        app="File Explorer",
        window_title="worktrace session folder",
        process_name="explorer.exe",
    ),
)


def build_fake_active_window_events(
    *,
    session_id: str,
    started_at: str,
    duration_minutes: int,
) -> list[RawEvent]:
    start = _parse_offset_datetime(started_at)
    duration = timedelta(minutes=duration_minutes)

    return [
        build_raw_event(
            event_id=f"{session_id}-active-window-{index:03d}",
            session_id=session_id,
            timestamp=(start + (duration * fixture.offset_ratio)).isoformat(),
            source="active_window",
            event_type="active_window_changed",
            privacy_level="safe",
            confidence=1,
            metadata={
                "app": fixture.app,
                "window_title": fixture.window_title,
                "process_name": fixture.process_name,
            },
        )
        for index, fixture in enumerate(ACTIVE_WINDOW_FIXTURE)
    ]


def save_fake_active_window_recording(
    connection: sqlite3.Connection,
    *,
    session_id: str,
    started_at: str,
    duration_minutes: int,
) -> list[RawEvent]:
    events = build_fake_active_window_events(
        session_id=session_id,
        started_at=started_at,
        duration_minutes=duration_minutes,
    )
    append_raw_events(connection, events)
    return events


def _parse_offset_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("started_at must include a timezone offset")
    return parsed


def _event_identity(event: RawEvent) -> tuple[str, str, str]:
    return (
        str(event.metadata.get("app", "")),
        str(event.metadata.get("window_title", "")),
        str(event.metadata.get("process_name", "")),
    )


def _get_window_title(user32: Any, hwnd: int) -> str:
    title_length = int(user32.GetWindowTextLengthW(hwnd))
    buffer = ctypes.create_unicode_buffer(title_length + 1)
    user32.GetWindowTextW(hwnd, buffer, title_length + 1)
    return str(buffer.value)


def _get_process_name(kernel32: Any, process_id: int) -> str:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id)
    if not handle:
        return "unknown.exe"

    try:
        buffer = ctypes.create_unicode_buffer(MAX_PROCESS_IMAGE_PATH)
        size = ctypes.c_ulong(MAX_PROCESS_IMAGE_PATH)
        succeeded = kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size))
        if not succeeded:
            return "unknown.exe"
        return Path(str(buffer.value)).name or "unknown.exe"
    finally:
        kernel32.CloseHandle(handle)
