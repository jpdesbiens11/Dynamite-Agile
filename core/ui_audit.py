"""« Audit » of the interface (core lot v0.7, D-B-022).

Anyone signed in files an observation about the screen they are on -- a
bug, an improvement, a question -- with a screenshot of the page, the tool
and the address. It is a platform-wide list (not tied to a project: the
interface is shared by every tool), followed up by the administrators
(Nouveau -> Planifié (target release, owner; D-B-025) -> En cours -> Fait /
Rejeté), exported to CSV to plan the next revisions.

Screenshots: PNG / JPEG / WebP only (bytes checked, never the name), stored
in data/ui_audit/<sha256>.<ext>, served back only to signed-in users.
"""
import csv
import hashlib
import io
import re
from pathlib import Path

from . import audit, db, permissions, uploads, validate
from .errors import ApiError
from .files import RawFile

MIGRATIONS = [
    (3, """
        CREATE TABLE ui_audits (
            id          INTEGER PRIMARY KEY,
            kind        TEXT NOT NULL DEFAULT 'improvement',
            priority    TEXT NOT NULL DEFAULT 'normal',
            status      TEXT NOT NULL DEFAULT 'new',
            module      TEXT NOT NULL DEFAULT '',
            page_url    TEXT NOT NULL DEFAULT '',
            page_title  TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL,
            admin_note  TEXT NOT NULL DEFAULT '',
            image_sha   TEXT NOT NULL DEFAULT '',
            image_mime  TEXT NOT NULL DEFAULT '',
            created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at  TEXT NOT NULL,
            updated_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at  TEXT NOT NULL
        );
        CREATE INDEX idx_ui_audits_status ON ui_audits(status, created_at);
    """),
    (4, """
        -- D-B-025: planning of the next revisions -- target release and owner.
        ALTER TABLE ui_audits ADD COLUMN target_release TEXT NOT NULL DEFAULT '';
        ALTER TABLE ui_audits ADD COLUMN assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
    """),
]

KINDS = {"bug": "Bug", "improvement": "Amélioration", "question": "Question"}
PRIORITIES = {"low": "Basse", "normal": "Normale", "high": "Haute"}
STATUSES = {"new": "Nouveau", "planned": "Planifié", "doing": "In Progress", "done": "Fait", "rejected": "Rejected"}
OPEN = ("new", "planned", "doing")
MAX_IMAGE = 10 * 1024 * 1024


def _choice(body, name, options, default):
    value = body.get(name, default)
    if value not in options:
        raise ApiError(400, "Valeur « {} » invalide pour {}. Correctif : {}.".format(
            value, name, ", ".join(options)))
    return value


def _row(conn, item_id):
    row = conn.execute(
        "SELECT a.*, u.display_name AS created_by_name, v.display_name AS updated_by_name, "
        "w.display_name AS assignee_name FROM ui_audits a LEFT JOIN users u ON u.id = a.created_by "
        "LEFT JOIN users v ON v.id = a.updated_by LEFT JOIN users w ON w.id = a.assignee_id WHERE a.id = ?",
        (item_id,)).fetchone()
    if row is None:
        raise ApiError(404, "Observation introuvable.")
    item = dict(row)
    item.update(kind_label=KINDS.get(item["kind"], item["kind"]),
                priority_label=PRIORITIES.get(item["priority"], item["priority"]),
                status_label=STATUSES.get(item["status"], item["status"]),
                has_image=bool(item["image_sha"]))
    item.pop("image_sha")
    return item


def _path(data_dir, sha, mime):
    ext = uploads.IMAGE_TYPES[mime][0]
    return Path(data_dir) / "ui_audit" / "{}.{}".format(sha, ext)


def api_list(ctx):
    if permissions.is_guest(ctx.user):  # 0.60.82 (D-O-088): the team's observations and accounts stay with the team
        return {"items": [], "kinds": KINDS, "priorities": PRIORITIES, "statuses": STATUSES, "users": [], "releases": [],
                "can_manage": False}
    ids = [r[0] for r in ctx.conn.execute(
        "SELECT id FROM ui_audits ORDER BY CASE status WHEN 'doing' THEN 0 WHEN 'planned' THEN 1 WHEN 'new' THEN 2 ELSE 3 END, "
        "created_at DESC LIMIT 1000")]
    items = [_row(ctx.conn, i) for i in ids]
    users = db.rows(ctx.conn.execute("SELECT id, display_name FROM users WHERE is_active = 1 ORDER BY display_name"))
    releases = sorted({i["target_release"] for i in items if i["target_release"]}, key=_release_key)
    return {"items": items, "kinds": KINDS, "priorities": PRIORITIES, "statuses": STATUSES, "users": users,
            "releases": releases, "can_manage": bool(ctx.user["is_admin"])}


