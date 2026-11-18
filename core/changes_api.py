"""Routes of « Changements » (core lot v0.39, 0.60.120, D-O-133): the page of a Space, its count, the read state.

GET  /api/changes?space=KEY&since=…&tab=…&who=…&source=…&state=new   the lines (core/changes.py), with the filters
     since: visit (my last visit, the default), 7 / 30 / 90 (days), all, a date AAAA-MM-JJ or a revision revX.XX
GET  /api/changes/count?space=KEY                                      what is new for me in this Space
POST /api/changes/seen  {space}                                        « Tout marquer vu »: my visit of the Space is now
POST /api/changes/ack   {space, ids}                                   « Vu » on lines (also when one opens the item)

What is « new » for a person: a change by somebody else, after their last visit of the Space (the last 7 days when
they never came), not marked « Vu ». The read state is personal: it never travels with a Space (core/backup.SKIP).
"""
import re
from datetime import datetime, timedelta, timezone

from . import audit, baselines, changes, db, permissions
from .errors import ApiError

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FIRST_VISIT_DAYS = 7
MAX_LINES = 400
SOURCES = {"manual": "", "ai": "ai", "import": "import"}


def _ago(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat()


def _space(ctx, key):
    key = str(key or "").strip().upper()
    for p in permissions.visible_projects(ctx.conn, ctx.user):
        if p["key"] == key:
            return p
    raise ApiError(404, "Space « {} » introuvable ou non accessible. Correctif : choisissez un Space de la liste.".format(key or "—"))


def seen_at(conn, user_id, pid):
    """(time, last line of the trail) of my last visit of the Space, or (None, 0)."""
    row = conn.execute("SELECT seen_at, seen_id FROM change_seen WHERE user_id = ? AND project_id = ?", (user_id, pid)).fetchone()
    return (row["seen_at"], row["seen_id"]) if row else (None, 0)


def _acked(conn, user_id, ids):
    if not ids:
        return set()
    marks = ",".join("?" * len(ids))
    return {r[0] for r in conn.execute("SELECT audit_id FROM change_acks WHERE user_id = ? AND audit_id IN ({})".format(marks),
                                       [user_id] + list(ids))}


def _since(ctx, value, mine):
    """(ISO time or None, label) of the « since » filter."""
    value = str(value or "visit").strip()
    if value == "visit":
        return (mine or _ago(FIRST_VISIT_DAYS)), ("depuis ma dernière visite" if mine else "des {} derniers jours".format(FIRST_VISIT_DAYS))
    if value == "all":
        return None, "depuis le début"
    if value.isdigit() and 0 < int(value) <= 3650:
        return _ago(int(value)), "des {} derniers jours".format(int(value))
    if DATE_RE.match(value):
        return value + "T00:00:00", "depuis le " + value
    rec = baselines.find(ctx.data_dir, value)
    if rec:
        return rec["created_at"], "depuis la révision {}".format(rec["label"])
    raise ApiError(400, "Période « {} » inconnue. Correctif : visit, 7, 30, 90, all, une date AAAA-MM-JJ ou une révision revX.XX."
                   .format(value))


def mark_new(conn, user_id, lines, visit):
    """Sets « new » on each grouped line: by somebody else, after the last visit (or the last 7 days), not « Vu »."""
    at, last = visit
    floor = _ago(FIRST_VISIT_DAYS)
    acked = _acked(conn, user_id, [i for ln in lines for i in ln["ids"]])
    for ln in lines:
        fresh = [i for i in ln["ids"] if i not in acked]
        ln["seen"] = not fresh
        after = max(fresh) > last if (at and fresh) else ln["ts"] >= floor
        ln["new"] = ln["user_id"] != user_id and bool(fresh) and after
    return lines


def lines_of(ctx, project, since):
    items = changes.scan(ctx.conn, {project["id"]: project["key"]}, since)
    return changes.group(items)


def api_list(ctx):
    project = _space(ctx, ctx.query.get("space"))
    visit = seen_at(ctx.conn, ctx.user["id"], project["id"])
    since, label = _since(ctx, ctx.query.get("since"), visit[0])
    lines = mark_new(ctx.conn, ctx.user["id"], lines_of(ctx, project, since), visit)
    tabs = sorted({(ln["tab"] or "space", ln["tab_label"]) for ln in lines}, key=lambda t: (t[0] == "space", t[1]))
    people = sorted({ln["initials"] for ln in lines})
    tab, who, src = ctx.query.get("tab") or "", (ctx.query.get("who") or "").upper(), ctx.query.get("source") or ""
    if tab:  # « space »: what belongs to the Space itself (its creation, its settings), not to one tab
        lines = [ln for ln in lines if (ln["tab"] or "space") == tab]
    if who:
        lines = [ln for ln in lines if ln["initials"] == who]
    if src in SOURCES:
        lines = [ln for ln in lines if ln["source"] == SOURCES[src]]
    if ctx.query.get("state") == "new":
        lines = [ln for ln in lines if ln["new"]]
    revisions = [r["label"] for r in baselines.records(ctx.data_dir)][-12:]
    return {"space": {"key": project["key"], "name": project["name"]}, "since": label, "seen_at": visit[0],
            "lines": [_public(ln) for ln in lines[:MAX_LINES]], "total": len(lines), "more": max(0, len(lines) - MAX_LINES),
            "new": sum(1 for ln in lines if ln["new"]), "tabs": [{"key": k, "label": v} for k, v in tabs], "people": people,
            "revisions": revisions}


def _public(ln):
    keep = ("ids", "ts", "initials", "user", "source", "tab", "tab_label", "code", "title", "href", "verb", "fields", "count",
            "new", "seen", "gone", "action")
    return {k: ln[k] for k in keep}


def count(conn, user, project):
    visit = seen_at(conn, user["id"], project["id"])
    items = changes.scan(conn, {project["id"]: project["key"]}, visit[0] or _ago(FIRST_VISIT_DAYS))
    lines = mark_new(conn, user["id"], changes.group(items), visit)
    news = [ln for ln in lines if ln["new"]]
    return {"new": len(news), "people": sorted({ln["initials"] for ln in news})}


def api_count(ctx):
    project = _space(ctx, ctx.query.get("space"))
    return dict(count(ctx.conn, ctx.user, project), space=project["key"])


def api_seen(ctx):
    project = _space(ctx, ctx.body.get("space"))
    now = db.utc_now()
    last = ctx.conn.execute("SELECT COALESCE(MAX(id), 0) FROM audit_log").fetchone()[0]
    ctx.conn.execute("INSERT INTO change_seen (user_id, project_id, seen_at, seen_id) VALUES (?, ?, ?, ?) "
                     "ON CONFLICT (user_id, project_id) DO UPDATE SET seen_at = excluded.seen_at, seen_id = excluded.seen_id",
                     (ctx.user["id"], project["id"], now, last))
    audit.log_action(ctx.conn, ctx.user["id"], "changes_seen", "change_seen", project["id"], {"space": project["key"]}, ctx.ip)
    return {"space": project["key"], "seen_at": now}


def api_ack(ctx):
    project = _space(ctx, ctx.body.get("space"))
    ids = [int(x) for x in (ctx.body.get("ids") or []) if str(x).isdigit()][:500]
    if not ids:
        raise ApiError(400, "Aucune ligne à marquer « Vu ». Correctif : envoyez ids, la liste des lignes du journal.")
    marks = ",".join("?" * len(ids))
    known = [r[0] for r in ctx.conn.execute("SELECT id FROM audit_log WHERE id IN ({})".format(marks), ids)]
    for i in known:
        ctx.conn.execute("INSERT OR IGNORE INTO change_acks (user_id, audit_id) VALUES (?, ?)", (ctx.user["id"], i))
    audit.log_action(ctx.conn, ctx.user["id"], "changes_ack", "change_acks", None, {"space": project["key"], "count": len(known)}, ctx.ip)
    return {"space": project["key"], "acked": len(known)}


def dashboard_section(conn, user, projects):
    """The Dashboard section « Nouveautés dans mes Spaces » (core/dashboard.py): one line per Space with something new."""
    items, total = [], 0
    for pid, key in projects.items():
        got = count(conn, user, {"id": pid, "key": key})
        if got["new"]:
            total += got["new"]
            items.append({"title": "{} · {} nouveauté{}".format(key, got["new"], "s" if got["new"] > 1 else ""),
                          "href": "#/changes/{}".format(key), "project": key, "status": "New",
                          "meta": "par " + ", ".join(got["people"][:6]), "late": False, "due": None})
    return {"key": "changes", "module": "changes", "title": "Nouveautés dans mes Spaces", "items": items, "total": len(items),
            "empty": "Rien de neuf depuis votre dernière visite.", "href": "#/changes",
            "kpi": {"label": "Nouveautés", "value": total, "tone": "info" if total else "neutral"}}


ROUTES = [
    ("GET", r"/api/changes", api_list, "user"),
    ("GET", r"/api/changes/count", api_count, "user"),
    ("POST", r"/api/changes/seen", api_seen, "user"),
    ("POST", r"/api/changes/ack", api_ack, "user"),
]
