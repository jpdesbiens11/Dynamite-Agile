"""Dynamite pages: one space per project, page tree, versions, edit lock,
and the live "Ticket Agile" block resolver (D-A-036).

Every save creates a version (dynamite_versions); a save based on an
older version than the current one is refused with the name of whoever
saved in between, so nobody silently overwrites a colleague (optimistic
lock). An edit lock (15 min, renewed while editing) warns a second editor
before they even start.
"""
import json

from core import audit, db, permissions, validate
from core.errors import ApiError

from . import content

LOCK_MINUTES = 15


def _pid(ctx):
    return validate.int_param(ctx.params, "pid")


def _log(ctx, action, object_id, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "dynamite_page", object_id, details, ctx.ip)


def _page(conn, project_id, page_id):
    row = conn.execute("SELECT * FROM dynamite_pages WHERE id = ? AND project_id = ?",
                       (page_id, project_id)).fetchone()
    if row is None:
        raise ApiError(404, "Page introuvable dans cet espace. Correctif : choisissez-la dans l'arbre "
                            "de gauche ; elle a peut-être été supprimée ou déplacée.")
    return row


def _parent(conn, project_id, value, own_id=None):
    if value in (None, "", 0):
        return None
    try:
        parent_id = int(value)
    except (TypeError, ValueError):
        raise ApiError(400, "Page parente invalide.")
    parent = _page(conn, project_id, parent_id)
    walk = parent
    while walk is not None:  # refuse a cycle: a page under its own descendant
        if own_id is not None and walk["id"] == own_id:
            raise ApiError(400, "Déplacement impossible : une page ne peut pas aller sous sa propre "
                                "sous-page. Correctif : choisissez un parent hors de cette branche.")
        walk = conn.execute("SELECT * FROM dynamite_pages WHERE id = ?", (walk["parent_id"],)).fetchone() \
            if walk["parent_id"] else None
    return parent["id"]


def _title(body):
    title = (body.get("title") or "").strip()
    if not title:
        raise ApiError(400, "Titre vide. Correctif : donnez un titre à la page.")
    if len(title) > 200:
        raise ApiError(400, "Titre de {} caractères. Correctif : 200 au maximum.".format(len(title)))
    return title


def _check_images(conn, project_id, body):
    from . import images  # local import: images imports this module
    images.check_page_images(conn, project_id, content.image_ids(body))


def _user_name(conn, user_id):
    row = conn.execute("SELECT display_name FROM users WHERE id = ?", (user_id,)).fetchone()
    return row["display_name"] if row else "un ancien compte"


# --------------------------------------------------------------------------
def api_tree(ctx):
    project_id = _pid(ctx)
    role = permissions.require_project_role(ctx.conn, ctx.user, project_id, "reader")
    pages = db.rows(ctx.conn.execute(
        "SELECT id, parent_id, title, position, updated_at FROM dynamite_pages WHERE project_id = ? "
        "ORDER BY position, title", (project_id,)).fetchall())
    project = ctx.conn.execute("SELECT key, name FROM projects WHERE id = ?", (project_id,)).fetchone()
    return {"pages": pages, "role": role, "project": dict(project)}


def api_create(ctx):
    project_id = _pid(ctx)
    permissions.require_project_role(ctx.conn, ctx.user, project_id, "editor")
    conn = ctx.conn
    title = _title(ctx.body)
    parent_id = _parent(conn, project_id, ctx.body.get("parent_id"))
    body = ctx.body.get("body") or {"type": "doc", "content": []}
    body_text = content.validate(body)
    _check_images(conn, project_id, body)
    position = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM dynamite_pages WHERE project_id = ? "
                            "AND parent_id IS ?", (project_id, parent_id)).fetchone()[0]
    now = db.utc_now()
    page_id = conn.execute(
        "INSERT INTO dynamite_pages (project_id, parent_id, title, position, current_version, created_by, "
        "created_at, updated_by, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)",
        (project_id, parent_id, title, position, ctx.user["id"], now, ctx.user["id"], now)).lastrowid
    conn.execute("INSERT INTO dynamite_versions (page_id, version, title, body, author_id, created_at, note) "
                 "VALUES (?, 1, ?, ?, ?, ?, 'Création')", (page_id, title, body_text, ctx.user["id"], now))
    _log(ctx, "dynamite_page_create", page_id, {"title": title})
    sent = _mentions(ctx, project_id, page_id, title, body_text, None)
    return {"id": page_id, "mentions_notice": sent}


