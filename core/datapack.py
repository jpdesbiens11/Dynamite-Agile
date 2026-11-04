"""Admin → Update → « Données » (core lot v0.26, D-B-094): the data of the site, apart from its framework (code).

Export: a sealed zip (core/seal.py) with the accounts WITHOUT their passwords (accounts.json), one file per Space
with every row tied to it (spaces/<KEY>.json, found by following the foreign keys like core/backup.py) and the
Space's attachments (attachments/<KEY>/...). All the Spaces or a selection. Data that belongs to no Space
(preferences, objectives, Timesheet weeks, Audit) only travels with « Site complet » (core/sitemove.py).

Import, step by step (core/update_review.py), nothing written before the last approval:
  1. Contenu du paquet -- source, date, author; refused if the file comes from a newer schema than this site.
  2. Comptes -- recognised by their username; a missing one is created with a temporary password (never admin);
     an existing one is never modified.
  3. One step per Space -- an existing Space is NEVER overwritten: skip it, or import it as a NEW Space under
     another key, with the types ticked (Dynamite, Agile, Goldmine, Testing, Exploration...).
Applied in one transaction (all or nothing), journalled; links to rows that were not imported are emptied.
"""
import json
import re
import sqlite3
import zipfile

from . import APP_VERSION, audit, auth, backup, db, modules, permissions, restorepoints, seal, uploads
from . import update_review as review
from .errors import ApiError

FMT, LABEL, PREFIX = "dynamite-site-data", "Données", "data"
TYPES = [  # (key, label, table matcher) -- first match wins; « core » is always imported
    ("dynamite", "Dynamite (pages, versions, commentaires)", r"^dynamite_"),
    ("goldmine", "Goldmine (Requirements, Q&R, Pugh)", r"^(agile_requirements|goldmine_)"),
    ("agile", "Agile (tickets, Sprints, Change Management)", r"^agile_"),
    ("testing", "Testing (essais, listes, plans)", r"^testing_"),
    ("exploration", "Exploration (Gantt)", r"^exploration_"),
    ("tools", "Tools (idéation, Kepner-Tregoe)", r"^tools_"),
    ("training", "Training", r"^training_"),
    ("codex", "Generator (références)", r"^codex_"),
    ("timesheet", "Timesheet", r"^timesheet_"),
]
SECRET_USER_COLS = {"password_hash", "must_change_password"}
# Hours belong to each person's weeks (timesheet_weeks, outside any Space): copying them into a new Space would count
# them twice. They travel only with « Site complet ».
SITE_ONLY = {"timesheet": "Timesheet — ne voyage qu'avec « Site complet » (heures liées aux semaines de chaque personne)"}


def type_of(table):
    for key, _label, pattern in TYPES:
        if re.match(pattern, table):
            return key
    return "core"


def _counts(tables):
    out = {}
    for t, rows in tables.items():
        if t != "projects" and rows:
            k = type_of(t)
            out[k] = out.get(k, 0) + len(rows)
    return out


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------
def _accounts(conn):
    return [{k: r[k] for k in r.keys() if k not in SECRET_USER_COLS} for r in conn.execute("SELECT * FROM users ORDER BY id")]


def _members(ctx, projects):
    yield "accounts.json", json.dumps(_accounts(ctx.conn), ensure_ascii=False).encode("utf-8")
    for p in projects:
        _info, rows = backup.collect(ctx.conn, p["id"])
        yield "spaces/{}.json".format(p["key"]), json.dumps(
            {t: [{k: v for k, v in r.items() if k != "__rowid"} for r in rs] for t, rs in rows.items()},
            ensure_ascii=False, default=str).encode("utf-8")
        for att in rows.get("attachments", []):
            path = uploads.file_path(ctx.data_dir, p["id"], att["sha256"], att["mime"])
            if path.exists():
                yield "attachments/{}/{}".format(p["key"], path.name), path.read_bytes()


