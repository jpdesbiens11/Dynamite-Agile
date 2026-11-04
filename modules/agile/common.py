"""Helpers shared by every Agile handler: access checks, lookups, history."""
import re

from core import audit, db, permissions, validate
from core.errors import ApiError

PRIORITIES = ("blocker", "high", "medium", "low", "trivial")
CATEGORIES = ("todo", "in_progress", "done")
LINK_TYPES = ("blocks", "relates", "duplicates", "implements", "resolves")
ICON_KEYS = ("epic", "story", "task", "bug", "subtask", "requirement", "ecn", "pr")
LABEL_RE = re.compile(r"^[\w.\-]{1,40}$", re.UNICODE)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_real_date(value):
    """Shape AND calendar: '2026-13-32' has the right shape but no such day."""
    import datetime
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def pid(ctx):
    return validate.int_param(ctx.params, "pid")


def access(ctx, minimum="reader", need_enabled=True):
    """Check the caller's role on the project; return (project_id, role)."""
    project_id = pid(ctx)
    role = permissions.require_project_role(ctx.conn, ctx.user, project_id, minimum)
    if need_enabled and not is_enabled(ctx.conn, project_id):
        raise ApiError(409, "Agile n'est pas activé sur ce projet.")
    return project_id, role


def is_enabled(conn, project_id):
    return conn.execute("SELECT 1 FROM agile_settings WHERE project_id = ?",
                        (project_id,)).fetchone() is not None


def log(ctx, action, object_type, object_id, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, object_type, object_id, details, ctx.ip)


def project_key(conn, project_id):
    return conn.execute("SELECT key FROM projects WHERE id = ?", (project_id,)).fetchone()["key"]


def get_issue(conn, project_id, number):
    row = conn.execute("SELECT * FROM agile_issues WHERE project_id = ? AND number = ?",
                       (project_id, number)).fetchone()
    if row is None:
        raise ApiError(404, "Ticket introuvable.")
    return row


KEY_RE = re.compile(r"^([A-Z][A-Z0-9]{1,9})-(\d+)$")


def find_by_key(conn, user, key):
    """Resolve a full ticket key ('EQP-12') across projects, checking the
    caller has at least reader access on the target project. Used for
    cross-project links (a work ticket that implements a requirement)."""
    match = KEY_RE.match((key or "").strip().upper())
    if not match:
        raise ApiError(400, "Key de ticket invalide (attendu : PROJET-numéro).")
    project = conn.execute("SELECT id FROM projects WHERE key = ? AND is_archived = 0",
                           (match.group(1),)).fetchone()
    if project is None:
        raise ApiError(404, "Projet introuvable pour la clé {}.".format(key))
    permissions.require_project_role(conn, user, project["id"], "reader")
    return get_issue(conn, project["id"], int(match.group(2)))


def issue_number(ctx):
    return validate.int_param(ctx.params, "num")


def owned(conn, table, row_id, project_id, label):
    """Fetch a row of a top-level table and check it belongs to the project."""
    row = conn.execute("SELECT * FROM {} WHERE id = ? AND project_id = ?".format(table),
                       (row_id, project_id)).fetchone()
    if row is None:
        raise ApiError(400, "{} introuvable dans ce projet.".format(label))
    return row


def status_row(conn, status_id, project_id):
    row = conn.execute(
        "SELECT s.* FROM agile_statuses s JOIN agile_workflows w ON w.id = s.workflow_id "
        "WHERE s.id = ? AND w.project_id = ?", (status_id, project_id)).fetchone()
    if row is None:
        raise ApiError(400, "Status introuvable dans ce projet.")
    return row


def members(conn, project_id):
    """Active users who can see the project (members and administrators)."""
    return db.rows(conn.execute(
        "SELECT u.id, u.display_name, u.username, COALESCE(m.role, 'admin') AS role "
        "FROM users u LEFT JOIN memberships m ON m.user_id = u.id AND m.project_id = ? "
        "WHERE u.is_active = 1 AND (m.user_id IS NOT NULL OR u.is_admin = 1) "
        "ORDER BY u.display_name", (project_id,)).fetchall())


def check_member(conn, project_id, user_id):
    if user_id is None:
        return None
    if not any(m["id"] == user_id for m in members(conn, project_id)):
        raise ApiError(400, "Cette personne n'a pas accès au projet.")
    return user_id


def opt_int(body, name):
    """Optional integer field: absent/None/'' -> None."""
    value = body.get(name)
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ApiError(400, "Champ invalide : {}.".format(name))
    try:
        return int(value)
    except ValueError:
        raise ApiError(400, "Champ invalide : {}.".format(name))


def opt_date(body, name):
    value = body.get(name)
    if value in (None, ""):
        return None
    if not is_real_date(value):
        raise ApiError(400, "Date « {} » invalide pour {}. Correctif : une date réelle au format "
                            "aaaa-mm-jj.".format(value, name))
    return value


def opt_points(body, name="story_points"):
    value = body.get(name)
    if value in (None, ""):
        return None
    try:
        points = float(value)
    except (TypeError, ValueError):
        raise ApiError(400, "Points invalides.")
    if not 0 <= points <= 1000:
        raise ApiError(400, "Points invalides (0 à 1000).")
    return points