def api_get(ctx):
    project_id = _pid(ctx)
    role = permissions.require_project_role(ctx.conn, ctx.user, project_id, "reader")
    conn = ctx.conn
    page = _page(conn, project_id, validate.int_param(ctx.params, "page"))
    version = conn.execute("SELECT * FROM dynamite_versions WHERE page_id = ? AND version = ?",
                           (page["id"], page["current_version"])).fetchone()
    crumbs, walk = [], page
    while walk["parent_id"]:
        walk = conn.execute("SELECT id, title, parent_id FROM dynamite_pages WHERE id = ?",
                            (walk["parent_id"],)).fetchone()
        crumbs.insert(0, {"id": walk["id"], "title": walk["title"]})
    children = db.rows(conn.execute("SELECT id, title FROM dynamite_pages WHERE parent_id = ? "
                                    "ORDER BY position, title", (page["id"],)).fetchall())
    lock = None
    if page["lock_by"] and page["lock_until"] and page["lock_until"] > db.utc_now() \
            and page["lock_by"] != ctx.user["id"]:
        lock = {"by": _user_name(conn, page["lock_by"]), "until": page["lock_until"]}
    return {"page": {"id": page["id"], "title": page["title"], "parent_id": page["parent_id"],
                     "version": page["current_version"], "updated_at": page["updated_at"],
                     "updated_by": _user_name(conn, page["updated_by"]),
                     "body": json.loads(version["body"])},
            "crumbs": crumbs, "children": children, "lock": lock, "role": role}


def api_save(ctx):
    project_id = _pid(ctx)
    permissions.require_project_role(ctx.conn, ctx.user, project_id, "editor")
    conn = ctx.conn
    page = _page(conn, project_id, validate.int_param(ctx.params, "page"))
    base = ctx.body.get("base_version")
    if base != page["current_version"]:
        raise ApiError(409, "{} a enregistré la version {} pendant que vous éditiez la version {}. "
                            "Correctif : copiez votre texte, rechargez la page, puis réappliquez vos "
                            "changements sur la dernière version.".format(
                                _user_name(conn, page["updated_by"]), page["current_version"], base))
    title = _title(ctx.body)
    body_text = content.validate(ctx.body.get("body"))
    _check_images(conn, project_id, ctx.body.get("body"))
    previous = conn.execute("SELECT body FROM dynamite_versions WHERE page_id = ? AND version = ?",
                            (page["id"], page["current_version"])).fetchone()
    note = (ctx.body.get("note") or "").strip()[:200]
    version = page["current_version"] + 1
    now = db.utc_now()
    conn.execute("INSERT INTO dynamite_versions (page_id, version, title, body, author_id, created_at, note) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?)", (page["id"], version, title, body_text, ctx.user["id"], now, note))
    conn.execute("UPDATE dynamite_pages SET title = ?, current_version = ?, updated_by = ?, updated_at = ?, "
                 "lock_by = NULL, lock_until = NULL WHERE id = ?",
                 (title, version, ctx.user["id"], now, page["id"]))
    _log(ctx, "dynamite_page_save", page["id"], {"version": version})
    sent = _mentions(ctx, project_id, page["id"], title, body_text, previous["body"] if previous else None)
    return {"version": version, "mentions_notice": sent}


