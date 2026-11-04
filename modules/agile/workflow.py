"""Configuration (admin): workflows, statuses, transitions, types, labels."""
from core import db, validate
from core.errors import ApiError

from . import common as c


def _workflow(ctx, project_id, wid):
    return c.owned(ctx.conn, "agile_workflows", wid, project_id, "Workflow")


def api_create_workflow(ctx):
    """New workflow with a single initial status, to be completed afterwards."""
    project_id, _ = c.access(ctx, "admin")
    name = validate.text(ctx.body, "name", 60)
    try:
        wid = ctx.conn.execute("INSERT INTO agile_workflows (project_id, name) VALUES (?, ?)",
                               (project_id, name)).lastrowid
    except db.sqlite3.IntegrityError:
        raise ApiError(409, "Un workflow porte déjà ce nom.")
    ctx.conn.execute("INSERT INTO agile_statuses (workflow_id, name, category, position, is_initial) "
                     "VALUES (?, 'To Do', 'todo', 0, 1)", (wid,))
    c.log(ctx, "agile_workflow_create", "agile_workflow", wid, {"name": name})
    return {"id": wid}


def api_rename_workflow(ctx):
    project_id, _ = c.access(ctx, "admin")
    wf = _workflow(ctx, project_id, validate.int_param(ctx.params, "wid"))
    name = validate.text(ctx.body, "name", 60)
    try:
        ctx.conn.execute("UPDATE agile_workflows SET name = ? WHERE id = ?", (name, wf["id"]))
    except db.sqlite3.IntegrityError:
        raise ApiError(409, "Un workflow porte déjà ce nom.")
    c.log(ctx, "agile_workflow_rename", "agile_workflow", wf["id"], {"name": name})
    return {"ok": True}


# --------------------------------------------------------------------------
# Statuses
# --------------------------------------------------------------------------
def api_create_status(ctx):
    project_id, _ = c.access(ctx, "admin")
    wf = _workflow(ctx, project_id, c.opt_int(ctx.body, "workflow_id") or 0)
    name = validate.text(ctx.body, "name", 40)
    category = validate.choice(ctx.body, "category", c.CATEGORIES)
    position = ctx.conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM agile_statuses "
                                "WHERE workflow_id = ?", (wf["id"],)).fetchone()[0]
    try:
        sid = ctx.conn.execute("INSERT INTO agile_statuses (workflow_id, name, category, position) "
                               "VALUES (?, ?, ?, ?)", (wf["id"], name, category, position)).lastrowid
    except db.sqlite3.IntegrityError:
        raise ApiError(409, "Ce workflow a déjà un status de ce nom.")
    c.log(ctx, "agile_status_create", "agile_status", sid, {"name": name, "workflow": wf["id"]})
    return {"id": sid}


def api_update_status(ctx):
    project_id, _ = c.access(ctx, "admin")
    status = c.status_row(ctx.conn, validate.int_param(ctx.params, "sid"), project_id)
    name = validate.text(ctx.body, "name", 40) if "name" in ctx.body else status["name"]
    category = (validate.choice(ctx.body, "category", c.CATEGORIES)
                if "category" in ctx.body else status["category"])
    position = c.opt_int(ctx.body, "position")
    if position is None:
        position = status["position"]
    try:
        ctx.conn.execute("UPDATE agile_statuses SET name = ?, category = ?, position = ? WHERE id = ?",
                         (name, category, position, status["id"]))
    except db.sqlite3.IntegrityError:
        raise ApiError(409, "Ce workflow a déjà un status de ce nom.")
    if validate.boolean(ctx.body, "is_initial", False):
        ctx.conn.execute("UPDATE agile_statuses SET is_initial = (id = ?) WHERE workflow_id = ?",
                         (status["id"], status["workflow_id"]))
    c.log(ctx, "agile_status_update", "agile_status", status["id"], {"name": name})
    return {"ok": True}


def api_delete_status(ctx):
    project_id, _ = c.access(ctx, "admin")
    status = c.status_row(ctx.conn, validate.int_param(ctx.params, "sid"), project_id)
    used = ctx.conn.execute("SELECT COUNT(*) FROM agile_issues WHERE status_id = ?",
                            (status["id"],)).fetchone()[0]
    if used:
        raise ApiError(409, "{} ticket(s) sont dans ce status : déplacez-les d'abord.".format(used))
    if status["is_initial"]:
        raise ApiError(409, "Le status initial ne peut pas être supprimé : désignez-en un autre d'abord.")
    ctx.conn.execute("DELETE FROM agile_statuses WHERE id = ?", (status["id"],))
    c.log(ctx, "agile_status_delete", "agile_status", status["id"], {"name": status["name"]})
    return {"ok": True}


# --------------------------------------------------------------------------
# Transitions
# --------------------------------------------------------------------------
def api_create_transition(ctx):
    project_id, _ = c.access(ctx, "admin")
    body = ctx.body
    wf = _workflow(ctx, project_id, c.opt_int(body, "workflow_id") or 0)
    to_status = c.status_row(ctx.conn, c.opt_int(body, "to_status_id") or 0, project_id)
    from_id = c.opt_int(body, "from_status_id")
    if from_id is not None:
        from_status = c.status_row(ctx.conn, from_id, project_id)
        if from_status["workflow_id"] != wf["id"]:
            raise ApiError(400, "Le status de départ n'appartient pas à ce workflow.")
        if from_id == to_status["id"]:
            raise ApiError(400, "Départ et arrivée identiques.")
    if to_status["workflow_id"] != wf["id"]:
        raise ApiError(400, "Le status d'arrivée n'appartient pas à ce workflow.")
    name = validate.text(body, "name", 60, required=False) or to_status["name"]
    min_role = body.get("min_role") or "editor"
    if min_role not in ("editor", "admin"):
        raise ApiError(400, "Rôle minimal invalide.")
    tid = ctx.conn.execute("INSERT INTO agile_transitions (workflow_id, from_status_id, to_status_id, "
                           "name, min_role) VALUES (?, ?, ?, ?, ?)",
                           (wf["id"], from_id, to_status["id"], name, min_role)).lastrowid
    c.log(ctx, "agile_transition_create", "agile_transition", tid, {"name": name})
    return {"id": tid}


