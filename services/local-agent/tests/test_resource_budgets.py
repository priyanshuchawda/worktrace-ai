from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from worktrace_agent.capture.screenshot_sampler import DEFAULT_INTERVAL_SECONDS
from worktrace_agent.capture.terminal_command_detector import normalize_terminal_command
from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.raw_events_repository import append_raw_events, list_raw_events
from worktrace_agent.db.session_state_repository import start_session
from worktrace_agent.performance.resource_budgets import (
    DEFAULT_RECORDING_RESOURCE_BUDGETS,
    ResourceBudgetViolationCode,
    ResourceSample,
    estimate_storage_growth,
    evaluate_recording_resource_budget,
    render_resource_budget_table,
)

SESSION_ID = "sess_resource_budget_001"
STARTED_AT = "2026-05-06T09:00:00+05:30"
HEAVY_MODEL_MODULES = (
    "torch",
    "transformers",
    "paddle",
    "paddleocr",
    "faster_whisper",
    "whisper",
    "llama_cpp",
)


def test_thirty_minute_healthy_fake_recording_passes_budget() -> None:
    samples = healthy_thirty_minute_samples()

    report = evaluate_recording_resource_budget(samples)

    assert report.passed is True
    assert report.duration_minutes == 30
    assert report.average_cpu_percent == 8.0
    assert report.peak_ram_mb == 640
    assert report.db_growth_mb == 35
    assert report.screenshot_mb_per_hour == 120
    assert report.model_loaded_during_recording is False
    assert report.violations == ()
    assert (
        DEFAULT_RECORDING_RESOURCE_BUDGETS.screenshot_interval_seconds == DEFAULT_INTERVAL_SECONDS
    )


def test_cpu_average_above_budget_fails() -> None:
    samples = [
        sample(index=index, cpu_percent=20, ram_mb=500, db_bytes=10, screenshot_bytes=10)
        for index in range(30)
    ]

    report = evaluate_recording_resource_budget(samples)

    assert report.passed is False
    assert [violation.code for violation in report.violations] == [
        ResourceBudgetViolationCode.CPU_AVERAGE_EXCEEDED
    ]
    assert "CPU average" in report.violations[0].user_message
    assert "20.00%" in report.violations[0].user_message


def test_ram_above_budget_fails() -> None:
    samples = [
        sample(index=index, cpu_percent=5, ram_mb=900, db_bytes=10, screenshot_bytes=10)
        for index in range(30)
    ]

    report = evaluate_recording_resource_budget(samples)

    assert report.passed is False
    assert [violation.code for violation in report.violations] == [
        ResourceBudgetViolationCode.RAM_LIMIT_EXCEEDED
    ]
    assert "RAM" in report.violations[0].user_message


def test_db_growth_above_budget_fails() -> None:
    samples = healthy_thirty_minute_samples(final_db_mb=130)

    report = evaluate_recording_resource_budget(samples)

    assert report.passed is False
    assert [violation.code for violation in report.violations] == [
        ResourceBudgetViolationCode.DB_GROWTH_EXCEEDED
    ]


def test_screenshot_storage_per_hour_above_budget_fails() -> None:
    samples = healthy_thirty_minute_samples(final_screenshot_mb=140)

    report = evaluate_recording_resource_budget(samples)

    assert report.passed is False
    assert [violation.code for violation in report.violations] == [
        ResourceBudgetViolationCode.SCREENSHOT_STORAGE_EXCEEDED
    ]


def test_any_model_loaded_during_recording_fails_budget() -> None:
    samples = healthy_thirty_minute_samples(model_loaded_index=5)

    report = evaluate_recording_resource_budget(samples)

    assert report.passed is False
    assert [violation.code for violation in report.violations] == [
        ResourceBudgetViolationCode.MODEL_LOADED_DURING_RECORDING
    ]
    assert "No local AI model should be loaded during recording." in (
        report.violations[0].user_message
    )


def test_disabled_or_not_installed_ai_states_pass_when_no_model_is_loaded() -> None:
    disabled_report = evaluate_recording_resource_budget(
        healthy_thirty_minute_samples(ai_status="disabled")
    )
    not_installed_report = evaluate_recording_resource_budget(
        healthy_thirty_minute_samples(ai_status="not_installed")
    )

    assert disabled_report.passed is True
    assert not_installed_report.passed is True


