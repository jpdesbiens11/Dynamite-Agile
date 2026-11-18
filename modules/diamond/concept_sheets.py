"""Diamond · concept sheets of a brick (0.60.105, D-O-117): the candidate solutions of a « to define » brick, CB-3.1,
CB-3.2… -- written in the platform (digital), drafted by an AI assistant and kept by a person (ai), or a paper sheet of
a creativity session, scanned (image or PDF, stored by core/uploads.py and sent back as it is, RawFile(export=False)).
A sheet becomes « selected » when the Pugh matrix that judged it is decided in its favour (concept_pugh.py).
"""
from core import audit, db, permissions, uploads, validate
from core.errors import ApiError
from core.files import RawFile

from . import concepts as C
from . import functions as F

MODULE = "diamond"
KINDS = {"digital": "Feuille numérique", "ai": "Générée avec l'IA", "scan": "Scan d'une feuille papier"}
STATUS = {"open": "Open", "selected": "Selected", "dropped": "Dropped"}
LIMITS = {"title": 160, "principle": 600, "description": 4000, "pros": 1500, "cons": 1500}
MAX_SHEETS, MAX_SCAN_MB = 40, 15


def code(concept_number, number):
    return "CB-{}.{}".format(concept_number, number)


def rows(conn, pid, concept_id=None):
    sql = ("SELECT s.*, c.number AS concept_number, c.name AS concept_name, u.display_name AS author_name, "
           "a.mime AS file_mime, a.original_name AS file_name FROM diamond_concept_sheets s "
           "JOIN diamond_concepts c ON c.id = s.concept_id LEFT JOIN users u ON u.id = s.author_id "
           "LEFT JOIN attachments a ON a.id = s.attachment_id WHERE s.project_id = ? AND s.archived = 0 AND c.archived = 0")
    args = [pid]
    if concept_id is not None:
        sql += " AND s.concept_id = ?"
        args.append(concept_id)
    out = [dict(r) for r in conn.execute(sql + " ORDER BY c.position, c.number, s.number", args)]
    for s in out:
        s["code"] = code(s["concept_number"], s["number"])
    return out


def _sheet(conn, pid, sid):
    row = conn.execute("SELECT * FROM diamond_concept_sheets WHERE id = ? AND project_id = ? AND archived = 0", (sid, pid)).fetchone()
    if row is None:
        raise ApiError(404, "Feuille de concept introuvable dans ce Space. Correctif : rechargez la page.")
    return dict(row)


def _fields(body, partial=False):
    out = {}
    for name in LIMITS:
        if partial and name not in body:
            continue
        value = str(body.get(name) or "").strip()
        if name in ("title", "principle"):
            value = " ".join(value.split())
        if name == "title" and not value:
            raise ApiError(400, "Titre de la feuille obligatoire. Correctif : quelques mots (ex. « Refroidissement par plaque froide »).")
        if len(value) > LIMITS[name]:
            raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(name, LIMITS[name], len(value)))
        out[name] = value
    if not partial or "kind" in body:
        out["kind"] = str(body.get("kind") or "digital")
        if out["kind"] not in KINDS:
            raise ApiError(400, "Nature « {} » inconnue. Correctif : {}.".format(out["kind"][:20], ", ".join(KINDS)))
    if "status" in body:
        if body["status"] not in STATUS:
            raise ApiError(400, "Status « {} » inconnu. Correctif : {}.".format(str(body["status"])[:20], ", ".join(STATUS)))
        out["status"] = body["status"]
    return out


def add(conn, user_id, pid, concept_id, fields, attachment_id=None):
    n = conn.execute("SELECT COUNT(*) FROM diamond_concept_sheets WHERE concept_id = ? AND archived = 0", (concept_id,)).fetchone()[0]
    if n >= MAX_SHEETS:
        raise ApiError(409, "{} feuilles au maximum par brique. Correctif : archivez les feuilles écartées.".format(MAX_SHEETS))
    number = conn.execute("SELECT COALESCE(MAX(number), 0) + 1 FROM diamond_concept_sheets WHERE concept_id = ?",
                          (concept_id,)).fetchone()[0]
    now = db.utc_now()
    return conn.execute(
        "INSERT INTO diamond_concept_sheets (project_id, concept_id, number, title, kind, principle, description, pros, cons, "
        "attachment_id, author_id, created_at, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (pid, concept_id, number, fields["title"], fields.get("kind", "digital"), fields.get("principle", ""),
         fields.get("description", ""), fields.get("pros", ""), fields.get("cons", ""), attachment_id, user_id, now, user_id,
         now)).lastrowid


