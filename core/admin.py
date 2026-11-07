"""Administration API: users, projects, memberships and audit log.

Every route here is declared with access "admin", so the router has already
rejected non-administrators before these functions run.
"""
import re

from . import audit, auth, db, mail, prefs, validate
from .errors import ApiError
from .permissions import VALID_ROLES

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,31}$")
PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")
USER_COLUMNS = ("id, username, display_name, is_admin, is_active, must_change_password, created_at, "
                "title, expertise, route_when, study_profile, email")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _get_user(conn, user_id):
    row = conn.execute("SELECT " + USER_COLUMNS + " FROM users WHERE id = ?",
                       (user_id,)).fetchone()
    if row is None:
        raise ApiError(404, "Utilisateur introuvable.")
    return row


def _get_project(conn, project_id):
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise ApiError(404, "Projet introuvable.")
    return row


def _other_active_admins(conn, user_id):
    return conn.execute(
        "SELECT COUNT(*) FROM users WHERE is_admin = 1 AND is_active = 1 AND id <> ?",
        (user_id,)).fetchone()[0]


def _update(conn, table, row_id, changes):
    """UPDATE with column names taken only from our own whitelisted keys."""
    assignments = ", ".join("{} = ?".format(column) for column in changes)
    conn.execute("UPDATE " + table + " SET " + assignments + " WHERE id = ?",
                 list(changes.values()) + [row_id])


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------
def list_users(ctx):
    result = ctx.conn.execute("SELECT " + USER_COLUMNS + " FROM users ORDER BY username")
    return {"users": db.rows(result.fetchall())}


def create_user(ctx):
    username = validate.text(ctx.body, "username", 32).lower()
    if not USERNAME_RE.match(username):
        raise ApiError(400, "Identifiant invalide : 2 à 32 caractères parmi minuscules, "
                            "chiffres, point, tiret et soulignement.")
    display_name = validate.text(ctx.body, "display_name", 80)
    is_admin = validate.boolean(ctx.body, "is_admin", default=False)
    profile = validate.text(ctx.body, "study_profile", 80, required=False)  # 0.60.01
    email = mail.clean_email(ctx.body.get("email"))  # 0.60.73 (D-O-079)
    if mail.email_taken(ctx.conn, email, 0):
        raise ApiError(409, "Ce courriel est déjà celui d'un autre compte.")
    if ctx.conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        raise ApiError(409, "Cet identifiant existe déjà.")

    temp = auth.generate_temp_password()
    cursor = ctx.conn.execute(
        "INSERT INTO users (username, display_name, password_hash, is_admin, is_active, "
        "must_change_password, created_at, study_profile, email) VALUES (?, ?, ?, ?, 1, 1, ?, ?, ?)",
        (username, display_name, auth.hash_password(temp), int(is_admin), db.utc_now(), profile, email))
    prefs.ensure_initials(ctx.conn, cursor.lastrowid)  # 0.60.19 (D-O-030)
    audit.log_action(ctx.conn, ctx.user["id"], "user_created", "user", cursor.lastrowid,
                     {"username": username, "is_admin": is_admin}, ctx.ip)
    return {"user": dict(_get_user(ctx.conn, cursor.lastrowid)), "temp_password": temp}


