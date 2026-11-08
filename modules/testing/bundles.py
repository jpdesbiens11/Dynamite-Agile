"""Test bundles and evidence of a test plan (0.60.90, D-O-096).

A plan sent to a supplier is run on real prototypes. Each prototype actually tested is one **bundle** of the plan (a
proto identifier, its serial number, a note): inside it, every test of the plan gets a result -- Passed, Passed with
derogation, Failed or Abandoned -- and the evidence that supports it. Evidence files (the filled-in report, lab
reports, spreadsheets, photos, logs...) are dropped in bulk on the plan, then pointed at from the results.

A plan cannot be closed before every bundle is complete (see close_blockers): a result for each test, a note for any
result other than Passed, and at least one evidence file behind every result except Abandoned.
"""
import json

from core import db, permissions, uploads, validate
from core.errors import ApiError
from core.files import RawFile

RESULTS = {"passed": "Passed", "derogation": "Passed with derogation", "failed": "Failed", "abandoned": "Abandoned"}
NEEDS_NOTE = ("derogation", "failed", "abandoned")
NEEDS_EVIDENCE = ("passed", "derogation", "failed")
OPEN = ("sent", "results")  # the plan statuses in which the campaign runs


def _plans():
    from . import plans
    return plans


def _open_plan(ctx):
    P = _plans()
    pid = P._pid(ctx, "editor")
    row = P._row(ctx, pid)
    if row["status"] not in OPEN:
        raise ApiError(409, "Plan {} « {} » : bundles et preuves se saisissent quand le plan est « Sent to Supplier » ou "
                            "« Results Received ». Correctif : envoyez d'abord le plan (ou rouvrez-le).".format(
                                row["code"], P.STATUSES[row["status"]]))
    return pid, row


def _bundle(ctx, row):
    b = ctx.conn.execute("SELECT * FROM testing_bundles WHERE id = ? AND plan_id = ?",
                         (int(ctx.params["bid"]), row["id"])).fetchone()
    if b is None:
        raise ApiError(404, "Bundle introuvable dans {}.".format(row["code"]))
    return b


def _evidence_row(ctx, row):
    e = ctx.conn.execute("SELECT * FROM testing_evidence WHERE id = ? AND plan_id = ?",
                         (int(ctx.params["eid"]), row["id"])).fetchone()
    if e is None:
        raise ApiError(404, "Preuve introuvable dans {}.".format(row["code"]))
    return e


def public(conn, row):
    """Bundles (with their results) and evidence of a plan, for the plan screen."""
    evidence = [dict(id=e["id"], name=e["name"], note=e["note"], bundle_id=e["bundle_id"], mime=e["mime"], size=e["size"],
                     at=e["created_at"], by=e["author"]) for e in conn.execute(
        "SELECT v.*, a.mime, a.size, u.display_name AS author FROM testing_evidence v JOIN attachments a ON a.id = v.attachment_id "
        "LEFT JOIN users u ON u.id = v.created_by WHERE v.plan_id = ? ORDER BY v.id", (row["id"],))]
    bundles = []
    for b in conn.execute("SELECT * FROM testing_bundles WHERE plan_id = ? ORDER BY id", (row["id"],)):
        results = {r["test_id"]: {"result": r["result"], "note": r["note"], "evidence": json.loads(r["evidence"] or "[]")}
                   for r in conn.execute("SELECT * FROM testing_results WHERE bundle_id = ?", (b["id"],))}
        bundles.append({"id": b["id"], "proto": b["proto"], "serial": b["serial"], "note": b["note"], "results": results})
    return {"bundles": bundles, "evidence": evidence, "result_labels": RESULTS, "blockers": close_blockers(conn, row)}


