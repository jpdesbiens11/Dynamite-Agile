"""Owners and follow-up of the actions of Diamond (0.60.38, D-O-047): the project risks and the DFMEA rows get a person
of the team, a due date and a status, and « Suivre dans Agile » turns the action into a ticket of the same Space.

  owner     a member of the Space (risks: owner_id since 0.60.14; DFMEA: action_owner_id);
  due       a date AAAA-MM-JJ (risks: due_date; DFMEA: action_due); late when past and not done;
  status    risks: open / in_progress / closed; DFMEA: open / in_progress / done (action_status);
  ticket    issue_id: the Agile ticket that carries the action. Its status is read from the ticket, never copied: when
            the ticket reaches a « done » status in Agile, the risk shows « Fermé » and the DFMEA row « Fait ».
The person sees her open actions on the Dashboard (« Mes actions Diamond », late first) and Bob le mineur in his summary.
Every write is journalled.
"""
import datetime as dt

from core import audit, validate
from core.errors import ApiError

from . import functions as F

DFMEA_STATUSES = {"open": "À faire", "in_progress": "En cours", "done": "Fait"}
FROM_CATEGORY = {"risk": {"todo": "open", "in_progress": "in_progress", "done": "closed"},
                 "dfmea": {"todo": "open", "in_progress": "in_progress", "done": "done"},
                 "pfmea": {"todo": "open", "in_progress": "in_progress", "done": "done"}}  # 0.60.103 (D-O-114): the PFMEA too
CLOSED = {"risk": "closed", "dfmea": "done", "pfmea": "done"}


def today():
    return dt.date.today().isoformat()


def members(conn, pid):
    return [dict(r) for r in conn.execute(
        "SELECT u.id, u.display_name FROM users u WHERE u.is_active = 1 AND (u.id IN (SELECT user_id FROM memberships WHERE project_id = ?) "
        "OR u.is_admin = 1) ORDER BY u.display_name", (pid,))]


def owner(conn, pid, value):
    if value in (None, "", 0, "0"):
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = -1
    if value not in {m["id"] for m in members(conn, pid)}:
        raise ApiError(400, "Responsable introuvable parmi les membres du Space. Correctif : ajoutez-le au Space, ou choisissez un membre.")
    return value


def due(value):
    value = str(value or "").strip()
    if value:
        try:
            dt.date.fromisoformat(value)
        except ValueError:
            raise ApiError(400, "Échéance « {} » : date AAAA-MM-JJ. Correctif : choisissez-la dans le calendrier.".format(value))
    return value


def tickets(conn, ids):
    ids = [i for i in set(ids) if i]
    if not ids:
        return {}
    rows = conn.execute(
        "SELECT i.id, i.number, i.title, i.due_date, p.key AS space, s.name AS status, s.category, u.display_name AS assignee "
        "FROM agile_issues i JOIN projects p ON p.id = i.project_id JOIN agile_statuses s ON s.id = i.status_id "
        "LEFT JOIN users u ON u.id = i.assignee_id WHERE i.id IN ({})".format(",".join("?" * len(ids))), ids).fetchall()
    return {r["id"]: dict(r, key="{}-{}".format(r["space"], r["number"]), href="#/agile/{}/issue/{}".format(r["space"], r["number"]))
            for r in rows}


def enrich(conn, rows, kind):
    """Adds ticket (or None), status_from_ticket and late; the status of a row followed in Agile is its ticket's."""
    field = "status" if kind == "risk" else "action_status"
    due_field = "due_date" if kind == "risk" else "action_due"
    found = tickets(conn, [r.get("issue_id") for r in rows])
    now = today()
    for r in rows:
        t = found.get(r.get("issue_id"))
        r["ticket"] = t
        r["status_from_ticket"] = bool(t)
        if t:
            r[field] = FROM_CATEGORY[kind].get(t["category"], r[field])
        r["late"] = bool(r.get(due_field)) and r[due_field] < now and r[field] != CLOSED[kind]
    return rows


