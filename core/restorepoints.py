"""Restore points of the data (core lot v0.28, D-B-104): « 2 × 3 chances » with the code backups of Admin → Update.

A point is an exact copy of the database (SQLite backup API, rollback-journal mode so it opens read-only), taken:
- automatically before an operation that changes many things at once: a framework update or a return to an older
  code, a data import, a configuration applied, a return of the whole site to a point;
- once a day, at the first request of the day (« quotidien »: the state at the end of the day before);
- on demand (« Créer un point maintenant »).
Only the 3 most recent points are kept (data/restore_points/<name>.sqlite + <name>.json). Files of the attachments are
never in a point: they are never deleted except with a Space, which keeps its own « avant suppression » backup.

Two ways back, both journalled:
- one Space of a point, restored as a NEW Space (core/backup.restore: nothing in service is overwritten);
- the whole site back to a point: a point « avant retour » is taken first, the journal of audit written since the
  point is kept, the sessions are closed (everybody signs in again), the migrations of the running code are applied.
"""
import datetime as dt
import json
import re
import sqlite3
import threading
import time
import types
from pathlib import Path

from . import APP_VERSION, audit, backup, db, modules, permissions, startup
from .errors import ApiError

KEEP = 3
FOLDER = "restore_points"
NAME_RE = re.compile(r"^data_\d{8}-\d{6}(-\d)?_[a-z-]+$")
LABELS = {
    "avant-update": "Avant une mise à jour du Framework",
    "avant-retour-code": "Avant un retour à une version du code",
    "avant-import": "Avant un import de données",
    "avant-config": "Avant une configuration appliquée",
    "avant-retour": "Avant un retour de tout le site à un point",
    "quotidien": "Point quotidien (début de journée)",
    "manuel": "Créé à la main",
}
_lock = threading.Lock()
_checked = {}  # data_dir -> local date already checked for the daily point


def folder(data_dir):
    path = Path(data_dir) / FOLDER
    path.mkdir(parents=True, exist_ok=True)
    return path


def _meta(path):
    try:
        return json.loads(path.with_suffix(".json").read_text("utf-8"))
    except (OSError, ValueError):
        return None


def points(data_dir):
    """Every point kept, newest first (a .sqlite without its .json is ignored)."""
    out = []
    for path in folder(data_dir).glob("data_*.sqlite"):
        meta = _meta(path)
        if meta and NAME_RE.match(path.stem):
            meta["size"] = path.stat().st_size
            out.append(meta)
    return sorted(out, key=lambda m: (m.get("ts") or 0, m["created_at"]), reverse=True)  # ts: two points in one second


def prune(data_dir, keep=KEEP):
    removed = []
    for meta in points(data_dir)[keep:]:
        for suffix in (".sqlite", ".json"):
            try:
                (folder(data_dir) / (meta["name"] + suffix)).unlink()
            except OSError:
                pass
        removed.append(meta["name"])
    return removed


def create(data_dir, reason, by="", label="", note="", keep=KEEP):
    """Copy the live database into a new point; returns its description. keep=None: no pruning (done by the caller)."""
    if reason not in LABELS:
        raise ValueError("unknown restore point reason: " + reason)
    now = dt.datetime.now()
    stem = "data_{}_{}".format(now.strftime("%Y%m%d-%H%M%S"), reason)
    base = folder(data_dir)
    for n in range(1, 10):  # two points in the same second
        if not (base / (stem + ".sqlite")).exists():
            break
        stem = "data_{}-{}_{}".format(now.strftime("%Y%m%d-%H%M%S"), n, reason)
    path = base / (stem + ".sqlite")
    src = sqlite3.connect(str(db._db_path), timeout=10)
    try:
        out = sqlite3.connect(str(path))
        try:
            src.backup(out)
            out.execute("PRAGMA journal_mode=DELETE")  # a single file, readable in read-only mode
            spaces = out.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            users = out.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            audit_max = out.execute("SELECT COALESCE(MAX(id), 0) FROM audit_log").fetchone()[0]
        finally:
            out.close()
    finally:
        src.close()
    meta = {"name": stem, "created_at": db.utc_now(), "ts": time.time(), "day": now.date().isoformat(), "local": now.strftime("%Y-%m-%d %H:%M"),
            "reason": reason, "label": label or LABELS[reason], "by": by or "automatique", "version": APP_VERSION,
            "note": str(note or "")[:200], "spaces": spaces, "users": users, "audit_max_id": audit_max}
    path.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    if keep:
        prune(data_dir, keep)
    return meta