def close_blockers(conn, row):
    """What still prevents closing the plan, as sentences (empty = complete)."""
    tests = json.loads(row["tests"] or "[]")
    bundles = conn.execute("SELECT * FROM testing_bundles WHERE plan_id = ? ORDER BY id", (row["id"],)).fetchall()
    if not bundles:
        return ["Aucun bundle : ajoutez un bundle par prototype effectivement testé."]
    known = {e["id"] for e in conn.execute("SELECT id FROM testing_evidence WHERE plan_id = ?", (row["id"],))}
    out = []
    for b in bundles:
        have = {r["test_id"]: r for r in conn.execute("SELECT * FROM testing_results WHERE bundle_id = ?", (b["id"],))}
        todo = [t for t in tests if t not in have or not have[t]["result"]]
        if todo:
            out.append("Bundle {} : sans résultat — {}{}.".format(b["proto"], ", ".join(todo[:6]), "…" if len(todo) > 6 else ""))
        for t in tests:
            r = have.get(t)
            if r is None or not r["result"]:
                continue
            if r["result"] in NEEDS_NOTE and not r["note"].strip():
                out.append("Bundle {}, {} : « {} » demande une justification.".format(b["proto"], t, RESULTS[r["result"]]))
            if r["result"] in NEEDS_EVIDENCE and not (set(json.loads(r["evidence"] or "[]")) & known):
                out.append("Bundle {}, {} : aucune preuve liée.".format(b["proto"], t))
    return out


def api_bundle_create(ctx):
    pid, row = _open_plan(ctx)
    proto = validate.text(ctx.body, "proto", 80)
    if ctx.conn.execute("SELECT 1 FROM testing_bundles WHERE plan_id = ? AND proto = ? COLLATE NOCASE", (row["id"], proto)).fetchone():
        raise ApiError(409, "Le prototype « {} » a déjà son bundle dans {}. Correctif : ouvrez-le, ou donnez un autre identifiant "
                            "(un bundle par prototype).".format(proto, row["code"]))
    now = db.utc_now()
    bid = ctx.conn.execute(
        "INSERT INTO testing_bundles (plan_id, proto, serial, note, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (row["id"], proto, validate.text(ctx.body, "serial", 80, required=False), validate.text(ctx.body, "note", 2000, required=False),
         ctx.user["id"], now, now)).lastrowid
    _plans()._log(ctx, "testing_bundle_created", row["id"], {"bundle": bid, "proto": proto})
    return {"id": bid}


