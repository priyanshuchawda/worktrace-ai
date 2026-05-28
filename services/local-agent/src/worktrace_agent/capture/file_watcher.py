from __future__ import annotations

import asyncio
import hashlib
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import Final, Protocol

from worktrace_agent.db.raw_events_repository import append_raw_events
from worktrace_agent.domain.raw_event import RawEvent, build_raw_event
from worktrace_agent.privacy.policy import PrivacyPolicy

FILE_OPERATIONS: Final = {"created", "modified", "deleted", "renamed"}
SENSITIVE_FILE_NAMES: Final = {".env", ".env.local", ".env.production", ".npmrc", ".pypirc"}
SENSITIVE_SUFFIXES: Final = {".key", ".pem", ".p12", ".pfx"}
SENSITIVE_NAME_PARTS: Final = ("secret", "password", "token", "credential")
IGNORED_PATH_PARTS: Final = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
    "venv",
}
REDACTED_FILE_NAME: Final = "[REDACTED]"


@dataclass(frozen=True)
class FileSnapshot:
    path: Path
    size: int
    modified_ns: int


class FileSnapshotProvider(Protocol):
    def snapshot(self, roots: Sequence[Path]) -> list[FileSnapshot]: ...


class PollingFileSnapshotProvider:
    def snapshot(self, roots: Sequence[Path]) -> list[FileSnapshot]:
        snapshots: list[FileSnapshot] = []
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if _path_has_ignored_part(path):
                    continue
                if not path.is_file():
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue
                snapshots.append(
                    FileSnapshot(
                        path=path,
                        size=stat.st_size,
                        modified_ns=stat.st_mtime_ns,
                    )
                )
        return snapshots


class FileWatcherWorker:
    def __init__(
        self,
        *,
        connection: sqlite3.Connection,
        session_id: str,
        roots: Sequence[Path],
        provider: FileSnapshotProvider | None = None,
        privacy_policy: PrivacyPolicy | None = None,
        interval_seconds: float = 1,
    ) -> None:
        self._connection = connection
        self._session_id = session_id
        self._roots = tuple(Path(root) for root in roots)
        self._provider = provider or PollingFileSnapshotProvider()
        self._privacy_policy = privacy_policy or PrivacyPolicy()
        self._interval_seconds = interval_seconds
        self._previous: dict[str, FileSnapshot] | None = None
        self._stop_event = asyncio.Event()
        self.last_error: str | None = None

    def poll_once(self, *, timestamp: str | None = None) -> list[RawEvent]:
        if not self._privacy_policy.should_capture_source("file_watcher"):
            return []

        occurred_at = timestamp or datetime.now(UTC).astimezone().isoformat()
        try:
            current = self._current_snapshot()
        except Exception:
            self.last_error = "file_watcher_provider_error"
            return []

        if self._previous is None:
            self._previous = current
            self.last_error = None
            return []

        events = _diff_snapshots(
            session_id=self._session_id,
            timestamp=occurred_at,
            previous=self._previous,
            current=current,
        )
        if events:
            append_raw_events(self._connection, events)
        self._previous = current
        self.last_error = None
        return events

    async def run(self) -> None:
        while not self._stop_event.is_set():
            self.poll_once()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval_seconds)
            except TimeoutError:
                continue

    async def stop(self) -> None:
        self._stop_event.set()
        await asyncio.sleep(0)

    def _current_snapshot(self) -> dict[str, FileSnapshot]:
        return {
            normalize_path(str(snapshot.path)): snapshot
            for snapshot in self._provider.snapshot(self._roots)
            if not _path_has_ignored_part(snapshot.path)
        }


