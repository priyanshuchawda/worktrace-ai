import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from worktrace_agent.capture.screenshot_sampler import ScreenshotArtifact

DEFAULT_MAX_SCREENSHOTS_PER_SESSION: Final = 720
DEFAULT_MAX_SCREENSHOT_BYTES_PER_SESSION: Final = 500 * 1024 * 1024


@dataclass(frozen=True)
class ScreenshotDeletionResult:
    deleted_files: int
    missing_files: int
    deleted_rows: int


@dataclass(frozen=True)
class ScreenshotRetentionConfig:
    max_count: int | None = DEFAULT_MAX_SCREENSHOTS_PER_SESSION
    max_total_bytes: int | None = DEFAULT_MAX_SCREENSHOT_BYTES_PER_SESSION


DEFAULT_SCREENSHOT_RETENTION_CONFIG: Final = ScreenshotRetentionConfig()


def save_screenshot(connection: sqlite3.Connection, screenshot: ScreenshotArtifact) -> None:
    with connection:
        connection.execute(
            """
            INSERT INTO screenshots (
              id,
              session_id,
              source_event_id,
              timestamp,
              width,
              height,
              stored_width,
              stored_height,
              byte_size,
              content_hash,
              visual_hash,
              storage_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                screenshot.id,
                screenshot.session_id,
                screenshot.source_event_id,
                screenshot.timestamp,
                screenshot.width,
                screenshot.height,
                screenshot.stored_width,
                screenshot.stored_height,
                screenshot.byte_size,
                screenshot.content_hash,
                screenshot.visual_hash,
                screenshot.storage_path,
            ),
        )


def list_screenshots(connection: sqlite3.Connection, session_id: str) -> list[ScreenshotArtifact]:
    rows = connection.execute(
        """
        SELECT
          id,
          session_id,
          source_event_id,
          timestamp,
          width,
          height,
          stored_width,
          stored_height,
          byte_size,
          content_hash,
          visual_hash,
          storage_path
        FROM screenshots
        WHERE session_id = ?
        ORDER BY timestamp ASC, id ASC
        """,
        (session_id,),
    ).fetchall()

    return [_screenshot_from_row(row) for row in rows]


def delete_screenshots_for_session(
    connection: sqlite3.Connection,
    *,
    session_id: str,
    artifact_root: Path,
) -> ScreenshotDeletionResult:
    screenshots = list_screenshots(connection, session_id)
    resolved_root = artifact_root.resolve()
    targets = [
        _resolve_artifact_path(resolved_root=resolved_root, storage_path=screenshot.storage_path)
        for screenshot in screenshots
    ]

    deleted_files = 0
    missing_files = 0
    for target in targets:
        if not target.exists():
            missing_files += 1
            continue
        if not target.is_file():
            raise ValueError("screenshot artifact path is not a file")
        target.unlink()
        deleted_files += 1

    with connection:
        cursor = connection.execute("DELETE FROM screenshots WHERE session_id = ?", (session_id,))

    return ScreenshotDeletionResult(
        deleted_files=deleted_files,
        missing_files=missing_files,
        deleted_rows=cursor.rowcount,
    )


def prune_screenshots_for_session(
    connection: sqlite3.Connection,
    *,
    session_id: str,
    artifact_root: Path,
    config: ScreenshotRetentionConfig | None = None,
) -> ScreenshotDeletionResult:
    resolved_config = config or DEFAULT_SCREENSHOT_RETENTION_CONFIG
    _validate_retention_config(resolved_config)
    screenshots = list_screenshots(connection, session_id)
    delete_ids = _retention_delete_ids(screenshots, resolved_config)
    if not delete_ids:
        return ScreenshotDeletionResult(deleted_files=0, missing_files=0, deleted_rows=0)

    resolved_root = artifact_root.resolve()
    by_id = {screenshot.id: screenshot for screenshot in screenshots}
    targets = [
        _resolve_artifact_path(
            resolved_root=resolved_root,
            storage_path=by_id[screenshot_id].storage_path,
        )
        for screenshot_id in delete_ids
    ]

    deleted_files = 0
    missing_files = 0
    for target in targets:
        if not target.exists():
            missing_files += 1
            continue
        if not target.is_file():
            raise ValueError("screenshot artifact path is not a file")
        target.unlink()
        deleted_files += 1

    deleted_rows = 0
    with connection:
        for screenshot_id in delete_ids:
            cursor = connection.execute("DELETE FROM screenshots WHERE id = ?", (screenshot_id,))
            deleted_rows += cursor.rowcount

    return ScreenshotDeletionResult(
        deleted_files=deleted_files,
        missing_files=missing_files,
        deleted_rows=deleted_rows,
    )


def _screenshot_from_row(row: sqlite3.Row) -> ScreenshotArtifact:
    return ScreenshotArtifact(
        id=str(row["id"]),
        session_id=str(row["session_id"]),
        source_event_id=str(row["source_event_id"]) if row["source_event_id"] is not None else None,
        timestamp=str(row["timestamp"]),
        width=int(row["width"]),
        height=int(row["height"]),
        stored_width=int(row["stored_width"]),
        stored_height=int(row["stored_height"]),
        byte_size=int(row["byte_size"]),
        content_hash=str(row["content_hash"]),
        visual_hash=str(row["visual_hash"]),
        storage_path=str(row["storage_path"]),
    )


def _resolve_artifact_path(*, resolved_root: Path, storage_path: str) -> Path:
    target = (resolved_root / storage_path).resolve()
    try:
        target.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError("screenshot artifact path is outside artifact root") from error
    return target


def _retention_delete_ids(
    screenshots: list[ScreenshotArtifact],
    config: ScreenshotRetentionConfig,
) -> list[str]:
    delete_ids: list[str] = []
    delete_id_set: set[str] = set()
    if config.max_count is not None and len(screenshots) > config.max_count:
        for screenshot in screenshots[: len(screenshots) - config.max_count]:
            delete_ids.append(screenshot.id)
            delete_id_set.add(screenshot.id)

    if config.max_total_bytes is not None:
        remaining = [screenshot for screenshot in screenshots if screenshot.id not in delete_id_set]
        total_bytes = sum(screenshot.byte_size for screenshot in remaining)
        for screenshot in remaining:
            if total_bytes <= config.max_total_bytes:
                break
            delete_ids.append(screenshot.id)
            delete_id_set.add(screenshot.id)
            total_bytes -= screenshot.byte_size

    return delete_ids


def _validate_retention_config(config: ScreenshotRetentionConfig) -> None:
    if config.max_count is not None and config.max_count < 0:
        raise ValueError("max_count must not be negative")
    if config.max_total_bytes is not None and config.max_total_bytes < 0:
        raise ValueError("max_total_bytes must not be negative")
