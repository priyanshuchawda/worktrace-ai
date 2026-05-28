from pathlib import Path

import pytest

from worktrace_agent.capture.screenshot_sampler import ScreenshotArtifact
from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.screenshots_repository import (
    delete_screenshots_for_session,
    list_screenshots,
    save_screenshot,
)
from worktrace_agent.db.session_state_repository import start_session
from worktrace_agent.privacy.policy import PrivacyPolicy
from worktrace_agent.privacy.redaction import (
    PRIVACY_TEST_CORPUS,
    count_privacy_leaks,
    redact_for_export,
    redact_for_log,
    redact_for_prompt,
)

SESSION_ID = "sess_privacy_001"
TIMESTAMP = "2026-05-06T09:30:00+05:30"


def build_screenshot(storage_path: str) -> ScreenshotArtifact:
    return ScreenshotArtifact(
        id=f"{SESSION_ID}-screenshot-001",
        session_id=SESSION_ID,
        source_event_id=None,
        timestamp=TIMESTAMP,
        width=8,
        height=8,
        stored_width=8,
        stored_height=8,
        byte_size=192,
        content_hash="abc123",
        visual_hash="def456",
        storage_path=storage_path,
    )


def test_privacy_leak_count_is_zero_for_prompt_export_and_log_surfaces() -> None:
    corpus_text = " ".join(PRIVACY_TEST_CORPUS)
    payload = {
        "prompt": corpus_text,
        "events": [{"metadata": {"command": corpus_text}}],
    }

    redacted_prompt = redact_for_prompt(payload)
    redacted_export = redact_for_export(payload)
    redacted_log = redact_for_log(f"debug payload: {corpus_text}")

    assert count_privacy_leaks(redacted_prompt) == 0
    assert count_privacy_leaks(redacted_export) == 0
    assert count_privacy_leaks(redacted_log) == 0


def test_hardened_redaction_removes_common_secret_formats_and_optional_contact_info() -> None:
    jwt_token = (
        "eyJ" + "hbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    github_pat = "github" + "_pat_" + "11AAAAAAA0abcdefghijklmnopqrstuvwxyzABCDEFGHIJK"
    github_oauth = "gh" + "o_" + "abcdefghijklmnopqrstuvwxyz1234567890"
    google_key = "AI" + "za" + "SyDq4mFakeGoogleApiKeyValueForTests1234"
    aws_access_key = "AK" + "IA" + "IOSFODNN7EXAMPLE"
    aws_secret_value = "wJ" + "alrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    private_key = (
        "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----"
    )
    payload = {
        "jwt": jwt_token,
        "github": github_pat,
        "github_oauth": github_oauth,
        "google": google_key,
        "aws_access_key": aws_access_key,
        "aws_secret": f"AWS_SECRET_ACCESS_KEY={aws_secret_value}",
        "private_key": private_key,
        "contact": "alice@example.org",
        "phone": "+1 415 555 2671",
    }

    redacted_without_contacts = redact_for_export(payload)
    redacted_with_contacts = redact_for_export(payload, redact_contact_info=True)
    serialized_without_contacts = str(redacted_without_contacts)
    serialized_with_contacts = str(redacted_with_contacts)

    assert jwt_token.split(".")[0] not in serialized_without_contacts
    assert github_pat not in serialized_without_contacts
    assert github_oauth not in serialized_without_contacts
    assert google_key not in serialized_without_contacts
    assert aws_access_key not in serialized_without_contacts
    assert aws_secret_value not in serialized_without_contacts
    assert private_key not in serialized_without_contacts
    assert "alice@example.org" in serialized_without_contacts
    assert "+1 415 555 2671" in serialized_without_contacts
    assert count_privacy_leaks(redacted_without_contacts) == 0
    assert "alice@example.org" not in serialized_with_contacts
    assert "+1 415 555 2671" not in serialized_with_contacts


def test_privacy_policy_supports_allowlist_blocklist_private_and_clipboard_safe_mode() -> None:
    policy = PrivacyPolicy(
        allowlist=("Code.exe",),
        blocklist=("chrome.exe",),
        private_mode=False,
        clipboard_safe_mode=True,
    )

    assert policy.should_capture_app("Code.exe")
    assert not policy.should_capture_app("chrome.exe")
    assert not policy.should_capture_app("notepad.exe")
    assert not policy.should_capture_clipboard_content()
    assert policy.clipboard_storage_mode == "metadata_only"

    private_policy = PrivacyPolicy(private_mode=True)

    assert not private_policy.should_capture_source("screenshot_sampler")
    assert not private_policy.should_capture_source("terminal_command_detector")
    assert not private_policy.should_capture_clipboard_content()


def test_delete_screenshots_removes_files_and_database_references(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    artifact_root = tmp_path / "session-artifacts"
    screenshot_file = artifact_root / "screenshots" / "frame.rgb"
    screenshot_file.parent.mkdir(parents=True)
    screenshot_file.write_bytes(b"fake-rgb")
    try:
        start_session(connection, session_id=SESSION_ID, started_at=TIMESTAMP)
        save_screenshot(connection, build_screenshot("screenshots/frame.rgb"))

        result = delete_screenshots_for_session(
            connection,
            session_id=SESSION_ID,
            artifact_root=artifact_root,
        )

        assert result.deleted_files == 1
        assert result.missing_files == 0
        assert not screenshot_file.exists()
        assert list_screenshots(connection, SESSION_ID) == []
    finally:
        connection.close()


def test_delete_screenshots_rejects_paths_outside_artifact_root(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    artifact_root = tmp_path / "session-artifacts"
    outside_file = tmp_path / "outside.rgb"
    artifact_root.mkdir()
    outside_file.write_bytes(b"must-stay")
    try:
        start_session(connection, session_id=SESSION_ID, started_at=TIMESTAMP)
        save_screenshot(connection, build_screenshot("../outside.rgb"))

        with pytest.raises(ValueError, match="outside artifact root"):
            delete_screenshots_for_session(
                connection,
                session_id=SESSION_ID,
                artifact_root=artifact_root,
            )

        assert outside_file.exists()
        assert len(list_screenshots(connection, SESSION_ID)) == 1
    finally:
        connection.close()
