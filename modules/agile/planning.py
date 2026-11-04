"""Planning: sprints, board, backlog ordering and target versions."""
from core import db, validate
from core.errors import ApiError

from . import common as c
from .issues import list_issues


def api_board(ctx):
    """Active sprint grouped by status; without an active sprint, every open
    ticket plus tickets finished in the last 14 days (kanban mode)."""
    project_id, _ = c.access(ctx)
    conn = ctx.conn
    sprint = conn.execute("SELECT * FROM agile_sprints WHERE project_id = ? AND state = 'active'",
                          (project_id,)).fetchone()
    if sprint:
        issues = list_issues(conn, project_id, "AND t.bucket = 'agile' AND i.sprint_id = ? ", (sprint["id"],))
    else:  # requirements and PR / bugs / ECN stay out of the board (D-B-010/011)
        issues = list_issues(conn, project_id, "AND t.bucket = 'agile' "
                             "AND (s.category != 'done' OR i.resolved_at >= datetime('now', '-14 days')) ")
    return {"sprint": dict(sprint) if sprint else None, "issues": issues}


def api_dependencies(ctx):
    """'blocks' pairs within the project, for the backlog's order warning
    (H21, option A): a blocked ticket ranked before its blocker is flagged,
    but nothing prevents the order -- see docs/AGILE_ARCHITECTURE.md."""
    project_id, _ = c.access(ctx)
    rows = ctx.conn.execute(
        "SELECT bi.number AS blocker, ti.number AS blocked "
        "FROM agile_links l JOIN agile_issues bi ON bi.id = l.source_id "
        "JOIN agile_issues ti ON ti.id = l.target_id "
        "WHERE l.link_type = 'blocks' AND bi.project_id = ? AND ti.project_id = ?",
        (project_id, project_id)).fetchall()
    return {"blocks": [{"blocker": r["blocker"], "blocked": r["blocked"]} for r in rows]}


def api_move_rank(ctx):
    """Place ticket `number` right after `after_number` (None = top)."""
    project_id, _ = c.access(ctx, "editor")
    conn = ctx.conn
    row = c.get_issue(conn, project_id, c.opt_int(ctx.body, "number") or 0)
    after = c.opt_int(ctx.body, "after_number")
    if after is None:
        low = None
        top = conn.execute("SELECT MIN(rank) FROM agile_issues WHERE project_id = ?",
                           (project_id,)).fetchone()[0]
        new_rank = (top or 0) - 1
    else:
        low = c.get_issue(conn, project_id, after)["rank"]
        high = conn.execute("SELECT MIN(rank) FROM agile_issues WHERE project_id = ? AND rank > ? "
                            "AND id != ?", (project_id, low, row["id"])).fetchone()[0]
        new_rank = low + 1 if high is None else (low + high) / 2
    conn.execute("UPDATE agile_issues SET rank = ? WHERE id = ?", (new_rank, row["id"]))
    c.log(ctx, "agile_issue_rank", "agile_issue", row["id"], None)
    return {"ok": True}


# --------------------------------------------------------------------------
# Sprints
# --------------------------------------------------------------------------
def api_create_sprint(ctx):
    project_id, _ = c.access(ctx, "editor")
    count = ctx.conn.execute("SELECT COUNT(*) FROM agile_sprints WHERE project_id = ?",
                             (project_id,)).fetchone()[0]
    name = validate.text(ctx.body, "name", 80, required=False) or "Sprint {}".format(count + 1)
    goal = validate.text(ctx.body, "goal", 500, required=False)
    sid = ctx.conn.execute("INSERT INTO agile_sprints (project_id, name, goal, created_at) "
                           "VALUES (?, ?, ?, ?)", (project_id, name, goal, db.utc_now())).lastrowid
    c.log(ctx, "agile_sprint_create", "agile_sprint", sid, {"name": name})
    return {"id": sid}


def _sprint(ctx, project_id):
    return c.owned(ctx.conn, "agile_sprints", validate.int_param(ctx.params, "sid"),
                   project_id, "Sprint")


def api_update_sprint(ctx):
    project_id, _ = c.access(ctx, "editor")
    sprint = _sprint(ctx, project_id)
    name = validate.text(ctx.body, "name", 80) if "name" in ctx.body else sprint["name"]
    goal = validate.text(ctx.body, "goal", 500, required=False) if "goal" in ctx.body else sprint["goal"]
    start = c.opt_date(ctx.body, "start_date") if "start_date" in ctx.body else sprint["start_date"]
    end = c.opt_date(ctx.body, "end_date") if "end_date" in ctx.body else sprint["end_date"]
    ctx.conn.execute("UPDATE agile_sprints SET name = ?, goal = ?, start_date = ?, end_date = ? "
                     "WHERE id = ?", (name, goal, start, end, sprint["id"]))
    c.log(ctx, "agile_sprint_update", "agile_sprint", sprint["id"], {"name": name})
    return {"ok": True}


