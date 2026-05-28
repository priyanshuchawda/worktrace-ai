import json
import sqlite3
from typing import cast

from worktrace_agent.capture.ocr_worker import OcrResult


def save_ocr_result(connection: sqlite3.Connection, result: OcrResult) -> None:
    with connection:
        connection.execute(
            """
            INSERT INTO ocr_results (
              id,
              session_id,
              screenshot_id,
              source_event_id,
              timestamp,
              text,
              confidence,
              engine_name,
              metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.id,
                result.session_id,
                result.screenshot_id,
                result.source_event_id,
                result.timestamp,
                result.text,
                result.confidence,
                result.engine_name,
                json.dumps(result.metadata, sort_keys=True),
            ),
        )


def list_ocr_results(connection: sqlite3.Connection, session_id: str) -> list[OcrResult]:
    rows = connection.execute(
        """
        SELECT
          id,
          session_id,
          screenshot_id,
          source_event_id,
          timestamp,
          text,
          confidence,
          engine_name,
          metadata_json
        FROM ocr_results
        WHERE session_id = ?
        ORDER BY timestamp ASC, id ASC
        """,
        (session_id,),
    ).fetchall()

    return [_ocr_result_from_row(row) for row in rows]


def _ocr_result_from_row(row: sqlite3.Row) -> OcrResult:
    metadata = json.loads(str(row["metadata_json"]))
    if not isinstance(metadata, dict):
        raise ValueError("ocr_results.metadata_json must decode to an object")

    return OcrResult(
        id=str(row["id"]),
        session_id=str(row["session_id"]),
        screenshot_id=str(row["screenshot_id"]),
        source_event_id=str(row["source_event_id"]) if row["source_event_id"] is not None else None,
        timestamp=str(row["timestamp"]),
        text=str(row["text"]),
        confidence=float(row["confidence"]),
        engine_name=str(row["engine_name"]),
        metadata=cast(dict[str, object], metadata),
    )
