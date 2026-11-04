"""Dynamite page comments (D-B-002): threaded, shown under a saved page.

Same model as Agile ticket comments (one level of `parent_comment_id`,
rendered as a tree). Plain text only, rendered with textContent. Each
comment records the page version it was written against, so a reviewer
can tell a remark about v3 from one about v5.

Who may comment: any project member, readers included -- commenting is
how a reviewer takes part in a page without being allowed to change it.
Only the author or a project admin deletes a comment; replies go with it.
"""
from core import audit, db, permissions, validate
from core.errors import ApiError

from . import pages

MAX_LENGTH = 10000
COMMENT_ROLE = "reader"


def _context(ctx, role):
    project_id = pages._pid(ctx)
    actual = permissions.require_project_role(ctx.conn, ctx.user, project_id, role)
    page = pages._page(ctx.conn, project_id, validate.int_param(ctx.params, "page"))
    return project_id, actual, page


def _log(ctx, action, object_id, details):
    audit.log_action(ctx.conn, ctx.user["id"], action, "dynamite_comment", object_id, details, ctx.ip)


def api_list(ctx):
    _, role, page = _context(ctx, "reader")
    comments = db.rows(ctx.conn.execute(
        "SELECT c.id, c.parent_comment_id, c.body, c.page_version, c.created_at, c.author_id, "
        "u.display_name AS author_name FROM dynamite_comments c "
        "LEFT JOIN users u ON u.id = c.author_id WHERE c.page_id = ? ORDER BY c.id",
        (page["id"],)).fetchall())
    return {"comments": comments, "role": role, "current_version": page["current_version"]}


def api_add(ctx):
    _, _, page = _context(ctx, COMMENT_ROLE)
    conn = ctx.conn
    body = validate.text(ctx.body, "body", MAX_LENGTH * 2, required=False)
    if not body:
        raise ApiError(400, "Commentaire vide. Correctif : écrivez votre remarque avant d'envoyer.")
    if len(body) > MAX_LENGTH:
        raise ApiError(400, "Commentaire de {} caractères. Correctif : {} au maximum, ou découpez-le "
                            "en plusieurs réponses.".format(len(body), MAX_LENGTH))
    parent_id = ctx.body.get("parent_comment_id")
    if parent_id not in (None, ""):
        try:
            parent_id = int(parent_id)
        except (TypeError, ValueError):
            raise ApiError(400, "Commentaire parent invalide.")
        if not conn.execute("SELECT 1 FROM dynamite_comments WHERE id = ? AND page_id = ?",
                            (parent_id, page["id"])).fetchone():
            raise ApiError(404, "Le commentaire auquel vous répondez n'existe plus. Correctif : "
                                "rechargez la page.")
    else:
        parent_id = None
    cid = conn.execute(
        "INSERT INTO dynamite_comments (page_id, parent_comment_id, author_id, page_version, body, "
        "created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (page["id"], parent_id, ctx.user["id"], page["current_version"], body, db.utc_now())).lastrowid
    _log(ctx, "dynamite_comment_add", cid, {"page": page["id"], "reply_to": parent_id})
    from core import mentions  # D-A-046
    key = conn.execute("SELECT key FROM projects WHERE id = ?", (page["project_id"],)).fetchone()["key"]
    sent = mentions.notify(conn, ctx.user, body, "page_comment", "#/dynamite/{}/page/{}".format(key, page["id"]),
                           page["title"], page["project_id"], "dynamite_comment:{}".format(cid))
    return {"id": cid, "mentions_notice": sent["notice"]}


def api_delete(ctx):
    _, role, page = _context(ctx, "reader")
    cid = validate.int_param(ctx.params, "cid")
    comment = ctx.conn.execute("SELECT * FROM dynamite_comments WHERE id = ? AND page_id = ?",
                               (cid, page["id"])).fetchone()
    if comment is None:
        raise ApiError(404, "Commentaire introuvable (déjà supprimé ?).")
    if comment["author_id"] != ctx.user["id"] and role != "admin":
        raise ApiError(403, "Seul l'auteur ou un administrateur du projet peut supprimer ce commentaire.")
    ctx.conn.execute("DELETE FROM dynamite_comments WHERE id = ?", (cid,))
    _log(ctx, "dynamite_comment_delete", cid, {"page": page["id"]})
    return {"ok": True}
