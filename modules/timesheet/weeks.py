"""Timesheet, employee side (D-B-023): one sheet per person and week
(Monday to Sunday), time ranges on projects of the database.

Cycle: Brouillon -> Soumise -> Approuvée (admin) or Renvoyée (admin, with a
note) -> corrected and submitted again. A range may be saved without its
description, but the week is never submitted while one is empty.
Loggable projects: active projects the person is a member of, the ones open
to everyone, and all of them for an administrator.
"""
import datetime as dt

from core import audit, db, validate
from core.errors import ApiError

from . import budget, catalog, leave

DAY_NAMES = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]


def monday(value=None):
    if value in (None, ""):
        day = dt.date.today()
    else:
        try:
            day = dt.date.fromisoformat(str(value)[:10])
        except ValueError:
            raise ApiError(400, "Date « {} » invalide. Correctif : format AAAA-MM-JJ.".format(value))
    return day - dt.timedelta(days=day.weekday())


def day_label(iso):
    d = dt.date.fromisoformat(iso)
    return "{} {}".format(DAY_NAMES[d.weekday()], d.strftime("%d/%m"))


def log(ctx, action, object_id, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "timesheet", object_id, details, ctx.ip)


# --------------------------------------------------------------------------
# Projects a person may log time on
# --------------------------------------------------------------------------
def settings(conn, project_id):
    row = conn.execute("SELECT * FROM timesheet_projects WHERE project_id = ?", (project_id,)).fetchone()
    return dict(row) if row else {"project_id": project_id, "organism": "", "contract_ref": "", "task_set": "pdp",
                                  "open_to_all": 0, "enabled": 1}


def loggable_projects(conn, user):
    rows = conn.execute(
        "SELECT p.id, p.key, p.name, COALESCE(t.organism, '') AS organism, COALESCE(t.task_set, 'pdp') AS task_set, "
        "COALESCE(t.open_to_all, 0) AS open_to_all FROM projects p "
        "LEFT JOIN timesheet_projects t ON t.project_id = p.id "
        "WHERE p.is_archived = 0 AND COALESCE(t.enabled, 1) = 1 AND (? = 1 OR COALESCE(t.open_to_all, 0) = 1 "
        "OR EXISTS (SELECT 1 FROM memberships m WHERE m.project_id = p.id AND m.user_id = ?)) "
        "ORDER BY CASE WHEN COALESCE(t.open_to_all, 0) = 1 THEN 1 ELSE 0 END, p.key",
        (1 if user["is_admin"] else 0, user["id"])).fetchall()
    return db.rows(rows)


# --------------------------------------------------------------------------
# Week
# --------------------------------------------------------------------------
def week_row(conn, user_id, start, create=False):
    row = conn.execute("SELECT * FROM timesheet_weeks WHERE user_id = ? AND week_start = ?",
                       (user_id, start.isoformat())).fetchone()
    if row is None and create:
        now = db.utc_now()
        conn.execute("INSERT INTO timesheet_weeks (user_id, week_start, status, created_at, updated_at) "
                     "VALUES (?, ?, 'draft', ?, ?)", (user_id, start.isoformat(), now, now))
        row = conn.execute("SELECT * FROM timesheet_weeks WHERE user_id = ? AND week_start = ?",
                           (user_id, start.isoformat())).fetchone()
    return dict(row) if row else None


def entries(conn, week_id):
    rows = conn.execute(
        "SELECT e.*, p.key AS project_key, p.name AS project_name FROM timesheet_entries e "
        "JOIN projects p ON p.id = e.project_id WHERE e.week_id = ? ORDER BY e.work_date, e.id", (week_id,)).fetchall()
    out = []
    names = budget.labels(conn)
    for r in db.rows(rows):
        r["task_label"] = names.get(r["task_key"], r["task_key"])
        r["day_label"] = day_label(r["work_date"])
        out.append(r)
    return out


def describe_week(conn, week, start):
    info = {"start": start.isoformat(), "end": (start + dt.timedelta(days=6)).isoformat(), "id": None,
            "status": "draft", "note": "", "submitted_at": None, "decided_at": None, "decided_by_name": None}
    if week:
        info.update(id=week["id"], status=week["status"], note=week["note"], submitted_at=week["submitted_at"],
                    decided_at=week["decided_at"])
        if week["decided_by"]:
            who = conn.execute("SELECT display_name FROM users WHERE id = ?", (week["decided_by"],)).fetchone()
            info["decided_by_name"] = who["display_name"] if who else None
    info["status_label"] = catalog.STATUSES[info["status"]]
    info["editable"] = info["status"] in catalog.EDITABLE
    return info


