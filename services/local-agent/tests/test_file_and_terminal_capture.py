import json
from pathlib import Path

import pytest

from worktrace_agent.capture.file_watcher import normalize_file_event
from worktrace_agent.capture.terminal_command_detector import (
    hash_command,
    normalize_terminal_command,
)
from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.raw_events_repository import append_raw_event, list_raw_events
from worktrace_agent.db.session_state_repository import start_session
from worktrace_agent.exporters.raw_json import export_redacted_raw_json
from worktrace_agent.privacy.redaction import PRIVACY_TEST_CORPUS, REDACTION_TOKEN, SECRET_VALUES

SESSION_ID = "sess_file_terminal_001"
TIMESTAMP = "2026-05-06T09:22:00+05:30"


def test_file_event_normalization_captures_path_and_operation_metadata() -> None:
    event = normalize_file_event(
        session_id=SESSION_ID,
        timestamp=TIMESTAMP,
        path=r"C:\Users\Admin\Desktop\screen-ai\apps\desktop\src\App.tsx",
        operation="modified",
    )

    assert event.source == "file_watcher"
    assert event.type == "file_changed"
    assert event.privacy_level == "safe"
    assert event.metadata == {
        "path": "C:/Users/Admin/Desktop/screen-ai/apps/desktop/src/App.tsx",
        "operation": "modified",
        "file_name": "App.tsx",
        "extension": ".tsx",
    }


def test_sensitive_file_event_is_marked_sensitive() -> None:
    event = normalize_file_event(
        session_id=SESSION_ID,
        timestamp=TIMESTAMP,
        path=r"C:\Users\Admin\Desktop\screen-ai\.env",
        operation="modified",
    )

    assert event.privacy_level == "sensitive"
    assert event.metadata["file_name"] == "[REDACTED]"
    assert event.metadata["path"] == "C:/Users/Admin/Desktop/screen-ai/[REDACTED]"


def test_invalid_file_operation_is_rejected() -> None:
    with pytest.raises(ValueError, match="operation"):
        normalize_file_event(
            session_id=SESSION_ID,
            timestamp=TIMESTAMP,
            path=r"C:\Users\Admin\Desktop\screen-ai\README.md",
            operation="opened",
        )


def test_terminal_command_is_redacted_before_storage_and_export(tmp_path: Path) -> None:
    raw_command = (
        'curl -H "Authorization: Bearer sk-test" https://api.example.test '
        "&& set GITHUB_TOKEN=ghp_test "
        "&& echo password=mysecret"
    )
    event = normalize_terminal_command(
        session_id=SESSION_ID,
        timestamp=TIMESTAMP,
        command=raw_command,
        shell="powershell",
        exit_code=1,
    )

    assert event.source == "terminal_command_detector"
    assert event.type == "terminal_command"
    assert event.privacy_level == "redacted"
    assert "raw_command" not in event.metadata
    redacted_command = event.metadata["command"]
    assert isinstance(redacted_command, str)
    assert redacted_command.count(REDACTION_TOKEN) >= 3
    assert event.metadata["command_hash"] == hash_command(redacted_command)
    assert event.metadata["command_hash"] != hash_command(raw_command)

    serialized_metadata = json.dumps(event.metadata)
    for secret in PRIVACY_TEST_CORPUS + SECRET_VALUES:
        assert secret not in serialized_metadata

    connection = initialize_database(tmp_path / "worktrace.sqlite")
    export_path = tmp_path / "exports" / "session.raw.json"
    try:
        start_session(connection, session_id=SESSION_ID, started_at=TIMESTAMP)
        append_raw_event(connection, event)

        stored_metadata = connection.execute(
            "SELECT metadata_json FROM raw_events WHERE id = ?",
            (event.id,),
        ).fetchone()["metadata_json"]
        loaded_event = list_raw_events(connection, SESSION_ID)[0]
        written_path = export_redacted_raw_json(connection, SESSION_ID, export_path)
        exported_text = written_path.read_text(encoding="utf-8")

        assert loaded_event == event
        for secret in PRIVACY_TEST_CORPUS + SECRET_VALUES:
            assert secret not in stored_metadata
            assert secret not in exported_text
    finally:
        connection.close()


def test_terminal_command_redacts_common_secret_formats_before_database_and_export(
    tmp_path: Path,
) -> None:
    github_pat = "github" + "_pat_" + "11AAAAAAA0abcdefghijklmnopqrstuvwxyzABCDEFGHIJK"
    google_key = "AI" + "za" + "SyDq4mFakeGoogleApiKeyValueForTests1234"
    aws_access_key = "AK" + "IA" + "IOSFODNN7EXAMPLE"
    aws_secret_value = "wJ" + "alrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    jwt_token = (
        "eyJ" + "hbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    raw_command = (
        f"deploy --token {github_pat} "
        f"--api-key {google_key} "
        f"AWS_ACCESS_KEY_ID={aws_access_key} "
        f"AWS_SECRET_ACCESS_KEY={aws_secret_value} "
        f"Authorization: Bearer {jwt_token}"
    )
    event = normalize_terminal_command(
        session_id=SESSION_ID,
        timestamp=TIMESTAMP,
        command=raw_command,
        shell="powershell",
        exit_code=1,
    )
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    export_path = tmp_path / "exports" / "session.raw.json"
    try:
        start_session(connection, session_id=SESSION_ID, started_at=TIMESTAMP)
        append_raw_event(connection, event)

        stored_metadata = connection.execute(
            "SELECT metadata_json FROM raw_events WHERE id = ?",
            (event.id,),
        ).fetchone()["metadata_json"]
        exported_text = export_redacted_raw_json(connection, SESSION_ID, export_path).read_text(
            encoding="utf-8"
        )

        for leaked_fragment in (
            github_pat,
            google_key,
            aws_access_key,
            aws_secret_value,
            jwt_token,
        ):
            assert leaked_fragment not in stored_metadata
            assert leaked_fragment not in exported_text
    finally:
        connection.close()


def test_safe_terminal_command_keeps_command_text() -> None:
    event = normalize_terminal_command(
        session_id=SESSION_ID,
        timestamp=TIMESTAMP,
        command="pnpm --dir apps/desktop test",
        shell="powershell",
        exit_code=0,
    )

    assert event.privacy_level == "safe"
    assert event.metadata["command"] == "pnpm --dir apps/desktop test"
    assert event.metadata["shell"] == "powershell"
    assert event.metadata["exit_code"] == 0