def before(ctx, reason, label=""):
    """The point taken by an operation, journalled in its transaction."""
    meta = create(ctx.data_dir, reason, by=ctx.user["display_name"], label=label)
    audit.log_action(ctx.conn, ctx.user["id"], "restore_point_created", "restore_point", None,
                     {"name": meta["name"], "reason": reason}, ctx.ip)
    return meta


def daily(data_dir, config):
    """Called by the router before each API request: the first one of the day takes the daily point."""
    if not data_dir or db._db_path is None or (config or {}).get("restore_daily", True) is False:
        return None
    today = dt.date.today().isoformat()
    key = str(data_dir)
    if _checked.get(key) == today:
        return None
    with _lock:
        if _checked.get(key) == today:
            return None
        meta = None
        if not any(p["reason"] == "quotidien" and p.get("day") == today for p in points(data_dir)):
            meta = create(data_dir, "quotidien")
        _checked[key] = today
        return meta


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
def _point(ctx):
    name = str(ctx.params.get("name") or "")
    path = folder(ctx.data_dir) / (name + ".sqlite")
    if not NAME_RE.match(name) or not path.exists() or _meta(path) is None:
        raise ApiError(404, "Point de restauration « {} » introuvable (effacé : seuls les {} plus récents sont gardés). "
                            "Correctif : rechargez la page.".format(name, KEEP))
    return path, _meta(path)


