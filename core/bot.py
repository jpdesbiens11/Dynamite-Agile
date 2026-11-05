"""Bob le mineur, the AI agent of the team (0.60.36, D-O-044): a read-only door for an agent that lives outside the
platform (on the same server or elsewhere, talking in Telegram), so it can answer « where is it? » with a pointer link that
opens the page and shows the point of interest (static/js/tools/pointer.js, D-O-043).

  - The platform never calls the agent: the agent calls in (FONDATIONS: no outbound call). Nothing of a project leaves
    the server unless the agent sends it to its own model -- the administrator chooses which Spaces it may read.
  - A key per agent (⚙ Admin → Bob), made by an administrator for chosen Spaces, shown once, stored as a SHA-256 hash,
    revoked in one click; every call is journalled (« bot_read », the key's name, the route) and counted.
  - Only GET, only these routes, at most 60 calls a minute per key. No session, no cookie, no CSRF: the key is sent as
    « Authorization: Bearer da_bot_… ».
Routes /api/bot/v1/…: spaces · search?q=&space= · summary?space= · pages?space= · point?space=&page=&focus=&note=
Every answer carries ready links (« url ») the agent pastes as they are.
"""
import hashlib
import secrets
import threading
import time
from urllib.parse import urlencode

from . import audit, db, modules
from .errors import ApiError

PREFIX = "da_bot_"
RATE = 60  # calls a minute per key
MIGRATIONS = [
    (18, """
        -- 0.60.36 (D-O-044): the keys of an AI agent (Bob le mineur): read-only, by Space, revocable, counted
        CREATE TABLE bot_tokens (
            id           INTEGER PRIMARY KEY,
            name         TEXT NOT NULL,
            prefix       TEXT NOT NULL,
            token_hash   TEXT NOT NULL UNIQUE,
            spaces       TEXT NOT NULL DEFAULT '',
            created_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at   TEXT NOT NULL,
            last_used_at TEXT NOT NULL DEFAULT '',
            uses         INTEGER NOT NULL DEFAULT 0,
            revoked_at   TEXT NOT NULL DEFAULT ''
        );
    """),
]
PAGES = [  # (module, route, label, what) -- where Bob can send people in a Space
    ("debuter", "#/debuter", "Débuter", "le parcours d'un projet selon le PDP"),
    ("goldmine", "#/goldmine/{key}", "Goldmine", "needs et requirements"),
    ("diamond", "#/diamond/{key}/ftree", "Diamond · Arbre fonctionnel", "les fonctions du produit"),
    ("diamond", "#/diamond/{key}/fstructure", "Diamond · Structure fonctionnelle", "entrées, sorties, flux, pièces"),
    ("diamond", "#/diamond/{key}/prisk", "Diamond · Risques projet", "le registre P × I"),
    ("diamond", "#/diamond/{key}/dfmea", "Diamond · DFMEA", "modes de défaillance, S / O / D, AP"),
    ("diamond", "#/diamond/{key}/dexport", "Diamond · Exporter", "Excel, draw.io, Word"),
    ("testing", "#/testing/{key}", "Testing", "la Test Base du Space"),
    ("exploration", "#/exploration/{key}/plan", "Exploration", "le plan et le Gantt"),
    ("agile", "#/agile/{key}/board", "Agile", "le board de l'équipe"),
    ("dynamite", "#/dynamite/{key}", "Dynamite", "les pages wiki"),
    ("timesheet", "#/timesheet", "Timesheet", "la feuille de temps"),
]
_calls = {}
_lock = threading.Lock()