def api_week(ctx):
    start = monday(ctx.query.get("start"))
    week = week_row(ctx.conn, ctx.user["id"], start)
    rows = entries(ctx.conn, week["id"]) if week else []
    days = [(start + dt.timedelta(days=i)).isoformat() for i in range(7)]
    totals = {d: round(sum(e["hours"] for e in rows if e["work_date"] == d), 2) for d in days}
    return {"week": describe_week(ctx.conn, week, start), "entries": rows, "days": days,
            "day_labels": [day_label(d) for d in days], "totals": totals,
            "total": round(sum(totals.values()), 2), "projects": loggable_projects(ctx.conn, ctx.user),
            "meta": budget.meta(ctx.conn), "is_admin": bool(ctx.user["is_admin"]), "today": dt.date.today().isoformat(),
            "leave": leave.week_summary(ctx.conn, ctx.user["id"], rows),  # D-B-031
            "is_manager": bool(leave.reports_of(ctx.conn, ctx.user["id"]))}


# --------------------------------------------------------------------------
# Entries (time ranges)
# --------------------------------------------------------------------------
def _fields(ctx, body, current=None):
    current = current or {}
    out = {}
    projects = {p["id"]: p for p in loggable_projects(ctx.conn, ctx.user)}
    if "project_id" in body or not current:
        try:
            pid = int(body.get("project_id"))
        except (TypeError, ValueError):
            pid = None
        if pid not in projects:
            raise ApiError(400, "Projet invalide ou non accessible. Correctif : choisissez un projet de la liste.")
        out["project_id"] = pid
    project = projects.get(out.get("project_id", current.get("project_id")))
    if project is None:
        raise ApiError(400, "Ce projet n'est plus ouvert aux feuilles de temps. Correctif : choisissez-en un autre.")
    if "task_key" in body or not current or "project_id" in out:
        task = str(body.get("task_key", current.get("task_key", "")))
        allowed = budget.allowed(ctx.conn, project["task_set"])
        if task and task == current.get("task_key") and "project_id" not in out:
            allowed = allowed + [task]  # a deactivated line stays on its existing range
        if task not in allowed:
            task = allowed[0] if "task_key" not in body and allowed else task
        if task not in allowed:
            raise ApiError(400, "Task « {} » invalide pour {}. Correctif : choisissez une task de la liste."
                           .format(task, project["key"]))
        out["task_key"] = task
    if "hours" in body or not current:
        try:
            hours = round(float(body.get("hours", 1)), 2)
        except (TypeError, ValueError):
            raise ApiError(400, "Heures « {} » invalides. Correctif : un nombre, ex. 1,5.".format(body.get("hours")))
        if not 0.25 <= hours <= catalog.MAX_DAY_HOURS or abs(hours * 4 - round(hours * 4)) > 1e-9:
            raise ApiError(400, "Heures {} refusées. Correctif : de 0,25 à 24, par quarts d'heure (0,25).".format(hours))
        out["hours"] = hours
    if "description" in body:
        out["description"] = validate.text(body, "description", catalog.MAX_DESCRIPTION, required=False)
    return out


def _date_in_week(value, start):
    try:
        day = dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        raise ApiError(400, "Date « {} » invalide. Correctif : format AAAA-MM-JJ.".format(value))
    if not start <= day <= start + dt.timedelta(days=6):
        raise ApiError(400, "Le {} n'est pas dans la semaine du {}. Correctif : changez de semaine.".format(day, start))
    return day.isoformat()


def _check_day(conn, week_id, work_date, hours, entry_id=None):
    other = conn.execute("SELECT COALESCE(SUM(hours), 0) FROM timesheet_entries WHERE week_id = ? AND work_date = ? "
                         "AND id != ?", (week_id, work_date, entry_id or 0)).fetchone()[0]
    if other + hours > catalog.MAX_DAY_HOURS:
        raise ApiError(400, "Plus de 24 h le {} ({} h). Correctif : réduisez les heures de cette journée."
                       .format(day_label(work_date), round(other + hours, 2)))


def _editable_week(week):
    if week["status"] not in catalog.EDITABLE:
        raise ApiError(409, "Semaine {} : plus modifiable. Correctif : retirez la soumission, ou demandez à un "
                            "administrateur de la rouvrir.".format(catalog.STATUSES[week["status"]].lower()))


