"""Move or copy Dynamite pages between spaces (D-B-049).

POST .../pages/<id>/transfer {mode: move | copy, target_pid, parent_id, with_children}
- move: the page and its whole branch change space (same ids, history and
  comments kept); in the same space it is a plain change of parent.
- copy: a new page (and, if asked, a copy of every sub-page) whose first
  version is the current content of the original, noted « Copie de … ».
Images live in the attachment store of a space: they are copied to the
target space and every version body is repointed, so a moved page still
shows its images and an old version can still be restored. Ticket blocks
keep their keys (they already work across spaces).
Rights: editor of the target space; editor of the source to move, reader
to copy. Journalled on both sides.
"""
import json
import shutil

from core import audit, db, permissions, uploads, validate
from core.errors import ApiError

from . import content
from .pages import _page, _parent

MODULE = "dynamite"


def _branch(conn, page_id):
    """The page and all its descendants, parents first."""
    out, todo = [], [page_id]
    while todo:
        pid = todo.pop(0)
        out.append(pid)
        todo += [r[0] for r in conn.execute("SELECT id FROM dynamite_pages WHERE parent_id = ? ORDER BY position, id", (pid,))]
    return out


def _remap(node, images):
    if isinstance(node, list):
        return any([_remap(n, images) for n in node])
    if not isinstance(node, dict):
        return False
    changed = False
    if node.get("type") == "image" and node.get("id") in images:
        node["id"] = images[node["id"]]
        changed = True
    for value in node.values():
        if isinstance(value, (list, dict)) and _remap(value, images):
            changed = True
    return changed


def _copy_images(ctx, source_pid, target_pid, bodies):
    """Attachment ids used by `bodies` in the source space -> ids in the target space."""
    ids = sorted({i for body in bodies for i in content.image_ids(body)})
    mapping = {}
    for image_id in ids:
        row = ctx.conn.execute("SELECT * FROM attachments WHERE id = ? AND project_id = ?", (image_id, source_pid)).fetchone()
        if row is None:
            continue
        found = ctx.conn.execute("SELECT id FROM attachments WHERE project_id = ? AND module = ? AND sha256 = ?",
                                 (target_pid, row["module"], row["sha256"])).fetchone()
        if found:
            mapping[image_id] = found["id"]
            continue
        src = uploads.file_path(ctx.data_dir, source_pid, row["sha256"], row["mime"])
        dst = uploads.file_path(ctx.data_dir, target_pid, row["sha256"], row["mime"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists() and not dst.exists():
            shutil.copyfile(src, dst)
        mapping[image_id] = ctx.conn.execute(
            "INSERT INTO attachments (project_id, module, sha256, mime, size, original_name, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (target_pid, row["module"], row["sha256"], row["mime"], row["size"],
                                                row["original_name"], ctx.user["id"], db.utc_now())).lastrowid
    return mapping


def _current(conn, page):
    row = conn.execute("SELECT body FROM dynamite_versions WHERE page_id = ? AND version = ?",
                       (page["id"], page["current_version"])).fetchone()
    return json.loads(row["body"]) if row else {"type": "doc", "content": []}


def _position(conn, target_pid, parent_id):
    return conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM dynamite_pages WHERE project_id = ? AND parent_id IS ?",
                        (target_pid, parent_id)).fetchone()[0]