def _hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token(conn, user_id, name, spaces):
    token = PREFIX + secrets.token_urlsafe(32)
    conn.execute("INSERT INTO bot_tokens (name, prefix, token_hash, spaces, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                 (name, token[:12], _hash(token), ",".join(spaces), user_id, db.utc_now()))
    return token


def authenticate(conn, header):
    """The key of « Authorization: Bearer … », or ApiError 401 / 429."""
    token = str(header or "")
    token = token[7:].strip() if token.lower().startswith("bearer ") else ""
    if not token.startswith(PREFIX):
        raise ApiError(401, "Clé de l'agent absente. Correctif : en-tête « Authorization: Bearer da_bot_… » (⚙ Admin → Bob).")
    row = conn.execute("SELECT * FROM bot_tokens WHERE token_hash = ?", (_hash(token),)).fetchone()
    if row is None or row["revoked_at"]:
        raise ApiError(401, "Clé de l'agent inconnue ou révoquée. Correctif : demandez une nouvelle clé à un administrateur (⚙ Admin → Bob).")
    now = time.monotonic()
    with _lock:
        recent = [t for t in _calls.get(row["id"], []) if now - t < 60]
        if len(recent) >= RATE:
            raise ApiError(429, "Trop d'appels : {} par minute au plus pour une clé d'agent.".format(RATE))
        _calls[row["id"]] = recent + [now]
    conn.execute("UPDATE bot_tokens SET uses = uses + 1, last_used_at = ? WHERE id = ?", (db.utc_now(), row["id"]))
    return dict(row)


def _projects(ctx):
    """{id: key} of the Spaces the key may read (active Spaces only)."""
    keys = [k for k in ctx.bot["spaces"].split(",") if k]
    if not keys:
        return {}
    rows = ctx.conn.execute("SELECT id, key FROM projects WHERE is_archived = 0 AND key IN ({})".format(",".join("?" * len(keys))), keys)
    return {r["id"]: r["key"] for r in rows}


def _space(ctx):
    key = str(ctx.query.get("space", "")).strip().upper()
    allowed = {v: k for k, v in _projects(ctx).items()}
    if key not in allowed:
        raise ApiError(403, "Space « {} » fermé à cette clé. Correctif : un des Spaces de /api/bot/v1/spaces.".format(key or "—"))
    return allowed[key], key


def _base(ctx):
    """The address people open: the public name (always HTTPS in production), else the Host the agent called."""
    public = (ctx.config or {}).get("public_name")
    if public:
        return "https://" + public
    return ("https://" if ctx.secure else "http://") + (getattr(ctx, "host", "") or "localhost")


def link(ctx, route, focus="", note=""):
    query = {k: v for k, v in (("focus", str(focus)[:160]), ("note", str(note)[:200])) if v}
    return _base(ctx) + "/" + ("?" + urlencode(query) if query else "") + route


def _log(ctx, route):
    audit.log_action(ctx.conn, ctx.bot["created_by"], "bot_read", "bot_token", ctx.bot["id"],
                     {"key": ctx.bot["name"], "route": route, "query": dict(ctx.query)}, ctx.ip)


def api_spaces(ctx):
    _log(ctx, "spaces")
    rows = ctx.conn.execute("SELECT id, key, name, description FROM projects WHERE id IN ({})".format(
        ",".join("?" * len(_projects(ctx))) or "NULL"), list(_projects(ctx))).fetchall()
    return {"agent": ctx.bot["name"], "spaces": [{"key": r["key"], "name": r["name"], "description": r["description"],
                                                 "url": link(ctx, "#/goldmine/{}".format(r["key"]))} for r in rows]}


def api_search(ctx):
    from .search import MAX_QUERY, Query
    raw = str(ctx.query.get("q", "")).strip()
    if not raw or len(raw) > MAX_QUERY:
        raise ApiError(400, "Recherche vide ou trop longue ({} caractères au plus).".format(MAX_QUERY))
    projects = _projects(ctx)
    if ctx.query.get("space"):
        pid, key = _space(ctx)
        projects = {pid: key}
    q, hits = Query(raw), []
    if projects:
        for _key, hook in modules.search_hooks():
            hits += hook(ctx.conn, projects, q) or []
    hits.sort(key=lambda h: (h["score"], h["updated_at"]), reverse=True)
    _log(ctx, "search")
    out = []
    for h in hits[:15]:
        first = h["title"].split(" ")[0]
        focus = h.get("focus") or (first if "-" in first and first[:1].isalnum() else h["title"][:60])  # a key (EQP-12) or the title
        out.append({"type": h["kind"], "space": h["project"], "title": h["title"], "snippet": h["snippet"],
                    "url": link(ctx, h["href"], focus)})
    return {"query": raw, "results": out, "total": len(hits)}


def api_pages(ctx):
    pid, key = _space(ctx)
    _log(ctx, "pages")
    return {"space": key, "pages": [{"module": m, "label": label, "what": what, "url": link(ctx, route.format(key=key))}
                                    for m, route, label, what in PAGES]}


def api_point(ctx):
    """A pointer link built for the agent: page (a route of /pages or a #/… route), focus (text to show), note."""
    pid, key = _space(ctx)
    page = str(ctx.query.get("page", "")).strip()
    route = next((r.format(key=key) for _m, r, label, _w in PAGES if page.lower() in (label.lower(), r.format(key=key).lower())), None)
    if route is None and page.startswith("#/") and ("/" + key) in page:
        route = page
    if route is None:
        raise ApiError(400, "Page « {} » inconnue. Correctif : un libellé ou une adresse de /api/bot/v1/pages?space={}.".format(page, key))
    _log(ctx, "point")
    return {"url": link(ctx, route, ctx.query.get("focus", ""), ctx.query.get("note", ""))}


def api_summary(ctx):
    """Where the project stands, with links: what a review would ask, the Diamond figures, the risks to act on."""
    pid, key = _space(ctx)
    _log(ctx, "summary")
    project = dict(ctx.conn.execute("SELECT key, name, description FROM projects WHERE id = ?", (pid,)).fetchone())
    out = {"space": project, "links": api_pages(ctx)["pages"]}
    for entry in modules.MODULE_MANIFEST:  # each module may say where it stands (bot_summary hook)
        hook = getattr(entry["module"], "bot_summary", None) if entry["module"] is not None else None
        if hook:
            out[entry["key"]] = hook(ctx.conn, pid, key, lambda route, focus="", note="": link(ctx, route, focus, note))
    return out


ROUTES = [
    ("GET", r"/api/bot/v1/spaces", api_spaces, "bot"),
    ("GET", r"/api/bot/v1/search", api_search, "bot"),
    ("GET", r"/api/bot/v1/pages", api_pages, "bot"),
    ("GET", r"/api/bot/v1/point", api_point, "bot"),
    ("GET", r"/api/bot/v1/summary", api_summary, "bot"),
]
