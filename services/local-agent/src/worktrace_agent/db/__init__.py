"""SQLite storage foundation for the WorkTrace local agent."""

from worktrace_agent.db.connection import initialize_database, open_database
from worktrace_agent.db.migrations import apply_migrations, get_applied_migrations

__all__ = [
    "apply_migrations",
    "get_applied_migrations",
    "initialize_database",
    "open_database",
]