def _mentions(ctx, project_id, page_id, title, body_text, previous_body):
    """D-A-046: « @username » in the page text -- only the mentions this version adds are notified."""
    from core import mentions
    key = ctx.conn.execute("SELECT key FROM projects WHERE id = ?", (project_id,)).fetchone()["key"]
    before = mentions.text_of_blocks(previous_body) if previous_body else None
    return mentions.notify(ctx.conn, ctx.user, mentions.text_of_blocks(body_text), "page",
                           "#/dynamite/{}/page/{}".format(key, page_id), title, project_id,
                           "dynamite_page:{}".format(page_id), previous_text=before if before is not None else None
                           )["notice"] if ctx.user else ""


def api_lock(ctx):
    """Take or renew the edit lock; refuse (with who) if someone else holds it."""
    project_id = _pid(ctx)
    permissions.require_project_role(ctx.conn, ctx.user, project_id, "editor")
    conn = ctx.conn
    page = _page(conn, project_id, validate.int_param(ctx.params, "page"))
    now = db.utc_now()
    if page["lock_by"] and page["lock_by"] != ctx.user["id"] and (page["lock_until"] or "") > now:
        raise ApiError(409, "{} édite cette page (verrou jusqu'à {} UTC). Correctif : attendez qu'il "
                            "enregistre, ou demandez-lui de fermer l'éditeur.".format(
                                _user_name(conn, page["lock_by"]), page["lock_until"][11:16]))
    until = conn.execute("SELECT strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now', ?)",
                         ("+{} minutes".format(LOCK_MINUTES),)).fetchone()[0]
    conn.execute("UPDATE dynamite_pages SET lock_by = ?, lock_until = ? WHERE id = ?",
                 (ctx.user["id"], until, page["id"]))
    return {"until": until}


def api_unlock(ctx):
    project_id = _pid(ctx)
    permissions.require_project_role(ctx.conn, ctx.user, project_id, "editor")
    ctx.conn.execute("UPDATE dynamite_pages SET lock_by = NULL, lock_until = NULL WHERE id = ? "
                     "AND project_id = ? AND lock_by = ?",
                     (validate.int_param(ctx.params, "page"), project_id, ctx.user["id"]))
    return {"ok": True}


def api_move(ctx):
    project_id = _pid(ctx)
    permissions.require_project_role(ctx.conn, ctx.user, project_id, "editor")
    conn = ctx.conn
    page = _page(conn, project_id, validate.int_param(ctx.params, "page"))
    parent_id = _parent(conn, project_id, ctx.body.get("parent_id"), own_id=page["id"])
    position = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM dynamite_pages WHERE project_id = ? "
                            "AND parent_id IS ?", (project_id, parent_id)).fetchone()[0]
    conn.execute("UPDATE dynamite_pages SET parent_id = ?, position = ? WHERE id = ?",
                 (parent_id, position, page["id"]))
    _log(ctx, "dynamite_page_move", page["id"], {"parent": parent_id})
    return {"ok": True}


def api_delete(ctx):
    project_id = _pid(ctx)
    permissions.require_project_role(ctx.conn, ctx.user, project_id, "admin")
    conn = ctx.conn
    page = _page(conn, project_id, validate.int_param(ctx.params, "page"))
    children = conn.execute("SELECT COUNT(*) FROM dynamite_pages WHERE parent_id = ?", (page["id"],)).fetchone()[0]
    if children:
        raise ApiError(409, "Cette page a {} sous-page(s). Correctif : déplacez ou supprimez-les "
                            "d'abord.".format(children))
    conn.execute("DELETE FROM dynamite_pages WHERE id = ?", (page["id"],))
    _log(ctx, "dynamite_page_delete", page["id"], {"title": page["title"]})
    return {"ok": True}


