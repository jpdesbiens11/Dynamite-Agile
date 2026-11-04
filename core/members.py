"""Rights per account and per project (core lot v0.10, D-B-027).

- Administrators: the full matrix accounts x projects (read / write /
  project admin), one cell at a time, from Administration → « Droits ».
- « Admin du projet » (membership role "manager"): manages the members of
  HIS project only -- add, change the right, remove -- nothing else (no
  account creation, no other project, no module administration).
Every change is journalled; a project always keeps at least one way to be
administered (global administrators), so no lock-out is possible.
"""
from . import audit, db, permissions, validate
from .errors import ApiError

ROLE_LABELS = {"reader": "Lecteur", "editor": "Éditeur", "manager": "Admin du projet"}


# The 0.1 table only accepted reader / editor: rebuilt once to accept
# « manager » (Admin du projet). Nothing references memberships.
MIGRATIONS = [
    (6, """
        CREATE TABLE memberships_v6 (
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            role       TEXT NOT NULL CHECK (role IN ('reader', 'editor', 'manager')),
            PRIMARY KEY (user_id, project_id)
        );
        INSERT INTO memberships_v6 (user_id, project_id, role) SELECT user_id, project_id, role FROM memberships;
        DROP TABLE memberships;
        ALTER TABLE memberships_v6 RENAME TO memberships;
        CREATE INDEX IF NOT EXISTS idx_memberships_project ON memberships(project_id);
    """),
]

