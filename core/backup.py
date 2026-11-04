"""Project lifecycle for administrators (core lot v0.10, D-B-030):
archive, back up, restore, delete -- the usual order of Jira / Confluence /
GitLab: a project is archived (read-only, hidden) before it may be deleted,
deletion asks for the project key to be typed and always writes a backup
first, and a backup is restored as a NEW project (never over an existing one).

Backup file (.zip): manifest.json (format, versions, project, row counts,
SHA-256 of data.json), data.json (every row tied to the project, found by
following the foreign keys from projects(id) -- modules need no code for it),
attachments/ (the project's files). Restore re-numbers every row, keeps links
to accounts that still exist, and lets modules fix ids stored inside content
(hook on_restore(conn, maps, old_key, new_key)).
Backups written by the server live in data/backups/ (kept until deleted).
"""
import datetime as dt
import hashlib
import io
import json
import re
import shutil
import sqlite3
import zipfile
from pathlib import Path

from . import APP_VERSION, audit, db, modules, uploads, validate
from .errors import ApiError
from .files import RawFile

MIGRATIONS = [
    (9, """
        -- D-B-061: key of a deleted Space, never given to a new Space (EQP-1 would come back otherwise).
        CREATE TABLE retired_project_keys (
            key        TEXT PRIMARY KEY,
            name       TEXT NOT NULL DEFAULT '',
            retired_at TEXT NOT NULL,
            backup     TEXT NOT NULL DEFAULT ''
        );
    """),
]

FORMAT = "dynamite-project-backup"
FORMAT_VERSION = 1
SKIP = {"users", "sessions", "audit_log", "schema_migrations", "meta", "ui_audits", "user_prefs", "app_settings",
        "timesheet_weeks"}
NAME_RE = re.compile(r"^[A-Z0-9]{2,10}_\d{8}-\d{6}(_[a-z-]+)?\.zip$")
MAX_UPLOAD = 500 * 1024 * 1024


# --------------------------------------------------------------------------
# Schema walk
# --------------------------------------------------------------------------
def _tables(conn):
    names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                                        "AND sql NOT LIKE 'CREATE VIRTUAL%'")]
    info = {}
    for name in names:
        if name in SKIP or name == "projects" or "_fts" in name:
            continue
        cols = {r[1]: {"notnull": bool(r[3]), "pk": r[5], "default": r[4]} for r in conn.execute(f'PRAGMA table_info("{name}")')}
        fks = [(r[3], r[2], r[4]) for r in conn.execute(f'PRAGMA foreign_key_list("{name}")')]
        info[name] = {"cols": cols, "fks": fks}
    return info


def _order(info, present):
    """Parents before children (self references ignored)."""
    done, order = set(), []
    while len(order) < len(present):
        progressed = False
        for t in present:
            if t in done:
                continue
            parents = {p for _c, p, _pc in info[t]["fks"] if p in present and p != t}
            if parents <= done:
                done.add(t)
                order.append(t)
                progressed = True
        if not progressed:  # a cycle between tables: keep a stable order
            order += [t for t in present if t not in done]
            break
    return order


def collect(conn, project_id):
    info = _tables(conn)
    rows = {"projects": [dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())]}
    changed = True
    while changed:
        changed = False
        for t, meta in info.items():
            conds, params = [], []
            for col, parent, pcol in meta["fks"]:
                if parent in rows and parent != t:
                    values = sorted({r[pcol] for r in rows[parent] if r.get(pcol) is not None})
                    if values:
                        conds.append('"{}" IN ({})'.format(col, ",".join("?" * len(values))))
                        params += values
            if not conds:
                continue
            found = [dict(r) for r in conn.execute('SELECT rowid AS "__rowid", * FROM "{}" WHERE {}'.format(t, " OR ".join(conds)), params)]
            if len(found) != len(rows.get(t, [])):
                rows[t] = found
                changed = True
    return info, rows


