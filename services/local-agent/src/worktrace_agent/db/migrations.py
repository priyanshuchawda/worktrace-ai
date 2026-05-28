import re
import sqlite3
from pathlib import Path

MIGRATION_NAME_PATTERN = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$")
ADD_COLUMN_PATTERN = re.compile(
    r"ALTER\s+TABLE\s+(?P<table>[a-zA-Z_][a-zA-Z0-9_]*)\s+ADD\s+COLUMN\s+"
    r"(?P<column>[a-zA-Z_][a-zA-Z0-9_]*)(?P<definition>.*)",
    re.IGNORECASE,
)
DEFAULT_MIGRATIONS_DIR = Path(__file__).with_name("migrations")


def get_applied_migrations(connection: sqlite3.Connection) -> list[str]:
    _ensure_migration_table(connection)
    rows = connection.execute(
        "SELECT filename FROM schema_migrations ORDER BY filename ASC"
    ).fetchall()
    return [str(row["filename"]) for row in rows]


def get_latest_schema_version(migrations_dir: Path | None = None) -> str:
    migration_files = _migration_files(migrations_dir or DEFAULT_MIGRATIONS_DIR)
    if not migration_files:
        return "none"
    return migration_files[-1].name


def apply_migrations(
    connection: sqlite3.Connection,
    migrations_dir: Path | None = None,
) -> list[str]:
    _ensure_migration_table(connection)

    applied = set(get_applied_migrations(connection))
    applied_now: list[str] = []

    for migration_file in _migration_files(migrations_dir or DEFAULT_MIGRATIONS_DIR):
        if migration_file.name in applied:
            continue

        sql = migration_file.read_text(encoding="utf-8")
        if _is_add_column_only_migration(sql):
            _apply_add_column_migration(connection, migration_file.name, sql)
            applied_now.append(migration_file.name)
            continue

        safe_filename = migration_file.name.replace("'", "''")
        migration_script = (
            "BEGIN;\n"  # nosec B608
            + sql
            + "\nINSERT INTO schema_migrations (filename) VALUES ('"  # nosec B608
            + safe_filename
            + "');\nCOMMIT;\n"
        )
        try:
            connection.executescript(migration_script)
        except sqlite3.OperationalError as error:
            connection.rollback()
            if _is_duplicate_column_error(error) and _added_columns_exist(
                connection, migration_file.read_text(encoding="utf-8")
            ):
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations (filename) VALUES (?)",
                    (migration_file.name,),
                )
                connection.commit()
                applied_now.append(migration_file.name)
                continue
            raise
        except sqlite3.Error:
            connection.rollback()
            raise
        applied_now.append(migration_file.name)

    return applied_now


def _migration_files(migrations_dir: Path) -> list[Path]:
    files = sorted(Path(migrations_dir).glob("*.sql"), key=lambda path: path.name)
    for migration_file in files:
        if not MIGRATION_NAME_PATTERN.match(migration_file.name):
            raise ValueError(f"Invalid migration filename: {migration_file.name}")
    return files


def _ensure_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          filename TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()


def _is_duplicate_column_error(error: sqlite3.OperationalError) -> bool:
    return "duplicate column name" in str(error).lower()


def _is_add_column_only_migration(sql: str) -> bool:
    statements = _sql_statements(sql)
    if not statements:
        return False
    return all(ADD_COLUMN_PATTERN.fullmatch(statement) for statement in statements)


def _apply_add_column_migration(
    connection: sqlite3.Connection,
    migration_name: str,
    sql: str,
) -> None:
    with connection:
        for statement in _sql_statements(sql):
            match = ADD_COLUMN_PATTERN.fullmatch(statement)
            if match is None:
                raise sqlite3.OperationalError("migration contains non ADD COLUMN statement")
            table = match.group("table")
            column = match.group("column")
            if _column_exists(connection, table, column):
                continue
            connection.execute(statement)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (filename) VALUES (?)",
            (migration_name,),
        )


def _added_columns_exist(connection: sqlite3.Connection, sql: str) -> bool:
    additions = [
        (match.group("table"), match.group("column")) for match in ADD_COLUMN_PATTERN.finditer(sql)
    ]
    if not additions:
        return False

    for table, column in additions:
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()  # nosec B608
        columns = {str(row["name"]) for row in rows}
        if column not in columns:
            return False
    return True


def _column_exists(connection: sqlite3.Connection, table: str, column: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()  # nosec B608
    columns = {str(row["name"]) for row in rows}
    return column in columns


def _sql_statements(sql: str) -> list[str]:
    return [statement.strip() for statement in sql.split(";") if statement.strip()]
