import sqlite3
import sys
from pathlib import Path
from typing import cast

from worktrace_agent.ai.model_availability import (
    CORE_WORKFLOWS,
    ModelAvailabilityConfig,
    ModelFailureCategory,
    ModelProbeResult,
    ModelProvider,
    ModelStatus,
    check_model_availability,
    disabled_model_availability,
)
from worktrace_agent.capture.terminal_command_detector import normalize_terminal_command
from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.raw_events_repository import append_raw_events, list_raw_events
from worktrace_agent.db.session_state_repository import start_session, stop_session
from worktrace_agent.exporters.markdown import export_session_markdown
from worktrace_agent.exporters.raw_json import export_redacted_raw_json
from worktrace_agent.privacy.redaction import PRIVACY_TEST_CORPUS, count_privacy_leaks

SESSION_ID = "sess_model_fallback_001"
HEAVY_MODEL_MODULES = (
    "torch",
    "transformers",
    "llama_cpp",
    "ollama",
    "paddleocr",
    "faster_whisper",
)


def test_required_model_states_are_explicit() -> None:
    assert {status.value for status in ModelStatus} == {
        "not_installed",
        "loading",
        "ready",
        "unavailable",
        "too_slow",
        "failed",
        "disabled",
    }


def test_disabled_ai_allows_core_workflows_and_disables_report_generation() -> None:
    availability = disabled_model_availability(
        model_name="local-report-model",
        provider=ModelProvider.LOCAL_FILE,
    )

    assert availability.status is ModelStatus.DISABLED
    assert availability.can_record is True
    assert availability.can_build_timeline is True
    assert availability.can_export is True
    assert availability.can_generate_report is False
    assert availability.allowed_core_workflows() == CORE_WORKFLOWS
    assert availability.to_debug_summary()["status"] == "disabled"


def test_missing_model_file_returns_not_installed_without_calling_probe(tmp_path: Path) -> None:
    probe = FakeProbe(ModelProbeResult.ready(latency_ms=12))

    availability = check_model_availability(
        ModelAvailabilityConfig(
            model_name="local-report-model",
            provider=ModelProvider.LOCAL_FILE,
            model_path=tmp_path / "missing-model.gguf",
        ),
        probe=probe,
    )

    assert availability.status is ModelStatus.NOT_INSTALLED
    assert availability.can_generate_report is False
    assert probe.call_count == 0


def test_ready_probe_result_is_represented_correctly(tmp_path: Path) -> None:
    model_path = tmp_path / "models" / "report-model.gguf"
    model_path.parent.mkdir(parents=True)
    model_path.write_text("fake model marker", encoding="utf-8")

    availability = check_model_availability(
        ModelAvailabilityConfig(
            model_name="local-report-model",
            provider=ModelProvider.LOCAL_FILE,
            model_path=model_path,
            timeout_ms=500,
        ),
        probe=FakeProbe(ModelProbeResult.ready(model_version="fake-v1", latency_ms=42)),
    )

    assert availability.status is ModelStatus.READY
    assert availability.can_generate_report is True
    assert availability.model_version == "fake-v1"
    assert availability.latency_ms == 42


def test_probe_unavailable_returns_safe_user_message() -> None:
    availability = check_model_availability(
        ModelAvailabilityConfig(
            model_name="local-report-model",
            provider=ModelProvider.FAKE,
        ),
        probe=FakeProbe(
            ModelProbeResult.unavailable(
                category=ModelFailureCategory.UNAVAILABLE,
                safe_message="Local model service is unavailable.",
            )
        ),
    )

    assert availability.status is ModelStatus.UNAVAILABLE
    assert availability.failure_category is ModelFailureCategory.UNAVAILABLE
    assert availability.user_message == "Local model service is unavailable."
    assert availability.can_generate_report is False


def test_probe_timeout_returns_too_slow() -> None:
    availability = check_model_availability(
        ModelAvailabilityConfig(
            model_name="local-report-model",
            provider=ModelProvider.FAKE,
            timeout_ms=100,
        ),
        probe=FakeProbe(ModelProbeResult.ready(latency_ms=250)),
    )

    assert availability.status is ModelStatus.TOO_SLOW
    assert availability.failure_category is ModelFailureCategory.TIMEOUT
    assert availability.latency_ms == 250
    assert availability.can_generate_report is False


