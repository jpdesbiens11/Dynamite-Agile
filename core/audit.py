"""Audit trail: every write action is recorded with who, what, when."""
import json

from . import db


def log_action(conn, user_id, action, object_type, object_id=None, details=None, ip=None):
    """Insert one audit entry in the caller's transaction."""
    conn.execute(
        "INSERT INTO audit_log (ts, user_id, action, object_type, object_id, details, ip) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (db.utc_now(), user_id, action, object_type,
         None if object_id is None else str(object_id),
         json.dumps(details, ensure_ascii=False) if details else None,
         ip),
    )


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