def _task_type(conn, pid):
    rows = conn.execute("SELECT * FROM agile_issue_types WHERE project_id = ? AND is_subtask = 0 AND is_requirement = 0 "
                        "AND change_role = '' AND bucket = 'agile' ORDER BY CASE icon_key WHEN 'task' THEN 0 WHEN 'story' THEN 1 "
                        "WHEN 'epic' THEN 3 ELSE 2 END, position", (pid,)).fetchall()
    if not rows:
        raise ApiError(409, "Aucun type de ticket dans l'Agile de ce Space. Correctif : ⚙ Admin → Spaces → ouvrir le Space pour "
                            "remettre Agile en place, ou créez un type « Task » dans Agile → Réglages.")
    return dict(rows[0])


def _source(conn, pid, kind, oid):
    from . import dfmea, risks
    if kind == "risk":
        row = next((r for r in risks.rows(conn, pid) if r["id"] == oid), None)
        if row is None:
            raise ApiError(404, "Risque introuvable dans ce Space (archivé ?). Correctif : rechargez la page.")
        code = "R-{}".format(row["number"])
        return row, code, row["action"], row["title"], row["owner_id"], row["due_date"], "prisk", "high" if row["score"] >= 15 else "medium"
    if kind == "pfmea":  # 0.60.103 (D-O-114)
        from . import pfmea
        row = next((r for r in pfmea.rows(conn, pid) if r["id"] == oid), None)
        if row is None:
            raise ApiError(404, "Ligne du PFMEA introuvable. Correctif : rechargez la page.")
        return (row, row["code"], row["action"], row["failure_mode"], row["action_owner_id"], row["action_due"], "pfmea",
                "high" if row["ap"] == "H" else "medium")
    row = next((r for r in dfmea.rows(conn, pid) if r["id"] == oid), None)
    if row is None:
        raise ApiError(404, "Ligne du DFMEA introuvable (effacée ?). Correctif : rechargez la page.")
    return (row, "DFMEA L{}".format(row["line"]), row["action"], row["failure_mode"], row["action_owner_id"], row["action_due"],
            "dfmea", "high" if row["ap"] == "H" else "medium")


def api_track(ctx):
    """POST …/actions/<risk|dfmea>/<id>/track: the action becomes a ticket of the Agile of the same Space."""
    from modules.agile import issues
    from . import dfmea, risks
    pid = F.access(ctx, "editor")
    kind, oid = ctx.params["kind"], validate.int_param(ctx.params, "oid")
    conn = ctx.conn
    row, code, action, what, who, when, page, priority = _source(conn, pid, kind, oid)
    if row["ticket"]:
        raise ApiError(409, "{} est déjà suivi dans Agile : {}. Correctif : ouvrez ce ticket.".format(code, row["ticket"]["key"]))
    if not action.strip():
        raise ApiError(400, "{} n'a pas encore d'action. Correctif : écrivez d'abord l'action (ce qui sera fait), puis « Suivre dans Agile ».".format(code))
    key = conn.execute("SELECT key FROM projects WHERE id = ?", (pid,)).fetchone()["key"]
    first = " ".join(action.split())
    focus = code if kind == "risk" else what[:80]
    body = {"type_id": _task_type(conn, pid)["id"], "priority": priority,
            "title": "{} · {}".format(code, first)[:255],
            "description": "Action de {} « {} » (Diamond).\n\n{}\n\nLa ligne dans Diamond : /?focus={}#/diamond/{}/{}".format(
                code, what, action.strip(), validate_link(focus), key, page)[:20000]}
    if who:
        body["assignee_id"] = who
    if when:
        body["due_date"] = when
    original, ctx.body = ctx.body, body
    try:
        made = issues.api_create(ctx)
    finally:
        ctx.body = original
    issue = conn.execute("SELECT id FROM agile_issues WHERE project_id = ? AND number = ?", (pid, made["number"])).fetchone()
    table = {"risk": "diamond_risks", "dfmea": "diamond_dfmea", "pfmea": "diamond_pfmea"}[kind]
    conn.execute("UPDATE {} SET issue_id = ? WHERE id = ?".format(table), (issue["id"], oid))
    audit.log_action(conn, ctx.user["id"], "diamond_action_tracked", table, oid, {"code": code, "ticket": made["key"]}, ctx.ip)
    if kind == "pfmea":
        from . import pfmea
        return dict(pfmea.payload(conn, ctx.user, pid), tracked=made["key"])
    data = risks.payload(conn, pid) if kind == "risk" else dfmea.payload(conn, pid)
    return dict(data, tracked=made["key"])


