from __future__ import annotations

import json
import platform
import sqlite3
from collections.abc import Iterable, Mapping
from pathlib import Path

from worktrace_agent.db.migrations import get_applied_migrations, get_latest_schema_version
from worktrace_agent.observability.safe_logging import sanitize_for_log
from worktrace_agent.privacy.redaction import redact_json_value, redact_text

DEFAULT_LOG_LINE_LIMIT = 200


def export_debug_bundle(
    bundle_path: Path,
    *,
    logs_dir: Path,
    db_path: Path | None,
    app_version: str,
    generated_at: str,
    job_summary: Mapping[str, object] | None = None,
    model_summary: Mapping[str, object] | None = None,
    recent_error_categories: Iterable[str] = (),
    log_line_limit: int = DEFAULT_LOG_LINE_LIMIT,
) -> Path:
    payload = {
        "app": _app_summary(app_version=app_version, generated_at=generated_at),
        "database": _database_summary(db_path),
        "jobs": sanitize_for_log(dict(job_summary or {"status": "not_implemented"})),
        "models": sanitize_for_log(dict(model_summary or {"status": "not_loaded"})),
        "recent_error_categories": [redact_text(category) for category in recent_error_categories],
        "logs": _log_summary(logs_dir, line_limit=log_line_limit),
    }
    redacted_payload = redact_json_value(payload)

    resolved_path = Path(bundle_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = resolved_path.with_suffix(f"{resolved_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(redacted_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary_path.replace(resolved_path)
    return resolved_path


def _app_summary(*, app_version: str, generated_at: str) -> dict[str, str]:
    return {
        "name": "worktrace-local-agent",
        "version": redact_text(app_version),
        "generated_at": redact_text(generated_at),
        "python_version": platform.python_version(),
        "platform": platform.system(),
    }


def _database_summary(db_path: Path | None) -> dict[str, object]:
    summary: dict[str, object] = {
        "schema_version": get_latest_schema_version(),
        "applied_migrations": [],
        "available": False,
    }
    if db_path is None or not Path(db_path).exists():
        return summary

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        applied_migrations = get_applied_migrations(connection)
    finally:
        connection.close()

    summary["applied_migrations"] = applied_migrations
    summary["available"] = True
    return summary


def _log_summary(logs_dir: Path, *, line_limit: int) -> dict[str, object]:
    log_files = sorted(Path(logs_dir).glob("worktrace.log*"), key=lambda path: path.name)
    lines: list[str] = []
    for log_file in log_files:
        lines.extend(
            redact_text(line)
            for line in log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        )

    limited_lines = lines[-line_limit:] if line_limit > 0 else []
    return {
        "files": [log_file.name for log_file in log_files],
        "line_count": len(limited_lines),
        "lines": limited_lines,
    }
