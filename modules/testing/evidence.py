"""Evidence of a test plan (0.60.90, D-O-096; files of any type, versions and network links: 0.60.94, D-O-100).

What the test supplier sends -- the filled-in report, lab reports, raw data, spreadsheets, photos, videos, archives --
is dropped on the plan, then pointed at from the results of each bundle (bundles.py). Any type of file is accepted, up
to « max_evidence_mb » of data/config.json (150 Mo); the server never opens it and only ever sends it back as a
download. A larger file stays on the network: the plan records its name, its size and where it lies (kind 'link'), and
that reference counts as evidence like a file.

A newer version from the supplier replaces the file (or the link) under the same evidence id, so the results that cite
it follow; the previous versions stay downloadable (history, newest first on screen). Removing an evidence also takes
it out of the results that cited it: the plan's blockers then name each result left without support.
"""
import json

from core import db, uploads, validate
from core.errors import ApiError
from core.files import RawFile

from .bundles import _open_plan, _plans

MODULE = "testing_plan"
MAX_LINK = 1000
MAX_VERSIONS = 50


def limit_mb(config):
    return int(config.get("max_evidence_mb", 150))


def _evidence(ctx, row):
    e = ctx.conn.execute("SELECT * FROM testing_evidence WHERE id = ? AND plan_id = ?",
                         (int(ctx.params["eid"]), row["id"])).fetchone()
    if e is None:
        raise ApiError(404, "Preuve introuvable dans {}.".format(row["code"]))
    return e


def _link(body):
    """Where a file too large for the platform lies (a network share, a drive, a folder): text, shown as it is."""
    link = validate.text(body, "link", MAX_LINK)
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in link):
        raise ApiError(400, "Emplacement réseau invalide (caractère de contrôle). Correctif : collez le chemin sur une seule "
                            "ligne, par exemple \\\\serveur\\partage\\Essais\\TP-001\\rapport.zip.")
    return link


def _declared_size(body):
    size = body.get("size")
    if size in (None, ""):
        return None
    if isinstance(size, bool) or not isinstance(size, int) or not 0 <= size <= 10 ** 15:
        raise ApiError(400, "Taille invalide : « size » est un nombre d'octets. Correctif : laissez-la vide si elle est inconnue.")
    return size


def listing(conn, row):
    """Evidence of a plan for the plan screen, the bundles and the results summary."""
    out = []
    for e in conn.execute(
            "SELECT v.*, a.mime, a.size, u.display_name AS author, w.display_name AS editor FROM testing_evidence v "
            "LEFT JOIN attachments a ON a.id = v.attachment_id LEFT JOIN users u ON u.id = v.created_by "
            "LEFT JOIN users w ON w.id = v.updated_by WHERE v.plan_id = ? ORDER BY v.id", (row["id"],)):
        link = e["kind"] == "link"
        history = [{k: h.get(k) for k in ("version", "name", "kind", "link", "size", "at", "by")}
                   for h in reversed(json.loads(e["history"] or "[]"))]
        out.append(dict(id=e["id"], name=e["name"], note=e["note"], bundle_id=e["bundle_id"], kind=e["kind"],
                        link=e["link"] if link else "", mime="" if link else (e["mime"] or ""),
                        size=e["link_size"] if link else e["size"], version=e["version"],
                        at=e["updated_at"] or e["created_at"], by=e["editor"] or e["author"], history=history))
    return out


def _uploaded(ctx, pid):
    stored = uploads.store_file(ctx, pid, MODULE, limit_mb(ctx.config) * 1048576)
    name = uploads.clean_name(ctx.upload.filename) or stored["original_name"] or "preuve"
    return stored, name


@uploads.large_body("max_evidence_mb")
def api_add(ctx):
    pid, row = _open_plan(ctx)
    stored, name = _uploaded(ctx, pid)
    eid = ctx.conn.execute(
        "INSERT INTO testing_evidence (plan_id, attachment_id, name, kind, created_by, created_at) VALUES (?, ?, ?, 'file', ?, ?)",
        (row["id"], stored["id"], name, ctx.user["id"], db.utc_now())).lastrowid
    _plans()._log(ctx, "testing_evidence_added", row["id"], {"file": name, "size": stored["size"], "type": stored["mime"]})
    return {"id": eid, "name": name}


def api_link_add(ctx):
    pid, row = _open_plan(ctx)
    name = validate.text(ctx.body, "name", 120)
    link, size = _link(ctx.body), _declared_size(ctx.body)
    eid = ctx.conn.execute(
        "INSERT INTO testing_evidence (plan_id, attachment_id, name, note, kind, link, link_size, created_by, created_at) "
        "VALUES (?, NULL, ?, ?, 'link', ?, ?, ?, ?)",
        (row["id"], name, validate.text(ctx.body, "note", 500, required=False), link, size, ctx.user["id"], db.utc_now())).lastrowid
    _plans()._log(ctx, "testing_evidence_linked", row["id"], {"file": name, "link": link, "size": size})
    return {"id": eid, "name": name}


