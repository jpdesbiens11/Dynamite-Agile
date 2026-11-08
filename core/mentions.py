"""@mentions and messages (core lot v0.19, D-A-046).

Writing « @username » in a wiki page, a page comment, a ticket / requirement / change comment or a Goldmine Q&A
sends a message to that person: a red counter on the « Dashboard » tab and a « Messages » section on the Dashboard
that shows the excerpt and opens the exact place to answer. Rules:
  * only an active account that may read the Space receives it (no message about a place he cannot open);
  * the author is told who was notified and who was not, and why (D-A-031);
  * a page saved again only notifies the mentions it adds, never the ones already there;
  * « @me » (one's own username) files a note in one's own Messages (0.45.1, D-B-089 -- was ignored before);
  * GET /api/mentions?box=sent lists what I sent, with the recipient and whether it was read.
Modules call notify(); the text is stored as a short excerpt (the place stays the source of truth).

D-B-100 (core lot v0.27): « Répondre ici » from the Dashboard posts the answer as a comment at the place of the
message (ticket / requirement / change comment, or page comment), signed by the account, with « @asker » added at the
end: the asker gets it in his Messages, marked as an answer, with « Acknowledge » to take it off his Dashboard. The
answered message leaves the replier's list (box « Traités » keeps it).
"""
import json
import re

from . import audit, db, permissions, validate
from .errors import ApiError

MENTION = re.compile(r"(?<![\w@./-])@([a-z0-9][a-z0-9._-]{1,39})", re.IGNORECASE)
EXCERPT = 280

MIGRATIONS = [
    (10, """
        CREATE TABLE mentions (
            id         INTEGER PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            author_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            kind       TEXT NOT NULL,
            title      TEXT NOT NULL DEFAULT '',
            href       TEXT NOT NULL,
            excerpt    TEXT NOT NULL DEFAULT '',
            source     TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            read_at    TEXT
        );
        CREATE INDEX idx_mentions_user ON mentions(user_id, read_at);
    """),
    (13, """
        -- D-B-100: answers from the Dashboard, acknowledged answers
        ALTER TABLE mentions ADD COLUMN reply_to INTEGER REFERENCES mentions(id) ON DELETE SET NULL;
        ALTER TABLE mentions ADD COLUMN answered_at TEXT;
        ALTER TABLE mentions ADD COLUMN done_at TEXT;
    """),
]

KINDS = {"page": "Page wiki", "page_comment": "Commentaire de page", "ticket_comment": "Commentaire de ticket",
         "qa": "Q&A Goldmine", "review": "Évaluation annuelle"}  # review: core lot v0.31 (D-B-112)


def usernames(text):
    return list(dict.fromkeys(m.lower() for m in MENTION.findall(text or "")))


def text_of_blocks(node):
    """Plain text of a Dynamite JSON body (every « text » leaf), to find the mentions of a page."""
    out = []

    def walk(n):
        if isinstance(n, dict):
            if isinstance(n.get("text"), str):
                out.append(n["text"])
            for v in n.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(json.loads(node) if isinstance(node, str) else node)
    return " ".join(out)


def _excerpt(text, name):
    text = " ".join((text or "").split())
    at = text.lower().find("@" + name)
    start = max(0, at - 90) if at >= 0 else 0
    piece = text[start:start + EXCERPT]
    return ("…" if start else "") + piece + ("…" if start + EXCERPT < len(text) else "")


def notify(conn, author, text, kind, href, title, project_id=None, source="", previous_text=None):
    """Send the messages of `text`; returns {"notified": [...], "skipped": [...]} and a French notice for the author."""
    names = usernames(text)
    if previous_text is not None:
        before = set(usernames(previous_text))
        names = [n for n in names if n not in before]
    notified, skipped, note = [], [], False
    now = db.utc_now()
    for name in names:
        user = conn.execute("SELECT * FROM users WHERE lower(username) = ?", (name,)).fetchone()
        if user is None:
            skipped.append("@{} : compte inconnu (vérifiez l'identifiant dans l'annuaire)".format(name))
        elif not user["is_active"]:
            skipped.append("@{} : compte désactivé".format(name))
        elif project_id is not None and permissions.project_role(conn, user, project_id) is None:
            skipped.append("@{} : n'a pas accès à ce Space (ajoutez-le aux membres pour qu'il voie le message)".format(name))
        else:
            conn.execute("INSERT INTO mentions (user_id, author_id, project_id, kind, title, href, excerpt, source, created_at) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (user["id"], author["id"], project_id, kind, title[:200], href,
                                                                _excerpt(text, name), source[:80], now))
            if user["id"] == author["id"]:
                note = True  # a reminder to oneself
            else:
                notified.append(user["display_name"] or user["username"])
    return {"notified": notified, "skipped": skipped, "notice": notice(notified, skipped, note)}


