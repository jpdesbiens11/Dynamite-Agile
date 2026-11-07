"""0.60.73 (D-O-079): « Mot de passe oublié ? » -- a single-use link by e-mail.

1. POST /api/password/forgot {login}: an identifier or an e-mail. The answer is ALWAYS the same, found or not, and
   comes back before the mail is sent (core.mail.send_later): nobody learns from it which accounts exist. A link is
   sent only to an active team account that has an e-mail (never the guest, never the inactive demo accounts), when
   Admin → Courriel is on. Limits: 5 requests per hour per IP address, 3 links per hour per account.
2. The link https://<tool>/#reset=<token> (the token stays in the browser: a fragment is never sent to a server
   nor in a Referer) opens the « Nouveau mot de passe » card. The token is random (32 bytes), stored hashed,
   good for 30 minutes and once.
   0.60.76 (D-O-082): the page checks the token by POST /api/password/reset/check {token} -- never in an address,
   which the server log and every reverse proxy write down in clear.
3. POST /api/password/reset {token, new_password}: same rules as any password (12 characters, not the identifier);
   every session of the account is closed, the other links of the account die, and it is journalled.
"""
import datetime as dt
import hashlib
import secrets
import threading
import time

from . import audit, auth, db, mail, permissions
from .errors import ApiError

MINUTES = 30
PER_IP_HOUR = 5
PER_USER_HOUR = 3
SENT = ("Si un compte correspond, un lien vient d'être envoyé à son courriel. Il est valide 30 minutes. Rien reçu ? "
        "Vérifiez les indésirables, ou demandez à votre administrateur.")
EXPIRED = "Lien expiré ou déjà utilisé. Correctif : redemandez « Mot de passe oublié ? » sur la page de connexion."

_hits = {}
_lock = threading.Lock()


def _hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _rate(ip):
    now = time.time()
    with _lock:
        prune(_hits, now, 3600)
        recent = [t for t in _hits.get(ip, []) if now - t < 3600]
        if len(recent) >= PER_IP_HOUR:
            raise ApiError(429, "Trop de demandes depuis cette adresse. Correctif : réessayez dans une heure.")
        recent.append(now)
        _hits[ip] = recent


def prune(hits, now, window, keep=256):
    """0.60.76 (D-O-082): forget the addresses whose requests are all older than the window (called under the lock)."""
    if len(hits) > keep:
        for ip in [ip for ip, times in hits.items() if not times or now - times[-1] >= window]:
            del hits[ip]


def _account(conn, login):
    login = (login or "").strip().lower() if isinstance(login, str) else ""
    if not login or len(login) > 254:
        return None
    column = "lower(email)" if "@" in login else "lower(username)"
    row = conn.execute("SELECT * FROM users WHERE {} = ?".format(column), (login,)).fetchone()
    if row is None or not row["is_active"] or not row["email"]:
        return None
    if permissions.is_guest(row) or str(row["username"]).startswith("demo."):
        return None
    return row


def _message(link, name):
    subject = "DynamiteAgile — réinitialiser votre mot de passe / reset your password"
    text = ("Bonjour {name},\n\n"
            "Quelqu'un (vous, sans doute) a demandé un nouveau mot de passe pour votre compte DynamiteAgile.\n"
            "Choisissez-le ici, dans les 30 minutes :\n\n{link}\n\n"
            "Vous n'avez rien demandé ? Ignorez ce courriel : votre mot de passe ne change pas.\n\n"
            "— — —\n\n"
            "Hello {name},\n\n"
            "Someone (most likely you) asked for a new password for your DynamiteAgile account.\n"
            "Choose it here, within 30 minutes:\n\n{link}\n\n"
            "Did not ask? Ignore this e-mail: your password stays the same.\n").format(name=name, link=link)
    return subject, text


def api_forgot(ctx):
    _rate(ctx.ip)
    if not mail.ready(ctx.data_dir):
        raise ApiError(503, "La récupération par courriel n'est pas activée sur ce serveur. Correctif : demandez un mot "
                            "de passe temporaire à votre administrateur.")
    user = _account(ctx.conn, ctx.body.get("login"))
    if user is None:
        return {"ok": True, "message": SENT}
    now = dt.datetime.now(dt.timezone.utc)
    hour_ago = (now - dt.timedelta(hours=1)).isoformat(timespec="seconds")
    recent = ctx.conn.execute("SELECT COUNT(*) FROM password_resets WHERE user_id = ? AND created_at > ?",
                              (user["id"], hour_ago)).fetchone()[0]
    if recent >= PER_USER_HOUR:
        audit.log_action(ctx.conn, None, "password_reset_throttled", "user", user["id"], None, ctx.ip)
        return {"ok": True, "message": SENT}
    token = secrets.token_urlsafe(32)
    ctx.conn.execute("INSERT INTO password_resets (token_hash, user_id, created_at, expires_at, ip) VALUES (?, ?, ?, ?, ?)",
                     (_hash(token), user["id"], now.isoformat(timespec="seconds"),
                      (now + dt.timedelta(minutes=MINUTES)).isoformat(timespec="seconds"), ctx.ip))
    audit.log_action(ctx.conn, None, "password_reset_requested", "user", user["id"], None, ctx.ip)
    link = mail.load(ctx.data_dir)["public_url"] + "/#reset=" + token
    subject, text = _message(link, user["display_name"])
    mail.send_later(ctx.data_dir, user["email"], subject, text)
    return {"ok": True, "message": SENT}


def _valid(conn, token):
    if not isinstance(token, str) or not 20 <= len(token) <= 100:
        return None
    row = conn.execute("SELECT r.*, u.username, u.is_active FROM password_resets r JOIN users u ON u.id = r.user_id "
                       "WHERE r.token_hash = ?", (_hash(token),)).fetchone()
    if row is None or row["used_at"] or not row["is_active"] or row["expires_at"] <= db.utc_now():
        return None
    return row


def api_check(ctx):
    row = _valid(ctx.conn, ctx.body.get("token"))
    if row is None:
        raise ApiError(410, EXPIRED)
    return {"ok": True, "username": row["username"]}


def api_reset(ctx):
    row = _valid(ctx.conn, ctx.body.get("token"))
    if row is None:
        raise ApiError(410, EXPIRED)
    password = ctx.body.get("new_password")
    auth.validate_new_password(password, row["username"])
    ctx.conn.execute("UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
                     (auth.hash_password(password), row["user_id"]))
    ctx.conn.execute("UPDATE password_resets SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
                     (db.utc_now(), row["user_id"]))
    auth.delete_user_sessions(ctx.conn, row["user_id"])
    if row["username"] == auth.INITIAL_ADMIN_USERNAME:
        auth.remove_initial_password_file(ctx.data_dir)
    audit.log_action(ctx.conn, row["user_id"], "password_reset_by_email", "user", row["user_id"], None, ctx.ip)
    return {"ok": True, "username": row["username"]}


ROUTES = [
    ("POST", r"/api/password/forgot", api_forgot, "public"),
    ("POST", r"/api/password/reset/check", api_check, "public"),  # 0.60.76 (D-O-082): was a GET with ?token=
    ("POST", r"/api/password/reset", api_reset, "public"),
]