def update_user(ctx):
    user_id = validate.int_param(ctx.params, "user_id")
    target = _get_user(ctx.conn, user_id)
    is_self = user_id == ctx.user["id"]

    changes = {}
    if "display_name" in ctx.body:
        changes["display_name"] = validate.text(ctx.body, "display_name", 80)
    for field, limit in (("title", 120), ("expertise", 1000), ("route_when", 1000),  # D-B-016
                         ("study_profile", 80)):  # 0.60.01: « Profil d'études »
        if field in ctx.body:
            changes[field] = validate.text(ctx.body, field, limit, required=False)
    if "email" in ctx.body:  # 0.60.73 (D-O-079): the address of « Mot de passe oublié ? »
        changes["email"] = mail.clean_email(ctx.body.get("email"))
        if mail.email_taken(ctx.conn, changes["email"], user_id):
            raise ApiError(409, "Ce courriel est déjà celui d'un autre compte.")
    for flag in ("is_admin", "is_active"):
        if flag in ctx.body:
            value = validate.boolean(ctx.body, flag)
            if is_self and not value:
                raise ApiError(400, "Impossible de retirer ce droit à votre propre compte.")
            changes[flag] = int(value)
    if not changes:
        raise ApiError(400, "Aucune modification demandée.")

    loses_admin = (target["is_admin"] and target["is_active"]
                   and (changes.get("is_admin", 1) == 0 or changes.get("is_active", 1) == 0))
    if loses_admin and _other_active_admins(ctx.conn, user_id) == 0:
        raise ApiError(400, "Il doit rester au moins un administrateur actif.")

    _update(ctx.conn, "users", user_id, changes)
    if changes.get("is_active") == 0:
        auth.delete_user_sessions(ctx.conn, user_id)
    audit.log_action(ctx.conn, ctx.user["id"], "user_updated", "user", user_id, changes, ctx.ip)
    return {"user": dict(_get_user(ctx.conn, user_id))}


def reset_user_password(ctx):
    user_id = validate.int_param(ctx.params, "user_id")
    _get_user(ctx.conn, user_id)
    if user_id == ctx.user["id"]:
        raise ApiError(400, "Pour votre propre compte, utilisez « Changer mon mot de passe ».")
    temp = auth.set_temp_password(ctx.conn, user_id)
    audit.log_action(ctx.conn, ctx.user["id"], "password_reset", "user", user_id, None, ctx.ip)
    return {"temp_password": temp}


# --------------------------------------------------------------------------
# Projects
# --------------------------------------------------------------------------
def list_projects(ctx):
    result = ctx.conn.execute(
        "SELECT p.id, p.key, p.name, p.description, p.is_archived, p.created_at, "
        "(SELECT COUNT(*) FROM memberships m WHERE m.project_id = p.id) AS member_count "
        "FROM projects p ORDER BY p.key")
    return {"projects": db.rows(result.fetchall())}


def create_project(ctx):
    key = validate.text(ctx.body, "key", 10).upper()
    name = validate.text(ctx.body, "name", 100)
    description = validate.text(ctx.body, "description", 500, required=False)
    provision = validate.boolean(ctx.body, "provision", True)
    return {"project": create_project_record(ctx, key, name, description, provision)}


def create_project_record(ctx, key, name, description="", provision=True):
    """Insert a project and let every module prepare it (core lot v0.5).
    Also used at start-up (core lot v0.7, e.g. the TESTING Space)."""
    if not PROJECT_KEY_RE.match(key):
        raise ApiError(400, "Clé invalide : 2 à 10 lettres majuscules ou chiffres, "
                            "en commençant par une lettre.")
    if ctx.conn.execute("SELECT 1 FROM projects WHERE key = ?", (key,)).fetchone():
        raise ApiError(409, "Cette clé de Space existe déjà.")
    if ctx.conn.execute("SELECT 1 FROM retired_project_keys WHERE key = ?", (key,)).fetchone():
        raise ApiError(409, "La clé {} a appartenu à un Space supprimé : elle n'est jamais réattribuée, pour que ses "
                            "tickets ({}-1, {}-2…) restent uniques. Correctif : choisissez une autre clé.".format(key, key, key))

    cursor = ctx.conn.execute(
        "INSERT INTO projects (key, name, description, created_at) VALUES (?, ?, ?, ?)",
        (key, name, description, db.utc_now()))
    audit.log_action(ctx.conn, ctx.user["id"], "project_created", "project", cursor.lastrowid,
                     {"key": key, "name": name}, ctx.ip)
    # Core lot v0.5 (D-B-012): every module prepares the project in the same
    # transaction -- a failing hook cancels the creation. "provision": false
    # (API only) keeps a bare project, used by tests of manual activation.
    if provision:
        from . import modules  # local import: modules imports the business packages
        for _key, hook in modules.project_hooks():
            hook(ctx, cursor.lastrowid)
    return dict(_get_project(ctx.conn, cursor.lastrowid))


