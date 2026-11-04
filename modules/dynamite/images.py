"""Dynamite images (D-B-004): pasted, dropped or chosen in the editor,
stored by the core attachment store (core/uploads.py, lot v0.4), shown by
the "image" block of a page body.

The image URL carries no project: GET /api/dynamite/image/<id> finds the
project from the attachment and checks the reader's role there. Like the
Ticket block (D-A-036), a missing image and an image of a space the
reader may not see get the same 404, so a page never reveals what its
reader has no right to see.
"""
from core import audit, permissions, uploads, validate
from core.errors import ApiError
from core.files import RawFile

from . import pages

MODULE = "dynamite"
MAX_IMAGE_MB = 10
NOT_FOUND = "Image introuvable ou non accessible."


@uploads.binary_body
def api_upload(ctx):
    project_id = pages._pid(ctx)
    permissions.require_project_role(ctx.conn, ctx.user, project_id, "editor")
    row = uploads.store_image(ctx, project_id, MODULE, MAX_IMAGE_MB * 1024 * 1024)
    audit.log_action(ctx.conn, ctx.user["id"], "dynamite_image_upload", "attachment", row["id"],
                     {"size": row["size"], "mime": row["mime"]}, ctx.ip)
    return {"id": row["id"], "mime": row["mime"], "size": row["size"], "name": row["original_name"]}


def api_get(ctx):
    image_id = validate.int_param(ctx.params, "id")
    row = ctx.conn.execute("SELECT * FROM attachments WHERE id = ? AND module = ?",
                           (image_id, MODULE)).fetchone()
    if row is None:
        raise ApiError(404, NOT_FOUND)
    try:
        permissions.require_project_role(ctx.conn, ctx.user, row["project_id"], "reader")
    except ApiError:
        raise ApiError(404, NOT_FOUND)
    ext = uploads.IMAGE_TYPES[row["mime"]][0]
    return RawFile.image(uploads.read(ctx.data_dir, row), "image-{}.{}".format(row["id"], ext), row["mime"])


def check_page_images(conn, project_id, image_ids):
    """Refuse a page that points at an image of another space (or none)."""
    if not image_ids:
        return
    marks = ", ".join("?" for _ in image_ids)
    found = {r[0] for r in conn.execute(
        "SELECT id FROM attachments WHERE module = ? AND project_id = ? AND id IN ({})".format(marks),
        (MODULE, project_id) + tuple(image_ids))}
    missing = sorted(set(image_ids) - found)
    if missing:
        raise ApiError(400, "Image(s) {} inconnue(s) dans cet espace. Correctif : insérez l'image "
                            "de nouveau (coller, glisser ou bouton Image) plutôt que de recopier "
                            "son numéro depuis une autre page.".format(", ".join(map(str, missing))))
