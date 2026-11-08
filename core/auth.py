"""Authentication: password hashing, login throttling and sessions.

Passwords are hashed with PBKDF2-SHA256 (always available in hashlib,
unlike scrypt which depends on the OpenSSL build). Session tokens are
random, sent to the browser in an HttpOnly cookie, and stored only as a
SHA-256 hash, so a copy of the database cannot be used to hijack sessions.
"""
import hashlib
import hmac
import secrets
import threading
import time
from pathlib import Path

from . import audit, db
from .errors import ApiError

PBKDF2_ITERATIONS = 310000
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 256
SESSION_COOKIE = "da_session"  # over HTTPS: "__Host-da_session" (core.tls.cookie_name)
INITIAL_ADMIN_USERNAME = "admin"
INITIAL_PASSWORD_FILE = "INITIAL_ADMIN_PASSWORD.txt"

_fail_lock = threading.Lock()
_failures = {}  # "username|ip" -> (failure_count, locked_until_epoch)
_ip_failures = {}  # 0.60.84 (D-O-090): ip -> [(epoch, username) of each failed login], every username together


# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------
def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(PBKDF2_ITERATIONS, salt.hex(), digest.hex())


def verify_password(password, stored):
    try:
        algorithm, iterations, salt_hex, hash_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                     bytes.fromhex(salt_hex), int(iterations))
    except (AttributeError, TypeError, ValueError):
        return False
    return hmac.compare_digest(digest.hex(), hash_hex)


# Used when the username does not exist, so response time does not reveal it.
_DUMMY_HASH = hash_password(secrets.token_hex(16))


def validate_new_password(password, username=""):
    if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
        raise ApiError(400, "Le mot de passe doit contenir au moins {} caractères.".format(
            PASSWORD_MIN_LENGTH))
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ApiError(400, "Le mot de passe est trop long.")
    if username and username.lower() in password.lower():
        raise ApiError(400, "Le mot de passe ne doit pas contenir l'identifiant.")


# D-A-040: in development mode (team tests) every temporary password is this value -- set at start-up by
# app_dynamite_agile.py, never in production (--prod / dev_mode false). The change at first login stays mandatory.
DEV_TEMP_PASSWORD = None


def generate_temp_password():
    return DEV_TEMP_PASSWORD or secrets.token_urlsafe(12)


def reset_pending_temp_passwords(conn):
    """Development mode (D-A-040): accounts that never chose their own password get the development temporary
    password. Accounts that already changed theirs are left alone. Returns the number of accounts reset."""
    if not DEV_TEMP_PASSWORD:
        return 0
    rows = conn.execute("SELECT id FROM users WHERE must_change_password = 1 AND is_active = 1").fetchall()
    for r in rows:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(DEV_TEMP_PASSWORD), r["id"]))
    return len(rows)


# --------------------------------------------------------------------------
# Login throttling (in memory, reset when the server restarts)
# --------------------------------------------------------------------------
def _check_lock(key, now, ip=None, cfg=None, known=None):
    """429 if this username is locked from this address, or if the address itself is over its ceiling.

    0.60.95 (D-O-101, R1 of D-O-095): behind a shared address (company VPN, NAT, school network) one person mistyping
    must not lock everyone out. The address ceiling therefore counts the different usernames that failed (one password
    tried on many accounts: « spraying »), next to a much higher ceiling of raw failures; someone who mistypes their own
    password only meets the per-username lock (login_max_failures). Above the ceiling, a username that already signed in
    from this address within login_known_days (`known()`, read from the audit log only then) may still try: its own
    lock still applies."""
    with _fail_lock:
        entry = _failures.get(key)
        if entry and entry[1] > now:
            raise ApiError(429, "Trop de tentatives. Réessayez dans quelques minutes.")
        over = False
        if ip is not None and cfg is not None:  # 0.60.84 (D-O-090): one password tried on every account (spraying)
            window = float(cfg.get("login_ip_window_minutes", 15)) * 60
            recent = [(t, u) for t, u in _ip_failures.get(ip, []) if now - t < window]
            _ip_failures[ip] = recent
            over = (len(recent) >= int(cfg.get("login_ip_max_failures", 200))
                    or len({u for _t, u in recent}) >= int(cfg.get("login_ip_max_usernames", 10)))
    if over and not (known and known()):
        raise ApiError(429, "Trop de tentatives depuis cette adresse. Réessayez dans quelques minutes.")