def notice(notified, skipped, note=False):
    parts = ["Note ajoutée à vos Messages (Dashboard)."] if note else []
    if notified:
        parts.append("Message envoyé à " + ", ".join(notified) + ".")
    if skipped:
        parts.append("Non notifié — " + " ; ".join(skipped) + ".")
    return " ".join(parts)


def api_list(ctx):
    if ctx.query.get("box") == "sent":  # D-B-089: what I sent -- to whom, read or not
        rows = ctx.conn.execute(
            "SELECT m.*, u.display_name AS recipient, p.key AS project_key FROM mentions m JOIN users u ON u.id = m.user_id "
            "LEFT JOIN projects p ON p.id = m.project_id WHERE m.author_id = ? AND m.user_id != ? ORDER BY m.id DESC LIMIT 100",
            (ctx.user["id"], ctx.user["id"])).fetchall()
        items = db.rows(rows)
        for it in items:
            it["kind_label"] = KINDS.get(it["kind"], it["kind"])
        return {"messages": items, "unread": 0, "box": "sent"}
    done = ctx.query.get("box") == "done"  # D-B-100: answered or acknowledged messages
    rows = ctx.conn.execute(
        "SELECT m.*, u.display_name AS author, u.username AS author_username, p.key AS project_key FROM mentions m "
        "LEFT JOIN users u ON u.id = m.author_id LEFT JOIN projects p ON p.id = m.project_id WHERE m.user_id = ? AND "
        "m.done_at IS {} NULL ORDER BY m.read_at IS NOT NULL, m.id DESC LIMIT 100".format("NOT" if done else ""),
        (ctx.user["id"],)).fetchall()
    items = db.rows(rows)
    for it in items:
        it["kind_label"] = KINDS.get(it["kind"], it["kind"])
        it["can_reply"] = bool(it["author_id"]) and it["author_id"] != ctx.user["id"] and bool(TARGET.match(it["href"] or ""))
    return {"messages": items, "unread": sum(1 for it in items if not it["read_at"]), "box": "done" if done else "inbox"}


def api_count(ctx):
    n = ctx.conn.execute("SELECT COUNT(*) FROM mentions WHERE user_id = ? AND read_at IS NULL AND done_at IS NULL",
                         (ctx.user["id"],)).fetchone()[0]
    return {"unread": n}


def api_read(ctx):
    ids = ctx.body.get("ids")
    now = db.utc_now()
    if ctx.body.get("all"):
        ctx.conn.execute("UPDATE mentions SET read_at = ? WHERE user_id = ? AND read_at IS NULL", (now, ctx.user["id"]))
    elif isinstance(ids, list) and ids:
        clean = [int(i) for i in ids if str(i).isdigit()][:200]
        ctx.conn.execute("UPDATE mentions SET read_at = ? WHERE user_id = ? AND read_at IS NULL AND id IN ({})".format(
            ",".join("?" * len(clean))), [now, ctx.user["id"]] + clean)
    else:
        raise ApiError(400, "Rien à marquer comme lu. Correctif : envoyez « ids » (liste) ou « all »: true.")
    return api_count(ctx)


TARGET = re.compile(r"^#/(?:(agile|goldmine)/([A-Z0-9]+)/issue/(\d+)|dynamite/([A-Z0-9]+)/page/(\d+))")


