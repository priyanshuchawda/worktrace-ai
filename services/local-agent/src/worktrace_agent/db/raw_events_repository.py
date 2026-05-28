import json
import sqlite3
from collections.abc import Iterable
from typing import cast

from worktrace_agent.domain.raw_event import RawEvent, build_raw_event


def append_raw_event(connection: sqlite3.Connection, event: RawEvent) -> None:
    append_raw_events(connection, [event])


def append_raw_events(connection: sqlite3.Connection, events: Iterable[RawEvent]) -> None:
    event_list = list(events)
    with connection:
        connection.executemany(
            """
            INSERT INTO raw_events (
              id,
              session_id,
              timestamp,
              source,
              type,
              privacy_level,
              confidence,
              metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    event.id,
                    event.session_id,
                    event.timestamp,
                    event.source,
                    event.type,
                    event.privacy_level,
                    event.confidence,
                    json.dumps(event.metadata, sort_keys=True),
                )
                for event in event_list
            ],
        )


def list_raw_events(connection: sqlite3.Connection, session_id: str) -> list[RawEvent]:
    rows = connection.execute(
        """
        SELECT id, session_id, timestamp, source, type, privacy_level, confidence, metadata_json
        FROM raw_events
        WHERE session_id = ?
        ORDER BY timestamp ASC, id ASC
        """,
        (session_id,),
    ).fetchall()

    return [_raw_event_from_row(row) for row in rows]


def _raw_event_from_row(row: sqlite3.Row) -> RawEvent:
    metadata = json.loads(str(row["metadata_json"]))
    if not isinstance(metadata, dict):
        raise ValueError("raw_events.metadata_json must decode to an object")

    return build_raw_event(
        event_id=str(row["id"]),
        session_id=str(row["session_id"]),
        timestamp=str(row["timestamp"]),
        source=str(row["source"]),
        event_type=str(row["type"]),
        privacy_level=str(row["privacy_level"]),
        confidence=float(row["confidence"]),
        metadata=cast(dict[str, object], metadata),
    )