def api_export(ctx):
    permissions.require_admin(ctx.user)
    passphrase = seal.check_passphrase(ctx.body.get("passphrase"))
    seal.purge(ctx)
    wanted = {str(k).upper() for k in (ctx.body.get("spaces") or [])}
    projects = [dict(r) for r in ctx.conn.execute("SELECT id, key, name, description FROM projects ORDER BY key")]
    if wanted:
        unknown = sorted(wanted - {p["key"] for p in projects})
        if unknown:
            raise ApiError(400, "Space(s) inconnu(s) : {}. Correctif : cochez des Spaces de la liste.".format(", ".join(unknown)))
        projects = [p for p in projects if p["key"] in wanted]
    token = seal.new_token()
    stamp = db.utc_now()[:16].replace(":", "").replace("-", "").replace("T", "-")
    name = "Dynamite_donnees_{}.zip".format(stamp)
    spaces = []
    for p in projects:
        _info, rows = backup.collect(ctx.conn, p["id"])
        spaces.append({"key": p["key"], "name": p["name"], "counts": _counts(rows)})
    manifest = seal.write(seal.folder(ctx, "exports") / "{}.{}.{}".format(token, PREFIX, name), FMT, _members(ctx, projects),
                          passphrase, {"created_by": ctx.user["display_name"], "spaces": spaces,
                                       "accounts": ctx.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                                       "migrations": [list(r) for r in ctx.conn.execute("SELECT module, version FROM schema_migrations")]})
    audit.log_action(ctx.conn, ctx.user["id"], "data_exported", "update", None,
                     {"spaces": [s["key"] for s in spaces], "files": len(manifest["files"])}, ctx.ip)
    return {"token": token, "name": name, "spaces": spaces}


def api_download(ctx):
    permissions.require_admin(ctx.user)
    return seal.download_once(ctx, PREFIX)


# --------------------------------------------------------------------------
# Import: upload, open (seal), steps
# --------------------------------------------------------------------------
def api_upload(ctx):
    permissions.require_admin(ctx.user)
    token = seal.receive(ctx, PREFIX)
    audit.log_action(ctx.conn, ctx.user["id"], "data_received", "update", None, {"bytes": len(ctx.upload.data)}, ctx.ip)
    return {"token": token}


api_upload.accepts_binary = True
api_upload.transfer = True


def _read(z, name):
    return json.loads(z.read(name).decode("utf-8"))


def free_key(conn, key, taken=()):
    """First key derived from `key` that is free here (never a retired key): EQP -> EQP2, EQP3..."""
    base = re.sub(r"[^A-Z0-9]", "", key.upper())[:8] or "SP"
    for n in range(1, 100):
        cand = base if n == 1 else "{}{}".format(base, n)
        if (cand not in taken and not conn.execute("SELECT 1 FROM projects WHERE key = ?", (cand,)).fetchone()
                and not conn.execute("SELECT 1 FROM retired_project_keys WHERE key = ?", (cand,)).fetchone()):
            return cand
    raise ApiError(409, "Aucune clé libre pour {}.".format(key))


def newer_schema(conn, manifest):
    here = {(m, v) for m, v in conn.execute("SELECT module, version FROM schema_migrations")}
    return sorted("{} {}".format(m, v) for m, v in (tuple(x) for x in manifest.get("migrations", [])) if (m, v) not in here)