def api_track_pfmea(ctx):
    """POST …/pfmea/rows/<id>/track (0.60.103, D-O-114): a PFMEA action becomes a ticket; the route sits under /pfmea so that
    the « PFMEA » switch of ⚙ Admin covers it, and the process access list of the Space applies."""
    from . import process
    process.access(ctx, "editor")
    ctx.params = dict(ctx.params, kind="pfmea")
    return api_track(ctx)


def validate_link(text):
    from urllib.parse import quote
    return quote(str(text), safe="")


def mine(conn, user_id, projects):
    """The open actions of one person in the given Spaces ({pid: key}), late first."""
    from . import dfmea, risks
    out = []
    for pid, key in projects.items():
        has = conn.execute("SELECT (SELECT COUNT(*) FROM diamond_risks WHERE project_id = ? AND owner_id = ? AND archived = 0) + "
                           "(SELECT COUNT(*) FROM diamond_dfmea WHERE project_id = ? AND action_owner_id = ?)", (pid, user_id, pid, user_id)).fetchone()[0]
        if not has:
            continue
        for r in risks.rows(conn, pid):
            if r["owner_id"] == user_id and r["status"] != "closed":
                out.append(_item(key, pid, "risk", r, "R-{}".format(r["number"]), r["title"], r["action"], r["due_date"],
                                 risks.STATUSES.get(r["status"], r["status"]), "prisk", "R-{}".format(r["number"])))
        for d in dfmea.rows(conn, pid):
            if d["action_owner_id"] == user_id and d["action_status"] != "done":
                out.append(_item(key, pid, "dfmea", d, "DFMEA L{}".format(d["line"]), d["failure_mode"], d["action"], d["action_due"],
                                 DFMEA_STATUSES.get(d["action_status"], d["action_status"]), "dfmea", d["failure_mode"][:80]))
    out.sort(key=lambda i: (not i["late"], i["due"] or "9999", i["project"], i["code"]))
    return out


def _item(key, pid, kind, row, code, what, action, when, status, page, focus):
    return {"kind": kind, "id": row["id"], "pid": pid, "project": key, "code": code, "what": what, "action": action, "due": when,
            "late": row["late"], "status": status, "status_key": row["status" if kind == "risk" else "action_status"],
            "ticket": row["ticket"]["key"] if row["ticket"] else "", "ticket_href": row["ticket"]["href"] if row["ticket"] else "",
            "page": "#/diamond/{}/{}".format(key, page), "focus": focus}


def dashboard(conn, user, projects):
    """Dashboard hook (core lot v0.10): « Mes actions Diamond », late first; the status changes right from the card when
    the action is not followed in Agile (otherwise the ticket carries it)."""
    items = []
    for a in mine(conn, user["id"], projects):
        url = "/api/diamond/p/{}/{}".format(a["pid"], "risks/{}".format(a["id"]) if a["kind"] == "risk" else "dfmea/rows/{}".format(a["id"]))
        field = "status" if a["kind"] == "risk" else "action_status"
        choices = {"risk": {"open": "Ouvert", "in_progress": "En traitement", "closed": "Fermé"}, "dfmea": DFMEA_STATUSES}[a["kind"]]
        item = {"title": "{} · {}".format(a["code"], a["action"] or a["what"])[:160],
                "href": "/?focus={}#{}".format(validate_link(a["focus"]), a["page"][1:]), "project": a["project"],
                "status": a["status"], "due": a["due"], "late": a["late"],
                "meta": " · ".join(x for x in (a["what"][:80], "ticket " + a["ticket"] if a["ticket"] else "") if x)}
        if not a["ticket"]:
            item["action"] = {"method": "PATCH", "url": url, "field": field, "current": a["status"],
                              "choices": [[k, v] for k, v in choices.items() if k != a["status_key"]]}
        items.append(item)
    late = sum(1 for i in items if i["late"])
    return [{"key": "diamond_actions", "title": "Mes actions Diamond (risques et DFMEA)", "items": items, "total": len(items),
             "list_href": "#/diamond/{key}/prisk", "mine": True,
             "empty": "Aucune action de risque ni de DFMEA ne vous est confiée.",
             "kpi": {"label": "Actions Diamond", "value": len(items), "tone": "danger" if late else "neutral",
                     "note": "{} en retard".format(late) if late else ""}}]
