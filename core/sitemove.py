"""Admin → Update → « Site complet » (core lot v0.26, D-B-094): move the whole site to another server, identically.

Export: one sealed zip (core/seal.py) with the code (code/...), an exact copy of the database (database.sqlite --
password hashes included so every account works as before; open sessions removed) and the files of data/
(attachments, Audit captures, Q&R archives). The server's own settings never travel: data/config.json, the TLS
certificates, the logs, the backups and the update history stay on each server.

Import, ONLY into an empty site (a fresh installation: no account other than the initial administrator), step by
step (core/update_review.py): content and seal, the framework (differences with the code in place, or « code
identique »), one step per Space (what it holds, per type), the accounts and administrators. All approved ->
« Appliquer »: backup of the code and database in place, code written, database and files replaced, restart.
The session of the person who applies ends: they log in again with an account of the moved site.
"""
import datetime as dt
import shutil
import sqlite3
import zipfile
from pathlib import Path

from . import APP_VERSION, audit, backup, datapack, db, permissions, seal, update
from . import update_review as review
from .errors import ApiError

FMT, LABEL, PREFIX = "dynamite-site-move", "Site complet", "move"
FILE_DIRS = ("attachments", "ui_audit", "qa_archives", "baselines")  # D-B-129: revisions travel with the site
CODE = "code/"


def _empty(conn):
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if users > 1:
        raise ApiError(409, "Ce site n'est pas vide ({} comptes) : « Site complet » ne s'importe que dans une nouvelle installation, "
                            "pour ne jamais écraser un site en service. Correctif : installez la plateforme sur le nouveau serveur, "
                            "connectez-vous avec l'admin initial et importez-y le paquet ; pour ajouter des Spaces à ce site, "
                            "utilisez le volet « Données ».".format(users))


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------
def _members(ctx, db_copy):
    root = update._cfg_root(ctx)
    for rel in update.code_files(root):
        yield CODE + rel, (root / rel).read_bytes()
    yield "database.sqlite", db_copy.read_bytes()
    for name in FILE_DIRS:
        base = Path(ctx.data_dir) / name
        for f in sorted(base.rglob("*")) if base.is_dir() else []:
            if f.is_file():
                yield "files/{}/{}".format(name, f.relative_to(base).as_posix()), f.read_bytes()