def _release_key(text):
    """0.9.0 before 0.10.0: numbers compared as numbers, the rest as text."""
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in re.split(r"[.\-\s]+", text)]


def api_count(ctx):
    """Open observations, for the badge of the top-bar button."""
    if permissions.is_guest(ctx.user):
        return {"open": 0}
    row = ctx.conn.execute("SELECT COUNT(*) FROM ui_audits WHERE status IN ('new', 'planned', 'doing')").fetchone()
    return {"open": row[0]}


def api_create(ctx):
    body = ctx.body
    description = validate.text(body, "description", 4000, required=False)
    if not description:
        raise ApiError(400, "Description vide. Correctif : décrivez ce qu'il faut corriger ou améliorer.")
    page_url = validate.text(body, "page_url", 500, required=False)
    if not page_url.startswith("#/"):  # shown as a link: only in-app addresses, never javascript: or http:
        page_url = ""
    now = db.utc_now()
    item_id = ctx.conn.execute(
        "INSERT INTO ui_audits (kind, priority, module, page_url, page_title, description, created_by, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (_choice(body, "kind", KINDS, "improvement"), _choice(body, "priority", PRIORITIES, "normal"),
         validate.text(body, "module", 40, required=False), page_url,
         validate.text(body, "page_title", 200, required=False), description, ctx.user["id"], now, now)).lastrowid
    audit.log_action(ctx.conn, ctx.user["id"], "ui_audit_created", "ui_audit", item_id, None, ctx.ip)
    return {"item": _row(ctx.conn, item_id)}


@uploads.binary_body
def api_image(ctx):
    item_id = validate.int_param(ctx.params, "aid")
    item = _row(ctx.conn, item_id)
    if item["created_by"] != ctx.user["id"] and not ctx.user["is_admin"]:
        raise ApiError(403, "Seul l'auteur ou un administrateur joint la capture.")
    data = ctx.upload.data if ctx.upload else b""
    if not data:
        raise ApiError(400, "Aucune image reçue. Correctif : capturez ou collez (Ctrl+V) une image.")
    if len(data) > MAX_IMAGE:
        raise ApiError(413, "Capture de plus de 10 Mo. Correctif : réduisez la fenêtre ou collez une image JPEG.")
    mime = uploads.sniff_image(data)
    if mime is None:
        raise ApiError(415, "Ce fichier n'est pas une image reconnue. Correctif : formats acceptés : {}."
                       .format(uploads.IMAGE_LABEL))
    sha = hashlib.sha256(data).hexdigest()
    path = _path(ctx.data_dir, sha, mime)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(path)
    ctx.conn.execute("UPDATE ui_audits SET image_sha = ?, image_mime = ? WHERE id = ?", (sha, mime, item_id))
    audit.log_action(ctx.conn, ctx.user["id"], "ui_audit_image", "ui_audit", item_id, {"bytes": len(data)}, ctx.ip)
    return {"item": _row(ctx.conn, item_id)}


def api_get_image(ctx):
    if permissions.is_guest(ctx.user):
        raise ApiError(404, "Pas de capture pour cette observation.")
    row = ctx.conn.execute("SELECT image_sha, image_mime FROM ui_audits WHERE id = ?",
                           (validate.int_param(ctx.params, "aid"),)).fetchone()
    if row is None or not row["image_sha"]:
        raise ApiError(404, "Pas de capture pour cette observation.")
    try:
        data = _path(ctx.data_dir, row["image_sha"], row["image_mime"]).read_bytes()
    except OSError:
        raise ApiError(404, "Capture absente du serveur (dossier data/ui_audit incomplet). "
                            "Correctif : restaurez ce dossier depuis la sauvegarde.")
    return RawFile.image(data, "audit.{}".format(uploads.IMAGE_TYPES[row["image_mime"]][0]), row["image_mime"])