def api_create(ctx):
    body = ctx.body
    work_date = body.get("work_date")
    start = monday(work_date)
    fields = _fields(ctx, body)
    week = week_row(ctx.conn, ctx.user["id"], start, create=True)
    _editable_week(week)
    work_date = _date_in_week(work_date, start)
    _check_day(ctx.conn, week["id"], work_date, fields["hours"])
    now = db.utc_now()
    entry_id = ctx.conn.execute(
        "INSERT INTO timesheet_entries (week_id, project_id, work_date, task_key, hours, description, created_at, "
        "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (week["id"], fields["project_id"], work_date, fields["task_key"], fields["hours"],
         fields.get("description", ""), now, now)).lastrowid
    log(ctx, "timesheet_entry_created", entry_id, {"date": work_date, "hours": fields["hours"]})
    return {"entry": next(e for e in entries(ctx.conn, week["id"]) if e["id"] == entry_id)}


def _own_entry(ctx):
    entry_id = validate.int_param(ctx.params, "eid")
    row = ctx.conn.execute("SELECT e.*, w.user_id, w.status, w.week_start FROM timesheet_entries e "
                           "JOIN timesheet_weeks w ON w.id = e.week_id WHERE e.id = ?", (entry_id,)).fetchone()
    if row is None or row["user_id"] != ctx.user["id"]:
        raise ApiError(404, "Plage de temps introuvable.")
    _editable_week(row)
    return dict(row)


def api_update(ctx):
    entry = _own_entry(ctx)
    changes = _fields(ctx, ctx.body, entry)
    if "work_date" in ctx.body:
        changes["work_date"] = _date_in_week(ctx.body["work_date"], dt.date.fromisoformat(entry["week_start"]))
    changes = {k: v for k, v in changes.items() if v != entry.get(k)}
    if changes:
        _check_day(ctx.conn, entry["week_id"], changes.get("work_date", entry["work_date"]),
                   changes.get("hours", entry["hours"]), entry["id"])
        changes["updated_at"] = db.utc_now()
        ctx.conn.execute("UPDATE timesheet_entries SET {} WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                         list(changes.values()) + [entry["id"]])
        log(ctx, "timesheet_entry_updated", entry["id"], {k: v for k, v in changes.items() if k != "updated_at"})
    return {"entry": next(e for e in entries(ctx.conn, entry["week_id"]) if e["id"] == entry["id"])}


def api_delete(ctx):
    entry = _own_entry(ctx)
    ctx.conn.execute("DELETE FROM timesheet_entries WHERE id = ?", (entry["id"],))
    log(ctx, "timesheet_entry_deleted", entry["id"], {"date": entry["work_date"], "hours": entry["hours"]})
    return {"ok": True}


# --------------------------------------------------------------------------
# Submit / recall
# --------------------------------------------------------------------------
def problems(rows):
    """Why a week cannot be submitted: one line per problem, naming the range and the fix."""
    if not rows:
        return ["Aucune plage de temps. Correctif : ajoutez au moins une plage avant de soumettre."]
    out = []
    for e in rows:
        if not e["description"].strip():
            out.append("{} · {} · {} ({} h) : description vide. Correctif : décrivez brièvement le travail fait."
                       .format(e["day_label"], e["project_key"], e["task_label"], e["hours"]))
    return out


def api_submit(ctx):
    start = monday(ctx.body.get("start"))
    week = week_row(ctx.conn, ctx.user["id"], start)
    if week is None:
        raise ApiError(400, "Aucune plage de temps. Correctif : ajoutez au moins une plage avant de soumettre.")
    _editable_week(week)
    found = problems(entries(ctx.conn, week["id"]))
    if found:
        raise ApiError(400, "Semaine non soumise — {} problème(s) : {}".format(len(found), " | ".join(found)))
    now = db.utc_now()
    ctx.conn.execute("UPDATE timesheet_weeks SET status = 'submitted', submitted_at = ?, updated_at = ? WHERE id = ?",
                     (now, now, week["id"]))
    log(ctx, "timesheet_week_submitted", week["id"], {"week": start.isoformat()})
    return api_week_for(ctx, start)


def api_recall(ctx):
    start = monday(ctx.body.get("start"))
    week = week_row(ctx.conn, ctx.user["id"], start)
    if week is None or week["status"] != "submitted":
        raise ApiError(409, "Seule une semaine soumise, pas encore approuvée, peut être retirée.")
    ctx.conn.execute("UPDATE timesheet_weeks SET status = 'draft', updated_at = ? WHERE id = ?", (db.utc_now(), week["id"]))
    log(ctx, "timesheet_week_recalled", week["id"], {"week": start.isoformat()})
    return api_week_for(ctx, start)


def api_week_for(ctx, start):
    ctx.query = {"start": start.isoformat()}
    return api_week(ctx)
