"""Audit trail: every write action is recorded with who, what, when.

Core lot v0.39 (0.60.120, D-O-133): each entry also keeps, at the time of the write, the three-letter traceability key of
its author (`initials`, so an old line keeps the key it was made with), its `source` (NULL by hand, « ai » for the answer of
an AI assistant applied by a round trip, « import » for a file) and the Space it touches when the object is a row of a
table tied to a Space (`project_id`) -- what « Changements » (core/changes.py) lists, even after the row is deleted.
"""
import contextlib
import contextvars
import json
import sqlite3

from . import db

_SOURCE = contextvars.ContextVar("audit_source", default=None)
SOURCES = ("ai", "import")
_TABLES = {}  # object type -> table tied to a Space (or None), read once per process


@contextlib.contextmanager
def source(name):
    """with audit.source("ai"): every entry written inside comes from an AI assistant (or « import »: a file)."""
    token = _SOURCE.set(name if name in SOURCES else None)
    try:
        yield
    finally:
        _SOURCE.reset(token)


def space_table(conn, object_type):
    """The table of a Space that an object type names (« diamond_functions », « agile_issue » -> agile_issues), or None."""
    if object_type not in _TABLES:
        found = None
        for name in (object_type, object_type + "s", object_type + "es"):
            cols = {r[1] for r in conn.execute('PRAGMA table_info("{}")'.format(name.replace('"', "")))}
            if {"id", "project_id"} <= cols:
                found = name
                break
        _TABLES[object_type] = found
    return _TABLES[object_type]


def _project(conn, object_type, object_id):
    if object_id is None:
        return None
    if object_type in ("project", "projects"):
        return int(object_id) if str(object_id).isdigit() else None
    table = space_table(conn, object_type)
    if not table or not str(object_id).isdigit():
        return None
    row = conn.execute('SELECT project_id FROM "{}" WHERE id = ?'.format(table), (int(object_id),)).fetchone()
    return row[0] if row else None


def _initials(conn, user_id):
    if not user_id:
        return None
    row = conn.execute("SELECT prefs FROM user_prefs WHERE user_id = ?", (user_id,)).fetchone()
    try:
        value = str(json.loads(row[0]).get("initials") or "").upper() if row else ""
    except (TypeError, ValueError):
        value = ""
    return value or None


def log_action(conn, user_id, action, object_type, object_id=None, details=None, ip=None, project_id=None):
    """Insert one audit entry in the caller's transaction."""
    try:
        pid = project_id if project_id is not None else _project(conn, object_type, object_id)
        initials = _initials(conn, user_id)
    except Exception:  # noqa: BLE001 -- the trail never blocks a write: the snapshot is a convenience
        pid, initials = project_id, None
    base = (db.utc_now(), user_id, action, object_type, None if object_id is None else str(object_id),
            json.dumps(details, ensure_ascii=False) if details else None, ip)
    try:
        conn.execute("INSERT INTO audit_log (ts, user_id, action, object_type, object_id, details, ip, initials, source, project_id) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", base + (initials, _SOURCE.get(), pid))
    except sqlite3.OperationalError as exc:  # a database not migrated yet (a site brought back to an old point)
        if "column" not in str(exc):
            raise
        conn.execute("INSERT INTO audit_log (ts, user_id, action, object_type, object_id, details, ip) VALUES (?, ?, ?, ?, ?, ?, ?)", base)


def recent(conn, limit=200):
    """Return the most recent entries, newest first."""
    limit = max(1, min(int(limit), 1000))
    result = conn.execute(
        "SELECT a.id, a.ts, a.user_id, u.username, a.action, a.object_type, "
        "a.object_id, a.details, a.ip "
        "FROM audit_log a LEFT JOIN users u ON u.id = a.user_id "
        "ORDER BY a.id DESC LIMIT ?", (limit,)).fetchall()
    entries = db.rows(result)
    for entry in entries:
        if entry["details"]:
            try:
                entry["details"] = json.loads(entry["details"])
            except ValueError:
                pass
    return entries
