"""⚙ Admin → Bob (0.60.36, D-O-044): the keys of the AI agent -- make one for chosen Spaces (shown once), list them with
their last use, revoke one. Administrators only; every write journalled."""
import re
from pathlib import Path

from . import audit, bot, db
from .errors import ApiError


def _rows(conn):
    return [dict(r) for r in conn.execute(
        "SELECT t.id, t.name, t.prefix, t.spaces, t.created_at, t.last_used_at, t.uses, t.revoked_at, u.display_name AS created_by "
        "FROM bot_tokens t LEFT JOIN users u ON u.id = t.created_by ORDER BY t.revoked_at != '', t.id DESC")]


def api_list(ctx):
    spaces = [dict(r) for r in ctx.conn.execute("SELECT key, name FROM projects WHERE is_archived = 0 ORDER BY key")]
    return {"tokens": _rows(ctx.conn), "spaces": spaces, "routes": [r[1] for r in bot.ROUTES], "rate": bot.RATE}


def api_create(ctx):
    name = str(ctx.body.get("name", "")).strip()
    if not 2 <= len(name) <= 60:
        raise ApiError(400, "Nom de la clé : de 2 à 60 caractères (ex. « Bob le mineur — Telegram »).")
    wanted = [str(k).strip().upper() for k in ctx.body.get("spaces") or [] if str(k).strip()]
    known = {r["key"] for r in ctx.conn.execute("SELECT key FROM projects WHERE is_archived = 0")}
    unknown = [k for k in wanted if k not in known]
    if not wanted or unknown:
        raise ApiError(400, "Spaces de la clé : {}. Correctif : cochez au moins un Space existant.".format(
            "inconnus : " + ", ".join(unknown) if unknown else "aucun"))
    if any(not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", k) for k in wanted):
        raise ApiError(400, "Clé de Space invalide.")
    token = bot.new_token(ctx.conn, ctx.user["id"], name, wanted)
    tid = ctx.conn.execute("SELECT id FROM bot_tokens WHERE prefix = ? ORDER BY id DESC LIMIT 1", (token[:12],)).fetchone()["id"]
    audit.log_action(ctx.conn, ctx.user["id"], "bot_token_create", "bot_token", tid, {"name": name, "spaces": wanted}, ctx.ip)
    return {"token": token, "tokens": _rows(ctx.conn)}


def api_revoke(ctx):
    tid = int(ctx.params["tid"])
    row = ctx.conn.execute("SELECT name, revoked_at FROM bot_tokens WHERE id = ?", (tid,)).fetchone()
    if row is None:
        raise ApiError(404, "Clé introuvable. Correctif : rechargez la page.")
    if not row["revoked_at"]:
        ctx.conn.execute("UPDATE bot_tokens SET revoked_at = ? WHERE id = ?", (db.utc_now(), tid))
        audit.log_action(ctx.conn, ctx.user["id"], "bot_token_revoke", "bot_token", tid, {"name": row["name"]}, ctx.ip)
    return {"tokens": _rows(ctx.conn)}


GUIDE = Path(__file__).resolve().parent.parent / "deploy" / "bob" / "BOB_LE_MINEUR.md"


def api_guide(ctx):
    """The persona and tools of Bob for the agent (deploy/bob/BOB_LE_MINEUR.md), the address of this server filled in."""
    public = (ctx.config or {}).get("public_name")
    url = "https://" + public if public else ("https://" if ctx.secure else "http://") + "<adresse-du-serveur>"
    return {"text": GUIDE.read_text("utf-8").replace("{{URL}}", url), "url": url}


ROUTES = [
    ("GET", r"/api/admin/bot/guide", api_guide, "admin"),
    ("GET", r"/api/admin/bot/tokens", api_list, "admin"),
    ("POST", r"/api/admin/bot/tokens", api_create, "admin"),
    ("POST", r"/api/admin/bot/tokens/(?P<tid>\d+)/revoke", api_revoke, "admin"),
]