def api_list(ctx):
    """Every sheet of the Space (« Feuilles de concept »)."""
    pid = F.access(ctx)
    return {"sheets": rows(ctx.conn, pid), "labels": {"kinds": KINDS, "status": STATUS}}


def api_create(ctx):
    pid = F.access(ctx, "editor")
    concept = C._concept(ctx.conn, pid, validate.int_param(ctx.params, "cid"))
    from .concept_freeze import guard  # 0.60.116 (D-O-129): no new concept under a frozen brick
    guard(ctx.conn, pid, concept["id"], "Ajouter une feuille de concept")
    fields = _fields(ctx.body)
    attachment = ctx.body.get("attachment_id")
    if attachment not in (None, ""):
        attachment = int(attachment)
        if not ctx.conn.execute("SELECT 1 FROM attachments WHERE id = ? AND project_id = ? AND module = ?",
                                (attachment, pid, MODULE)).fetchone():
            raise ApiError(400, "Scan introuvable dans ce Space. Correctif : déposez de nouveau le fichier.")
        fields["kind"] = "scan"
    else:
        attachment = None
    sid = add(ctx.conn, ctx.user["id"], pid, concept["id"], fields, attachment)
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_sheet_create", "diamond_concept_sheet", sid,
                     {"concept": C.code(concept["number"]), "kind": fields["kind"]}, ctx.ip)
    return {"sheets": rows(ctx.conn, pid, concept["id"]), "created": sid}


def api_update(ctx):
    pid = F.access(ctx, "editor")
    s = _sheet(ctx.conn, pid, validate.int_param(ctx.params, "sid"))
    from .concept_freeze import guard
    guard(ctx.conn, pid, s["concept_id"], "Modifier une feuille de concept")
    fields = _fields(ctx.body, partial=True)
    if fields:
        sets = ", ".join("{} = ?".format(k) for k in fields)
        ctx.conn.execute("UPDATE diamond_concept_sheets SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(sets),
                         tuple(fields.values()) + (ctx.user["id"], db.utc_now(), s["id"]))
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_sheet_update", "diamond_concept_sheet", s["id"], {"fields": sorted(fields)}, ctx.ip)
    return {"sheets": rows(ctx.conn, pid, s["concept_id"])}


def api_archive(ctx):
    pid = F.access(ctx, "editor")
    s = _sheet(ctx.conn, pid, validate.int_param(ctx.params, "sid"))
    from .concept_freeze import guard
    guard(ctx.conn, pid, s["concept_id"], "Archiver une feuille de concept")
    ctx.conn.execute("UPDATE diamond_concept_sheets SET archived = 1, updated_by = ?, updated_at = ? WHERE id = ?",
                     (ctx.user["id"], db.utc_now(), s["id"]))
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_sheet_archive", "diamond_concept_sheet", s["id"], {"title": s["title"]}, ctx.ip)
    return {"sheets": rows(ctx.conn, pid, s["concept_id"])}


@uploads.binary_body
def api_upload(ctx):
    """The scan of a paper sheet: an image (photo, scanner) or a PDF; the sheet is created next (api_create)."""
    pid = F.access(ctx, "editor")
    data = getattr(getattr(ctx, "upload", None), "data", b"") or b""
    if data.startswith(b"%PDF-"):
        row = uploads.store_pdf(ctx, pid, MODULE, MAX_SCAN_MB * 1048576)
    else:
        row = uploads.store_image(ctx, pid, MODULE, MAX_SCAN_MB * 1048576)
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_sheet_upload", "attachment", row["id"], {"size": row["size"], "mime": row["mime"]}, ctx.ip)
    return {"id": row["id"], "mime": row["mime"], "size": row["size"], "name": row["original_name"]}


def api_file(ctx):
    """The scan of a sheet, sent back as it was deposited (shown inline: an image, or a PDF the browser opens)."""
    pid = validate.int_param(ctx.params, "pid")
    permissions.require_project_role(ctx.conn, ctx.user, pid, "reader")
    s = _sheet(ctx.conn, pid, validate.int_param(ctx.params, "sid"))
    row = ctx.conn.execute("SELECT * FROM attachments WHERE id = ? AND project_id = ?", (s["attachment_id"], pid)).fetchone()
    if row is None:
        raise ApiError(404, "Cette feuille n'a pas de scan.")
    if row["mime"] in uploads.IMAGE_TYPES:
        return RawFile.image(uploads.read(ctx.data_dir, row), row["original_name"] or "scan", row["mime"])
    return RawFile(uploads.read(ctx.data_dir, row), row["original_name"] or "scan.pdf", row["mime"], inline=True, export=False)
