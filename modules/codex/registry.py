"""Codex registry (D-B-021): document references reserved per project.

The server, not the browser, stamps the reference: the date-time serial is
unique across the whole platform (index on date + time), so two people
reserving in the same second get two numbers. A number is never reused:
a reference is voided, never deleted.
Rights: readers see the registry; editors reserve and revise; voiding is
kept to administrators.
"""
import csv
import datetime as dt
import io
import re
import sqlite3

from core import audit, db, permissions, validate
from core.errors import ApiError
from core.files import RawFile

from . import catalog

SUB_RE = re.compile(r"^\d{1,2}$")
MAX_TITLE = 150
MAX_REFS = 5000
STATUS_LABELS = {"active": "Active", "void": "Annulée"}
CSV_COLUMNS = ["Référence", "Revision", "Type", "Nom du type", "Étape PDP", "Subdivision", "Système", "Titre",
               "Nom de fichier", "Dossier", "Status", "Motif d'annulation", "Réservée par", "Réservée le (UTC)",
               "Modifiée le (UTC)"]


def _pid(ctx):
    return validate.int_param(ctx.params, "pid")


def _log(ctx, action, ref_id, details):
    audit.log_action(ctx.conn, ctx.user["id"], action, "codex_ref", ref_id, details, ctx.ip)


# --------------------------------------------------------------------------
# Validation: every refusal names the value and the fix (D-A-031)
# --------------------------------------------------------------------------
def _doc_type(body):
    value = str(body.get("doc_type") or "").strip().upper()
    retired = catalog.RETIRED_TYPES.get(value)
    if retired:
        raise ApiError(400, "Le code « {} » ({}) n'est plus offert. Correctif : utilisez {} ({}).".format(
            value, retired["name"], retired["replaced_by"], catalog.DOC_TYPES[retired["replaced_by"]]["name"]))
    if value not in catalog.DOC_TYPES:
        raise ApiError(400, "Type de document « {} » inconnu. Correctif : choisissez un type de la liste "
                            "(ex. LCV, CDCF, VVR).".format(value))
    return value


def _chapter(body):
    """The step of the PDP (« step » in the request, column pdp_step)."""
    value = str(body.get("step") or body.get("pdp_step") or "").strip()[:2].zfill(2)
    if value not in catalog.STEPS:
        raise ApiError(400, "Étape du PDP « {} » inconnue. Correctif : choisissez une étape de la liste "
                            "(ex. 09 Recherche des fonctions, 11 CdCF).".format(value))
    return value


def _sub(body):
    value = str(body.get("sub") or body.get("pdp_sub") or "").strip() or "00"
    if not SUB_RE.match(value):
        raise ApiError(400, "Subdivision « {} » invalide. Correctif : 1 ou 2 chiffres (ex. 03), "
                            "ou laissez vide pour 00.".format(value))
    return value.zfill(2)


def _system(body):
    value = str(body.get("system_code") or "").strip().upper()
    if value and not catalog.SYSTEM_RE.match(value):
        raise ApiError(400, "Code système « {} » invalide. Correctif : lettres, chiffres et tirets, "
                            "20 caractères au maximum (ex. CHAUF, SS-02).".format(value))
    return value


def _revision(body, minimum=1):
    value = body.get("revision", 1)
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ApiError(400, "Revision « {} » invalide. Correctif : un nombre entier de {} à 99.".format(value, minimum))
    if not minimum <= value <= 99:
        raise ApiError(400, "Revision {} hors limites. Correctif : un nombre entier de {} à 99.".format(value, minimum))
    return value


def _title(body):
    return validate.text(body, "title", MAX_TITLE, required=False)


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------
def _decorate(row):
    ref = dict(row)
    ref["type_name"] = catalog.ALL_TYPES.get(ref["doc_type"], {}).get("name", "")
    ref["status_label"] = STATUS_LABELS.get(ref["status"], ref["status"])
    return ref


SELECT = ("SELECT r.*, u.display_name AS created_by_name FROM codex_refs r "
          "LEFT JOIN users u ON u.id = r.created_by ")


def load(conn, project_id):
    return [_decorate(r) for r in conn.execute(
        SELECT + "WHERE r.project_id = ? ORDER BY r.date_serial DESC, r.time_serial DESC LIMIT ?",
        (project_id, MAX_REFS)).fetchall()]


def _one(conn, project_id, ref_id):
    row = conn.execute(SELECT + "WHERE r.id = ? AND r.project_id = ?", (ref_id, project_id)).fetchone()
    if row is None:
        raise ApiError(404, "Référence introuvable dans ce projet.")
    return _decorate(row)


def api_meta(ctx):
    return catalog.meta()


def api_list(ctx):
    project_id = _pid(ctx)
    role = permissions.require_project_role(ctx.conn, ctx.user, project_id, "reader")
    return {"refs": load(ctx.conn, project_id), "role": role, "can_edit": role in ("editor", "admin"),
            "can_void": role == "admin", "now": db.utc_now()}


