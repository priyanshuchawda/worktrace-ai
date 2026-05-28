import json
import sqlite3
from pathlib import Path

from worktrace_agent.capture.file_watcher import normalize_file_event
from worktrace_agent.capture.terminal_command_detector import normalize_terminal_command
from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.raw_events_repository import append_raw_events
from worktrace_agent.db.session_state_repository import start_session, stop_session
from worktrace_agent.domain.raw_event import build_raw_event
from worktrace_agent.exporters.markdown import export_session_markdown
from worktrace_agent.exporters.raw_json import export_redacted_raw_json
from worktrace_agent.privacy.redaction import (
    PRIVACY_TEST_CORPUS,
    REDACTION_TOKEN,
    count_privacy_leaks,
)

SESSION_ID = "sess_export_001"
STARTED_AT = "2026-05-06T09:14:00+05:30"
STOPPED_AT = "2026-05-06T09:22:00+05:30"


def test_markdown_export_contains_timeline_evidence_and_no_unredacted_secrets(
    tmp_path: Path,
) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        save_export_fixture(connection)

        export_path = export_session_markdown(
            connection,
            SESSION_ID,
            tmp_path / "exports" / "session.md",
        )

        markdown = export_path.read_text(encoding="utf-8")

        assert "# WorkTrace Session Export" in markdown
        assert "## Timeline" in markdown
        assert "## Findings" in markdown
        assert "## Evidence" in markdown
        assert "Evidence: evt_export_code" in markdown
        assert "Repeated terminal command" in markdown
        assert REDACTION_TOKEN in markdown
        assert count_privacy_leaks(markdown) == 0
    finally:
        connection.close()


def test_raw_json_export_for_same_session_remains_redacted(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        save_export_fixture(connection)

        export_path = export_redacted_raw_json(
            connection,
            SESSION_ID,
            tmp_path / "exports" / "session.raw.json",
        )

        exported_text = export_path.read_text(encoding="utf-8")
        exported_data = json.loads(exported_text)

        assert exported_data["session"]["id"] == SESSION_ID
        assert len(exported_data["events"]) == 5
        assert REDACTION_TOKEN in exported_text
        assert count_privacy_leaks(exported_text) == 0
    finally:
        connection.close()


def save_export_fixture(connection: sqlite3.Connection) -> None:
    start_session(
        connection,
        session_id=SESSION_ID,
        started_at=STARTED_AT,
        title=f"Export review {PRIVACY_TEST_CORPUS[0]}",
    )
    append_raw_events(
        connection,
        [
            build_raw_event(
                event_id="evt_export_code",
                session_id=SESSION_ID,
                timestamp="2026-05-06T09:14:00+05:30",
                source="active_window",
                event_type="active_window_changed",
                privacy_level="sensitive",
                confidence=0.95,
                metadata={
                    "app": "VS Code",
                    "window_title": f"settings.py {PRIVACY_TEST_CORPUS[1]}",
                },
            ),
            normalize_file_event(
                session_id=SESSION_ID,
                timestamp="2026-05-06T09:15:00+05:30",
                path=r"C:\Users\Admin\Desktop\screen-ai\services\local-agent\settings.py",
                operation="modified",
            ),
            normalize_terminal_command(
                session_id=SESSION_ID,
                timestamp="2026-05-06T09:16:00+05:30",
                command="uv run --python 3.13 pytest",
                shell="powershell",
                exit_code=1,
            ),
            normalize_terminal_command(
                session_id=SESSION_ID,
                timestamp="2026-05-06T09:17:00+05:30",
                command="uv run --python 3.13 pytest",
                shell="powershell",
                exit_code=1,
            ),
            normalize_terminal_command(
                session_id=SESSION_ID,
                timestamp="2026-05-06T09:18:00+05:30",
                command="uv run --python 3.13 pytest",
                shell="powershell",
                exit_code=0,
            ),
        ],
    )
    stop_session(connection, session_id=SESSION_ID, occurred_at=STOPPED_AT)
