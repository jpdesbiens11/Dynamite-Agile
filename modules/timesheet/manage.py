"""Timesheet, administrator side (D-B-023): projects and their organism,
approval of submitted weeks.

Rights: global administrators (and the approvers for their people's weeks)."""
from core import admin, db, permissions, validate
from core.errors import ApiError

from . import budget, catalog, leave, weeks


def _admin(ctx):
    permissions.require_admin(ctx.user)


# --------------------------------------------------------------------------
# Projects <-> organisms
# --------------------------------------------------------------------------
def save_settings(conn, project_id, **values):
    current = weeks.settings(conn, project_id)
    current.update(values)
    conn.execute(
        "INSERT INTO timesheet_projects (project_id, organism, contract_ref, task_set, open_to_all, enabled, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(project_id) DO UPDATE SET organism = excluded.organism, "
        "contract_ref = excluded.contract_ref, task_set = excluded.task_set, open_to_all = excluded.open_to_all, "
        "enabled = excluded.enabled, updated_at = excluded.updated_at",
        (project_id, current["organism"], current["contract_ref"], current["task_set"], int(current["open_to_all"]),
         int(current["enabled"]), db.utc_now()))


def api_projects(ctx):
    _admin(ctx)
    rows = ctx.conn.execute(
        "SELECT p.id, p.key, p.name, p.is_archived, COALESCE(t.organism, '') AS organism, "
        "COALESCE(t.contract_ref, '') AS contract_ref, COALESCE(t.task_set, 'pdp') AS task_set, "
        "COALESCE(t.open_to_all, 0) AS open_to_all, COALESCE(t.enabled, 1) AS enabled, "
        "(SELECT COALESCE(SUM(e.hours), 0) FROM timesheet_entries e WHERE e.project_id = p.id) AS hours "
        "FROM projects p LEFT JOIN timesheet_projects t ON t.project_id = p.id ORDER BY p.is_archived, p.key").fetchall()
    organisms = sorted({r["organism"] for r in rows if r["organism"]})
    return {"projects": db.rows(rows), "organisms": organisms, "meta": budget.meta(ctx.conn)}


def api_save_project(ctx):
    _admin(ctx)
    project_id = validate.int_param(ctx.params, "pid")
    if not ctx.conn.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,)).fetchone():
        raise ApiError(404, "Projet introuvable.")
    body = ctx.body
    values = {}
    if "organism" in body:
        values["organism"] = validate.text(body, "organism", 80, required=False)
    if "contract_ref" in body:
        values["contract_ref"] = validate.text(body, "contract_ref", 80, required=False)
    if "task_set" in body:
        sets = budget.structure(ctx.conn)
        values["task_set"] = validate.choice(body, "task_set", tuple(sets))
        current = weeks.settings(ctx.conn, project_id)["task_set"]
        if not sets[values["task_set"]]["active"] and values["task_set"] != current:
            raise ApiError(400, "Le Funding Space « {} » est désactivé. Correctif : réactivez-le ou choisissez-en un "
                                "autre.".format(sets[values["task_set"]]["label"]))
    if "open_to_all" in body:
        values["open_to_all"] = validate.boolean(body, "open_to_all")
    if "enabled" in body:
        values["enabled"] = validate.boolean(body, "enabled")
    save_settings(ctx.conn, project_id, **values)
    weeks.log(ctx, "timesheet_project_settings", project_id, {k: v for k, v in values.items()})
    return {"settings": weeks.settings(ctx.conn, project_id)}