# --------------------------------------------------------------------------
# Reserving
# --------------------------------------------------------------------------
def reserve(ctx, project_id, fields, moment=None):
    """Insert a reference at the first free serial from `moment` (UTC)."""
    date, time = catalog.serial_parts(moment or dt.datetime.now(dt.timezone.utc))
    for _ in range(1000):
        if ctx.conn.execute("SELECT 1 FROM codex_refs WHERE date_serial = ? AND time_serial = ?",
                            (date, time)).fetchone():
            date, time = catalog.next_slot(date, time)
            continue
        made = catalog.names(fields["doc_type"], date, time, fields["pdp_step"], fields["pdp_sub"],
                             fields["system_code"], fields["revision"], fields["title"])
        now = db.utc_now()
        try:
            cur = ctx.conn.execute(
                "INSERT INTO codex_refs (project_id, reference, date_serial, time_serial, doc_type, pdp_step, "
                "pdp_sub, system_code, revision, title, file_name, svn_path, folder, status, created_by, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)",
                (project_id, made["reference"], date, time, fields["doc_type"], fields["pdp_step"],
                 fields["pdp_sub"], fields["system_code"], fields["revision"], fields["title"], made["file_name"],
                 made["svn_path"], made["folder"], ctx.user["id"], now, now))
        except sqlite3.IntegrityError:  # taken between the check and the insert
            date, time = catalog.next_slot(date, time)
            continue
        _log(ctx, "codex_reserve", cur.lastrowid, {"reference": made["reference"], "file_name": made["file_name"]})
        return cur.lastrowid
    raise ApiError(503, "Aucun numéro libre trouvé. Correctif : réessayez dans une seconde.")


def api_reserve(ctx):
    project_id = _pid(ctx)
    permissions.require_project_role(ctx.conn, ctx.user, project_id, "editor")
    body = ctx.body
    fields = {"doc_type": _doc_type(body), "pdp_step": _chapter(body), "pdp_sub": _sub(body),
              "system_code": _system(body), "revision": _revision(body), "title": _title(body)}
    count = ctx.conn.execute("SELECT COUNT(*) FROM codex_refs WHERE project_id = ?", (project_id,)).fetchone()[0]
    if count >= MAX_REFS:
        raise ApiError(400, "Registre plein ({} références). Correctif : créez un nouveau projet.".format(MAX_REFS))
    ref_id = reserve(ctx, project_id, fields)
    return {"ref": _one(ctx.conn, project_id, ref_id)}


# --------------------------------------------------------------------------
# Revising and voiding
# --------------------------------------------------------------------------
def api_update(ctx):
    """Title, system code or revision (never lowered); void / restore by an admin."""
    project_id = _pid(ctx)
    role = permissions.require_project_role(ctx.conn, ctx.user, project_id, "editor")
    ref = _one(ctx.conn, project_id, validate.int_param(ctx.params, "rid"))
    body = ctx.body
    changes = {}
    if "status" in body:
        if role != "admin":
            raise ApiError(403, "Annuler ou rétablir une référence est réservé aux administrateurs. "
                                "Correctif : demandez-le à un administrateur du projet.")
        status = validate.choice(body, "status", tuple(STATUS_LABELS))
        reason = validate.text(body, "void_reason", 300, required=status == "void")
        changes.update(status=status, void_reason=reason if status == "void" else "")
    if ref["status"] == "void" and set(body) - {"status", "void_reason"}:
        raise ApiError(400, "Référence {} annulée : elle ne se modifie plus. Correctif : un administrateur "
                            "peut la rétablir, ou réservez une nouvelle référence.".format(ref["reference"]))
    if "title" in body:
        changes["title"] = _title(body)
    if "system_code" in body:
        changes["system_code"] = _system(body)
    if "revision" in body:
        revision = _revision(body, ref["revision"])
        changes["revision"] = revision
    changes = {k: v for k, v in changes.items() if v != ref.get(k)}
    if not changes:
        return {"ref": ref}
    merged = dict(ref, **changes)
    made = catalog.names(merged["doc_type"], merged["date_serial"], merged["time_serial"], merged["pdp_step"],
                         merged["pdp_sub"], merged["system_code"], merged["revision"], merged["title"])
    changes.update(file_name=made["file_name"], svn_path=made["svn_path"], updated_at=db.utc_now())
    ctx.conn.execute("UPDATE codex_refs SET {} WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                     list(changes.values()) + [ref["id"]])
    _log(ctx, "codex_update", ref["id"], {"reference": ref["reference"],
                                          "changes": {k: [ref.get(k), v] for k, v in changes.items()
                                                      if k not in ("updated_at", "svn_path")}})
    return {"ref": _one(ctx.conn, project_id, ref["id"])}


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------
def api_export_csv(ctx):
    project_id = _pid(ctx)
    permissions.require_project_role(ctx.conn, ctx.user, project_id, "reader")
    key = ctx.conn.execute("SELECT key FROM projects WHERE id = ?", (project_id,)).fetchone()["key"]
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    for r in load(ctx.conn, project_id):
        writer.writerow([r["reference"], r["revision"], r["doc_type"], r["type_name"], r["pdp_step"],
                         r["pdp_sub"], r["system_code"], r["title"], r["file_name"], r["svn_path"],
                         r["status_label"], r["void_reason"], r["created_by_name"] or "", r["created_at"],
                         r["updated_at"]])
    return RawFile.csv(out.getvalue(), "{}_codex_{}.csv".format(key, dt.date.today().isoformat()))