def api_bundle_update(ctx):
    pid, row = _open_plan(ctx)
    b = _bundle(ctx, row)
    changes = {k: validate.text(ctx.body, k, lim, required=(k == "proto")) for k, lim in (("proto", 80), ("serial", 80), ("note", 2000))
               if k in ctx.body}
    if changes.get("proto") and ctx.conn.execute("SELECT 1 FROM testing_bundles WHERE plan_id = ? AND proto = ? COLLATE NOCASE AND id <> ?",
                                                 (row["id"], changes["proto"], b["id"])).fetchone():
        raise ApiError(409, "Le prototype « {} » a déjà son bundle. Correctif : un bundle par prototype.".format(changes["proto"]))
    if changes:
        changes["updated_at"] = db.utc_now()
        ctx.conn.execute("UPDATE testing_bundles SET {} WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                         list(changes.values()) + [b["id"]])
        _plans()._log(ctx, "testing_bundle_updated", row["id"], {"bundle": b["id"], "fields": sorted(changes)})
    return {"ok": True}


def api_bundle_delete(ctx):
    pid, row = _open_plan(ctx)
    b = _bundle(ctx, row)
    ctx.conn.execute("DELETE FROM testing_results WHERE bundle_id = ?", (b["id"],))
    ctx.conn.execute("UPDATE testing_evidence SET bundle_id = NULL WHERE bundle_id = ?", (b["id"],))
    ctx.conn.execute("DELETE FROM testing_bundles WHERE id = ?", (b["id"],))
    _plans()._log(ctx, "testing_bundle_deleted", row["id"], {"proto": b["proto"]})
    return {"ok": True}


def api_result(ctx):
    pid, row = _open_plan(ctx)
    b = _bundle(ctx, row)
    test_id = str(ctx.params["tid"]).upper()
    if test_id not in json.loads(row["tests"] or "[]"):
        raise ApiError(404, "Le test {} n'est pas dans le plan {}.".format(test_id, row["code"]))
    result = str(ctx.body.get("result") or "")
    if result and result not in RESULTS:
        raise ApiError(400, "Résultat « {} » inconnu. Correctif : {}.".format(result, ", ".join(RESULTS)))
    note = validate.text(ctx.body, "note", 4000, required=False)
    ids = ctx.body.get("evidence") or []
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        raise ApiError(400, "« evidence » doit être une liste d'identifiants de preuves.")
    known = {e["id"] for e in ctx.conn.execute("SELECT id FROM testing_evidence WHERE plan_id = ?", (row["id"],))}
    if set(ids) - known:
        raise ApiError(400, "Preuve inconnue dans {}. Correctif : déposez d'abord le fichier dans « Preuves ».".format(row["code"]))
    now = db.utc_now()
    ctx.conn.execute(
        "INSERT INTO testing_results (bundle_id, test_id, result, note, evidence, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(bundle_id, test_id) DO UPDATE SET result = excluded.result, note = excluded.note, evidence = excluded.evidence, "
        "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
        (b["id"], test_id, result, note, json.dumps(sorted(set(ids))), ctx.user["id"], now))
    _plans()._log(ctx, "testing_result_set", row["id"], {"bundle": b["proto"], "test": test_id, "result": result})
    return {"ok": True}


@uploads.binary_body
def api_evidence_add(ctx):
    pid, row = _open_plan(ctx)
    stored = uploads.store_evidence(ctx, pid, "testing_plan", int(ctx.config.get("max_upload_mb", 50)) * 1048576)
    name = stored["original_name"] or "preuve"
    eid = ctx.conn.execute("INSERT INTO testing_evidence (plan_id, attachment_id, name, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
                           (row["id"], stored["id"], name, ctx.user["id"], db.utc_now())).lastrowid
    _plans()._log(ctx, "testing_evidence_added", row["id"], {"file": name, "size": stored["size"], "type": stored["mime"]})
    return {"id": eid, "name": name}


def api_evidence_update(ctx):
    pid, row = _open_plan(ctx)
    e = _evidence_row(ctx, row)
    note = validate.text(ctx.body, "note", 500, required=False) if "note" in ctx.body else e["note"]
    bundle_id = e["bundle_id"]
    if "bundle_id" in ctx.body:
        bundle_id = ctx.body["bundle_id"]
        if bundle_id is not None and not ctx.conn.execute("SELECT 1 FROM testing_bundles WHERE id = ? AND plan_id = ?",
                                                          (bundle_id, row["id"])).fetchone():
            raise ApiError(400, "Bundle inconnu dans {}.".format(row["code"]))
    ctx.conn.execute("UPDATE testing_evidence SET note = ?, bundle_id = ? WHERE id = ?", (note, bundle_id, e["id"]))
    return {"ok": True}


def api_evidence_delete(ctx):
    pid, row = _open_plan(ctx)
    e = _evidence_row(ctx, row)
    for r in ctx.conn.execute("SELECT r.evidence, b.proto, r.test_id FROM testing_results r JOIN testing_bundles b ON b.id = r.bundle_id "
                              "WHERE b.plan_id = ?", (row["id"],)):
        if e["id"] in json.loads(r["evidence"] or "[]"):
            raise ApiError(409, "« {} » soutient le résultat de {} (bundle {}). Correctif : retirez-la de ce résultat, puis "
                                "supprimez-la.".format(e["name"], r["test_id"], r["proto"]))
    ctx.conn.execute("DELETE FROM testing_evidence WHERE id = ?", (e["id"],))  # the stored file stays (content-addressed store)
    _plans()._log(ctx, "testing_evidence_deleted", row["id"], {"file": e["name"]})
    return {"ok": True}


def api_evidence_file(ctx):
    P = _plans()
    pid = P._pid(ctx)
    row = P._row(ctx, pid)
    e = _evidence_row(ctx, row)
    att = ctx.conn.execute("SELECT * FROM attachments WHERE id = ?", (e["attachment_id"],)).fetchone()
    if att is None:
        raise ApiError(404, "Fichier de preuve absent du serveur. Correctif : restaurez data/attachments depuis la sauvegarde.")
    return RawFile(uploads.read(ctx.data_dir, att), e["name"], att["mime"], export=False)
