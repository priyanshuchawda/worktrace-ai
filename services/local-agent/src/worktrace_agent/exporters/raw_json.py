import json
import sqlite3
from pathlib import Path

from worktrace_agent.db.repositories import load_session
from worktrace_agent.privacy.redaction import redact_json_value


def export_redacted_raw_json(
    connection: sqlite3.Connection,
    session_id: str,
    export_path: Path,
) -> Path:
    fake_session = load_session(connection, session_id)
    payload = {
        "session": fake_session.session,
        "events": fake_session.events,
    }
    redacted_payload = redact_json_value(payload)

    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(
        json.dumps(redacted_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return export_path
