from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path

from worktrace_agent.capture.file_watcher import (
    FileSnapshot,
    FileWatcherWorker,
    normalize_file_event,
)
from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.raw_events_repository import list_raw_events
from worktrace_agent.db.session_state_repository import start_session

SESSION_ID = "sess_file_watcher_001"
STARTED_AT = "2026-05-07T09:14:00+05:30"
SECOND_POLL_AT = "2026-05-07T09:14:05+05:30"


class SequenceFileSnapshotProvider:
    def __init__(self, snapshots: Sequence[Sequence[FileSnapshot] | Exception]) -> None:
        self._snapshots = list(snapshots)
        self.calls = 0

    def snapshot(self, roots: Sequence[Path]) -> list[FileSnapshot]:
        self.calls += 1
        next_value = self._snapshots.pop(0)
        if isinstance(next_value, Exception):
            raise next_value
        return list(next_value)


def file_snapshot(path: Path, *, size: int = 10, modified_ns: int = 100) -> FileSnapshot:
    return FileSnapshot(path=path, size=size, modified_ns=modified_ns)


def test_file_watcher_persists_created_modified_deleted_and_renamed_events(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    old_path = root / "src" / "old.py"
    renamed_path = root / "src" / "new.py"
    created_path = root / "src" / "created.py"
    modified_path = root / "src" / "modified.py"
    deleted_path = root / "src" / "deleted.py"
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        worker = FileWatcherWorker(
            connection=connection,
            session_id=SESSION_ID,
            roots=(root,),
            provider=SequenceFileSnapshotProvider(
                [
                    [
                        file_snapshot(old_path, size=12, modified_ns=10),
                        file_snapshot(modified_path, size=20, modified_ns=20),
                        file_snapshot(deleted_path, size=30, modified_ns=30),
                    ],
                    [
                        file_snapshot(renamed_path, size=12, modified_ns=10),
                        file_snapshot(modified_path, size=25, modified_ns=25),
                        file_snapshot(created_path, size=40, modified_ns=40),
                    ],
                ]
            ),
        )

        assert worker.poll_once(timestamp=STARTED_AT) == []
        emitted = worker.poll_once(timestamp=SECOND_POLL_AT)

        events = list_raw_events(connection, SESSION_ID)
        operations = [event.metadata["operation"] for event in emitted]
        assert operations == ["renamed", "created", "modified", "deleted"]
        assert {event.id for event in events} == {event.id for event in emitted}
        renamed = emitted[0]
        assert str(renamed.metadata["path"]).endswith("src/new.py")
        assert str(renamed.metadata["previous_path"]).endswith("src/old.py")
    finally:
        connection.close()


def test_file_watcher_ignores_noisy_folders(tmp_path: Path) -> None:
    root = tmp_path / "project"
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        worker = FileWatcherWorker(
            connection=connection,
            session_id=SESSION_ID,
            roots=(root,),
            provider=SequenceFileSnapshotProvider(
                [
                    [],
                    [
                        file_snapshot(root / "node_modules" / "pkg" / "index.js"),
                        file_snapshot(root / ".git" / "index"),
                        file_snapshot(root / "src" / "app.py"),
                    ],
                ]
            ),
        )

        worker.poll_once(timestamp=STARTED_AT)
        emitted = worker.poll_once(timestamp=SECOND_POLL_AT)

        assert len(emitted) == 1
        assert str(emitted[0].metadata["path"]).endswith("src/app.py")
        assert len(list_raw_events(connection, SESSION_ID)) == 1
    finally:
        connection.close()


def test_sensitive_file_paths_are_marked_without_storing_raw_sensitive_name() -> None:
    event = normalize_file_event(
        session_id=SESSION_ID,
        timestamp=STARTED_AT,
        path=r"C:\Users\Admin\Desktop\screen-ai\.env",
        operation="created",
    )

    assert event.privacy_level == "sensitive"
    assert event.metadata["file_name"] == "[REDACTED]"
    assert event.metadata["path"] == "C:/Users/Admin/Desktop/screen-ai/[REDACTED]"
    assert ".env" not in str(event.metadata)


def test_file_watcher_provider_error_does_not_corrupt_session(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        worker = FileWatcherWorker(
            connection=connection,
            session_id=SESSION_ID,
            roots=(tmp_path / "project",),
            provider=SequenceFileSnapshotProvider([RuntimeError("watch unavailable")]),
        )

        assert worker.poll_once(timestamp=STARTED_AT) == []
        assert worker.last_error == "file_watcher_provider_error"
        assert list_raw_events(connection, SESSION_ID) == []
        row = connection.execute(
            "SELECT status FROM sessions WHERE id = ?", (SESSION_ID,)
        ).fetchone()
        assert row["status"] == "recording"
    finally:
        connection.close()


def test_file_watcher_worker_stops_cleanly(tmp_path: Path) -> None:
    async def run_worker() -> None:
        connection = initialize_database(tmp_path / "worktrace.sqlite")
        try:
            start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
            provider = SequenceFileSnapshotProvider(
                [
                    [],
                    [file_snapshot(tmp_path / "project" / "src" / "app.py")],
                ]
            )
            worker = FileWatcherWorker(
                connection=connection,
                session_id=SESSION_ID,
                roots=(tmp_path / "project",),
                provider=provider,
                interval_seconds=0.01,
            )

            task = asyncio.create_task(worker.run())
            while provider.calls < 2:
                await asyncio.sleep(0)
            await worker.stop()
            await task

            assert len(list_raw_events(connection, SESSION_ID)) == 1
        finally:
            connection.close()

    asyncio.run(run_worker())