# --------------------------------------------------------------------------
# Backup
# --------------------------------------------------------------------------
def build(ctx, project_id, reason=""):
    """(file name, bytes) of a backup of the project."""
    info, rows = collect(ctx.conn, project_id)
    project = rows["projects"][0]
    data = json.dumps({t: [{k: v for k, v in r.items() if k != "__rowid"} for r in rs] for t, rs in rows.items()},
                      ensure_ascii=False, default=str).encode("utf-8")
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    manifest = {"format": FORMAT, "format_version": FORMAT_VERSION, "app_version": APP_VERSION,
                "created_at": db.utc_now(), "created_by": ctx.user["display_name"] if "display_name" in ctx.user.keys() else "",
                "reason": reason, "project": {k: project[k] for k in ("id", "key", "name", "description")},
                "counts": {t: len(rs) for t, rs in rows.items()}, "sha256": hashlib.sha256(data).hexdigest(),
                "migrations": [list(r) for r in ctx.conn.execute("SELECT module, version FROM schema_migrations")]}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        z.writestr("data.json", data)
        for att in rows.get("attachments", []):
            path = uploads.file_path(ctx.data_dir, project_id, att["sha256"], att["mime"])
            if path.exists():
                z.write(path, "attachments/{}".format(path.name))
    name = "{}_{}{}.zip".format(project["key"], stamp, "_" + reason if reason else "")
    return name, buf.getvalue(), manifest


def _backup_dir(ctx):
    path = Path(ctx.data_dir) / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _project_id(ctx):
    project_id = validate.int_param(ctx.params, "pid")
    if not ctx.conn.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,)).fetchone():
        raise ApiError(404, "Projet introuvable.")
    return project_id


def api_backup(ctx):
    """Download a backup now; a copy is also kept on the server."""
    project_id = _project_id(ctx)
    name, data, manifest = build(ctx, project_id)
    (_backup_dir(ctx) / name).write_bytes(data)
    audit.log_action(ctx.conn, ctx.user["id"], "project_backup", "project", project_id,
                     {"file": name, "rows": sum(manifest["counts"].values())}, ctx.ip)
    return RawFile(data, name, "application/zip")


def api_impact(ctx):
    """What a deletion would remove (shown before the confirmation)."""
    project_id = _project_id(ctx)
    _info, rows = collect(ctx.conn, project_id)
    project = rows["projects"][0]
    return {"project": {k: project[k] for k in ("id", "key", "name", "is_archived")},
            "counts": {t: len(rs) for t, rs in rows.items() if t != "projects" and rs}}


# --------------------------------------------------------------------------
# Delete (archived projects only, key typed, backup first)
# --------------------------------------------------------------------------
def api_delete(ctx):
    project_id = _project_id(ctx)
    info, rows = collect(ctx.conn, project_id)
    project = rows["projects"][0]
    if not project["is_archived"]:
        raise ApiError(409, "Le projet {} n'est pas archivé. Correctif : archivez-le d'abord ; la suppression n'est "
                            "possible que depuis les projets archivés.".format(project["key"]))
    if str(ctx.body.get("confirm_key", "")).strip().upper() != project["key"]:
        raise ApiError(400, "Clé de confirmation incorrecte. Correctif : tapez exactement {} pour confirmer.".format(project["key"]))
    name, data, manifest = build(ctx, project_id, "avant-suppression")
    (_backup_dir(ctx) / name).write_bytes(data)
    order = _order(info, [t for t in rows if t != "projects"])
    for t in order:  # break self references, then delete children first
        for col, parent, _pc in info[t]["fks"]:
            if parent == t and rows[t]:
                ids = [r["__rowid"] for r in rows[t]]
                ctx.conn.execute('UPDATE "{}" SET "{}" = NULL WHERE rowid IN ({})'.format(t, col, ",".join("?" * len(ids))), ids)
    for t in reversed(order):
        ids = [r["__rowid"] for r in rows[t]]
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            ctx.conn.execute('DELETE FROM "{}" WHERE rowid IN ({})'.format(t, ",".join("?" * len(chunk))), chunk)
    ctx.conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    ctx.conn.execute("INSERT OR REPLACE INTO retired_project_keys (key, name, retired_at, backup) VALUES (?, ?, ?, ?)",
                     (project["key"], project["name"], db.utc_now(), name))
    folder = Path(ctx.data_dir) / "attachments" / str(project_id)
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
    audit.log_action(ctx.conn, ctx.user["id"], "project_deleted", "project", project_id,
                     {"key": project["key"], "backup": name, "rows": sum(manifest["counts"].values())}, ctx.ip)
    return {"ok": True, "backup": name}