def _known_here(conn, username, ip, days):
    """0.60.95 (D-O-101): did this username sign in from this address recently? (audit log, kept with the data)"""
    since = db.utc_in(-24 * float(days))
    return conn.execute("SELECT 1 FROM audit_log a JOIN users u ON u.id = a.user_id WHERE a.ts >= ? AND a.action = 'login' "
                        "AND a.ip = ? AND u.username = ? LIMIT 1", (since, ip, username)).fetchone() is not None


def _prune(now, keep=1024):
    """Called under _fail_lock: forget the counters that no longer lock anything (they grew with every username tried)."""
    if len(_failures) > keep:
        for k in [k for k, (_c, until, *last) in _failures.items() if until <= now and (not last or now - last[0] > 3600)]:
            del _failures[k]
    if len(_ip_failures) > keep:
        for ip in [ip for ip, times in _ip_failures.items() if not times or now - times[-1][0] > 3600]:
            del _ip_failures[ip]


def _record_failure(key, now, max_failures, lock_minutes, ip=None, username=""):
    with _fail_lock:
        count, locked_until = _failures.get(key, (0, 0, 0))[:2]
        if locked_until and locked_until <= now:
            count = 0  # Previous lock expired: start counting again
        count += 1
        locked_until = now + lock_minutes * 60 if count >= max_failures else 0
        _failures[key] = (count, locked_until, now)
        if ip is not None:
            _ip_failures.setdefault(ip, []).append((now, username))
        _prune(now)


# --------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------
def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def login(conn, username, password, ip, cfg):
    """Check credentials and open a session. Returns (token, csrf, user_row)."""
    if (not isinstance(username, str) or not isinstance(password, str)
            or not username.strip() or not password):
        raise ApiError(400, "Identifiant et mot de passe requis.")
    username = username.strip().lower()
    invalid = ApiError(401, "Identifiant ou mot de passe invalide.")
    if len(username) > 64 or len(password) > PASSWORD_MAX_LENGTH:
        raise invalid

    key = "{}|{}".format(username, ip)
    now = time.time()
    _check_lock(key, now, ip, cfg, lambda: _known_here(conn, username, ip, cfg.get("login_known_days", 30)))

    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    password_ok = verify_password(password, user["password_hash"] if user else _DUMMY_HASH)
    if not (user and user["is_active"] and password_ok):
        _record_failure(key, now, int(cfg["login_max_failures"]), int(cfg["login_lock_minutes"]), ip, username)
        user_id = user["id"] if user else None
        audit.log_action(conn, user_id, "login_failed", "user", user_id,
                         {"username": username}, ip)
        conn.commit()  # Keep the audit entry even though we raise below
        raise invalid

    with _fail_lock:
        _failures.pop(key, None)
        if ip in _ip_failures:  # 0.60.95 (D-O-101): this person has proven who they are; their typos no longer count
            _ip_failures[ip] = [(t, u) for t, u in _ip_failures[ip] if u != username]
    purge_expired_sessions(conn)
    token, csrf = create_session(conn, user["id"], ip, cfg["session_hours"])
    audit.log_action(conn, user["id"], "login", "user", user["id"], None, ip)
    return token, csrf, user


def create_session(conn, user_id, ip, hours):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, csrf_token, created_at, expires_at, ip) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (_hash_token(token), user_id, csrf, db.utc_now(), db.utc_in(hours), ip))
    return token, csrf