def test_budget_report_messages_are_safe_and_user_readable() -> None:
    report = evaluate_recording_resource_budget(
        healthy_thirty_minute_samples(
            ai_status="ready OPENAI_API_KEY=sk-test", model_loaded_index=2
        )
    )

    assert report.passed is False
    assert "OPENAI_API_KEY" not in report.violations[0].user_message
    assert "sk-test" not in report.violations[0].user_message
    assert "[REDACTED]" in report.violations[0].user_message


def test_budget_checks_do_not_import_heavy_model_modules() -> None:
    for module_name in HEAVY_MODEL_MODULES:
        sys.modules.pop(module_name, None)

    evaluate_recording_resource_budget(healthy_thirty_minute_samples())

    assert not any(module_name in sys.modules for module_name in HEAVY_MODEL_MODULES)


def test_budget_failure_does_not_mutate_session_rows_or_raw_events(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        save_budget_fixture(connection)
        before_session = session_row(connection)
        before_events = list_raw_events(connection, SESSION_ID)

        evaluate_recording_resource_budget(healthy_thirty_minute_samples(model_loaded_index=1))
        estimate_storage_growth(
            db_path=tmp_path / "worktrace.sqlite",
            screenshots_root=tmp_path / "screenshots",
        )

        after_session = session_row(connection)
        after_events = list_raw_events(connection, SESSION_ID)

        assert after_session == before_session
        assert [event.id for event in after_events] == [event.id for event in before_events]
    finally:
        connection.close()


def test_storage_growth_estimate_reads_database_and_screenshot_files(tmp_path: Path) -> None:
    db_path = tmp_path / "worktrace.sqlite"
    screenshots_root = tmp_path / "screenshots"
    screenshots_root.mkdir()
    (screenshots_root / "one.rgb").write_bytes(b"a" * 10)
    (screenshots_root / "nested").mkdir()
    (screenshots_root / "nested" / "two.rgb").write_bytes(b"b" * 15)
    connection = initialize_database(db_path)
    connection.close()

    storage = estimate_storage_growth(db_path=db_path, screenshots_root=screenshots_root)

    assert storage.db_bytes > 0
    assert storage.screenshot_bytes == 25


def test_resource_budget_table_is_deterministic() -> None:
    report = evaluate_recording_resource_budget(healthy_thirty_minute_samples())

    table = render_resource_budget_table(report)

    assert table == (
        "| metric | actual | budget | passed |\n"
        "| --- | ---: | ---: | --- |\n"
        "| duration_minutes | 30.00 | 30.00 | yes |\n"
        "| average_cpu_percent | 8.00 | 15.00 | yes |\n"
        "| peak_ram_mb | 640.00 | 800.00 | yes |\n"
        "| db_growth_mb | 35.00 | 100.00 | yes |\n"
        "| screenshot_mb_per_hour | 120.00 | 250.00 | yes |\n"
        "| model_loaded_during_recording | 0.00 | 0.00 | yes |"
    )


def healthy_thirty_minute_samples(
    *,
    final_db_mb: int = 35,
    final_screenshot_mb: int = 60,
    model_loaded_index: int | None = None,
    ai_status: str = "disabled",
) -> tuple[ResourceSample, ...]:
    return tuple(
        sample(
            index=index,
            cpu_percent=8,
            ram_mb=640,
            db_bytes=mb_to_bytes(round(final_db_mb * index / 29)),
            screenshot_bytes=mb_to_bytes(round(final_screenshot_mb * index / 29)),
            model_loaded=model_loaded_index == index,
            ai_status=ai_status,
        )
        for index in range(30)
    )


def sample(
    *,
    index: int,
    cpu_percent: float,
    ram_mb: float,
    db_bytes: int,
    screenshot_bytes: int,
    model_loaded: bool = False,
    ai_status: str = "disabled",
) -> ResourceSample:
    timestamp = datetime.fromisoformat(STARTED_AT) + timedelta(minutes=index)
    return ResourceSample(
        sampled_at=timestamp.isoformat(),
        cpu_percent=cpu_percent,
        ram_mb=ram_mb,
        db_bytes=db_bytes,
        screenshot_bytes=screenshot_bytes,
        model_loaded=model_loaded,
        ai_status=ai_status,
    )


def mb_to_bytes(value: int) -> int:
    return value * 1024 * 1024


def save_budget_fixture(connection: sqlite3.Connection) -> None:
    start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
    append_raw_events(
        connection,
        [
            normalize_terminal_command(
                session_id=SESSION_ID,
                timestamp="2026-05-06T09:01:00+05:30",
                command="uv run --python 3.13 pytest",
                shell="powershell",
                exit_code=0,
            )
        ],
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
    return dict(row)