def _move(ctx, page, source_pid, target_pid, parent_id):
    conn = ctx.conn
    branch = _branch(conn, page["id"])
    if target_pid == source_pid:
        conn.execute("UPDATE dynamite_pages SET parent_id = ?, position = ? WHERE id = ?",
                     (parent_id, _position(conn, target_pid, parent_id), page["id"]))
        return {"moved": len(branch), "page_id": page["id"]}
    versions = conn.execute("SELECT id, body FROM dynamite_versions WHERE page_id IN ({})".format(",".join("?" * len(branch))),
                            branch).fetchall()
    bodies = [json.loads(v["body"]) for v in versions]
    mapping = _copy_images(ctx, source_pid, target_pid, bodies)
    for v, body in zip(versions, bodies):
        if mapping and _remap(body, mapping):
            conn.execute("UPDATE dynamite_versions SET body = ? WHERE id = ?", (json.dumps(body, ensure_ascii=False), v["id"]))
    conn.execute("UPDATE dynamite_pages SET project_id = ?, lock_by = NULL, lock_until = NULL WHERE id IN ({})".format(
        ",".join("?" * len(branch))), [target_pid] + branch)
    conn.execute("UPDATE dynamite_pages SET parent_id = ?, position = ? WHERE id = ?",
                 (parent_id, _position(conn, target_pid, parent_id), page["id"]))
    return {"moved": len(branch), "page_id": page["id"], "images": len(mapping)}


def _copy(ctx, page, source_pid, target_pid, parent_id, with_children):
    conn = ctx.conn
    key = conn.execute("SELECT key FROM projects WHERE id = ?", (source_pid,)).fetchone()["key"]
    now = db.utc_now()
    made = []

    def copy_one(src, new_parent, top):
        body = _current(conn, src)
        if target_pid != source_pid:
            _remap(body, _copy_images(ctx, source_pid, target_pid, [body]))
        title = src["title"]
        if top and target_pid == source_pid and new_parent == src["parent_id"]:
            title = (title + " (copie)")[:200]
        text = content.validate(body)
        new_id = conn.execute(
            "INSERT INTO dynamite_pages (project_id, parent_id, title, position, current_version, created_by, created_at, "
            "updated_by, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)",
            (target_pid, new_parent, title, _position(conn, target_pid, new_parent), ctx.user["id"], now, ctx.user["id"], now)).lastrowid
        conn.execute("INSERT INTO dynamite_versions (page_id, version, title, body, author_id, created_at, note) "
                     "VALUES (?, 1, ?, ?, ?, ?, ?)", (new_id, title, text, ctx.user["id"], now,
                                                      "Copie de {} · {} (v{})".format(key, src["title"], src["current_version"])[:200]))
        made.append(new_id)
        if with_children:
            for child in conn.execute("SELECT * FROM dynamite_pages WHERE parent_id = ? ORDER BY position, id", (src["id"],)).fetchall():
                copy_one(child, new_id, False)
        return new_id

    first = copy_one(page, parent_id, True)
    return {"copied": len(made), "page_id": first}


def api_transfer(ctx):
    source_pid = validate.int_param(ctx.params, "pid")
    mode = ctx.body.get("mode")
    if mode not in ("move", "copy"):
        raise ApiError(400, "Action inconnue. Correctif : move (déplacer) ou copy (copier).")
    permissions.require_project_role(ctx.conn, ctx.user, source_pid, "editor" if mode == "move" else "reader")
    page = _page(ctx.conn, source_pid, validate.int_param(ctx.params, "page"))
    target_pid = int(ctx.body.get("target_pid") or source_pid)
    target = ctx.conn.execute("SELECT id, key FROM projects WHERE id = ? AND is_archived = 0", (target_pid,)).fetchone()
    if target is None:
        raise ApiError(404, "Space cible introuvable ou archivé.")
    permissions.require_project_role(ctx.conn, ctx.user, target_pid, "editor")
    parent_id = _parent(ctx.conn, target_pid, ctx.body.get("parent_id"), own_id=page["id"] if mode == "move" else None)
    if mode == "move":
        result = _move(ctx, page, source_pid, target_pid, parent_id)
    else:
        result = _copy(ctx, page, source_pid, target_pid, parent_id, validate.boolean(ctx.body, "with_children", False))
    details = dict(result, mode=mode, source=source_pid, target=target_pid)
    audit.log_action(ctx.conn, ctx.user["id"], "dynamite_page_" + mode, "dynamite_page", result["page_id"], details, ctx.ip)
    result["target_key"] = target["key"]
    return result