def api_delete_transition(ctx):
    project_id, _ = c.access(ctx, "admin")
    tid = validate.int_param(ctx.params, "tid")
    row = ctx.conn.execute("SELECT t.* FROM agile_transitions t JOIN agile_workflows w "
                           "ON w.id = t.workflow_id WHERE t.id = ? AND w.project_id = ?",
                           (tid, project_id)).fetchone()
    if row is None:
        raise ApiError(404, "Transition introuvable.")
    ctx.conn.execute("DELETE FROM agile_transitions WHERE id = ?", (tid,))
    c.log(ctx, "agile_transition_delete", "agile_transition", tid, {"name": row["name"]})
    return {"ok": True}


# --------------------------------------------------------------------------
# Issue types and labels
# --------------------------------------------------------------------------
def api_create_type(ctx):
    project_id, _ = c.access(ctx, "admin")
    body = ctx.body
    name = validate.text(body, "name", 40)
    icon = body.get("icon_key") or "task"
    if icon not in c.ICON_KEYS:
        raise ApiError(400, "Icône invalide.")
    wf = _workflow(ctx, project_id, c.opt_int(body, "workflow_id") or 0)
    position = ctx.conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM agile_issue_types "
                                "WHERE project_id = ?", (project_id,)).fetchone()[0]
    is_subtask = validate.boolean(body, "is_subtask", False)
    is_requirement = validate.boolean(body, "is_requirement", False)
    if is_subtask and is_requirement:
        raise ApiError(400, "Un type ne peut pas être à la fois sous-ticket et requirement.")
    try:
        tid = ctx.conn.execute(
            "INSERT INTO agile_issue_types (project_id, name, icon_key, workflow_id, is_subtask, "
            "is_requirement, position) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, name, icon, wf["id"], int(is_subtask), int(is_requirement),
             position)).lastrowid
    except db.sqlite3.IntegrityError:
        raise ApiError(409, "Un type porte déjà ce nom.")
    c.log(ctx, "agile_type_create", "agile_issue_type", tid, {"name": name})
    return {"id": tid}


def api_update_type(ctx):
    project_id, _ = c.access(ctx, "admin")
    itype = c.owned(ctx.conn, "agile_issue_types", validate.int_param(ctx.params, "tid"),
                    project_id, "Type")
    body = ctx.body
    name = validate.text(body, "name", 40) if "name" in body else itype["name"]
    icon = body.get("icon_key", itype["icon_key"])
    if icon not in c.ICON_KEYS:
        raise ApiError(400, "Icône invalide.")
    wf_id = itype["workflow_id"]
    if "workflow_id" in body:
        wf_id = _workflow(ctx, project_id, c.opt_int(body, "workflow_id") or 0)["id"]
        used = ctx.conn.execute("SELECT COUNT(*) FROM agile_issues WHERE type_id = ?",
                                (itype["id"],)).fetchone()[0]
        if used and wf_id != itype["workflow_id"]:
            raise ApiError(409, "Des tickets utilisent ce type : changement de workflow impossible en V1.")
    is_requirement = (validate.boolean(body, "is_requirement", bool(itype["is_requirement"])))
    if is_requirement and itype["is_subtask"]:
        raise ApiError(400, "Un sous-ticket ne peut pas être marqué requirement.")
    try:
        ctx.conn.execute("UPDATE agile_issue_types SET name = ?, icon_key = ?, workflow_id = ?, "
                         "is_requirement = ? WHERE id = ?",
                         (name, icon, wf_id, int(is_requirement), itype["id"]))
    except db.sqlite3.IntegrityError:
        raise ApiError(409, "Un type porte déjà ce nom.")
    c.log(ctx, "agile_type_update", "agile_issue_type", itype["id"], {"name": name})
    return {"ok": True}


def api_update_label(ctx):
    project_id, _ = c.access(ctx, "admin")
    label = c.owned(ctx.conn, "agile_labels", validate.int_param(ctx.params, "lid"),
                    project_id, "Label")
    name = validate.text(ctx.body, "name", 40) if "name" in ctx.body else label["name"]
    if not c.LABEL_RE.match(name):
        raise ApiError(400, "Label invalide : sans espace, 40 caractères au maximum.")
    color = ctx.body.get("color_key", label["color_key"])
    if color not in ("neutral", "blue", "green", "amber", "red", "violet"):
        raise ApiError(400, "Couleur invalide.")
    try:
        ctx.conn.execute("UPDATE agile_labels SET name = ?, color_key = ? WHERE id = ?",
                         (name, color, label["id"]))
    except db.sqlite3.IntegrityError:
        raise ApiError(409, "Un label porte déjà ce nom.")
    c.log(ctx, "agile_label_update", "agile_label", label["id"], {"name": name})
    return {"ok": True}


def api_delete_label(ctx):
    project_id, _ = c.access(ctx, "admin")
    label = c.owned(ctx.conn, "agile_labels", validate.int_param(ctx.params, "lid"),
                    project_id, "Label")
    ctx.conn.execute("DELETE FROM agile_labels WHERE id = ?", (label["id"],))
    c.log(ctx, "agile_label_delete", "agile_label", label["id"], {"name": label["name"]})
    return {"ok": True}