# --------------------------------------------------------------------------
# Approval
# --------------------------------------------------------------------------
def api_approvals(ctx):
    """Administrators see every sheet; a manager (approver) the sheets of the
    people who named him in their settings (D-B-031)."""
    reports = None if ctx.user["is_admin"] else leave.reports_of(ctx.conn, ctx.user["id"])
    if reports == []:
        raise ApiError(403, "Aucune feuille à approuver : personne ne vous a nommé gestionnaire. Correctif : chaque "
                            "employé choisit son gestionnaire dans menu à votre nom → Paramètres.")
    status = ctx.query.get("status", "submitted")
    if status not in catalog.STATUSES and status != "all":
        raise ApiError(400, "Status « {} » inconnu. Correctif : {} ou all.".format(status, ", ".join(catalog.STATUSES)))
    conds, params = ([], []) if status == "all" else (["w.status = ?"], [status])
    if reports is not None:
        conds.append("w.user_id IN ({})".format(",".join("?" * len(reports))))
        params += reports
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    rows = ctx.conn.execute(
        "SELECT w.*, u.display_name, u.username, (SELECT COALESCE(SUM(hours), 0) FROM timesheet_entries e "
        "WHERE e.week_id = w.id) AS total FROM timesheet_weeks w JOIN users u ON u.id = w.user_id {} "
        "ORDER BY w.week_start DESC, u.display_name LIMIT 300".format(where), params).fetchall()
    out = []
    for r in db.rows(rows):
        if status == "all" and r["total"] == 0 and r["status"] == "draft":
            continue
        r["status_label"] = catalog.STATUSES[r["status"]]
        r["entries"] = weeks.entries(ctx.conn, r["id"])
        r["leave"] = leave.week_summary(ctx.conn, r["user_id"], r["entries"])
        out.append(r)
    return {"weeks": out, "statuses": catalog.STATUSES, "is_admin": bool(ctx.user["is_admin"])}


def api_decide(ctx):
    week_id = validate.int_param(ctx.params, "wid")
    week = ctx.conn.execute("SELECT * FROM timesheet_weeks WHERE id = ?", (week_id,)).fetchone()
    if week is None:
        raise ApiError(404, "Feuille de temps introuvable.")
    if not leave.can_approve(ctx.conn, ctx.user, week["user_id"]):
        raise ApiError(403, "Seul le gestionnaire de cette personne ou un administrateur décide de sa feuille de temps.")
    if week["user_id"] == ctx.user["id"] and not ctx.user["is_admin"]:
        raise ApiError(403, "Vous ne pouvez pas approuver votre propre feuille de temps.")
    action = validate.choice(ctx.body, "action", ("approve", "return", "reopen"))
    note = validate.text(ctx.body, "note", 500, required=action == "return")
    allowed = {"approve": ("submitted",), "return": ("submitted", "approved"), "reopen": ("approved", "submitted")}
    if week["status"] not in allowed[action]:
        raise ApiError(409, "Action impossible sur une feuille « {} ».".format(catalog.STATUSES[week["status"]]))
    if action == "approve":
        problems = weeks.problems(weeks.entries(ctx.conn, week_id))
        if problems:
            raise ApiError(400, "Feuille incomplète : " + " | ".join(problems))
    new_status = {"approve": "approved", "return": "returned", "reopen": "draft"}[action]
    now = db.utc_now()
    ctx.conn.execute("UPDATE timesheet_weeks SET status = ?, note = ?, decided_by = ?, decided_at = ?, updated_at = ? "
                     "WHERE id = ?", (new_status, "" if action == "approve" else note, ctx.user["id"], now, now, week_id))
    weeks.log(ctx, "timesheet_week_" + action, week_id, {"week": week["week_start"], "user_id": week["user_id"],
                                                          "note": note})
    return {"ok": True, "status": new_status}


# --------------------------------------------------------------------------
# Internal Space (INT) -- core start-up hook (lot v0.7)
# --------------------------------------------------------------------------
def ensure_internal_project(ctx):
    """Create the INT Space on first launch: internal codes and leave, organism « Interne », open to everyone."""
    if ctx.conn.execute("SELECT 1 FROM projects WHERE key = ?", (catalog.INTERNAL_KEY,)).fetchone():
        return None
    return admin.create_project_record(ctx, catalog.INTERNAL_KEY, catalog.INTERNAL_NAME, catalog.INTERNAL_DESCRIPTION)