def api_open(ctx):
    permissions.require_admin(ctx.user)
    token = seal.clean_token(ctx.body.get("token"))
    path = seal.incoming(ctx, token, PREFIX)
    z, manifest = seal.open_sealed(path, ctx.body.get("passphrase"), FMT, LABEL)
    missing = newer_schema(ctx.conn, manifest)
    if missing:
        raise ApiError(409, "Paquet exporté par la version {} : ce site ({}) n'a pas encore les migrations {}. Correctif : "
                            "mettez d'abord le Framework à jour (volet Framework), puis importez les données.".format(
                                manifest.get("app_version"), APP_VERSION, ", ".join(missing[:6])))
    accounts = _read(z, "accounts.json")
    existing = {r["username"].lower() for r in ctx.conn.execute("SELECT username FROM users")}
    new_accounts = [a["username"] for a in accounts if a["username"].lower() not in existing]
    steps = [{"id": "content", "title": "Contenu du paquet", "kind": "info",
              "why": "Exporté le {} par {} depuis la version {} : {} Space(s), {} compte(s). Sceau vérifié.".format(
                  (manifest.get("created_at") or "")[:16].replace("T", " "), manifest.get("created_by"), manifest.get("app_version"),
                  len(manifest.get("spaces", [])), len(accounts))},
             {"id": "accounts", "title": "Comptes", "kind": "accounts", "count": len(new_accounts),
              "why": "{} compte(s) à créer (mot de passe temporaire, changement obligatoire, jamais administrateur) ; {} déjà "
                     "présent(s), reconnus par leur identifiant et jamais modifiés.".format(len(new_accounts), len(accounts) - len(new_accounts)),
              "new": new_accounts, "same": [a["username"] for a in accounts if a["username"].lower() in existing]}]
    taken = set()
    for sp in manifest.get("spaces", []):
        exists = bool(ctx.conn.execute("SELECT 1 FROM projects WHERE key = ?", (sp["key"],)).fetchone())
        key = free_key(ctx.conn, sp["key"], taken)
        taken.add(key)
        steps.append({"id": "space-" + sp["key"], "title": "Space {} — {}".format(sp["key"], sp["name"]), "kind": "space",
                      "space": sp["key"], "exists": exists, "counts": sp.get("counts", {}), "count": sum(sp.get("counts", {}).values()),
                      "why": ("Ce Space existe déjà ici : il ne sera jamais écrasé. Sautez-le, ou importez-le comme nouveau Space "
                              "sous une autre clé." if exists else "Nouveau Space sur ce site."),
                      "options": {"action": "skip" if exists else "new", "key": key,
                                  "types": [k for k in sp.get("counts", {}) if k != "core" and k not in SITE_ONLY]}})
    for n, s in enumerate(steps, 1):
        s.update(n=n, status="pending", seen_by=[], by=None, at=None, comment="", files=[])
    state = review.create(seal.folder(ctx, "incoming"), token, manifest.get("app_version"), None, steps, kind=PREFIX,
                          extra={"sha_manifest": manifest.get("created_at")})
    audit.log_action(ctx.conn, ctx.user["id"], "data_opened", "update", None, {"spaces": len(steps) - 2}, ctx.ip)
    return review.summary(state)


def _state(ctx):
    token = seal.clean_token(ctx.params.get("token"))
    seal.incoming(ctx, token, PREFIX)
    folder = seal.folder(ctx, "incoming")
    return folder, review.load(folder, token)


def api_review(ctx):
    permissions.require_admin(ctx.user)
    return review.summary(_state(ctx)[1])


def api_review_step(ctx):
    permissions.require_admin(ctx.user)
    folder, state = _state(ctx)
    step = review.step_of(state, ctx.params["n"])
    review.mark_seen(state, step, ctx.user)
    review.save(folder, state)
    labels = dict((k, label) for k, label, _p in TYPES)
    labels["core"] = "Noyau (membres, pièces jointes, @mentions) — toujours importé"
    labels.update(SITE_ONLY)
    return {"step": {k: step.get(k) for k in ("n", "id", "title", "why", "kind", "status", "by", "at", "comment", "options",
                                             "counts", "exists", "new", "same", "space")},
            "types": labels, "fixed": sorted(SITE_ONLY), "total": len(state["steps"])}