def get_session(conn, token):
    """Return the session joined with its user, or None if invalid/expired."""
    if not token:
        return None
    row = conn.execute(
        "SELECT s.csrf_token, s.expires_at, s.client_cert, u.id, u.username, u.display_name, "
        "u.is_admin, u.is_active, u.must_change_password "
        "FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?",
        (_hash_token(token),)).fetchone()
    if row is None or not row["is_active"] or row["expires_at"] <= db.utc_now():
        return None
    return row


def bind_session_cert(conn, token, fingerprint):
    """D-B-090: remember the client certificate (mTLS) that opened the session."""
    conn.execute("UPDATE sessions SET client_cert = ? WHERE token_hash = ?", (fingerprint, _hash_token(token)))


def delete_session(conn, token):
    if token:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))


def delete_user_sessions(conn, user_id, except_token=None):
    if except_token:
        conn.execute("DELETE FROM sessions WHERE user_id = ? AND token_hash <> ?",
                     (user_id, _hash_token(except_token)))
    else:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


def purge_expired_sessions(conn):
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (db.utc_now(),))


# --------------------------------------------------------------------------
# Account maintenance
# --------------------------------------------------------------------------
def change_password(conn, user_id, old_password, new_password):
    row = conn.execute("SELECT username, password_hash FROM users WHERE id = ?",
                       (user_id,)).fetchone()
    if row is None:
        raise ApiError(404, "Utilisateur introuvable.")
    if not isinstance(old_password, str) or not verify_password(old_password, row["password_hash"]):
        raise ApiError(400, "Mot de passe actuel incorrect.")
    if old_password == new_password:
        raise ApiError(400, "Le nouveau mot de passe doit être différent de l'actuel.")
    validate_new_password(new_password, row["username"])
    conn.execute("UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
                 (hash_password(new_password), user_id))


def set_temp_password(conn, user_id):
    """Assign a new temporary password, close all sessions, return it."""
    temp = generate_temp_password()
    conn.execute("UPDATE users SET password_hash = ?, must_change_password = 1 WHERE id = ?",
                 (hash_password(temp), user_id))
    delete_user_sessions(conn, user_id)
    return temp


def ensure_initial_admin(conn, data_dir, dev_password=None):
    """On an empty database, create 'admin' and return its temporary password.

    `dev_password` is a development-only convenience (never the default,
    only ever set by an explicit --dev-admin CLI flag): the account is
    created with that fixed password and must_change_password already off,
    so local iteration doesn't require reading a generated password each
    time the data folder is wiped. It must never be used past development;
    the caller is responsible for the loud warning.
    """
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        return None
    if dev_password:
        cursor = conn.execute(
            "INSERT INTO users (username, display_name, password_hash, is_admin, is_active, "
            "must_change_password, created_at) VALUES (?, ?, ?, 1, 1, 0, ?)",
            (INITIAL_ADMIN_USERNAME, "Administrateur", hash_password(dev_password), db.utc_now()))
        audit.log_action(conn, None, "initial_admin_created_dev", "user", cursor.lastrowid)
        return dev_password
    temp = generate_temp_password()
    cursor = conn.execute(
        "INSERT INTO users (username, display_name, password_hash, is_admin, is_active, "
        "must_change_password, created_at) VALUES (?, ?, ?, 1, 1, 1, ?)",
        (INITIAL_ADMIN_USERNAME, "Administrateur", hash_password(temp), db.utc_now()))
    audit.log_action(conn, None, "initial_admin_created", "user", cursor.lastrowid)
    (Path(data_dir) / INITIAL_PASSWORD_FILE).write_text(
        "Initial administrator account\n"
        "Username: {}\nTemporary password: {}\n\n"
        "This file is deleted automatically after the first password change.\n".format(
            INITIAL_ADMIN_USERNAME, temp),
        encoding="utf-8")
    return temp


def remove_initial_password_file(data_dir):
    path = Path(data_dir) / INITIAL_PASSWORD_FILE
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def public_user(row):
    """Fields that are safe to send to the browser."""
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "is_admin": bool(row["is_admin"]),
        "must_change_password": bool(row["must_change_password"]),
        "is_guest": str(row["username"]).lower() == "invite",  # 0.60.63 (D-O-072): read-only visitor
    }
