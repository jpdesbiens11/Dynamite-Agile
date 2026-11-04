"""SQLite access for Dynamite | Agile.

One short-lived connection is opened per HTTP request. WAL journal mode
lets many readers work while one writer commits, which is plenty for
10 to 30 users. Each build step adds its tables with CREATE IF NOT EXISTS,
so upgrading never deletes existing data.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id                   INTEGER PRIMARY KEY,
    username             TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name         TEXT NOT NULL,
    password_hash        TEXT NOT NULL,
    is_admin             INTEGER NOT NULL DEFAULT 0,
    is_active            INTEGER NOT NULL DEFAULT 1,
    must_change_password INTEGER NOT NULL DEFAULT 1,
    created_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf_token TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    ip         TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS projects (
    id                 INTEGER PRIMARY KEY,
    key                TEXT NOT NULL UNIQUE,
    name               TEXT NOT NULL,
    description        TEXT NOT NULL DEFAULT '',
    next_ticket_number INTEGER NOT NULL DEFAULT 1,
    is_archived        INTEGER NOT NULL DEFAULT 0,
    created_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memberships (
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role       TEXT NOT NULL CHECK (role IN ('reader', 'editor')),
    PRIMARY KEY (user_id, project_id)
);
CREATE INDEX IF NOT EXISTS idx_memberships_project ON memberships(project_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY,
    ts          TEXT NOT NULL,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id   TEXT,
    details     TEXT,
    ip          TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);

CREATE TABLE IF NOT EXISTS schema_migrations (
    module     TEXT NOT NULL,
    version    INTEGER NOT NULL,
    applied_at TEXT NOT NULL,
    PRIMARY KEY (module, version)
);
"""

_db_path = None


def init_db(db_path, extra_schema="", migrations=()):
    """Create the database file and all tables if they do not exist.

    `extra_schema` is the concatenated SCHEMA of every registered business
    module (see core/modules.py) -- applied after the core tables so a
    module's CREATE TABLE can reference `projects(id)`.

    `migrations` is a sequence of (module_key, version, sql) tuples. Each
    one runs exactly once, in version order per module, and is recorded in
    schema_migrations. Use it for any change to a table already in service
    (ALTER TABLE ADD COLUMN, new index, data fix...).
    """
    global _db_path
    _db_path = Path(db_path)
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_db_path), timeout=10)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        if extra_schema.strip():
            conn.executescript(extra_schema)
        conn.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
                     (str(SCHEMA_VERSION),))
        conn.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'",
                     (str(SCHEMA_VERSION),))
        conn.commit()
        apply_migrations(conn, migrations)
    finally:
        conn.close()


def apply_migrations(conn, migrations):
    """Run pending (module, version, sql) migrations; return how many ran."""
    done = {(row[0], row[1]) for row in
            conn.execute("SELECT module, version FROM schema_migrations")}
    count = 0
    for module, version, sql in sorted(migrations, key=lambda m: (m[0], m[1])):
        if (module, version) in done:
            continue
        # executescript() commits first, so each migration is its own unit.
        conn.executescript("BEGIN;\n" + sql + "\nINSERT INTO schema_migrations "
                           "(module, version, applied_at) VALUES ('{}', {}, '{}');\nCOMMIT;"
                           .format(module.replace("'", ""), int(version), utc_now()))
        count += 1
    return count


@contextmanager
def connect():
    """Yield a connection; commit on success, roll back on any error."""
    if _db_path is None:
        raise RuntimeError("Database not initialised: call init_db() first")
    conn = sqlite3.connect(str(_db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def sqlite_version():
    return sqlite3.sqlite_version


def utc_now():
    """Current UTC time as ISO 8601 text (sortable as a string)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_in(hours):
    """UTC time `hours` from now, same format as utc_now()."""
    moment = datetime.now(timezone.utc) + timedelta(hours=float(hours))
    return moment.replace(microsecond=0).isoformat()


def rows(result):
    """Convert sqlite3.Row objects to plain dicts for JSON output."""
    return [dict(row) for row in result]