def _check_options(ctx, state, step, options):
    if step["kind"] != "space":
        return None
    options = options or {}
    action = options.get("action")
    if action == "skip":
        return {"action": "skip", "key": step["options"]["key"], "types": []}
    if action != "new":
        raise ApiError(400, "Choix « {} » inconnu pour le Space {} (acceptés : skip, new).".format(action, step["space"]))
    key = str(options.get("key") or "").strip().upper()
    from .admin import PROJECT_KEY_RE
    if not PROJECT_KEY_RE.match(key):
        raise ApiError(400, "Clé « {} » invalide. Correctif : 2 à 10 lettres majuscules ou chiffres, une lettre d'abord.".format(key))
    if ctx.conn.execute("SELECT 1 FROM projects WHERE key = ?", (key,)).fetchone():
        raise ApiError(409, "La clé {} existe déjà ici : un Space en service n'est jamais écrasé. Correctif : proposez {}.".format(
            key, free_key(ctx.conn, key)))
    if ctx.conn.execute("SELECT 1 FROM retired_project_keys WHERE key = ?", (key,)).fetchone():
        raise ApiError(409, "La clé {} a appartenu à un Space supprimé et n'est jamais réattribuée. Correctif : choisissez {}.".format(
            key, free_key(ctx.conn, key)))
    others = [s["options"]["key"] for s in state["steps"] if s["kind"] == "space" and s is not step
              and s["status"] == "approved" and s["options"]["action"] == "new"]
    if key in others:
        raise ApiError(409, "La clé {} est déjà choisie pour un autre Space de cet import.".format(key))
    known = {k for k, _l, _p in TYPES}
    types = [t for t in options.get("types") or [] if t in known and t not in SITE_ONLY]
    return {"action": "new", "key": key, "types": types}


def api_review_decide(ctx):
    permissions.require_admin(ctx.user)
    folder, state = _state(ctx)
    step = review.step_of(state, ctx.params["n"])
    options = _check_options(ctx, state, step, ctx.body.get("options")) if ctx.body.get("decision") == "approve" else None
    return review.decide(ctx, folder, state, ctx.params["n"], ctx.body.get("decision"), ctx.body.get("comment"), options)


# --------------------------------------------------------------------------
# Apply (one transaction)
# --------------------------------------------------------------------------
def _insert_space(ctx, z, tables, info, maps, user_map, key, types):
    old = tables["projects"][0]
    pid = ctx.conn.execute("INSERT INTO projects (key, name, description, next_ticket_number, is_archived, created_at) "
                           "VALUES (?, ?, ?, ?, ?, ?)", (key, old["name"][:100], old.get("description", ""),
                                                         old.get("next_ticket_number", 1), old.get("is_archived", 0), db.utc_now())).lastrowid
    maps.setdefault("projects", {})[old["id"]] = pid
    keep = [t for t in tables if t in info and (type_of(t) == "core" or type_of(t) in types)]
    counts, lost, later = {}, {}, []
    for t in backup._order(info, keep):
        cols = info[t]["cols"]
        pk_id = "id" in cols and cols["id"]["pk"] == 1 and sum(1 for c in cols.values() if c["pk"]) == 1
        maps.setdefault(t, {})
        for row in tables[t]:
            new = {k: v for k, v in row.items() if k in cols}
            old_id = new.pop("id", None) if pk_id else None
            refs = {}
            for col, parent, _pcol in info[t]["fks"]:
                value = new.get(col)
                if value is None:
                    continue
                if parent == t:
                    refs[col], new[col] = value, None
                    continue  # set once every row of the table exists
                elif parent == "users":
                    new[col] = user_map.get(value)
                else:
                    new[col] = maps.get(parent, {}).get(value)
                if new[col] is None:
                    lost[t + "." + col] = lost.get(t + "." + col, 0) + 1
            if any(new.get(c) is None and (cols[c]["notnull"] or cols[c]["pk"]) and cols[c]["default"] is None for c in new):
                continue  # tied to something that was not imported
            names = list(new)
            cur = ctx.conn.execute('INSERT INTO "{}" ({}) VALUES ({})'.format(
                t, ",".join('"{}"'.format(c) for c in names), ",".join("?" * len(names))), [new[c] for c in names])
            if pk_id:
                maps[t][old_id] = cur.lastrowid
            if refs:
                later.append((t, cur.lastrowid, refs))
            counts[type_of(t)] = counts.get(type_of(t), 0) + 1
    for t, new_id, refs in later:
        sets = {c: maps[t].get(v) for c, v in refs.items()}
        ctx.conn.execute('UPDATE "{}" SET {} WHERE rowid = ?'.format(t, ", ".join('"{}" = ?'.format(c) for c in sets)),
                         list(sets.values()) + [new_id])
    names = set(z.namelist())
    for att in tables.get("attachments", []):
        if att.get("id") not in maps.get("attachments", {}):
            continue
        target = uploads.file_path(ctx.data_dir, pid, att["sha256"], att["mime"])
        member = "attachments/{}/{}".format(old["key"], target.name)
        if member in names:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(member))
    for _key, hook in modules.restore_hooks():
        hook(ctx.conn, maps, old["key"], key)
    return pid, counts, lost