def api_start_sprint(ctx):
    project_id, _ = c.access(ctx, "editor")
    sprint = _sprint(ctx, project_id)
    if sprint["state"] != "future":
        raise ApiError(409, "Seul un sprint à venir peut être démarré.")
    if ctx.conn.execute("SELECT 1 FROM agile_sprints WHERE project_id = ? AND state = 'active'",
                        (project_id,)).fetchone():
        raise ApiError(409, "Un sprint est déjà actif : clôturez-le d'abord.")
    start = c.opt_date(ctx.body, "start_date") or db.utc_now()[:10]
    end = c.opt_date(ctx.body, "end_date")
    if end and end < start:
        raise ApiError(400, "La date de fin précède la date de début.")
    ctx.conn.execute("UPDATE agile_sprints SET state = 'active', start_date = ?, end_date = ? "
                     "WHERE id = ?", (start, end, sprint["id"]))
    c.log(ctx, "agile_sprint_start", "agile_sprint", sprint["id"], None)
    return {"ok": True}


def api_close_sprint(ctx):
    """Close the active sprint; unfinished tickets go back to the backlog."""
    project_id, _ = c.access(ctx, "editor")
    sprint = _sprint(ctx, project_id)
    if sprint["state"] != "active":
        raise ApiError(409, "Seul le sprint actif peut être clôturé.")
    moved = ctx.conn.execute(
        "UPDATE agile_issues SET sprint_id = NULL, updated_at = ? WHERE sprint_id = ? AND status_id IN "
        "(SELECT id FROM agile_statuses WHERE category != 'done')",
        (db.utc_now(), sprint["id"])).rowcount
    ctx.conn.execute("UPDATE agile_sprints SET state = 'closed', end_date = COALESCE(end_date, ?) "
                     "WHERE id = ?", (db.utc_now()[:10], sprint["id"]))
    c.log(ctx, "agile_sprint_close", "agile_sprint", sprint["id"], {"returned_to_backlog": moved})
    return {"ok": True, "returned_to_backlog": moved}


def api_delete_sprint(ctx):
    project_id, _ = c.access(ctx, "editor")
    sprint = _sprint(ctx, project_id)
    if sprint["state"] != "future":
        raise ApiError(409, "Seul un sprint à venir peut être supprimé.")
    ctx.conn.execute("DELETE FROM agile_sprints WHERE id = ?", (sprint["id"],))
    c.log(ctx, "agile_sprint_delete", "agile_sprint", sprint["id"], {"name": sprint["name"]})
    return {"ok": True}


# --------------------------------------------------------------------------
# Versions
# --------------------------------------------------------------------------
def api_create_version(ctx):
    project_id, _ = c.access(ctx, "editor")
    name = validate.text(ctx.body, "name", 60)
    try:
        vid = ctx.conn.execute("INSERT INTO agile_versions (project_id, name, release_date) "
                               "VALUES (?, ?, ?)",
                               (project_id, name, c.opt_date(ctx.body, "release_date"))).lastrowid
    except db.sqlite3.IntegrityError:
        raise ApiError(409, "Cette version existe déjà.")
    c.log(ctx, "agile_version_create", "agile_version", vid, {"name": name})
    return {"id": vid}


def api_update_version(ctx):
    project_id, _ = c.access(ctx, "editor")
    version = c.owned(ctx.conn, "agile_versions", validate.int_param(ctx.params, "vid"),
                      project_id, "Version")
    name = validate.text(ctx.body, "name", 60) if "name" in ctx.body else version["name"]
    date = c.opt_date(ctx.body, "release_date") if "release_date" in ctx.body else version["release_date"]
    released = validate.boolean(ctx.body, "is_released", bool(version["is_released"]))
    try:
        ctx.conn.execute("UPDATE agile_versions SET name = ?, release_date = ?, is_released = ? "
                         "WHERE id = ?", (name, date, int(released), version["id"]))
    except db.sqlite3.IntegrityError:
        raise ApiError(409, "Cette version existe déjà.")
    c.log(ctx, "agile_version_update", "agile_version", version["id"], {"name": name})
    return {"ok": True}


def api_delete_version(ctx):
    project_id, _ = c.access(ctx, "admin")
    version = c.owned(ctx.conn, "agile_versions", validate.int_param(ctx.params, "vid"),
                      project_id, "Version")
    ctx.conn.execute("DELETE FROM agile_versions WHERE id = ?", (version["id"],))
    c.log(ctx, "agile_version_delete", "agile_version", version["id"], {"name": version["name"]})
    return {"ok": True}