def _project(conn, project_id):
    row = conn.execute("SELECT id, key, name, is_archived FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise ApiError(404, "Projet introuvable.")
    return dict(row)


def _require_manager(ctx, project_id):
    project = _project(ctx.conn, project_id)
    if not permissions.is_project_manager(ctx.conn, ctx.user, project_id):
        raise ApiError(403, "Réservé aux administrateurs de ce projet. Correctif : demandez à un administrateur "
                            "de vous nommer « Admin du projet ».")
    return project


def _set(ctx, project_id, user_id, role):
    user = ctx.conn.execute("SELECT id, is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        raise ApiError(404, "Compte introuvable.")
    if role is None:
        ctx.conn.execute("DELETE FROM memberships WHERE user_id = ? AND project_id = ?", (user_id, project_id))
        audit.log_action(ctx.conn, ctx.user["id"], "member_removed", "project", project_id, {"user_id": user_id}, ctx.ip)
        return
    if role not in permissions.VALID_ROLES:
        raise ApiError(400, "Droit « {} » inconnu. Correctif : reader, editor ou manager.".format(role))
    ctx.conn.execute("INSERT OR REPLACE INTO memberships (user_id, project_id, role) VALUES (?, ?, ?)",
                     (user_id, project_id, role))
    audit.log_action(ctx.conn, ctx.user["id"], "member_set", "project", project_id,
                     {"user_id": user_id, "role": role}, ctx.ip)


def _role_body(ctx):
    role = ctx.body.get("role")
    if role in (None, "", "none"):
        return None
    if role not in permissions.VALID_ROLES:
        raise ApiError(400, "Droit « {} » inconnu. Correctif : reader (lecteur), editor (éditeur), "
                            "manager (admin du projet) ou none.".format(role))
    return role


# --------------------------------------------------------------------------
# Project admins (and administrators): members of one project
# --------------------------------------------------------------------------
def api_managed(ctx):
    """Projects whose members the current user may manage (user menu)."""
    if ctx.user["is_admin"]:
        rows = ctx.conn.execute("SELECT id, key, name FROM projects WHERE is_archived = 0 ORDER BY key").fetchall()
    else:
        rows = ctx.conn.execute(
            "SELECT p.id, p.key, p.name FROM projects p JOIN memberships m ON m.project_id = p.id "
            "WHERE m.user_id = ? AND m.role = 'manager' AND p.is_archived = 0 ORDER BY p.key", (ctx.user["id"],)).fetchall()
    return {"projects": db.rows(rows)}


def api_members(ctx):
    project_id = validate.int_param(ctx.params, "pid")
    project = _require_manager(ctx, project_id)
    members = db.rows(ctx.conn.execute(
        "SELECT u.id, u.username, u.display_name, u.is_admin, m.role FROM memberships m JOIN users u ON u.id = m.user_id "
        "WHERE m.project_id = ? AND u.is_active = 1 ORDER BY u.display_name", (project_id,)).fetchall())
    for m in members:
        m["role_label"] = ROLE_LABELS.get(m["role"], m["role"])
    member_ids = {m["id"] for m in members}
    others = [u for u in db.rows(ctx.conn.execute(
        "SELECT id, username, display_name FROM users WHERE is_active = 1 ORDER BY display_name").fetchall())
        if u["id"] not in member_ids]
    return {"project": project, "members": members, "candidates": others, "roles": ROLE_LABELS,
            "is_admin": bool(ctx.user["is_admin"])}


def api_set_member(ctx):
    project_id = validate.int_param(ctx.params, "pid")
    _require_manager(ctx, project_id)
    user_id = validate.int_param(ctx.params, "uid")
    role = _role_body(ctx)
    if user_id == ctx.user["id"] and not ctx.user["is_admin"] and role != "manager":
        raise ApiError(400, "Vous ne pouvez pas retirer vos propres droits d'admin du projet. Correctif : demandez-le "
                            "à un autre admin du projet ou à un administrateur.")
    _set(ctx, project_id, user_id, role)
    return api_members(ctx)


# --------------------------------------------------------------------------
# Administrators: the matrix accounts x projects
# --------------------------------------------------------------------------
def api_matrix(ctx):
    users = db.rows(ctx.conn.execute(
        "SELECT id, username, display_name, is_admin, is_active FROM users ORDER BY is_active DESC, display_name").fetchall())
    projects = db.rows(ctx.conn.execute("SELECT id, key, name, is_archived FROM projects ORDER BY is_archived, key").fetchall())
    cells = {"{}:{}".format(r["user_id"], r["project_id"]): r["role"]
             for r in ctx.conn.execute("SELECT user_id, project_id, role FROM memberships")}
    from . import prefs
    for u in users:  # D-B-050: export right (Word / PDF of wiki pages), given per account
        u["can_export"] = bool(u["is_admin"]) or bool(prefs.get(ctx.conn, u["id"]).get("can_export"))
    return {"users": users, "projects": projects, "cells": cells, "roles": ROLE_LABELS}


def api_matrix_set(ctx):
    project_id = int(ctx.body.get("project_id") or 0)
    user_id = int(ctx.body.get("user_id") or 0)
    _project(ctx.conn, project_id)
    _set(ctx, project_id, user_id, _role_body(ctx))
    return {"ok": True}


# --------------------------------------------------------------------------
# New account from an existing profile (D-B-045): same project rights
# --------------------------------------------------------------------------
COPIED_PREFS = ("manager_id", "theme", "font", "font_size", "density", "landing", "my_items")


def api_duplicate_user(ctx):
    """Create an account (temporary password) with the project rights of an existing one --
    an intern or a new colleague on the same projects. The administrator flag is never copied."""
    from . import admin, prefs
    source_id = validate.int_param(ctx.params, "user_id")
    source = ctx.conn.execute("SELECT * FROM users WHERE id = ?", (source_id,)).fetchone()
    if source is None:
        raise ApiError(404, "Profil modèle introuvable.")
    original = ctx.body
    ctx.body = {"username": original.get("username"), "display_name": original.get("display_name"), "is_admin": False}
    try:
        created = admin.create_user(ctx)
    finally:
        ctx.body = original
    new_id = created["user"]["id"]
    rights = ctx.conn.execute("SELECT project_id, role FROM memberships WHERE user_id = ?", (source_id,)).fetchall()
    for r in rights:
        ctx.conn.execute("INSERT OR REPLACE INTO memberships (user_id, project_id, role) VALUES (?, ?, ?)",
                         (new_id, r["project_id"], r["role"]))
    model = prefs.get(ctx.conn, source_id)
    copied = {k: model[k] for k in COPIED_PREFS if model.get(k) not in (None, "")}
    if copied:
        prefs.update(ctx, new_id, copied)
    audit.log_action(ctx.conn, ctx.user["id"], "user_duplicated", "user", new_id,
                     {"from": source["username"], "projects": len(rights), "prefs": sorted(copied)}, ctx.ip)
    created["projects"] = len(rights)
    return created


P = r"/api/projects/(?P<pid>\d+)/members"

ROUTES = [
    ("GET", r"/api/me/managed-projects", api_managed, "user"),
    ("GET", P, api_members, "user"),
    ("PUT", P + r"/(?P<uid>\d+)", api_set_member, "user"),
    ("GET", r"/api/admin/rights", api_matrix, "admin"),
    ("POST", r"/api/admin/users/(?P<user_id>\d+)/duplicate", api_duplicate_user, "admin"),
    ("PUT", r"/api/admin/rights", api_matrix_set, "admin"),
]