def api_apply(ctx):
    permissions.require_admin(ctx.user)
    folder, state = _state(ctx)
    review.require_ready(state)
    path = seal.incoming(ctx, state["token"], PREFIX)
    point = restorepoints.before(ctx, "avant-import")  # D-B-104
    z = zipfile.ZipFile(path)  # the seal was checked at opening; the file has not left data/
    user_map, created = {}, []
    for a in _read(z, "accounts.json"):
        row = ctx.conn.execute("SELECT id FROM users WHERE username = ?", (a["username"],)).fetchone()
        if row:
            user_map[a["id"]] = row["id"]
            continue
        temp = auth.generate_temp_password()
        cols = {r[1] for r in ctx.conn.execute("PRAGMA table_info(users)")}
        values = {k: v for k, v in a.items() if k in cols and k not in ("id", "is_admin") and k not in SECRET_USER_COLS}
        values.update(password_hash=auth.hash_password(temp), must_change_password=1, is_admin=0,
                      created_at=values.get("created_at") or db.utc_now())
        user_map[a["id"]] = ctx.conn.execute('INSERT INTO users ({}) VALUES ({})'.format(
            ",".join('"{}"'.format(k) for k in values), ",".join("?" * len(values))), list(values.values())).lastrowid
        created.append({"username": a["username"], "temp_password": temp})
    info, maps, done = backup._tables(ctx.conn), {}, []
    try:
        for step in state["steps"]:
            if step["kind"] != "space" or step["options"]["action"] != "new":
                continue
            tables = _read(z, "spaces/{}.json".format(step["space"]))
            pid, counts, lost = _insert_space(ctx, z, tables, info, maps, user_map, step["options"]["key"], step["options"]["types"])
            done.append({"from": step["space"], "key": step["options"]["key"], "id": pid, "counts": counts,
                         "lost_links": sum(lost.values()), "lost_detail": lost})
    except sqlite3.IntegrityError as exc:
        raise ApiError(409, "Import annulé, rien n'a été écrit : conflit dans le Space {} ({}). Correctif : un élément unique sur "
                            "toute la plateforme (ex. numéro Generator) existe déjà ici ; décochez ce type pour ce Space.".format(
                                step["space"], exc))
    review.close(folder, state)
    audit.log_action(ctx.conn, ctx.user["id"], "data_imported", "update", None,
                     {"spaces": [{k: d[k] for k in ("from", "key", "counts")} for d in done],
                      "accounts_created": [c["username"] for c in created]}, ctx.ip)
    z.close()
    path.unlink()
    return {"ok": True, "spaces": done, "created": created, "point": point["name"]}


ROUTES = [
    ("POST", r"/api/data/export", api_export, "admin"),
    ("GET", r"/api/data/export/(?P<token>[a-f0-9]{32})", api_download, "admin"),
    ("POST", r"/api/data/upload", api_upload, "admin"),
    ("POST", r"/api/data/open", api_open, "admin"),
    ("GET", r"/api/data/review/(?P<token>[a-f0-9]{32})", api_review, "admin"),
    ("GET", r"/api/data/review/(?P<token>[a-f0-9]{32})/(?P<n>\d+)", api_review_step, "admin"),
    ("POST", r"/api/data/review/(?P<token>[a-f0-9]{32})/(?P<n>\d+)", api_review_decide, "admin"),
    ("POST", r"/api/data/apply/(?P<token>[a-f0-9]{32})", api_apply, "admin"),
]
