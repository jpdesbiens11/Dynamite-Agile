"""0.60.73 (D-O-079): e-mail -- the only way the server ever talks to the outside, and only for « Mot de passe oublié ».

Off by default. The administrator sets an SMTP server in Admin → Plateforme → Courriel (Gmail with an app password,
the mailbox of the domain…): host, port, STARTTLS or SSL, account, sender, and the public address of the tool used in
the links. The settings live in data/mail.json (0600), never in the database: a Space backup or a data pack never
carries the SMTP password, and the password is never sent back to the browser (has_password only).

Each account gets an e-mail address (users.email, unique when set): the administrator types it in Admin → Comptes,
the person changes it from the menu at their name (« Courriel de récupération »).
"""
import json
import os
import re
import smtplib
import ssl
import threading
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path

from . import audit, validate
from .errors import ApiError

MIGRATIONS = [
    (19, """
        -- 0.60.73 (D-O-079): the e-mail of an account, for « Mot de passe oublié » (empty = no reset by e-mail)
        ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT '';
        CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique ON users(lower(email)) WHERE email <> '';
        CREATE TABLE IF NOT EXISTS password_resets (
            token_hash TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used_at    TEXT,
            ip         TEXT
        );
        CREATE INDEX IF NOT EXISTS password_resets_user ON password_resets(user_id);
    """),
]

FILE = "mail.json"
EMAIL_RE = re.compile(r"^[^@\s<>\"',;]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")
HOST_RE = re.compile(r"^[A-Za-z0-9.-]{1,253}$")
DEFAULTS = {"enabled": False, "host": "", "port": 587, "security": "starttls", "username": "", "password": "",
            "sender": "", "sender_name": "DynamiteAgile", "public_url": ""}
TIMEOUT = 20


def clean_email(value, required=False):
    """'' or a plain address (lower-cased); 400 otherwise."""
    value = (value or "").strip() if isinstance(value, str) else ""
    if not value:
        if required:
            raise ApiError(400, "Courriel manquant.")
        return ""
    if len(value) > 254 or not EMAIL_RE.match(value):
        raise ApiError(400, "Courriel invalide : une adresse comme prenom@exemple.ca est attendue.")
    return value.lower()


def email_taken(conn, email, user_id):
    return bool(email) and conn.execute("SELECT 1 FROM users WHERE lower(email) = ? AND id <> ?",
                                        (email.lower(), user_id)).fetchone() is not None


def set_user_email(conn, user_id, raw):
    email = clean_email(raw)
    if email_taken(conn, email, user_id):
        raise ApiError(409, "Ce courriel est déjà celui d'un autre compte.")
    conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
    return email


def _path(data_dir):
    return Path(data_dir) / FILE


def load(data_dir):
    out = dict(DEFAULTS)
    if data_dir:
        try:
            raw = json.loads(_path(data_dir).read_text(encoding="utf-8"))
            out.update({k: raw[k] for k in DEFAULTS if k in raw})
        except (OSError, ValueError):
            pass
    return out


def _save(data_dir, value):
    path = _path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def ready(data_dir):
    """True when « Mot de passe oublié ? » can send its link."""
    cfg = load(data_dir)
    return bool(cfg["enabled"] and cfg["host"] and cfg["sender"] and cfg["public_url"])


def send(data_dir, to, subject, text):
    """Send one plain-text message; raises ApiError(502) with the server's answer when it fails."""
    cfg = load(data_dir)
    if not (cfg["host"] and cfg["sender"]):
        raise ApiError(400, "Courriel non configuré : Admin → Plateforme → Courriel.")
    msg = EmailMessage()
    msg["From"] = formataddr((cfg["sender_name"] or "DynamiteAgile", cfg["sender"]))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=cfg["sender"].rsplit("@", 1)[-1])
    msg.set_content(text)
    context = ssl.create_default_context()
    try:
        if cfg["security"] == "ssl":
            server = smtplib.SMTP_SSL(cfg["host"], int(cfg["port"]), timeout=TIMEOUT, context=context)
        else:
            server = smtplib.SMTP(cfg["host"], int(cfg["port"]), timeout=TIMEOUT)
        with server:
            if cfg["security"] == "starttls":
                server.starttls(context=context)
            if cfg["username"]:
                server.login(cfg["username"], cfg["password"])
            server.send_message(msg)
    except (smtplib.SMTPException, OSError, ssl.SSLError) as err:
        raise ApiError(502, "Le serveur de courriel a refusé l'envoi : {}. Correctif : vérifiez l'hôte, le port, la "
                            "sécurité et le compte (Gmail : un mot de passe d'application).".format(str(err)[:200]))