def _new_version(ctx, row, e, name, attachment_id, link, link_size):
    """Keep the current version in history, then put the new one under the same id (the results that cite it follow)."""
    size, sha = e["link_size"], None
    if e["kind"] == "file":
        att = ctx.conn.execute("SELECT size, sha256 FROM attachments WHERE id = ?", (e["attachment_id"],)).fetchone()
        size, sha = (att["size"], att["sha256"]) if att else (None, None)
    who = ctx.conn.execute("SELECT display_name FROM users WHERE id = ?", (e["updated_by"] or e["created_by"],)).fetchone()
    history = json.loads(e["history"] or "[]") + [{
        # the file by its content (sha256), not by attachment id: a restore or a Space copy renumbers the attachments
        "version": e["version"], "name": e["name"], "kind": e["kind"], "sha256": sha,
        "link": e["link"], "size": size, "at": e["updated_at"] or e["created_at"], "by": who["display_name"] if who else ""}]
    ctx.conn.execute(
        "UPDATE testing_evidence SET name = ?, kind = ?, attachment_id = ?, link = ?, link_size = ?, version = ?, history = ?, "
        "updated_by = ?, updated_at = ? WHERE id = ?",
        (name, "link" if link else "file", attachment_id, link, link_size, e["version"] + 1,
         json.dumps(history[-MAX_VERSIONS:], ensure_ascii=False), ctx.user["id"], db.utc_now(), e["id"]))
    _plans()._log(ctx, "testing_evidence_replaced", row["id"], {
        "evidence": e["id"], "previous": e["name"], "file": name, "version": e["version"] + 1, "link": link or None})
    return {"id": e["id"], "name": name, "version": e["version"] + 1}


@uploads.large_body("max_evidence_mb")
def api_replace(ctx):
    pid, row = _open_plan(ctx)
    e = _evidence(ctx, row)
    stored, name = _uploaded(ctx, pid)
    return _new_version(ctx, row, e, name, stored["id"], "", None)


def api_link_replace(ctx):
    pid, row = _open_plan(ctx)
    e = _evidence(ctx, row)
    name = validate.text(ctx.body, "name", 120, required=False) or e["name"]
    return _new_version(ctx, row, e, name, None, _link(ctx.body), _declared_size(ctx.body))


def api_update(ctx):
    pid, row = _open_plan(ctx)
    e = _evidence(ctx, row)
    note = validate.text(ctx.body, "note", 500, required=False) if "note" in ctx.body else e["note"]
    bundle_id = e["bundle_id"]
    if "bundle_id" in ctx.body:
        bundle_id = ctx.body["bundle_id"]
        if bundle_id is not None and not ctx.conn.execute("SELECT 1 FROM testing_bundles WHERE id = ? AND plan_id = ?",
                                                          (bundle_id, row["id"])).fetchone():
            raise ApiError(400, "Bundle inconnu dans {}.".format(row["code"]))
    ctx.conn.execute("UPDATE testing_evidence SET note = ?, bundle_id = ? WHERE id = ?", (note, bundle_id, e["id"]))
    _plans()._log(ctx, "testing_evidence_updated", row["id"], {"evidence": e["id"], "bundle": bundle_id})
    return {"ok": True}


def api_delete(ctx):
    pid, row = _open_plan(ctx)
    e = _evidence(ctx, row)
    released = []
    for r in ctx.conn.execute("SELECT r.id, r.evidence, r.test_id, b.proto FROM testing_results r "
                              "JOIN testing_bundles b ON b.id = r.bundle_id WHERE b.plan_id = ?", (row["id"],)).fetchall():
        ids = json.loads(r["evidence"] or "[]")
        if e["id"] in ids:
            ctx.conn.execute("UPDATE testing_results SET evidence = ? WHERE id = ?",
                             (json.dumps([i for i in ids if i != e["id"]]), r["id"]))
            released.append("{} · {}".format(r["proto"], r["test_id"]))
    ctx.conn.execute("DELETE FROM testing_evidence WHERE id = ?", (e["id"],))  # the stored files stay (content-addressed store)
    _plans()._log(ctx, "testing_evidence_deleted", row["id"], {"file": e["name"], "results": released})
    return {"ok": True, "results": released}


def api_file(ctx):
    """The current version, or an earlier one (?version=N), always as a download."""
    P = _plans()
    pid = P._pid(ctx)
    row = P._row(ctx, pid)
    e = _evidence(ctx, row)
    want = str(ctx.query.get("version") or "").strip()
    name, kind, link = e["name"], e["kind"], e["link"]
    att = ctx.conn.execute("SELECT * FROM attachments WHERE id = ? AND project_id = ?", (e["attachment_id"], pid)).fetchone()
    if want and want != str(e["version"]):
        old = next((h for h in json.loads(e["history"] or "[]") if str(h.get("version")) == want), None)
        if old is None:
            raise ApiError(404, "Version {} introuvable pour « {} ».".format(want[:10], e["name"]))
        name, kind, link = old.get("name") or name, old.get("kind") or "file", old.get("link") or ""
        att = ctx.conn.execute("SELECT * FROM attachments WHERE project_id = ? AND module = ? AND sha256 = ?",
                               (pid, MODULE, str(old.get("sha256") or ""))).fetchone()
    if kind == "link":
        raise ApiError(409, "« {} » n'est pas sur la plateforme. Correctif : ouvrez-le sur le réseau : {}".format(name, link))
    if att is None:
        raise ApiError(404, "Fichier de preuve absent du serveur. Correctif : restaurez data/attachments depuis la sauvegarde.")
    return RawFile(uploads.read(ctx.data_dir, att), name, att["mime"], export=False)


def on_restore(conn, maps, old_key, new_key):
    """Core lot v0.10 hook: a restored (or copied) Space renumbers its evidence; the results cite them by id (JSON)."""
    evidence = maps.get("testing_evidence", {})
    for rid in maps.get("testing_results", {}).values():
        row = conn.execute("SELECT evidence FROM testing_results WHERE id = ?", (rid,)).fetchone() if rid else None
        if row is None:
            continue
        ids = sorted({evidence[i] for i in json.loads(row["evidence"] or "[]") if evidence.get(i)})
        conn.execute("UPDATE testing_results SET evidence = ? WHERE id = ?", (json.dumps(ids), rid))