def _read_only(path):
    conn = sqlite3.connect("file:{}?mode=ro".format(path.as_posix()), uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def api_list(ctx):
    permissions.require_admin(ctx.user)
    from . import update  # update imports this module
    return {"keep": KEEP, "points": points(ctx.data_dir), "framework": update.code_versions(ctx), "version": APP_VERSION}


def api_create(ctx):
    permissions.require_admin(ctx.user)
    meta = create(ctx.data_dir, "manuel", by=ctx.user["display_name"], note=ctx.body.get("note"))
    audit.log_action(ctx.conn, ctx.user["id"], "restore_point_created", "restore_point", None,
                     {"name": meta["name"], "reason": "manuel"}, ctx.ip)
    return {"point": meta, "points": points(ctx.data_dir)}


def api_spaces(ctx):
    """The Spaces of a point, and whether each one still exists now."""
    permissions.require_admin(ctx.user)
    path, meta = _point(ctx)
    conn = _read_only(path)
    try:
        rows = [dict(r) for r in conn.execute("SELECT id, key, name, is_archived FROM projects ORDER BY key")]
    finally:
        conn.close()
    live = {r["key"] for r in ctx.conn.execute("SELECT key FROM projects")}
    retired = {r["key"] for r in ctx.conn.execute("SELECT key FROM retired_project_keys")}
    for r in rows:
        r["exists_now"] = r["key"] in live
        r["suggested_key"] = r["key"] if r["key"] not in live else _free_key(r["key"], live | retired)
    return {"point": meta, "spaces": rows}


def _free_key(key, taken):
    for suffix in ("R", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"):
        candidate = (key[:10 - len(suffix)] + suffix).upper()
        if candidate not in taken:
            return candidate
    return ""


def api_restore_space(ctx):
    """One Space of the point, as a NEW Space (never over a Space in service)."""
    permissions.require_admin(ctx.user)
    path, meta = _point(ctx)
    key = str(ctx.body.get("key") or "").strip().upper()
    conn = _read_only(path)
    try:
        row = conn.execute("SELECT id FROM projects WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise ApiError(404, "Le Space {} n'existe pas dans ce point. Correctif : choisissez-le dans la liste.".format(key))
        shim = types.SimpleNamespace(conn=conn, data_dir=ctx.data_dir, user=ctx.user)
        _name, data, manifest = backup.build(shim, row["id"], "point")
    finally:
        conn.close()
    files = manifest["counts"].get("attachments", 0)
    result = backup.restore(ctx, data, ctx.body.get("new_key") or key, ctx.body.get("new_name"), skip_conflicts=True)
    # the files of a Space deleted since the point are in its « avant suppression » backup, not on disk any more
    result["missing_files"] = max(0, files - result.get("files", 0))
    audit.log_action(ctx.conn, ctx.user["id"], "restore_point_space", "project", result["project"]["id"],
                     {"point": meta["name"], "from": key, "key": result["project"]["key"],
                      "skipped": result.get("skipped", {})}, ctx.ip)
    return result


def api_revert(ctx):
    """The whole site back to the point (the code does not change)."""
    permissions.require_admin(ctx.user)
    path, meta = _point(ctx)
    if str(ctx.body.get("confirm") or "") != meta["name"]:
        raise ApiError(400, "Confirmation incorrecte. Correctif : renvoyez le nom exact du point ({}).".format(meta["name"]))
    who, user_id, ip = ctx.user["display_name"], ctx.user["id"], ctx.ip
    ctx.conn.commit()
    safety = create(ctx.data_dir, "avant-retour", by=who, keep=None)  # pruned once the return is done
    since = [dict(r) for r in ctx.conn.execute(
        "SELECT a.ts, a.user_id, a.action, a.object_type, a.object_id, a.details, a.ip, u.username "
        "FROM audit_log a LEFT JOIN users u ON u.id = a.user_id WHERE a.id > ? ORDER BY a.id", (meta.get("audit_max_id", 0),))]
    src = sqlite3.connect(str(path))
    try:
        src.backup(ctx.conn)  # the whole database replaced, page by page, in the live file
    finally:
        src.close()
    ctx.conn.execute("DELETE FROM sessions")  # a session closed since the point never comes back
    users = {r["id"]: r["username"] for r in ctx.conn.execute("SELECT id, username FROM users")}
    for a in since:  # the journal of audit is never taken back
        keep_user = a["user_id"] in users and users[a["user_id"]] == a["username"]
        details = a["details"] if keep_user or not a["username"] else json.dumps(
            {"compte": a["username"], "details": a["details"]}, ensure_ascii=False)
        ctx.conn.execute("INSERT INTO audit_log (ts, user_id, action, object_type, object_id, details, ip) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (a["ts"], a["user_id"] if keep_user else None, a["action"], a["object_type"], a["object_id"], details, a["ip"]))
    ctx.conn.commit()
    db.init_db(db._db_path, modules.registered_schema(), modules.registered_migrations())  # schema of the running code
    startup.run(ctx.data_dir, ctx.config)
    keep_user = users.get(user_id) == ctx.user["username"] if "username" in ctx.user.keys() else False
    audit.log_action(ctx.conn, user_id if keep_user else None, "data_reverted", "restore_point", None,
                     {"point": meta["name"], "point_at": meta["local"], "by": who, "safety_point": safety["name"],
                      "audit_rows_kept": len(since)}, ip)
    prune(ctx.data_dir)
    return {"ok": True, "point": meta, "safety_point": safety["name"], "audit_rows_kept": len(since), "signed_out": True}


P = r"/api/admin/restore-points/(?P<name>data_[0-9_a-z-]+)"
ROUTES = [
    ("GET", r"/api/admin/restore-points", api_list, "admin"),
    ("POST", r"/api/admin/restore-points", api_create, "admin"),
    ("GET", P + r"/spaces", api_spaces, "admin"),
    ("POST", P + r"/space", api_restore_space, "admin"),
    ("POST", P + r"/revert", api_revert, "admin"),
]