def _mine(ctx):
    row = ctx.conn.execute("SELECT m.*, u.username AS author_username FROM mentions m LEFT JOIN users u ON u.id = m.author_id "
                           "WHERE m.id = ? AND m.user_id = ?", (validate.int_param(ctx.params, "mid"), ctx.user["id"])).fetchone()
    if row is None:
        raise ApiError(404, "Message introuvable dans vos Messages.")
    return row


def api_reply(ctx):
    """D-B-100: the answer goes to the place of the message as a comment, « @asker » at the end."""
    from modules.help.local_api import LocalApi  # local import: the comment routes belong to the modules
    msg = _mine(ctx)
    text = validate.text(ctx.body, "text", 9000)
    m = TARGET.match(msg["href"] or "")
    if not msg["author_username"] or msg["author_id"] == ctx.user["id"] or m is None:
        raise ApiError(409, "On ne peut pas répondre ici à ce message (note à soi-même, auteur supprimé ou lieu sans "
                            "commentaires). Correctif : « Ouvrir sur place ».")
    key = m.group(2) or m.group(4)
    project = ctx.conn.execute("SELECT id FROM projects WHERE key = ?", (key,)).fetchone()
    if project is None:
        raise ApiError(404, "Le Space {} n'existe plus.".format(key))
    body = text.rstrip() + " @" + msg["author_username"]
    if m.group(1):
        path = "/api/agile/p/{}/issues/{}/comments".format(project["id"], m.group(3))
    else:
        path = "/api/dynamite/p/{}/pages/{}/comments".format(project["id"], m.group(5))
    saved = dict(ctx.body), dict(ctx.params), dict(ctx.query)
    before = ctx.conn.execute("SELECT COALESCE(MAX(id), 0) FROM mentions").fetchone()[0]
    try:
        result = LocalApi(ctx).post(path, {"body": body})
    finally:
        ctx.body, ctx.params, ctx.query = saved
    now = db.utc_now()
    ctx.conn.execute("UPDATE mentions SET reply_to = ? WHERE id > ? AND author_id = ? AND user_id = ?",
                     (msg["id"], before, ctx.user["id"], msg["author_id"]))
    ctx.conn.execute("UPDATE mentions SET answered_at = ?, done_at = ?, read_at = COALESCE(read_at, ?) WHERE id = ?",
                     (now, now, now, msg["id"]))
    audit.log_action(ctx.conn, ctx.user["id"], "message_replied", "mention", msg["id"], {"href": msg["href"]}, ctx.ip)
    notice = (result or {}).get("mentions_notice") or ""
    return {"ok": True, "href": msg["href"], "notice": notice or "Réponse enregistrée sur place."}


def api_ack(ctx):
    """D-B-100: « Acknowledge » -- the message leaves the Dashboard (box « Traités » keeps it)."""
    msg = _mine(ctx)
    now = db.utc_now()
    ctx.conn.execute("UPDATE mentions SET done_at = ?, read_at = COALESCE(read_at, ?) WHERE id = ?", (now, now, msg["id"]))
    return api_count(ctx)


def api_people(ctx):
    """Autocomplete of « @ »: active accounts, with their username (what the mention writes)."""
    if permissions.is_guest(ctx.user):  # 0.60.82 (D-O-088): a guest mentions nobody; never the list of the accounts
        return {"people": []}
    q = validate.text(ctx.query, "q", 40, required=False).lower()
    rows = ctx.conn.execute("SELECT username, display_name FROM users WHERE is_active = 1 AND (lower(username) LIKE ? OR "
                            "lower(display_name) LIKE ?) ORDER BY display_name LIMIT 8", ("%" + q + "%", "%" + q + "%")).fetchall()
    return {"people": db.rows(rows)}


ROUTES = [
    ("GET", r"/api/mentions", api_list, "user"),
    ("GET", r"/api/mentions/count", api_count, "user"),
    ("POST", r"/api/mentions/read", api_read, "user"),
    ("GET", r"/api/mentions/people", api_people, "user"),
    ("POST", r"/api/mentions/(?P<mid>\d+)/reply", api_reply, "user"),
    ("POST", r"/api/mentions/(?P<mid>\d+)/ack", api_ack, "user"),
]
