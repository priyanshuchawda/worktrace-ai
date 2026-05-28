import json
import logging
from pathlib import Path

from worktrace_agent import __version__
from worktrace_agent.db.connection import initialize_database
from worktrace_agent.observability.debug_bundle import export_debug_bundle
from worktrace_agent.observability.safe_logging import setup_rotating_local_logger, write_safe_log
from worktrace_agent.privacy.redaction import PRIVACY_TEST_CORPUS, count_privacy_leaks


def test_safe_log_writer_redacts_secrets_and_omits_private_surfaces(tmp_path: Path) -> None:
    logger = setup_rotating_local_logger(
        tmp_path / "logs",
        logger_name="worktrace.test.safe",
        max_bytes=10_000,
        backup_count=1,
    )

    write_safe_log(
        logger,
        level="info",
        category="capture_error",
        message=f"Failed capture with {PRIVACY_TEST_CORPUS[0]}",
        metadata={
            "session_id": "sess_observe_001",
            "screenshot_bytes": "raw-image-bytes",
            "raw_clipboard_text": "copied private clipboard",
            "full_prompt": "summarize this private prompt",
            "safe_error_category": "capture_error",
        },
    )

    text = _read_logs(tmp_path / "logs")

    assert count_privacy_leaks(text) == 0
    assert "raw-image-bytes" not in text
    assert "copied private clipboard" not in text
    assert "summarize this private prompt" not in text
    assert "screenshot_bytes" not in text
    assert "raw_clipboard_text" not in text
    assert "full_prompt" not in text
    assert "sess_observe_001" in text
    assert "safe_error_category" in text


def test_local_logs_rotate_when_size_limit_is_exceeded(tmp_path: Path) -> None:
    logger = setup_rotating_local_logger(
        tmp_path / "logs",
        logger_name="worktrace.test.rotate",
        max_bytes=240,
        backup_count=2,
    )

    for index in range(20):
        write_safe_log(
            logger,
            level="info",
            category="rotation_test",
            message=f"rotation message {index}",
            metadata={"index": index, "padding": "x" * 80},
        )

    log_files = sorted(path.name for path in (tmp_path / "logs").glob("worktrace.log*"))

    assert "worktrace.log" in log_files
    assert "worktrace.log.1" in log_files


def test_debug_bundle_includes_safe_summaries_and_no_test_secrets(tmp_path: Path) -> None:
    db_path = tmp_path / "worktrace.sqlite"
    connection = initialize_database(db_path)
    connection.close()

    logger = setup_rotating_local_logger(
        tmp_path / "logs",
        logger_name="worktrace.test.bundle",
        max_bytes=10_000,
        backup_count=1,
    )
    write_safe_log(
        logger,
        level="error",
        category="sidecar_error",
        message=f"Sidecar failed with {PRIVACY_TEST_CORPUS[1]}",
        metadata={
            "session_id": "sess_bundle_001",
            "clipboard_text": "raw clipboard should not ship",
            "prompt": "full prompt should not ship",
        },
    )

    bundle_path = export_debug_bundle(
        tmp_path / "debug" / "bundle.json",
        logs_dir=tmp_path / "logs",
        db_path=db_path,
        app_version=__version__,
        generated_at="2026-05-06T12:00:00+05:30",
        recent_error_categories=("SIDECAR_UNAVAILABLE",),
    )

    bundle_text = bundle_path.read_text(encoding="utf-8")
    bundle = json.loads(bundle_text)

    assert count_privacy_leaks(bundle_text) == 0
    assert "raw clipboard should not ship" not in bundle_text
    assert "full prompt should not ship" not in bundle_text
    assert bundle["app"]["version"] == __version__
    assert bundle["database"]["schema_version"] == "004_session_organization.sql"
    assert bundle["database"]["applied_migrations"] == [
        "001_initial.sql",
        "002_screenshots.sql",
        "003_ocr_results.sql",
        "004_session_organization.sql",
    ]
    assert bundle["jobs"] == {"status": "not_implemented"}
    assert bundle["models"] == {"status": "not_loaded"}
    assert bundle["recent_error_categories"] == ["SIDECAR_UNAVAILABLE"]
    assert bundle["logs"]["line_count"] >= 1


def _read_logs(log_dir: Path) -> str:
    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            for handler in logger.handlers:
                handler.flush()
    return "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(log_dir.glob("worktrace.log*"))
    )