def api_versions(ctx):
    project_id = _pid(ctx)
    permissions.require_project_role(ctx.conn, ctx.user, project_id, "reader")
    page = _page(ctx.conn, project_id, validate.int_param(ctx.params, "page"))
    return {"versions": db.rows(ctx.conn.execute(
        "SELECT v.version, v.title, v.created_at, v.note, u.display_name AS author FROM dynamite_versions v "
        "LEFT JOIN users u ON u.id = v.author_id WHERE v.page_id = ? ORDER BY v.version DESC",
        (page["id"],)).fetchall()), "current": page["current_version"]}


def api_version(ctx):
    project_id = _pid(ctx)
    permissions.require_project_role(ctx.conn, ctx.user, project_id, "reader")
    page = _page(ctx.conn, project_id, validate.int_param(ctx.params, "page"))
    row = ctx.conn.execute("SELECT * FROM dynamite_versions WHERE page_id = ? AND version = ?",
                           (page["id"], validate.int_param(ctx.params, "ver"))).fetchone()
    if row is None:
        raise ApiError(404, "Version introuvable. Correctif : choisissez-la dans l'historique.")
    body = json.loads(row["body"])
    return {"version": row["version"], "title": row["title"], "body": body,
            "text": content.plain_text(body), "created_at": row["created_at"]}


def api_restore(ctx):
    """Restoring never deletes anything: it saves the old content as a new version."""
    project_id = _pid(ctx)
    permissions.require_project_role(ctx.conn, ctx.user, project_id, "editor")
    conn = ctx.conn
    page = _page(conn, project_id, validate.int_param(ctx.params, "page"))
    number = validate.int_param(ctx.params, "ver")
    old = conn.execute("SELECT * FROM dynamite_versions WHERE page_id = ? AND version = ?",
                       (page["id"], number)).fetchone()
    if old is None:
        raise ApiError(404, "Version introuvable.")
    version = page["current_version"] + 1
    now = db.utc_now()
    conn.execute("INSERT INTO dynamite_versions (page_id, version, title, body, author_id, created_at, note) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?)", (page["id"], version, old["title"], old["body"],
                                                  ctx.user["id"], now, "Restauration de la version {}".format(number)))
    conn.execute("UPDATE dynamite_pages SET title = ?, current_version = ?, updated_by = ?, updated_at = ? "
                 "WHERE id = ?", (old["title"], version, ctx.user["id"], now, page["id"]))
    _log(ctx, "dynamite_page_restore", page["id"], {"from": number, "version": version})
    return {"version": version}


# --------------------------------------------------------------------------
def api_ticket(ctx):
    """Live data for a "Ticket Agile" block. The same 404 answers a missing
    ticket and a ticket in a project the viewer cannot read, so a page never
    reveals what its reader is not allowed to see (D-A-036)."""
    key = (ctx.params.get("key") or "").upper()
    hidden = ApiError(404, "Ticket {} introuvable ou non accessible avec vos droits.".format(key))
    if not content.KEY_RE.match(key):
        raise ApiError(400, "Clé « {} » invalide. Correctif : format PROJET-numéro, ex. EQP-4.".format(key))
    prefix, number = key.rsplit("-", 1)
    project = ctx.conn.execute("SELECT id FROM projects WHERE key = ?", (prefix,)).fetchone()
    if project is None or permissions.project_role(ctx.conn, ctx.user, project["id"]) is None:
        raise hidden
    row = ctx.conn.execute(
        "SELECT i.number, i.title, i.priority, s.name AS status_name, s.category AS status_category, "
        "t.name AS type_name, t.icon_key, t.is_requirement, u.display_name AS assignee_name "
        "FROM agile_issues i JOIN agile_statuses s ON s.id = i.status_id "
        "JOIN agile_issue_types t ON t.id = i.type_id LEFT JOIN users u ON u.id = i.assignee_id "
        "WHERE i.project_id = ? AND i.number = ?", (project["id"], int(number))).fetchone()
    if row is None:
        raise hidden
    return dict(row, key=key, project_key=prefix)
