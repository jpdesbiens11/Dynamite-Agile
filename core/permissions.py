"""Project-level access rules: reader < editor < admin."""
from . import db
from .errors import ApiError

ROLE_LEVEL = {"reader": 1, "editor": 2, "admin": 3}
# "manager" = « Admin du projet » (core lot v0.10, D-B-027): an editor who also
# manages the members of this project. Modules see it as "editor"; only the
# member-management screens (core/members.py) look at the raw membership.
VALID_ROLES = ("reader", "editor", "manager")


def require_admin(user):
    if not user["is_admin"]:
        raise ApiError(403, "Réservé aux administrateurs.")


def project_role(conn, user, project_id):
    """Return 'admin', 'editor', 'reader' or None for this user and project."""
    if user["is_admin"]:
        return "admin"
    row = conn.execute(
        "SELECT m.role FROM memberships m JOIN projects p ON p.id = m.project_id "
        "WHERE m.user_id = ? AND m.project_id = ? AND p.is_archived = 0",
        (user["id"], project_id)).fetchone()
    if row is None:
        return None
    return "editor" if row["role"] == "manager" else row["role"]


def is_project_manager(conn, user, project_id):
    """Global administrator, or « Admin du projet » of this (active) project."""
    if user["is_admin"]:
        return True
    return conn.execute(
        "SELECT 1 FROM memberships m JOIN projects p ON p.id = m.project_id "
        "WHERE m.user_id = ? AND m.project_id = ? AND m.role = 'manager' AND p.is_archived = 0",
        (user["id"], project_id)).fetchone() is not None


def require_project_role(conn, user, project_id, minimum="reader"):
    """Raise unless the user has at least `minimum` on the project.

    A project the user cannot see answers 404, so its existence is not revealed.
    """
    role = project_role(conn, user, project_id)
    if role is None:
        raise ApiError(404, "Projet introuvable.")
    if ROLE_LEVEL[role] < ROLE_LEVEL[minimum]:
        raise ApiError(403, "Droits insuffisants sur ce projet.")
    return role


def visible_projects(conn, user):
    """Active projects the user can open, with their role."""
    if user["is_admin"]:
        result = conn.execute(
            "SELECT id, key, name, description, 'admin' AS role FROM projects "
            "WHERE is_archived = 0 ORDER BY key").fetchall()
    else:
        result = conn.execute(
            "SELECT p.id, p.key, p.name, p.description, "
            "CASE m.role WHEN 'manager' THEN 'editor' ELSE m.role END AS role, "
            "CASE m.role WHEN 'manager' THEN 1 ELSE 0 END AS is_manager FROM projects p "
            "JOIN memberships m ON m.project_id = p.id "
            "WHERE m.user_id = ? AND p.is_archived = 0 ORDER BY p.key",
            (user["id"],)).fetchall()
    return db.rows(result)