# --------------------------------------------------------------------------
# Restore (always as a new project)
# --------------------------------------------------------------------------
def _read(data):
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        manifest = json.loads(z.read("manifest.json"))
        raw = z.read("data.json")
    except (zipfile.BadZipFile, KeyError, ValueError):
        raise ApiError(400, "Ce fichier n'est pas une sauvegarde de projet. Correctif : choisissez un .zip produit par "
                            "« Sauvegarder » (Administration → Projets).")
    if manifest.get("format") != FORMAT or manifest.get("format_version", 0) > FORMAT_VERSION:
        raise ApiError(400, "Format de sauvegarde inconnu ou plus récent que cette version de la plateforme.")
    if hashlib.sha256(raw).hexdigest() != manifest.get("sha256"):
        raise ApiError(400, "Sauvegarde corrompue (empreinte SHA-256 différente). Correctif : utilisez une autre copie.")
    return z, manifest, json.loads(raw)


def restore(ctx, data, key=None, name=None, skip_conflicts=False):
    """Restore a backup as a NEW project. skip_conflicts (restore points, D-B-104): a row that would break a uniqueness
    rule of the whole platform (e.g. a Generator number still in service) is left out and counted in « skipped »."""
    from .admin import PROJECT_KEY_RE
    z, manifest, tables = _read(data)
    old = tables["projects"][0]
    key = (key or old["key"]).strip().upper()
    if not PROJECT_KEY_RE.match(key):
        raise ApiError(400, "Clé « {} » invalide. Correctif : 2 à 10 lettres majuscules ou chiffres.".format(key))
    if ctx.conn.execute("SELECT 1 FROM projects WHERE key = ?", (key,)).fetchone():
        raise ApiError(409, "La clé {} existe déjà. Correctif : restaurez sous une autre clé (la restauration crée "
                            "toujours un nouveau projet).".format(key))
    if key != old["key"] and ctx.conn.execute("SELECT 1 FROM retired_project_keys WHERE key = ?", (key,)).fetchone():
        raise ApiError(409, "La clé {} a appartenu à un Space supprimé : elle n'est jamais réattribuée. Correctif : "
                            "choisissez une autre clé.".format(key))
    # the Space itself coming back under its own key keeps its ticket counter: nothing is reused
    ctx.conn.execute("DELETE FROM retired_project_keys WHERE key = ?", (key,))
    new_pid = ctx.conn.execute(
        "INSERT INTO projects (key, name, description, next_ticket_number, is_archived, created_at) VALUES (?, ?, ?, ?, 0, ?)",
        (key, (name or old["name"])[:100], old.get("description", ""), old.get("next_ticket_number", 1), db.utc_now())).lastrowid
    info = _tables(ctx.conn)
    present = [t for t in tables if t in info]
    maps = {"projects": {old["id"]: new_pid}}
    users = {r[0] for r in ctx.conn.execute("SELECT id FROM users")}
    later = []
    counts, skipped = {}, {}
    try:
        for t in _order(info, present):
            meta = info[t]
            cols = meta["cols"]
            pk_id = "id" in cols and cols["id"]["pk"] == 1 and sum(1 for c in cols.values() if c["pk"]) == 1
            maps.setdefault(t, {})
            for row in tables[t]:
                new = {k: v for k, v in row.items() if k in cols}
                old_id = new.pop("id", None) if pk_id else None
                self_refs = {}
                for col, parent, pcol in meta["fks"]:
                    value = new.get(col)
                    if value is None:
                        continue
                    if parent == t:
                        self_refs[col] = value
                        new[col] = None
                    elif parent in maps and value in maps[parent]:
                        new[col] = maps[parent][value]
                    elif parent == "users":
                        new[col] = value if value in users else None
                    elif parent in present or parent == "projects":
                        exists = ctx.conn.execute('SELECT 1 FROM "{}" WHERE "{}" = ?'.format(parent, pcol), (value,)).fetchone()
                        new[col] = value if exists else None
                if any(new.get(c) is None and (cols[c]["notnull"] or cols[c]["pk"]) and cols[c]["default"] is None
                       for c in new):
                    if pk_id:
                        maps[t][old_id] = None  # its children lose the link instead of pointing at another row
                    continue  # a link to something outside the backup that no longer exists
                names = list(new)
                try:
                    cur = ctx.conn.execute('INSERT INTO "{}" ({}) VALUES ({})'.format(
                        t, ",".join('"{}"'.format(c) for c in names), ",".join("?" * len(names))), [new[c] for c in names])
                except sqlite3.IntegrityError as exc:
                    if not (skip_conflicts and "UNIQUE" in str(exc)):
                        raise
                    skipped[t] = skipped.get(t, 0) + 1
                    if pk_id:
                        maps[t][old_id] = None
                    continue
                if pk_id:
                    maps[t][old_id] = cur.lastrowid
                if self_refs:
                    later.append((t, cur.lastrowid, self_refs))
                counts[t] = counts.get(t, 0) + 1
    except sqlite3.IntegrityError as exc:
        raise ApiError(409, "Restauration impossible : conflit dans la table {} ({}). Correctif : un élément unique sur "
                            "toute la plateforme (ex. numéro Generator) existe encore ; restaurez après suppression du "
                            "projet d'origine.".format(t, exc))
    for t, new_id, refs in later:
        sets = {c: maps[t].get(v) for c, v in refs.items()}
        ctx.conn.execute('UPDATE "{}" SET {} WHERE rowid = ?'.format(t, ", ".join('"{}" = ?'.format(c) for c in sets)),
                         list(sets.values()) + [new_id])
    files = 0
    for att in tables.get("attachments", []):
        member = "attachments/" + uploads.file_path(ctx.data_dir, 0, att["sha256"], att["mime"]).name  # PDFs too (D-B-104)
        if member in z.namelist():
            target = uploads.file_path(ctx.data_dir, new_pid, att["sha256"], att["mime"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(member))
            files += 1
    for _key, hook in modules.restore_hooks():
        hook(ctx.conn, maps, old["key"], key)
    audit.log_action(ctx.conn, ctx.user["id"], "project_restored", "project", new_pid,
                     {"from": old["key"], "key": key, "backup_of": manifest.get("created_at"), "rows": counts}, ctx.ip)
    return {"project": {"id": new_pid, "key": key}, "counts": counts, "skipped": skipped, "files": files}


@uploads.binary_body
def api_restore_upload(ctx):
    data = ctx.upload.data if ctx.upload else b""
    if not data:
        raise ApiError(400, "Aucun fichier reçu. Correctif : choisissez le .zip de sauvegarde.")
    return restore(ctx, data, ctx.query.get("key"), ctx.query.get("name"))


def _stored(ctx):
    name = ctx.params.get("name", "")
    if not NAME_RE.match(name):
        raise ApiError(400, "Nom de sauvegarde invalide.")
    path = _backup_dir(ctx) / name
    if not path.exists():
        raise ApiError(404, "Sauvegarde introuvable.")
    return path


def api_list(ctx):
    out = []
    for path in sorted(_backup_dir(ctx).glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
        if not NAME_RE.match(path.name):
            continue
        try:
            with zipfile.ZipFile(path) as z:
                m = json.loads(z.read("manifest.json"))
        except (zipfile.BadZipFile, KeyError, ValueError):
            continue
        out.append({"name": path.name, "size": path.stat().st_size, "project": m.get("project"), "created_at": m.get("created_at"),
                    "created_by": m.get("created_by"), "reason": m.get("reason", ""), "rows": sum(m.get("counts", {}).values()),
                    "app_version": m.get("app_version")})
    return {"backups": out}


def api_download(ctx):
    path = _stored(ctx)
    return RawFile(path.read_bytes(), path.name, "application/zip")


def api_restore_stored(ctx):
    path = _stored(ctx)
    return restore(ctx, path.read_bytes(), ctx.body.get("key"), ctx.body.get("name"))


def api_delete_backup(ctx):
    path = _stored(ctx)
    if str(ctx.body.get("confirm", "")) != path.name:
        raise ApiError(400, "Confirmation incorrecte. Correctif : renvoyez le nom exact du fichier.")
    path.unlink()
    audit.log_action(ctx.conn, ctx.user["id"], "backup_deleted", "backup", None, {"file": path.name}, ctx.ip)
    return {"ok": True}


P = r"/api/admin/projects/(?P<pid>\d+)"
B = r"/api/admin/backups/(?P<name>[A-Za-z0-9_.\-]+)"

ROUTES = [
    ("GET", P + r"/backup\.zip", api_backup, "admin"),
    ("GET", P + r"/impact", api_impact, "admin"),
    ("POST", P + r"/delete", api_delete, "admin"),
    ("GET", r"/api/admin/backups", api_list, "admin"),
    ("POST", r"/api/admin/restore", api_restore_upload, "admin"),
    ("GET", B, api_download, "admin"),
    ("POST", B + r"/restore", api_restore_stored, "admin"),
    ("POST", B + r"/delete", api_delete_backup, "admin"),
]
