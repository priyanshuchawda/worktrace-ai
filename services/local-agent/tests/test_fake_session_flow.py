from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.repositories import load_session, save_session
from worktrace_agent.domain.session import validate_fake_session
from worktrace_agent.exporters.raw_json import export_redacted_raw_json
from worktrace_agent.privacy.redaction import PRIVACY_TEST_CORPUS

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "fake_session.json"


def load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fake_session_fixture_validates() -> None:
    fake_session = validate_fake_session(load_fixture())

    assert fake_session.session["id"] == "sess_fake_001"
    assert len(fake_session.events) == 2
    assert fake_session.events[0]["metadata"]["app"] == "VS Code"


def test_fake_session_round_trip_passes(tmp_path: Path) -> None:
    fake_session = validate_fake_session(load_fixture())
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        save_session(connection, fake_session)
        loaded_session = load_session(connection, "sess_fake_001")

        assert loaded_session == fake_session
    finally:
        connection.close()


def test_export_contains_no_secrets_from_privacy_test_corpus(tmp_path: Path) -> None:
    fake_session = validate_fake_session(load_fixture())
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    export_path = tmp_path / "exports" / "sess_fake_001.raw.json"
    try:
        save_session(connection, fake_session)
        written_path = export_redacted_raw_json(connection, "sess_fake_001", export_path)

        exported_text = written_path.read_text(encoding="utf-8")
        exported_data = json.loads(exported_text)

        assert written_path == export_path
        assert exported_data["session"]["id"] == "sess_fake_001"
        assert len(exported_data["events"]) == 2
        assert "[REDACTED]" in exported_text
        for secret in PRIVACY_TEST_CORPUS:
            assert secret not in exported_text
    finally:
        connection.close()


def test_invalid_fake_session_missing_event_id_is_rejected() -> None:
    raw_session = deepcopy(load_fixture())
    assert isinstance(raw_session["events"], list)
    del raw_session["events"][0]["id"]

    with pytest.raises(ValueError, match="events\\[0\\].id"):
        validate_fake_session(raw_session)


def test_export_unknown_session_is_rejected(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        with pytest.raises(ValueError, match="Unknown session"):
            export_redacted_raw_json(connection, "sess_missing", tmp_path / "missing.json")
    finally:
        connection.close()