def update_project(ctx):
    project_id = validate.int_param(ctx.params, "project_id")
    _get_project(ctx.conn, project_id)
    changes = {}
    if "name" in ctx.body:
        changes["name"] = validate.text(ctx.body, "name", 100)
    if "description" in ctx.body:
        changes["description"] = validate.text(ctx.body, "description", 500, required=False)
    if "is_archived" in ctx.body:
        changes["is_archived"] = int(validate.boolean(ctx.body, "is_archived"))
    if not changes:
        raise ApiError(400, "Aucune modification demandée.")
    _update(ctx.conn, "projects", project_id, changes)
    audit.log_action(ctx.conn, ctx.user["id"], "project_updated", "project", project_id,
                     changes, ctx.ip)
    return {"project": dict(_get_project(ctx.conn, project_id))}


def list_members(ctx):
    project_id = validate.int_param(ctx.params, "project_id")
    _get_project(ctx.conn, project_id)
    result = ctx.conn.execute(
        "SELECT u.id, u.username, u.display_name, u.is_active, m.role "
        "FROM memberships m JOIN users u ON u.id = m.user_id "
        "WHERE m.project_id = ? ORDER BY u.username", (project_id,))
    return {"members": db.rows(result.fetchall())}


def set_member(ctx):
    project_id = validate.int_param(ctx.params, "project_id")
    user_id = validate.int_param(ctx.params, "user_id")
    _get_project(ctx.conn, project_id)
    _get_user(ctx.conn, user_id)
    role = validate.choice(ctx.body, "role", VALID_ROLES)
    ctx.conn.execute(
        "INSERT OR REPLACE INTO memberships (user_id, project_id, role) VALUES (?, ?, ?)",
        (user_id, project_id, role))
    audit.log_action(ctx.conn, ctx.user["id"], "member_set", "project", project_id,
                     {"user_id": user_id, "role": role}, ctx.ip)
    return {"ok": True}


def remove_member(ctx):
    project_id = validate.int_param(ctx.params, "project_id")
    user_id = validate.int_param(ctx.params, "user_id")
    cursor = ctx.conn.execute(
        "DELETE FROM memberships WHERE project_id = ? AND user_id = ?", (project_id, user_id))
    if cursor.rowcount == 0:
        raise ApiError(404, "Cet utilisateur n'est pas membre du projet.")
    audit.log_action(ctx.conn, ctx.user["id"], "member_removed", "project", project_id,
                     {"user_id": user_id}, ctx.ip)
    return {"ok": True}


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------
def audit_log(ctx):
    try:
        limit = int(ctx.query.get("limit", 200))
    except ValueError:
        raise ApiError(400, "Paramètre invalide : limit.")
    return {"entries": audit.recent(ctx.conn, limit)}


USER_ID = r"(?P<user_id>\d+)"
PROJECT_ID = r"(?P<project_id>\d+)"

ROUTES = [
    ("GET", r"/api/admin/users", list_users, "admin"),
    ("POST", r"/api/admin/users", create_user, "admin"),
    ("PATCH", r"/api/admin/users/" + USER_ID, update_user, "admin"),
    ("POST", r"/api/admin/users/" + USER_ID + r"/reset-password", reset_user_password, "admin"),
    ("GET", r"/api/admin/projects", list_projects, "admin"),
    ("POST", r"/api/admin/projects", create_project, "admin"),
    ("PATCH", r"/api/admin/projects/" + PROJECT_ID, update_project, "admin"),
    ("GET", r"/api/admin/projects/" + PROJECT_ID + r"/members", list_members, "admin"),
    ("PUT", r"/api/admin/projects/" + PROJECT_ID + r"/members/" + USER_ID, set_member, "admin"),
    ("DELETE", r"/api/admin/projects/" + PROJECT_ID + r"/members/" + USER_ID,
     remove_member, "admin"),
    ("GET", r"/api/admin/audit", audit_log, "admin"),
]
