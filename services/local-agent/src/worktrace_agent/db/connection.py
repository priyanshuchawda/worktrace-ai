import sqlite3
from pathlib import Path

from worktrace_agent.db.migrations import apply_migrations

DEFAULT_BUSY_TIMEOUT_MS = 5_000


def open_database(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite database with local-app safety pragmas enabled."""
    resolved_path = Path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(resolved_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute(f"PRAGMA busy_timeout = {DEFAULT_BUSY_TIMEOUT_MS};")
    connection.execute("PRAGMA journal_mode = WAL;")
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def initialize_database(db_path: Path) -> sqlite3.Connection:
    """Open a database and apply all pending versioned migrations."""
    connection = open_database(db_path)
    try:
        apply_migrations(connection)
    except Exception:
        connection.close()
        raise
    return connection