def _changes(ctx, body, before):
    changes = {}
    if "status" in body:
        changes["status"] = _choice(body, "status", STATUSES, before["status"])
    if "priority" in body:
        changes["priority"] = _choice(body, "priority", PRIORITIES, before["priority"])
    if "kind" in body:
        changes["kind"] = _choice(body, "kind", KINDS, before["kind"])
    if "admin_note" in body:
        changes["admin_note"] = validate.text(body, "admin_note", 2000, required=False)
    if "target_release" in body:
        changes["target_release"] = validate.text(body, "target_release", 30, required=False)
    if "assignee_id" in body:
        value = body.get("assignee_id")
        if value in (None, "", 0):
            changes["assignee_id"] = None
        else:
            try:
                value = int(value)
            except (TypeError, ValueError):
                value = -1
            if not ctx.conn.execute("SELECT 1 FROM users WHERE id = ? AND is_active = 1", (value,)).fetchone():
                raise ApiError(400, "Responsable « {} » inconnu. Correctif : choisissez une personne de la liste."
                               .format(body.get("assignee_id")))
            changes["assignee_id"] = value
    if changes.get("target_release") and changes.get("status", before["status"]) == "new":
        changes["status"] = "planned"  # given a release: planned
    return {k: v for k, v in changes.items() if v != before.get(k)}


def _apply(ctx, item_id, changes):
    if not changes:
        return
    changes = dict(changes, updated_by=ctx.user["id"], updated_at=db.utc_now())
    ctx.conn.execute("UPDATE ui_audits SET {} WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                     list(changes.values()) + [item_id])
    audit.log_action(ctx.conn, ctx.user["id"], "ui_audit_updated", "ui_audit", item_id,
                     {k: v for k, v in changes.items() if k not in ("updated_by", "updated_at", "admin_note")}, ctx.ip)


def _require_manager(ctx):
    if not ctx.user["is_admin"]:
        raise ApiError(403, "Réservé aux administrateurs. Correctif : ajoutez plutôt une nouvelle observation.")


def api_update(ctx):
    """Status, priority, type, target release, owner and answer: administrators only."""
    _require_manager(ctx)
    item_id = validate.int_param(ctx.params, "aid")
    _apply(ctx, item_id, _changes(ctx, ctx.body, _row(ctx.conn, item_id)))
    return {"item": _row(ctx.conn, item_id)}


def api_bulk(ctx):
    """Same changes on several observations (plan a release in one go)."""
    _require_manager(ctx)
    ids = ctx.body.get("ids")
    if not isinstance(ids, list) or not ids or len(ids) > 500 or not all(isinstance(i, int) for i in ids):
        raise ApiError(400, "Aucune observation choisie. Correctif : cochez au moins une ligne (500 au maximum).")
    changes = ctx.body.get("changes")
    if not isinstance(changes, dict) or not changes:
        raise ApiError(400, "Aucun changement demandé. Correctif : choisissez un statut, une révision ou un responsable.")
    for item_id in ids:
        _apply(ctx, item_id, _changes(ctx, changes, _row(ctx.conn, item_id)))
    return {"items": [_row(ctx.conn, i) for i in ids]}


CSV_COLUMNS = ["ID", "Statut", "Type", "Priorité", "Révision cible", "Responsable", "Outil", "Page", "Description",
               "Suivi", "Auteur", "Créée le (UTC)", "Modifiée le (UTC)", "Capture"]


def api_export(ctx):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    for i in api_list(ctx)["items"]:
        writer.writerow([i["id"], i["status_label"], i["kind_label"], i["priority_label"], i["target_release"],
                         i["assignee_name"] or "", i["module"], i["page_url"], i["description"], i["admin_note"],
                         i["created_by_name"] or "", i["created_at"], i["updated_at"], "oui" if i["has_image"] else "non"])
    return RawFile.csv(out.getvalue(), "audit_interface_{}.csv".format(db.utc_now()[:10]))


A = r"/api/ui-audit/(?P<aid>\d+)"

ROUTES = [
    ("GET", r"/api/ui-audit", api_list, "user"),
    ("GET", r"/api/ui-audit/count", api_count, "user"),
    ("GET", r"/api/ui-audit/export\.csv", api_export, "user"),
    ("POST", r"/api/ui-audit/bulk", api_bulk, "user"),
    ("POST", r"/api/ui-audit", api_create, "user"),
    ("PATCH", A, api_update, "user"),
    ("POST", A + r"/image", api_image, "user"),
    ("GET", A + r"/image", api_get_image, "user"),
]