def normalize_file_event(
    *,
    session_id: str,
    timestamp: str,
    path: str,
    operation: str,
    previous_path: str | None = None,
) -> RawEvent:
    if operation not in FILE_OPERATIONS:
        raise ValueError(f"operation must be one of {sorted(FILE_OPERATIONS)}")

    normalized_path = normalize_path(path)
    file_name = PureWindowsPath(normalized_path).name
    extension = PureWindowsPath(normalized_path).suffix
    privacy_level = (
        "sensitive" if is_sensitive_path(file_name=file_name, extension=extension) else "safe"
    )
    metadata: dict[str, object] = {
        "path": redact_sensitive_path(normalized_path)
        if privacy_level == "sensitive"
        else normalized_path,
        "operation": operation,
        "file_name": REDACTED_FILE_NAME if privacy_level == "sensitive" else file_name,
        "extension": extension,
    }
    if previous_path is not None:
        normalized_previous_path = normalize_path(previous_path)
        previous_file_name = PureWindowsPath(normalized_previous_path).name
        previous_extension = PureWindowsPath(normalized_previous_path).suffix
        previous_is_sensitive = is_sensitive_path(
            file_name=previous_file_name,
            extension=previous_extension,
        )
        metadata["previous_path"] = (
            redact_sensitive_path(normalized_previous_path)
            if previous_is_sensitive
            else normalized_previous_path
        )

    return build_raw_event(
        event_id=build_file_event_id(
            session_id=session_id,
            timestamp=timestamp,
            normalized_path=normalized_path,
            operation=operation,
        ),
        session_id=session_id,
        timestamp=timestamp,
        source="file_watcher",
        event_type="file_changed",
        privacy_level=privacy_level,
        confidence=1,
        metadata=metadata,
    )


def normalize_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("path must be a non-empty string")
    return normalized


def is_sensitive_path(*, file_name: str, extension: str) -> bool:
    lower_file_name = file_name.lower()
    lower_extension = extension.lower()
    return (
        lower_file_name in SENSITIVE_FILE_NAMES
        or lower_extension in SENSITIVE_SUFFIXES
        or any(part in lower_file_name for part in SENSITIVE_NAME_PARTS)
    )


def redact_sensitive_path(normalized_path: str) -> str:
    parts = normalized_path.rsplit("/", 1)
    if len(parts) == 1:
        return REDACTED_FILE_NAME
    return f"{parts[0]}/{REDACTED_FILE_NAME}"


def build_file_event_id(
    *,
    session_id: str,
    timestamp: str,
    normalized_path: str,
    operation: str,
) -> str:
    digest = hashlib.sha256(
        f"{session_id}|{timestamp}|{normalized_path}|{operation}".encode()
    ).hexdigest()
    return f"{session_id}-file-{digest[:16]}"


def _diff_snapshots(
    *,
    session_id: str,
    timestamp: str,
    previous: dict[str, FileSnapshot],
    current: dict[str, FileSnapshot],
) -> list[RawEvent]:
    previous_paths = set(previous)
    current_paths = set(current)
    created_paths = current_paths - previous_paths
    deleted_paths = previous_paths - current_paths
    renamed_pairs = _detect_renames(
        previous=previous,
        current=current,
        deleted_paths=deleted_paths,
        created_paths=created_paths,
    )
    renamed_old_paths = {old_path for old_path, _ in renamed_pairs}
    renamed_new_paths = {new_path for _, new_path in renamed_pairs}

    events: list[RawEvent] = []
    for old_path, new_path in renamed_pairs:
        events.append(
            normalize_file_event(
                session_id=session_id,
                timestamp=timestamp,
                path=new_path,
                operation="renamed",
                previous_path=old_path,
            )
        )
    for path in sorted(created_paths - renamed_new_paths):
        events.append(
            normalize_file_event(
                session_id=session_id,
                timestamp=timestamp,
                path=path,
                operation="created",
            )
        )
    for path in sorted(current_paths & previous_paths):
        if _file_identity(current[path]) != _file_identity(previous[path]):
            events.append(
                normalize_file_event(
                    session_id=session_id,
                    timestamp=timestamp,
                    path=path,
                    operation="modified",
                )
            )
    for path in sorted(deleted_paths - renamed_old_paths):
        events.append(
            normalize_file_event(
                session_id=session_id,
                timestamp=timestamp,
                path=path,
                operation="deleted",
            )
        )
    return events


def _detect_renames(
    *,
    previous: dict[str, FileSnapshot],
    current: dict[str, FileSnapshot],
    deleted_paths: set[str],
    created_paths: set[str],
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    unmatched_created = set(created_paths)
    for deleted_path in sorted(deleted_paths):
        deleted_identity = _file_identity(previous[deleted_path])
        match = next(
            (
                created_path
                for created_path in sorted(unmatched_created)
                if _file_identity(current[created_path]) == deleted_identity
            ),
            None,
        )
        if match is None:
            continue
        pairs.append((deleted_path, match))
        unmatched_created.remove(match)
    return pairs


def _file_identity(snapshot: FileSnapshot) -> tuple[int, int]:
    return snapshot.size, snapshot.modified_ns


def _path_has_ignored_part(path: Path) -> bool:
    return any(part.casefold() in IGNORED_PATH_PARTS for part in path.parts)
