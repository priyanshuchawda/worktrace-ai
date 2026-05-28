from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from worktrace_agent.capture.screenshot_sampler import ScreenshotArtifact
from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.screenshots_repository import (
    ScreenshotRetentionConfig,
    list_screenshots,
    prune_screenshots_for_session,
    save_screenshot,
)
from worktrace_agent.db.session_state_repository import start_session

SESSION_ID = "sess_retention_001"
STARTED_AT = "2026-05-07T09:14:00+05:30"


def test_retention_prunes_oldest_screenshots_by_count(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    artifact_root = tmp_path / "session-artifacts"
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        for index in range(4):
            save_fixture_screenshot(
                connection,
                artifact_root=artifact_root,
                index=index,
                byte_size=10,
            )

        result = prune_screenshots_for_session(
            connection,
            session_id=SESSION_ID,
            artifact_root=artifact_root,
            config=ScreenshotRetentionConfig(max_count=2),
        )

        assert result.deleted_rows == 2
        assert result.deleted_files == 2
        assert result.missing_files == 0
        assert [screenshot.id for screenshot in list_screenshots(connection, SESSION_ID)] == [
            "shot_002",
            "shot_003",
        ]
        assert not (artifact_root / "screenshots" / "shot_000.png").exists()
        assert not (artifact_root / "screenshots" / "shot_001.png").exists()
    finally:
        connection.close()


def test_retention_prunes_oldest_screenshots_by_total_bytes(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    artifact_root = tmp_path / "session-artifacts"
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        for index, byte_size in enumerate((10, 12, 14)):
            save_fixture_screenshot(
                connection,
                artifact_root=artifact_root,
                index=index,
                byte_size=byte_size,
            )

        result = prune_screenshots_for_session(
            connection,
            session_id=SESSION_ID,
            artifact_root=artifact_root,
            config=ScreenshotRetentionConfig(max_total_bytes=25),
        )

        assert result.deleted_rows == 2
        assert result.deleted_files == 2
        assert [screenshot.id for screenshot in list_screenshots(connection, SESSION_ID)] == [
            "shot_002"
        ]
    finally:
        connection.close()


def test_retention_counts_missing_files_and_deletes_rows(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    artifact_root = tmp_path / "session-artifacts"
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        save_fixture_screenshot(
            connection,
            artifact_root=artifact_root,
            index=0,
            byte_size=10,
        )
        (artifact_root / "screenshots" / "shot_000.png").unlink()

        result = prune_screenshots_for_session(
            connection,
            session_id=SESSION_ID,
            artifact_root=artifact_root,
            config=ScreenshotRetentionConfig(max_count=0),
        )

        assert result.deleted_rows == 1
        assert result.deleted_files == 0
        assert result.missing_files == 1
        assert list_screenshots(connection, SESSION_ID) == []
    finally:
        connection.close()


def test_retention_rejects_paths_outside_artifact_root(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    artifact_root = tmp_path / "session-artifacts"
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        save_screenshot(
            connection,
            screenshot=artifact(index=0, byte_size=10, storage_path="../escape.png"),
        )

        with pytest.raises(ValueError, match="outside artifact root"):
            prune_screenshots_for_session(
                connection,
                session_id=SESSION_ID,
                artifact_root=artifact_root,
                config=ScreenshotRetentionConfig(max_count=0),
            )
    finally:
        connection.close()


def save_fixture_screenshot(
    connection: sqlite3.Connection,
    *,
    artifact_root: Path,
    index: int,
    byte_size: int,
) -> None:
    screenshot = artifact(index=index, byte_size=byte_size)
    target = artifact_root / screenshot.storage_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"x" * byte_size)
    save_screenshot(connection, screenshot=screenshot)


def artifact(*, index: int, byte_size: int, storage_path: str | None = None) -> ScreenshotArtifact:
    screenshot_id = f"shot_{index:03d}"
    return ScreenshotArtifact(
        id=screenshot_id,
        session_id=SESSION_ID,
        source_event_id=None,
        timestamp=f"2026-05-07T09:14:{index:02d}+05:30",
        width=8,
        height=8,
        stored_width=8,
        stored_height=8,
        byte_size=byte_size,
        content_hash=f"content_hash_{index:03d}",
        visual_hash=f"{index:016x}",
        storage_path=storage_path or f"screenshots/{screenshot_id}.png",
    )
