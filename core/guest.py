"""0.60.63 (D-O-072): guest access -- anyone can look at a public instance without an account or a password.

Off by default. The administrator turns it on (Admin → Comptes → Accès invité) and picks the Spaces guests see
(the DEMO Space, by default). A visitor clicks « Entrer en invité » on the sign-in page and gets a session of the
account `invite`, a reader of those Spaces only -- each visitor has their own session, nobody types a password.

Read-only, enforced by the server (router.py calls guard() before every handler): every write is refused except
signing out, the privacy events and the PDF / Word export of a Dynamite page (exporting is allowed on purpose: the
tool is free and is shown off). Admin, Settings, password and initials stay closed; 0.60.66: the team's timesheets of the
guest's Spaces are read-only (modules/timesheet/manage.py), the language stays in the browser (admin routes
are admin-only; writes are refused). Guest sign-ins are limited per IP address and journalled.
"""
import json
import re
import secrets
import threading
import time

from . import audit, auth, db, permissions, prefs, validate
from .errors import ApiError

USERNAME = permissions.GUEST_USERNAME
DISPLAY_NAME = "Invité (lecture seule)"
SESSION_HOURS = 8
MAX_PER_HOUR = 30  # guest sign-ins per IP address and per hour
# The only writes a guest may make.
ALLOWED_WRITES = re.compile(r"/api/(logout|privacy/event)|/api/dynamite/p/\d+/pages/\d+/export\.(pdf|docx)")
READ_ONLY = ("Mode invité : lecture seule. Cette action demande un compte d'équipe. Correctif : installez Dynamite | Agile "
             "pour votre équipe (gratuit, open source), ou demandez un compte à l'administrateur.")

_hits = {}
_lock = threading.Lock()


def settings(conn):
    row = conn.execute("SELECT value FROM app_settings WHERE key = 'guest'").fetchone()
    value = {"enabled": False, "projects": []}
    if row:
        try:
            raw = json.loads(row["value"])
            value["enabled"] = bool(raw.get("enabled"))
            value["projects"] = [int(p) for p in raw.get("projects", []) if isinstance(p, int)]
        except (ValueError, AttributeError):
            pass
    return value


def enabled(conn):
    return settings(conn)["enabled"]


def is_guest(user):
    return bool(user) and permissions.is_guest(user)


def guard(session, method, path):
    """Called by the router: a guest reads, never writes (except the few ALLOWED_WRITES)."""
    if session is not None and method != "GET" and is_guest(session) and not ALLOWED_WRITES.fullmatch(path):
        raise ApiError(403, READ_ONLY)


def _account(conn):
    """The `invite` account, created on first use; its password is random and never shown (nobody signs in with it)."""
    row = conn.execute("SELECT * FROM users WHERE username = ?", (USERNAME,)).fetchone()
    if row is None:
        conn.execute("INSERT INTO users (username, display_name, password_hash, is_admin, is_active, must_change_password, "
                     "created_at) VALUES (?, ?, ?, 0, 1, 0, ?)",
                     (USERNAME, DISPLAY_NAME, auth.hash_password(secrets.token_urlsafe(32)), db.utc_now()))
        row = conn.execute("SELECT * FROM users WHERE username = ?", (USERNAME,)).fetchone()
    return row


def _sync(conn, value):
    """The account is active while guest access is on, inactive otherwise (its sessions end). Which Spaces it reads
    comes from the setting itself (permissions.guest_projects), never from membership rows."""
    user = _account(conn)
    conn.execute("UPDATE users SET is_admin = 0, must_change_password = 0, is_active = ? WHERE id = ?",
                 (1 if value["enabled"] else 0, user["id"]))
    prefs._put(conn, user["id"], {"can_export": True})  # exporting is allowed on purpose (the tool is shown off)
    if not value["enabled"]:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
    return user


def _rate(ip):
    now = time.time()
    with _lock:
        recent = [t for t in _hits.get(ip, []) if now - t < 3600]
        if len(recent) >= MAX_PER_HOUR:
            raise ApiError(429, "Trop de visites invité depuis cette adresse. Correctif : réessayez dans une heure.")
        recent.append(now)
        _hits[ip] = recent


def api_login(ctx):
    """POST /api/login/guest -- opens a guest session (no password)."""
    value = settings(ctx.conn)
    if not value["enabled"]:
        raise ApiError(403, "L'accès invité n'est pas ouvert sur ce serveur.")
    _rate(ctx.ip)
    user = _sync(ctx.conn, value)
    auth.purge_expired_sessions(ctx.conn)
    hours = min(float(ctx.config.get("session_hours", SESSION_HOURS)), SESSION_HOURS)
    token, csrf = auth.create_session(ctx.conn, user["id"], ctx.ip, hours)
    audit.log_action(ctx.conn, user["id"], "guest_login", "user", user["id"], None, ctx.ip)
    ctx.set_session_cookie(token, int(hours * 3600))
    from . import session_api
    return session_api._me_payload(ctx.conn, ctx.conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone(),
                                   csrf, ctx.ip)


def _payload(conn):
    value = settings(conn)
    projects = [dict(r) for r in conn.execute("SELECT id, key, name FROM projects WHERE is_archived = 0 ORDER BY key")]
    return {"guest": value, "projects": projects,
            "sessions": conn.execute("SELECT COUNT(*) FROM sessions s JOIN users u ON u.id = s.user_id "
                                     "WHERE u.username = ? AND s.expires_at > ?", (USERNAME, db.utc_now())).fetchone()[0]}


def api_admin_get(ctx):
    return _payload(ctx.conn)


def api_admin_put(ctx):
    current = settings(ctx.conn)
    if "enabled" in ctx.body:
        current["enabled"] = validate.boolean(ctx.body, "enabled")
    if "projects" in ctx.body:
        raw = ctx.body.get("projects")
        if not isinstance(raw, list) or not all(isinstance(p, int) for p in raw):
            raise ApiError(400, "Spaces invalides : une liste d'identifiants est attendue.")
        known = {r["id"] for r in ctx.conn.execute("SELECT id FROM projects WHERE is_archived = 0")}
        current["projects"] = sorted({p for p in raw if p in known})
    if current["enabled"] and not current["projects"]:
        raise ApiError(400, "Choisissez au moins un Space visible par les invités avant d'ouvrir l'accès.")
    ctx.conn.execute("INSERT INTO app_settings (key, value, updated_by, updated_at) VALUES ('guest', ?, ?, ?) "
                     "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_by = excluded.updated_by, "
                     "updated_at = excluded.updated_at", (json.dumps(current), ctx.user["id"], db.utc_now()))
    _sync(ctx.conn, current)
    audit.log_action(ctx.conn, ctx.user["id"], "guest_access_changed", "settings", None, current, ctx.ip)
    return _payload(ctx.conn)


ROUTES = [
    ("POST", r"/api/login/guest", api_login, "public"),
    ("GET", r"/api/admin/guest", api_admin_get, "admin"),
    ("PUT", r"/api/admin/guest", api_admin_put, "admin"),
]