def can_edit(ctx, role, issue):
    """D-B-017: a ticket is edited by its assignee or an administrator only.
    Other editors may comment, and take an unassigned ticket."""
    return role == "admin" or (role == "editor" and issue["assignee_id"] == ctx.user["id"])


def can_take(ctx, role, issue):
    return role == "editor" and issue["assignee_id"] is None


def require_edit(ctx, role, issue):
    if not can_edit(ctx, role, issue):
        raise ApiError(403, "Seul le responsable du ticket ou un administrateur peut le modifier"
                       + (" : prenez d'abord le ticket." if can_take(ctx, role, issue) else "."))


def add_history(ctx, issue_id, field, old, new):
    ctx.conn.execute(
        "INSERT INTO agile_history (issue_id, user_id, ts, field, old_value, new_value) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (issue_id, ctx.user["id"], db.utc_now(), field,
         None if old is None else str(old), None if new is None else str(new)))


# --------------------------------------------------------------------------
# Activation: default types and workflow (hypothesis H9)
# --------------------------------------------------------------------------
DEFAULT_STATUSES = [("To Do", "todo", 1), ("In Progress", "in_progress", 0),
                    ("In Review", "in_progress", 0), ("Done", "done", 0)]
DEFAULT_TRANSITIONS = [  # (from, to, name); from None = any status
    ("To Do", "In Progress", "Start"),
    ("In Progress", "In Review", "Send to Review"),
    ("In Review", "In Progress", "Back to In Progress"),
    ("In Review", "Done", "Done"),
    ("In Progress", "Done", "Done"),
    (None, "To Do", "Back to To Do"),
]
DEFAULT_TYPES = [("Epic", "epic", 0), ("Story", "story", 0), ("Task", "task", 0),
                 ("Bug", "bug", 0), ("Sub-task", "subtask", 1)]


def api_init(ctx):
    project_id, _ = access(ctx, "admin", need_enabled=False)
    if is_enabled(ctx.conn, project_id):
        raise ApiError(409, "Agile est déjà activé sur ce projet.")
    return enable_project(ctx, project_id)


def enable_project(ctx, project_id):
    """Default workflow and types; also run on project creation (D-B-012)."""
    conn = ctx.conn
    conn.execute("INSERT INTO agile_settings (project_id, enabled_at, enabled_by) VALUES (?, ?, ?)",
                 (project_id, db.utc_now(), ctx.user["id"]))
    wf = conn.execute("INSERT INTO agile_workflows (project_id, name, is_default) VALUES (?, ?, 1)",
                      (project_id, "Standard Workflow")).lastrowid
    ids = {}
    for pos, (name, cat, initial) in enumerate(DEFAULT_STATUSES):
        ids[name] = conn.execute(
            "INSERT INTO agile_statuses (workflow_id, name, category, position, is_initial) "
            "VALUES (?, ?, ?, ?, ?)", (wf, name, cat, pos, initial)).lastrowid
    for src, dst, name in DEFAULT_TRANSITIONS:
        conn.execute("INSERT INTO agile_transitions (workflow_id, from_status_id, to_status_id, name) "
                     "VALUES (?, ?, ?, ?)", (wf, ids[src] if src else None, ids[dst], name))
    for pos, (name, icon, sub) in enumerate(DEFAULT_TYPES):
        conn.execute("INSERT INTO agile_issue_types (project_id, name, icon_key, workflow_id, "
                     "is_subtask, position) VALUES (?, ?, ?, ?, ?, ?)",
                     (project_id, name, icon, wf, sub, pos))
    log(ctx, "agile_enable", "project", project_id)
    return {"ok": True}


def api_meta(ctx):
    """Everything the screens need to build forms, filters and the board."""
    project_id, role = access(ctx, "reader", need_enabled=False)
    conn = ctx.conn
    project = dict(conn.execute("SELECT id, key, name, description FROM projects WHERE id = ?",
                                (project_id,)).fetchone())
    if not is_enabled(conn, project_id):
        return {"project": project, "role": role, "enabled": False}
    q = lambda sql: db.rows(conn.execute(sql, (project_id,)).fetchall())  # noqa: E731
    return {
        "project": project, "role": role, "enabled": True,
        "workflows": q("SELECT * FROM agile_workflows WHERE project_id = ? ORDER BY is_default DESC, name"),
        "statuses": q("SELECT s.* FROM agile_statuses s JOIN agile_workflows w ON w.id = s.workflow_id "
                      "WHERE w.project_id = ? ORDER BY w.is_default DESC, s.workflow_id, s.position"),
        "transitions": q("SELECT t.* FROM agile_transitions t JOIN agile_workflows w ON w.id = t.workflow_id "
                         "WHERE w.project_id = ? ORDER BY t.id"),
        "types": q("SELECT * FROM agile_issue_types WHERE project_id = ? ORDER BY position, id"),
        "labels": q("SELECT l.*, (SELECT COUNT(*) FROM agile_issue_labels il WHERE il.label_id = l.id) "
                    "AS uses FROM agile_labels l WHERE project_id = ? ORDER BY name"),
        "sprints": q("SELECT * FROM agile_sprints WHERE project_id = ? ORDER BY "
                     "CASE state WHEN 'active' THEN 0 WHEN 'future' THEN 1 ELSE 2 END, id"),
        "versions": q("SELECT * FROM agile_versions WHERE project_id = ? ORDER BY is_released, name"),
        "members": members(conn, project_id),
        "priorities": list(PRIORITIES),
    }
