from __future__ import annotations

import asyncio
import base64
import contextlib
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from worktrace_agent.capture.active_window import (
    ActiveWindowProvider,
    ActiveWindowRecorder,
    WindowsActiveWindowProvider,
)
from worktrace_agent.capture.file_watcher import (
    FileSnapshotProvider,
    FileWatcherWorker,
)
from worktrace_agent.capture.screenshot_capture import (
    ScreenshotCaptureWorker,
    ScreenshotProvider,
    WindowsScreenshotProvider,
)
from worktrace_agent.capture.screenshot_sampler import ScreenshotArtifact, ScreenshotSampler
from worktrace_agent.capture.terminal_command_detector import normalize_terminal_command
from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.ocr_repository import list_ocr_results
from worktrace_agent.db.raw_events_repository import append_raw_event, list_raw_events
from worktrace_agent.db.screenshots_repository import (
    ScreenshotDeletionResult,
    delete_screenshots_for_session,
    list_screenshots,
)
from worktrace_agent.db.session_state_repository import (
    ACTIVE_STATUSES,
    SessionTransitionError,
    delete_session_record,
    interrupt_session,
    list_sessions,
    list_sessions_by_status,
    load_session_record,
    pause_session,
    resume_session,
    start_session,
    stop_session,
)
from worktrace_agent.domain.raw_event import RawEvent
from worktrace_agent.domain.session_state import SessionRecord
from worktrace_agent.exporters.markdown import export_session_markdown
from worktrace_agent.exporters.raw_json import export_redacted_raw_json
from worktrace_agent.privacy.config import PrivacyPolicyConfigService
from worktrace_agent.privacy.policy import PrivacyPolicy
from worktrace_agent.privacy.redaction import redact_text

SESSION_COUNT_QUERIES = {
    "raw_events": """
        SELECT session_id, COUNT(*) AS row_count
        FROM raw_events
        GROUP BY session_id
    """,
    "screenshots": """
        SELECT session_id, COUNT(*) AS row_count
        FROM screenshots
        GROUP BY session_id
    """,
}

EXPORT_PREVIEW_MAX_CHARS = 4_000
SCREENSHOT_PREVIEW_MAX_BYTES = 5 * 1024 * 1024


@dataclass
class RunningRecorder:
    recorder: ActiveWindowRecorder
    task: asyncio.Task[None]


@dataclass(frozen=True)
class SessionExportPreview:
    format: str
    path: Path
    preview: str
    evidence_ids: list[str]


@dataclass(frozen=True)
class SessionFolder:
    path: Path


@dataclass(frozen=True)
class ScreenshotPreview:
    screenshot_id: str
    image_data_url: str
    ocr_snippets: list[str]


@dataclass(frozen=True)
class SessionSummary:
    id: str
    started_at: str
    ended_at: str | None
    status: str
    title: str | None
    goal: str | None
    project_label: str | None
    tags: list[str]
    storage_path: str | None
    privacy_mode: str
    event_count: int
    screenshot_count: int


@dataclass(frozen=True)
class SessionDeletionResult:
    deleted_session_rows: int
    deleted_screenshot_files: int
    missing_screenshot_files: int
    deleted_screenshot_rows: int
    removed_artifact_root: bool


