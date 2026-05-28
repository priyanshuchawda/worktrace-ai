import json
import sqlite3

from worktrace_agent.domain.session import FakeSession, validate_fake_session


def save_session(connection: sqlite3.Connection, fake_session: FakeSession) -> None:
    with connection:
        session = fake_session.session
        connection.execute(
            """
            INSERT INTO sessions (
              id,
              started_at,
              ended_at,
              status,
              title,
              goal,
              project_label,
              tags_json,
              storage_path,
              privacy_mode,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
              started_at = excluded.started_at,
              ended_at = excluded.ended_at,
              status = excluded.status,
              title = excluded.title,
              goal = excluded.goal,
              project_label = excluded.project_label,
              tags_json = excluded.tags_json,
              storage_path = excluded.storage_path,
              privacy_mode = excluded.privacy_mode,
              updated_at = CURRENT_TIMESTAMP
            """,
            (
                session["id"],
                session["started_at"],
                session.get("ended_at"),
                session["status"],
                session.get("title"),
                session.get("goal"),
                session.get("project_label"),
                json.dumps(session.get("tags", []), separators=(",", ":")),
                session.get("storage_path"),
                session["privacy_mode"],
            ),
        )
        connection.execute("DELETE FROM raw_events WHERE session_id = ?", (session["id"],))
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
                    event["id"],
                    event["session_id"],
                    event["timestamp"],
                    event["source"],
                    event["type"],
                    event["privacy_level"],
                    event["confidence"],
                    json.dumps(event["metadata"], sort_keys=True),
                )
                for event in fake_session.events
            ],
        )


def load_session(connection: sqlite3.Connection, session_id: str) -> FakeSession:
    session_row = connection.execute(
        """
        SELECT id, started_at, ended_at, status, title, goal, project_label, tags_json,
               storage_path, privacy_mode
        FROM sessions
        WHERE id = ?
        """,
        (session_id,),
    ).fetchone()
    if session_row is None:
        raise ValueError(f"Unknown session: {session_id}")

    event_rows = connection.execute(
        """
        SELECT id, session_id, timestamp, source, type, privacy_level, confidence, metadata_json
        FROM raw_events
        WHERE session_id = ?
        ORDER BY timestamp ASC, id ASC
        """,
        (session_id,),
    ).fetchall()

    session = dict(session_row)
    session["tags"] = json.loads(str(session.pop("tags_json")))
    raw_session = {
        "session": session,
        "events": [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "timestamp": row["timestamp"],
                "source": row["source"],
                "type": row["type"],
                "privacy_level": row["privacy_level"],
                "confidence": row["confidence"],
                "metadata": json.loads(row["metadata_json"]),
            }
            for row in event_rows
        ],
    }
    return validate_fake_session(raw_session)