def send_later(data_dir, to, subject, text, on_error=None):
    """Same, in the background: the answer of « Mot de passe oublié » never waits for the mail server (nor says,
    by its delay, whether the account exists)."""
    def run():
        try:
            send(data_dir, to, subject, text)
        except ApiError as err:
            if on_error:
                on_error(err.message)
    threading.Thread(target=run, daemon=True).start()


# ---------------- Admin → Plateforme → Courriel ----------------

def _payload(ctx):
    cfg = load(ctx.data_dir)
    public = (ctx.config or {}).get("public_name") or ""
    me = ctx.conn.execute("SELECT email FROM users WHERE id = ?", (ctx.user["id"],)).fetchone()
    return {"mail": {k: v for k, v in cfg.items() if k != "password"}, "has_password": bool(cfg["password"]),
            "suggested_url": "https://" + public if public else "", "my_email": me["email"] if me else "",
            "accounts_with_email": ctx.conn.execute("SELECT COUNT(*) FROM users WHERE email <> '' AND is_active = 1").fetchone()[0]}


def api_admin_get(ctx):
    return _payload(ctx)


def api_admin_put(ctx):
    cfg = load(ctx.data_dir)
    body = ctx.body
    for key, limit in (("host", 253), ("username", 254), ("sender_name", 80), ("public_url", 200)):
        if key in body:
            cfg[key] = validate.text(body, key, limit, required=False)
    if cfg["host"] and not HOST_RE.match(cfg["host"]):
        raise ApiError(400, "Hôte invalide : un nom comme smtp.gmail.com est attendu.")
    if "sender" in body:
        cfg["sender"] = clean_email(body.get("sender"))
    if "port" in body:
        port = body.get("port")
        if not isinstance(port, int) or not 1 <= port <= 65535:
            raise ApiError(400, "Port invalide (587 pour STARTTLS, 465 pour SSL).")
        cfg["port"] = port
    if "security" in body:
        if body.get("security") not in ("starttls", "ssl", "none"):
            raise ApiError(400, "Chiffrement invalide : starttls, ssl ou none.")
        cfg["security"] = body["security"]
    if body.get("password"):  # empty = keep the one already saved
        cfg["password"] = validate.text(body, "password", 256)
    if body.get("clear_password"):
        cfg["password"] = ""
    cfg["public_url"] = cfg["public_url"].rstrip("/")
    if cfg["public_url"] and not re.match(r"^https://[A-Za-z0-9.-]+(:\d+)?$", cfg["public_url"]):
        raise ApiError(400, "Adresse de l'outil invalide : https://votre-domaine (sans chemin), celle que voit l'équipe.")
    if "enabled" in body:
        cfg["enabled"] = validate.boolean(body, "enabled")
    if cfg["security"] == "none" and cfg["username"]:
        raise ApiError(400, "Sans chiffrement, le mot de passe du compte SMTP passerait en clair : choisissez STARTTLS ou SSL.")
    if cfg["enabled"] and not (cfg["host"] and cfg["sender"] and cfg["public_url"]):
        raise ApiError(400, "Pour activer : hôte SMTP, expéditeur et adresse de l'outil sont requis.")
    _save(ctx.data_dir, cfg)
    audit.log_action(ctx.conn, ctx.user["id"], "mail_settings_changed", "settings", None,
                     {k: v for k, v in cfg.items() if k != "password"}, ctx.ip)
    return _payload(ctx)


def api_admin_test(ctx):
    to = clean_email(ctx.body.get("to"), required=True)
    send(ctx.data_dir, to, "DynamiteAgile — courriel test / test e-mail",
         "Ce courriel test confirme que DynamiteAgile peut envoyer les liens « Mot de passe oublié ».\n\n"
         "This test e-mail confirms DynamiteAgile can send the « Forgot password » links.\n")
    audit.log_action(ctx.conn, ctx.user["id"], "mail_test_sent", "settings", None, {"to": to}, ctx.ip)
    return {"ok": True, "to": to}


# ---------------- the person's own address ----------------

def api_me_get(ctx):
    row = ctx.conn.execute("SELECT email FROM users WHERE id = ?", (ctx.user["id"],)).fetchone()
    return {"email": row["email"] if row else "", "reset_ready": ready(ctx.data_dir)}


def api_me_put(ctx):
    email = set_user_email(ctx.conn, ctx.user["id"], ctx.body.get("email"))
    audit.log_action(ctx.conn, ctx.user["id"], "email_changed", "user", ctx.user["id"], None, ctx.ip)
    return {"email": email, "reset_ready": ready(ctx.data_dir)}


ROUTES = [
    ("GET", r"/api/admin/mail", api_admin_get, "admin"),
    ("PUT", r"/api/admin/mail", api_admin_put, "admin"),
    ("POST", r"/api/admin/mail/test", api_admin_test, "admin"),
    ("GET", r"/api/me/email", api_me_get, "user"),
    ("PUT", r"/api/me/email", api_me_put, "user"),
]