class SessionRecorderService:
    def __init__(
        self,
        *,
        db_path: Path,
        active_window_provider: ActiveWindowProvider | None = None,
        screenshot_provider: ScreenshotProvider | None = None,
        file_snapshot_provider: FileSnapshotProvider | None = None,
        recorder_poll_interval_seconds: float = 1,
        screenshot_interval_seconds: float = 5,
        file_watch_interval_seconds: float = 1,
        privacy_policy_config_service: PrivacyPolicyConfigService | None = None,
    ) -> None:
        self._db_path = Path(db_path)
        self._connection = initialize_database(db_path)
        self._active_window_provider = active_window_provider or WindowsActiveWindowProvider()
        self._screenshot_provider = screenshot_provider or WindowsScreenshotProvider()
        self._file_snapshot_provider = file_snapshot_provider
        self._recorder_poll_interval_seconds = recorder_poll_interval_seconds
        self._screenshot_interval_seconds = screenshot_interval_seconds
        self._file_watch_interval_seconds = file_watch_interval_seconds
        self._privacy_policy_config_service = privacy_policy_config_service
        self._running_recorders: dict[str, RunningRecorder] = {}
        self._running_screenshot_workers: dict[str, RunningScreenshotWorker] = {}
        self._screenshot_samplers: dict[str, ScreenshotSampler] = {}
        self._running_file_watchers: dict[str, RunningFileWatcher] = {}
        self._lock = asyncio.Lock()
        self._mark_stale_active_sessions_interrupted()

    async def start_recording_session(
        self,
        *,
        session_id: str,
        started_at: str,
        title: str | None,
        goal: str | None = None,
        project_label: str | None = None,
        tags: list[str] | None = None,
        storage_path: str | None = None,
        privacy_mode: str = "standard",
        file_watch_roots: list[str] | None = None,
    ) -> SessionRecord:
        async with self._lock:
            await self._interrupt_other_active_sessions(
                next_session_id=session_id,
                occurred_at=started_at,
            )
            session = start_session(
                self._connection,
                session_id=session_id,
                started_at=started_at,
                title=title,
                goal=goal,
                project_label=project_label,
                tags=tags,
                storage_path=storage_path,
                privacy_mode=privacy_mode,
            )
            self._start_workers_for_session(session, file_watch_roots=file_watch_roots)
            return session

    async def pause_recording_session(self, *, session_id: str, paused_at: str) -> SessionRecord:
        async with self._lock:
            session = pause_session(
                self._connection,
                session_id=session_id,
                occurred_at=paused_at,
            )
            await self._stop_workers_for_session(session_id)
            return session

    async def resume_recording_session(
        self,
        *,
        session_id: str,
        resumed_at: str,
        file_watch_roots: list[str] | None = None,
    ) -> SessionRecord:
        async with self._lock:
            session = resume_session(
                self._connection,
                session_id=session_id,
                occurred_at=resumed_at,
            )
            self._start_workers_for_session(session, file_watch_roots=file_watch_roots)
            return session

    async def stop_recording_session(self, *, session_id: str, stopped_at: str) -> SessionRecord:
        async with self._lock:
            await self._stop_workers_for_session(session_id)
            return stop_session(
                self._connection,
                session_id=session_id,
                occurred_at=stopped_at,
            )

    def list_session_events(self, *, session_id: str) -> list[RawEvent]:
        resolved_session_id = self._resolve_session_id(session_id)
        if resolved_session_id is None:
            return []
        return list_raw_events(self._connection, resolved_session_id)

    def list_sessions(self) -> list[SessionSummary]:
        sessions = list_sessions(self._connection)
        event_counts = self._count_rows_by_session("raw_events")
        screenshot_counts = self._count_rows_by_session("screenshots")
        return [
            SessionSummary(
                id=session.id,
                started_at=session.started_at,
                ended_at=session.ended_at,
                status=session.status.value,
                title=session.title,
                goal=session.goal,
                project_label=session.project_label,
                tags=list(session.tags),
                storage_path=session.storage_path,
                privacy_mode=session.privacy_mode,
                event_count=event_counts.get(session.id, 0),
                screenshot_count=screenshot_counts.get(session.id, 0),
            )
            for session in sessions
        ]

    async def _interrupt_other_active_sessions(
        self,
        *,
        next_session_id: str,
        occurred_at: str,
    ) -> None:
        active_sessions = list_sessions_by_status(self._connection, ACTIVE_STATUSES)
        for session in active_sessions:
            if session.id == next_session_id:
                continue
            await self._stop_workers_for_session(session.id)
            interrupt_session(
                self._connection,
                session_id=session.id,
                occurred_at=occurred_at,
            )

    def _mark_stale_active_sessions_interrupted(self) -> None:
        active_sessions = list_sessions_by_status(self._connection, ACTIVE_STATUSES)
        if not active_sessions:
            return
        occurred_at = datetime.now(UTC).isoformat()
        for session in active_sessions:
            interrupt_session(
                self._connection,
                session_id=session.id,
                occurred_at=occurred_at,
            )

    def ingest_terminal_command(
        self,
        *,
        session_id: str,
        timestamp: str,
        command: str,
        shell: str,
        exit_code: int | None,
    ) -> RawEvent:
        event = normalize_terminal_command(
            session_id=session_id,
            timestamp=timestamp,
            command=command,
            shell=shell,  # nosec B604
            exit_code=exit_code,
        )
        append_raw_event(self._connection, event)
        return event

    def list_session_screenshots(self, *, session_id: str) -> list[ScreenshotArtifact]:
        resolved_session_id = self._resolve_session_id(session_id)
        if resolved_session_id is None:
            return []
        return list_screenshots(self._connection, resolved_session_id)

    def screenshot_preview(self, *, session_id: str, screenshot_id: str) -> ScreenshotPreview:
        resolved_session_id = self._require_session_id(session_id)
        screenshot = next(
            (
                candidate
                for candidate in list_screenshots(self._connection, resolved_session_id)
                if candidate.id == screenshot_id
            ),
            None,
        )
        if screenshot is None:
            raise ValueError(f"Screenshot not found: {screenshot_id}")

        artifact_root = self._artifact_root_for_session_id(resolved_session_id)
        path = _resolve_artifact_path(
            artifact_root=artifact_root,
            storage_path=screenshot.storage_path,
        )
        if not path.is_file():
            raise ValueError("Screenshot artifact file is missing")
        if path.stat().st_size > SCREENSHOT_PREVIEW_MAX_BYTES:
            raise ValueError("Screenshot artifact is too large to preview")

        image_data_url = "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode(
            "ascii"
        )
        ocr_snippets = [
            _ocr_snippet(result.text)
            for result in list_ocr_results(self._connection, resolved_session_id)
            if result.screenshot_id == screenshot.id
        ]
        return ScreenshotPreview(
            screenshot_id=screenshot.id,
            image_data_url=image_data_url,
            ocr_snippets=ocr_snippets,
        )

    def delete_session_screenshots(self, *, session_id: str) -> ScreenshotDeletionResult:
        resolved_session_id = self._resolve_session_id(session_id)
        if resolved_session_id is None:
            return ScreenshotDeletionResult(deleted_files=0, missing_files=0, deleted_rows=0)
        return delete_screenshots_for_session(
            self._connection,
            session_id=resolved_session_id,
            artifact_root=self._artifact_root_for_session_id(resolved_session_id),
        )

    def export_session_markdown_preview(self, *, session_id: str) -> SessionExportPreview:
        resolved_session_id = self._require_session_id(session_id)
        export_path = (
            self._artifact_root_for_session_id(resolved_session_id) / "exports" / "session.md"
        )
        written_path = export_session_markdown(
            self._connection,
            resolved_session_id,
            export_path,
        )
        return SessionExportPreview(
            format="markdown",
            path=written_path,
            preview=_preview_text(written_path),
            evidence_ids=self._evidence_ids_for_session(resolved_session_id),
        )

    def export_session_raw_json_preview(self, *, session_id: str) -> SessionExportPreview:
        resolved_session_id = self._require_session_id(session_id)
        export_path = (
            self._artifact_root_for_session_id(resolved_session_id) / "exports" / "session.raw.json"
        )
        written_path = export_redacted_raw_json(
            self._connection,
            resolved_session_id,
            export_path,
        )
        return SessionExportPreview(
            format="raw_json",
            path=written_path,
            preview=_preview_text(written_path),
            evidence_ids=self._evidence_ids_for_session(resolved_session_id),
        )

    def session_folder(self, *, session_id: str) -> SessionFolder:
        resolved_session_id = self._require_session_id(session_id)
        return SessionFolder(path=self._artifact_root_for_session_id(resolved_session_id))

    async def delete_session(self, *, session_id: str) -> SessionDeletionResult:
        resolved_session_id = self._require_session_id(session_id)
        await self._stop_workers_for_session(resolved_session_id)
        session = load_session_record(self._connection, resolved_session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")

        screenshot_result = delete_screenshots_for_session(
            self._connection,
            session_id=resolved_session_id,
            artifact_root=self._artifact_root_for_session(session),
        )
        deleted_rows = delete_session_record(self._connection, session_id=resolved_session_id)
        removed_artifact_root = self._remove_default_artifact_root_for_session_id(
            resolved_session_id,
            session,
        )

        return SessionDeletionResult(
            deleted_session_rows=deleted_rows,
            deleted_screenshot_files=screenshot_result.deleted_files,
            missing_screenshot_files=screenshot_result.missing_files,
            deleted_screenshot_rows=screenshot_result.deleted_rows,
            removed_artifact_root=removed_artifact_root,
        )

    def close(self) -> None:
        self._connection.close()

    def _resolve_session_id(self, session_id: str) -> str | None:
        if session_id != "latest":
            return session_id

        row = self._connection.execute(
            """
            SELECT id
            FROM sessions
            ORDER BY started_at DESC, created_at DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return None
        return str(row["id"])

    def _require_session_id(self, session_id: str) -> str:
        resolved_session_id = self._resolve_session_id(session_id)
        if resolved_session_id is None or not self._session_exists(resolved_session_id):
            raise ValueError(f"Unknown session: {session_id}")
        return resolved_session_id

    def _session_exists(self, session_id: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        return row is not None

    def _evidence_ids_for_session(self, session_id: str) -> list[str]:
        return [event.id for event in list_raw_events(self._connection, session_id)]

    def _count_rows_by_session(self, table_name: str) -> dict[str, int]:
        query = SESSION_COUNT_QUERIES.get(table_name)
        if query is None:
            raise ValueError("Unsupported session count table")
        rows = self._connection.execute(query).fetchall()
        return {str(row["session_id"]): int(row["row_count"]) for row in rows}

    def _active_process_name(self) -> str | None:
        try:
            snapshot = self._active_window_provider.get_active_window()
        except Exception:
            return None
        if snapshot is None:
            return None
        return snapshot.process_name

    def _start_workers_for_session(
        self,
        session: SessionRecord,
        *,
        file_watch_roots: list[str] | None,
    ) -> None:
        session_id = session.id
        privacy_policy = self._privacy_policy_for_session(session)
        if session_id not in self._running_recorders:
            recorder = ActiveWindowRecorder(
                connection=self._connection,
                session_id=session_id,
                provider=self._active_window_provider,
                privacy_policy=privacy_policy,
                poll_interval_seconds=self._recorder_poll_interval_seconds,
            )
            recorder.poll_once()
            self._running_recorders[session_id] = RunningRecorder(
                recorder=recorder,
                task=asyncio.create_task(recorder.run()),
            )
        if session_id not in self._running_screenshot_workers:
            screenshot_worker = ScreenshotCaptureWorker(
                connection=self._connection,
                session_id=session_id,
                artifact_root=self._artifact_root_for_session(session),
                provider=self._screenshot_provider,
                sampler=self._screenshot_samplers.setdefault(session_id, ScreenshotSampler()),
                privacy_policy=privacy_policy,
                interval_seconds=self._screenshot_interval_seconds,
            )
            active_process_name = self._active_process_name()
            screenshot_worker.poll_once(active_process_name=active_process_name)
            self._running_screenshot_workers[session_id] = RunningScreenshotWorker(
                worker=screenshot_worker,
                task=asyncio.create_task(
                    screenshot_worker.run(
                        active_process_name_provider=self._active_process_name,
                    )
                ),
            )
        roots = [Path(root) for root in file_watch_roots or [] if root.strip()]
        if roots and session_id not in self._running_file_watchers:
            file_watcher = FileWatcherWorker(
                connection=self._connection,
                session_id=session_id,
                roots=roots,
                provider=self._file_snapshot_provider,
                privacy_policy=privacy_policy,
                interval_seconds=self._file_watch_interval_seconds,
            )
            file_watcher.poll_once()
            self._running_file_watchers[session_id] = RunningFileWatcher(
                worker=file_watcher,
                task=asyncio.create_task(file_watcher.run()),
            )

    async def _stop_workers_for_session(self, session_id: str) -> None:
        running_file_watcher = self._running_file_watchers.pop(session_id, None)
        if running_file_watcher is not None:
            await running_file_watcher.worker.stop()
            with contextlib.suppress(asyncio.CancelledError):
                await running_file_watcher.task

        running_screenshots = self._running_screenshot_workers.pop(session_id, None)
        if running_screenshots is not None:
            await running_screenshots.worker.stop()
            with contextlib.suppress(asyncio.CancelledError):
                await running_screenshots.task

        running = self._running_recorders.pop(session_id, None)
        if running is not None:
            await running.recorder.stop()
            with contextlib.suppress(asyncio.CancelledError):
                await running.task

    def _privacy_policy_for_session(self, session: SessionRecord) -> PrivacyPolicy:
        if self._privacy_policy_config_service is None:
            return PrivacyPolicy(private_mode=session.privacy_mode == "private")
        config = self._privacy_policy_config_service.load()
        return PrivacyPolicy(
            allowlist=config.allowlist,
            blocklist=config.blocklist,
            private_mode=session.privacy_mode == "private",
            clipboard_safe_mode=config.clipboard_safe_mode,
        )

    def _artifact_root_for_session(self, session: SessionRecord) -> Path:
        if session.storage_path:
            return Path(session.storage_path)
        return self._artifact_root_for_session_id(session.id)

    def _artifact_root_for_session_id(self, session_id: str) -> Path:
        base = self._db_path.parent
        if base.name == "db":
            base = base.parent
        return base / "sessions" / session_id

    def _remove_default_artifact_root_for_session_id(
        self,
        session_id: str,
        session: SessionRecord,
    ) -> bool:
        default_root = self._artifact_root_for_session_id(session_id)
        if session.storage_path is not None and Path(session.storage_path) != default_root:
            return False
        if not default_root.exists():
            return False

        resolved_root = default_root.resolve()
        resolved_sessions_root = default_root.parent.resolve()
        if resolved_root.parent != resolved_sessions_root or resolved_root.name != session_id:
            raise ValueError("session artifact root is outside the managed sessions directory")
        if not resolved_root.is_dir():
            raise ValueError("session artifact root is not a directory")

        shutil.rmtree(resolved_root)
        return True


@dataclass
class RunningScreenshotWorker:
    worker: ScreenshotCaptureWorker
    task: asyncio.Task[None]


@dataclass
class RunningFileWatcher:
    worker: FileWatcherWorker
    task: asyncio.Task[None]


def _preview_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if len(text) <= EXPORT_PREVIEW_MAX_CHARS:
        return text
    return f"{text[:EXPORT_PREVIEW_MAX_CHARS]}\n..."


def _resolve_artifact_path(*, artifact_root: Path, storage_path: str) -> Path:
    resolved_root = artifact_root.resolve()
    target = (resolved_root / storage_path).resolve()
    try:
        target.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError("screenshot artifact path is outside artifact root") from error
    return target


def _ocr_snippet(text: str) -> str:
    redacted = redact_text(text, redact_contact_info=True).strip()
    if len(redacted) <= 280:
        return redacted
    return f"{redacted[:280]}..."


def map_session_error(error: SessionTransitionError) -> tuple[int, str]:
    return 409, str(error)


def is_sqlite_missing_session_error(error: sqlite3.Error) -> bool:
    return "FOREIGN KEY constraint failed" in str(error)