def test_probe_exception_returns_redacted_failed_state() -> None:
    availability = check_model_availability(
        ModelAvailabilityConfig(
            model_name="local-report-model",
            provider=ModelProvider.FAKE,
        ),
        probe=RaisingProbe(RuntimeError(f"provider failed with {PRIVACY_TEST_CORPUS[0]}")),
    )

    summary = availability.to_debug_summary()

    assert availability.status is ModelStatus.FAILED
    assert availability.failure_category is ModelFailureCategory.PROBE_FAILED
    assert availability.can_generate_report is False
    assert count_privacy_leaks(availability.user_message) == 0
    assert count_privacy_leaks(summary) == 0
    assert "provider failed" not in availability.user_message


def test_no_model_installed_still_allows_timeline_markdown_and_raw_json_export(
    tmp_path: Path,
) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        save_model_fallback_fixture(connection)
        availability = check_model_availability(
            ModelAvailabilityConfig(
                model_name="local-report-model",
                provider=ModelProvider.LOCAL_FILE,
                model_path=tmp_path / "models" / "missing-model.gguf",
            )
        )

        markdown_path = export_session_markdown(
            connection,
            SESSION_ID,
            tmp_path / "exports" / "session.md",
        )
        raw_json_path = export_redacted_raw_json(
            connection,
            SESSION_ID,
            tmp_path / "exports" / "session.raw.json",
        )

        assert availability.status is ModelStatus.NOT_INSTALLED
        assert "No LLM was used" in markdown_path.read_text(encoding="utf-8")
        assert raw_json_path.exists()
    finally:
        connection.close()


def test_model_failure_does_not_mutate_session_rows_or_raw_events(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        save_model_fallback_fixture(connection)
        before_session = session_row(connection)
        before_events = list_raw_events(connection, SESSION_ID)

        check_model_availability(
            ModelAvailabilityConfig(
                model_name="local-report-model",
                provider=ModelProvider.FAKE,
            ),
            probe=RaisingProbe(RuntimeError("model crashed")),
        )

        after_session = session_row(connection)
        after_events = list_raw_events(connection, SESSION_ID)

        assert after_session == before_session
        assert [event.id for event in after_events] == [event.id for event in before_events]
    finally:
        connection.close()


def test_session_state_flow_does_not_import_heavy_model_modules(tmp_path: Path) -> None:
    for module_name in HEAVY_MODEL_MODULES:
        sys.modules.pop(module_name, None)

    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(
            connection,
            session_id="sess_no_model_import_001",
            started_at="2026-05-06T09:14:00+05:30",
        )
        stop_session(
            connection,
            session_id="sess_no_model_import_001",
            occurred_at="2026-05-06T09:16:00+05:30",
        )

        assert not any(module_name in sys.modules for module_name in HEAVY_MODEL_MODULES)
    finally:
        connection.close()


class FakeProbe:
    def __init__(self, result: ModelProbeResult) -> None:
        self.result = result
        self.call_count = 0

    def check(self, config: ModelAvailabilityConfig) -> ModelProbeResult:
        self.call_count += 1
        return self.result


class RaisingProbe:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def check(self, config: ModelAvailabilityConfig) -> ModelProbeResult:
        raise self.error


def save_model_fallback_fixture(connection: sqlite3.Connection) -> None:
    start_session(
        connection,
        session_id=SESSION_ID,
        started_at="2026-05-06T09:14:00+05:30",
        title="Model fallback fixture",
    )
    append_raw_events(
        connection,
        [
            normalize_terminal_command(
                session_id=SESSION_ID,
                timestamp="2026-05-06T09:15:00+05:30",
                command="uv run --python 3.13 pytest",
                shell="powershell",
                exit_code=0,
            )
        ],
    )
    stop_session(
        connection,
        session_id=SESSION_ID,
        occurred_at="2026-05-06T09:16:00+05:30",
    )


def session_row(connection: sqlite3.Connection) -> dict[str, object]:
    row = connection.execute(
        """
        SELECT id, started_at, ended_at, status, title, storage_path, privacy_mode
        FROM sessions
        WHERE id = ?
        """,
        (SESSION_ID,),
    ).fetchone()
    if row is None:
        raise AssertionError(f"missing session row: {SESSION_ID}")
    return dict(cast(sqlite3.Row, row))