def api_export(ctx):
    permissions.require_admin(ctx.user)
    passphrase = seal.check_passphrase(ctx.body.get("passphrase"))
    seal.purge(ctx)
    exports = seal.folder(ctx, "exports")
    token = seal.new_token()
    db_copy = exports / (token + ".tmp.sqlite")
    update._snapshot_db(ctx, db_copy)
    conn = sqlite3.connect(str(db_copy))
    try:
        conn.execute("DELETE FROM sessions")  # an open session never travels
        conn.commit()
        conn.execute("VACUUM")
        counts = {"users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                  "spaces": [r[0] for r in conn.execute("SELECT key FROM projects ORDER BY key")]}
    finally:
        conn.close()
    name = "Dynamite_site_complet_v{}_{}.zip".format(APP_VERSION, dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    try:
        manifest = seal.write(exports / "{}.{}.{}".format(token, PREFIX, name), FMT, _members(ctx, db_copy), passphrase,
                              {"created_by": ctx.user["display_name"], "accounts": counts["users"], "spaces": counts["spaces"]})
    finally:
        db_copy.unlink()
    audit.log_action(ctx.conn, ctx.user["id"], "site_exported", "update", None,
                     {"version": APP_VERSION, "files": len(manifest["files"]), "spaces": len(counts["spaces"])}, ctx.ip)
    return {"token": token, "name": name, "accounts": counts["users"], "spaces": counts["spaces"]}


def api_download(ctx):
    permissions.require_admin(ctx.user)
    return seal.download_once(ctx, PREFIX)


# --------------------------------------------------------------------------
# Import: upload, open, steps
# --------------------------------------------------------------------------
def api_upload(ctx):
    permissions.require_admin(ctx.user)
    _empty(ctx.conn)
    token = seal.receive(ctx, PREFIX)
    audit.log_action(ctx.conn, ctx.user["id"], "site_received", "update", None, {"bytes": len(ctx.upload.data)}, ctx.ip)
    return {"token": token}


api_upload.accepts_binary = True
api_upload.transfer = True


def _code_files(z):
    return {i.filename[len(CODE):]: i for i in z.infolist() if i.filename.startswith(CODE) and not i.is_dir()}


def _code_report(ctx, z):
    root = update._cfg_root(ctx)
    files, current = _code_files(z), set(update.code_files(root))
    changed = sorted(r for r in files if r in current and z.read(files[r]) != (root / r).read_bytes())
    return {"zip": z, "files": files, "added": sorted(set(files) - current), "changed": changed,
            "removed": sorted(current - set(files))}


def _db_path(ctx, token):
    return seal.folder(ctx, "incoming") / "{}.move.sqlite".format(token)


def api_open(ctx):
    permissions.require_admin(ctx.user)
    _empty(ctx.conn)
    token = seal.clean_token(ctx.body.get("token"))
    z, manifest = seal.open_sealed(seal.incoming(ctx, token, PREFIX), ctx.body.get("passphrase"), FMT, LABEL)
    target = _db_path(ctx, token)
    target.write_bytes(z.read("database.sqlite"))
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    try:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ApiError(400, "La base du paquet est endommagée (integrity_check). Correctif : refaites l'export.")
        spaces = []
        for p in conn.execute("SELECT id, key, name FROM projects ORDER BY key").fetchall():
            _info, rows = backup.collect(conn, p["id"])
            spaces.append({"key": p["key"], "name": p["name"], "counts": datapack._counts(rows)})
        accounts = [dict(r) for r in conn.execute("SELECT username, display_name, is_admin, is_active FROM users ORDER BY username")]
        version = (conn.execute("SELECT MAX(version) FROM schema_migrations WHERE module = 'core'").fetchone()[0])
    finally:
        conn.close()
    code = _code_report(ctx, z)
    touched = [{"path": f, "state": s} for s, items in (("added", code["added"]), ("changed", code["changed"]),
                                                          ("removed", code["removed"])) for f in items]
    steps = [{"id": "content", "title": "Contenu et sceau", "kind": "info",
              "why": "Site exporté le {} par {} (version {}, migration core {}) : {} Space(s), {} compte(s), {} fichier(s). "
                     "Sceau vérifié : rien n'a changé depuis l'export.".format(
                         (manifest.get("created_at") or "")[:16].replace("T", " "), manifest.get("created_by"),
                         manifest.get("app_version"), version, len(spaces), len(accounts), len(manifest.get("files", {})))},
             {"id": "framework", "title": "Framework : " + ("{} fichier(s) différent(s)".format(len(touched)) if touched
                                                             else "code identique"), "kind": "code", "files": touched,
              "why": ("Le code du paquet (version {}) remplacera celui en place (version {}). Lisez les différences."
                      .format(manifest.get("app_version"), APP_VERSION) if touched else
                      "Le code du paquet est identique au code en place : rien ne change.")}]
    for sp in spaces:
        steps.append({"id": "space-" + sp["key"], "title": "Space {} — {}".format(sp["key"], sp["name"]), "kind": "space",
                      "space": sp["key"], "counts": sp["counts"], "count": sum(sp["counts"].values()),
                      "why": "Repris à l'identique (mêmes clés, mêmes numéros, mêmes droits)."})
    admins = [a["username"] for a in accounts if a["is_admin"]]
    steps.append({"id": "accounts", "title": "Comptes et administrateurs", "kind": "accounts", "count": len(accounts),
                  "why": "{} compte(s) avec leurs mots de passe actuels ; administrateurs : {}. Le compte d'installation de ce "
                         "serveur disparaît et votre session se ferme : reconnectez-vous avec un compte du site déménagé."
                         .format(len(accounts), ", ".join(admins) or "aucun"),
                  "new": [a["username"] for a in accounts], "same": []})
    for n, s in enumerate(steps, 1):
        s.setdefault("files", [])
        s.update(n=n, status="pending", seen_by=[], by=None, at=None, comment="")
    state = review.create(seal.folder(ctx, "incoming"), token, manifest.get("app_version"), APP_VERSION, steps, kind=PREFIX)
    audit.log_action(ctx.conn, ctx.user["id"], "site_opened", "update", None,
                     {"version": manifest.get("app_version"), "spaces": len(spaces), "accounts": len(accounts)}, ctx.ip)
    return review.summary(state)


def _state(ctx):
    token = seal.clean_token(ctx.params.get("token"))
    path = seal.incoming(ctx, token, PREFIX)
    folder = seal.folder(ctx, "incoming")
    return folder, review.load(folder, token), path


def api_review(ctx):
    permissions.require_admin(ctx.user)
    return review.summary(_state(ctx)[1])


def api_review_step(ctx):
    permissions.require_admin(ctx.user)
    folder, state, path = _state(ctx)
    step = review.step_of(state, ctx.params["n"])
    files = []
    if step["kind"] == "code" and step["files"]:
        z = zipfile.ZipFile(path)
        files = review.framework_detail(step, update._cfg_root(ctx), z, _code_files(z))
    review.mark_seen(state, step, ctx.user)
    review.save(folder, state)
    labels = {k: label for k, label, _p in datapack.TYPES}
    labels["core"] = "Noyau (membres, pièces jointes, @mentions)"
    return {"step": {k: step.get(k) for k in ("n", "id", "title", "why", "kind", "status", "by", "at", "comment", "counts",
                                             "new", "same", "space")}, "files": files, "types": labels, "total": len(state["steps"])}


def api_review_decide(ctx):
    permissions.require_admin(ctx.user)
    folder, state, _path = _state(ctx)
    return review.decide(ctx, folder, state, ctx.params["n"], ctx.body.get("decision"), ctx.body.get("comment"))


# --------------------------------------------------------------------------
# Apply
# --------------------------------------------------------------------------
def api_apply(ctx):
    permissions.require_admin(ctx.user)
    folder, state, path = _state(ctx)
    review.require_ready(state)
    _empty(ctx.conn)
    data_dir, root = Path(ctx.data_dir), update._cfg_root(ctx)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backups = seal.folder(ctx, "backups")
    code_backup = backups / "code_v{}_{}.zip".format(APP_VERSION, stamp)
    code_backup.write_bytes(update._zip_code(root))
    db_backup = backups / "db_v{}_{}.sqlite".format(APP_VERSION, stamp)
    update._snapshot_db(ctx, db_backup)
    z = zipfile.ZipFile(path)
    code = _code_report(ctx, z)
    if code["added"] or code["changed"] or code["removed"]:
        update._write(root, code)
    for name in FILE_DIRS:  # files of the empty site kept aside, then the moved ones
        current = data_dir / name
        if current.exists():
            shutil.move(str(current), str(backups / "{}_{}".format(name, stamp)))
    for info in z.infolist():
        if info.filename.startswith("files/") and not info.is_dir():
            rel = info.filename[len("files/"):]
            if ".." in rel.split("/") or "\\" in rel or rel.split("/")[0] not in FILE_DIRS:
                continue
            target = data_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(info))
    who = ctx.user["display_name"]
    ctx.conn.commit()
    src = sqlite3.connect(str(_db_path(ctx, state["token"])))
    try:
        src.backup(ctx.conn)  # the whole database replaced, page by page, in the live file
    finally:
        src.close()
    audit.log_action(ctx.conn, None, "site_imported", "update", None,
                     {"by": who, "version": state.get("version"), "code_backup": code_backup.name, "db_backup": db_backup.name}, ctx.ip)
    history = update._history(ctx)
    history.append({"version": state.get("version"), "from": APP_VERSION, "applied_at": db.utc_now(), "by": who,
                    "action": "site_move", "code_backup": code_backup.name, "db_backup": db_backup.name,
                    "log": "Déménagement : site complet importé.", "added": len(code["added"]),
                    "changed": len(code["changed"]), "removed": len(code["removed"])})
    update._save_history(ctx, history)
    review.close(folder, state)
    z.close()
    path.unlink()
    _db_path(ctx, state["token"]).unlink()
    return {"ok": True, "version": state.get("version"), "backup": code_backup.name, "db_backup": db_backup.name,
            "restarting": update._restart(ctx)}


ROUTES = [
    ("POST", r"/api/site/export", api_export, "admin"),
    ("GET", r"/api/site/export/(?P<token>[a-f0-9]{32})", api_download, "admin"),
    ("POST", r"/api/site/upload", api_upload, "admin"),
    ("POST", r"/api/site/open", api_open, "admin"),
    ("GET", r"/api/site/review/(?P<token>[a-f0-9]{32})", api_review, "admin"),
    ("GET", r"/api/site/review/(?P<token>[a-f0-9]{32})/(?P<n>\d+)", api_review_step, "admin"),
    ("POST", r"/api/site/review/(?P<token>[a-f0-9]{32})/(?P<n>\d+)", api_review_decide, "admin"),
    ("POST", r"/api/site/apply/(?P<token>[a-f0-9]{32})", api_apply, "admin"),
]
