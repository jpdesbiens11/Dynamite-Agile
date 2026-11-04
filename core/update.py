"""Admin → Update (core lot v0.21, D-A-049): update the CODE of the site online, never its data.

1. Export: one zip with the code only (no data/), the starting prompt for Claude (Opus 5.5 or later), the context
   of the installation (version, modules, applied migrations, row counts -- no content) and the database structure.
2. Claude works on it (FONDATIONS instructions + the prompt) and returns a zip of the code, same structure.
3. Import, in two steps: « Vérifier » (structure, higher version, Python syntax of every file, no DROP of table or
   column, no data/) then « Appliquer »: automatic backup of the current code AND a restore point of the data
   (core/restorepoints.py), new code written over the old one (data/ is never touched), service restarted. The
   migrations of the new code run at start-up: they only add (tables, columns), so everything entered by hand is kept.
4. « Revenir à cette version »: the code backup of any previous update, same mechanism. D-B-104: the 3 most recent
   copies of the code are kept (Admin → Update et sauvegardes → Restaurer, with the 3 restore points of the data).
Every step is journalled; the history keeps the log of each import (UPDATE_LOG.md of the zip).
"""
import datetime as dt
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
import threading
import zipfile
from pathlib import Path

from . import APP_VERSION, audit, db, permissions, restorepoints
from . import update_review as review
from .errors import ApiError
from .files import RawFile

BASE = Path(__file__).resolve().parent.parent
ROOT = "Dynamite_Agile"
CODE_DIRS = ("core", "modules", "static", "tools", "tests", "deploy", "docs", ".claude")  # .claude: shared skills (D-B-093)
TOP_FILES = re.compile(r"^[A-Za-z0-9_.-]+\.(py|md|txt|bat|sh|cfg|toml)$|^\.gitignore$")
SKIP = re.compile(r"(^|/)(__pycache__|\.git|data)(/|$)|\.(pyc|pyo|db|sqlite|db-wal|db-shm)$"
                  r"|^\.claude/settings\.local\.json$")  # personal Claude Code settings never travel
MAX_ZIP_MB = 60
DESTRUCTIVE = re.compile(r"\bDROP\s+(TABLE|COLUMN)\b|\bDELETE\s+FROM\s+(users|projects|memberships)\b", re.IGNORECASE)
MIN_CLAUDE = "Claude Opus 5.5"

PROMPT = """# Mise à jour du site Dynamite | Agile — prompt de départ

**Modèle requis : {min_claude} ou plus récent.** Joindre à la conversation : ce zip, le fichier des instructions du
projet (FONDATIONS) et, s'il existe, le dernier UPDATE_LOG.md.

Travaille en **mode verbose** : annonce chaque étape, chaque fichier modifié et pourquoi, les tests lancés et leur
résultat, et pose une question à la fois si une demande est ambiguë.

## Contexte
- Version en ligne : **{version}** (exportée le {date} par {who}).
- Le zip contient le **code seulement** : `{root}/` (core, modules, static, tools, tests, deploy, docs, .claude). Les
  données (`data/`) restent sur le serveur ; `UPDATE_CONTEXT.json` et `SCHEMA.sql` décrivent la base sans son contenu.
- Pour tout écran ou style : suivre la skill `.claude/skills/dynamite-design/SKILL.md` (après FONDATIONS).

## Règles de la mise à jour (non négociables)
1. **Ne jamais perdre une donnée saisie** : les migrations ajoutent (tables, colonnes, valeurs par défaut) ; jamais de
   `DROP TABLE`, `DROP COLUMN` ni d'effacement de données. Un champ retiré de l'affichage reste dans la base.
2. Un champ ou une fonction **nouveaux** portent l'attribut `data-new="<version>-<clé>"` sur leur champ (input, select,
   textarea) ou leur bouton / onglet : la plateforme affiche **[new]** jusqu'à ce que le champ soit rempli ou la
   fonction utilisée.
3. Augmenter `APP_VERSION` (core/__init__.py) ; mettre à jour `docs/ETAT_PROJET.md`, `docs/DECISIONS.md`, `CLAUDE.md`.
4. Écrire `UPDATE_LOG.md` à la racine du zip : version, date, liste des changements, migrations ajoutées, champs
   [new], tests passés. Ce journal est gardé par le site et renvoyé au prochain export.
4b. Écrire `UPDATE_CHANGES.json` à la racine du zip : `{{"changes": [{{"id": "C1", "title": "…", "why": "…",
   "files": ["chemin/relatif", …]}}]}}` — un changement par sujet, en français (termes techniques en anglais), et
   **chaque fichier ajouté, modifié ou retiré dans au moins un changement**. L'administrateur revoit et approuve chaque
   changement un par un (Admin → Update, revue pas à pas) ; un fichier non déclaré est signalé et souvent refusé.
   S'il joint un « Retour de revue », corriger ce qui a été refusé et garder ce qui a été approuvé.
5. Bibliothèque standard Python seulement ; fichiers < 500 lignes ; tous les tests passent
   (`python -m unittest discover -s tests -t .`).
6. Rendre **un zip du code, même structure** (`{root}/...`, sans `data/`) : il sera importé dans Admin → Update.

## Demande de mise à jour
(Écrire ici ce qu'il faut changer.)

## Dernier journal de mise à jour
{last_log}
"""


def _cfg_root(ctx):
    return Path(ctx.config.get("code_root") or BASE)


def _dir(ctx, name):
    path = Path(ctx.data_dir) / "updates" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _log(ctx, action, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "update", None, details, ctx.ip)


def _version_tuple(text):
    return tuple(int(x) for x in re.findall(r"\d+", text or "0")[:3])


def _history(ctx):
    path = Path(ctx.data_dir) / "updates" / "history.json"
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return []


def _save_history(ctx, items):
    (Path(ctx.data_dir) / "updates").mkdir(parents=True, exist_ok=True)
    (Path(ctx.data_dir) / "updates" / "history.json").write_text(json.dumps(items[-50:], ensure_ascii=False, indent=1), "utf-8")


def code_files(root):
    """Relative paths of the code under `root` (what an update may replace)."""
    out = []
    for f in sorted(root.iterdir()):
        if f.is_file() and TOP_FILES.match(f.name):
            out.append(f.name)
    for d in CODE_DIRS:
        for f in sorted((root / d).rglob("*")) if (root / d).exists() else []:
            rel = f.relative_to(root).as_posix()
            if f.is_file() and not SKIP.search(rel):
                out.append(rel)
    return out


def _zip_code(root, extra=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in code_files(root):
            z.write(root / rel, ROOT + "/" + rel)
        for name, data in (extra or {}).items():
            z.writestr(ROOT + "/" + name, data)
    return buf.getvalue()


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------
def api_export(ctx):
    permissions.require_admin(ctx.user)
    conn = ctx.conn
    tables = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    schema = "\n\n".join(r["sql"] + ";" for r in conn.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type DESC, name"))
    from . import modules
    history = _history(ctx)
    last_log = history[-1]["log"] if history and history[-1].get("log") else "(aucun import précédent enregistré)"
    context = {"version": APP_VERSION, "exported_at": db.utc_now(), "exported_by": ctx.user["display_name"],
               "modules": [m["key"] for m in modules.MODULE_MANIFEST if m["module"] is not None],
               "migrations": [dict(r) for r in conn.execute("SELECT * FROM schema_migrations ORDER BY module, version")]
               if "schema_migrations" in tables else [],
               "row_counts": {t: conn.execute('SELECT COUNT(*) FROM "{}"'.format(t)).fetchone()[0] for t in tables},
               "updates": [{k: h.get(k) for k in ("version", "from", "applied_at", "by")} for h in history]}
    prompt = PROMPT.format(min_claude=MIN_CLAUDE, version=APP_VERSION, date=dt.date.today().isoformat(),
                           who=ctx.user["display_name"], root=ROOT, last_log=last_log)
    data = _zip_code(_cfg_root(ctx), {"UPDATE_PROMPT.md": prompt, "UPDATE_CONTEXT.json": json.dumps(context, ensure_ascii=False, indent=1),
                                      "SCHEMA.sql": schema})
    _log(ctx, "update_export", {"version": APP_VERSION, "bytes": len(data)})
    return RawFile(data, "Dynamite_Agile_v{}_code_pour_Claude.zip".format(APP_VERSION), "application/zip")


# --------------------------------------------------------------------------
# Import: check, apply, rollback
# --------------------------------------------------------------------------
def _members(z):
    """{relative path: ZipInfo} of the code in the zip (root folder optional), refusing anything unsafe."""
    names = [i for i in z.infolist() if not i.is_dir()]
    prefix = ROOT + "/" if names and all(i.filename.startswith(ROOT + "/") for i in names) else ""
    out, problems = {}, []
    for info in names:
        rel = info.filename[len(prefix):]
        if rel.startswith("/") or ".." in rel.split("/") or "\\" in rel:
            problems.append("« {} » : chemin refusé (absolu ou « .. »).".format(info.filename))
        elif re.match(r"^data(/|$)", rel):
            problems.append("« {} » : le dossier data/ n'est jamais importé (les données restent sur le serveur). Correctif : "
                            "retirez-le du zip.".format(info.filename))
        elif SKIP.search(rel) or rel in ("UPDATE_PROMPT.md", "UPDATE_CONTEXT.json", "SCHEMA.sql", review.CHANGES_FILE):
            continue
        elif "/" in rel and rel.split("/")[0] not in CODE_DIRS:
            problems.append("« {} » : dossier inconnu (acceptés : {}).".format(info.filename, ", ".join(CODE_DIRS)))
        elif "/" not in rel and not TOP_FILES.match(rel):
            problems.append("« {} » : fichier de premier niveau refusé.".format(info.filename))
        else:
            out[rel] = info
    return out, problems


def check(root, data):
    """Report of an update zip against the code under `root`."""
    if len(data) > MAX_ZIP_MB * 1048576:
        raise ApiError(413, "Zip de {:.0f} Mo : {} Mo au maximum.".format(len(data) / 1048576, MAX_ZIP_MB))
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ApiError(415, "Ce fichier n'est pas un zip. Correctif : importez le zip rendu par Claude.")
    files, problems = _members(z)
    for needed in ("app_dynamite_agile.py", "core/__init__.py"):
        if needed not in files:
            problems.append("« {} » absent : ce zip n'est pas le code du site.".format(needed))
    version = ""
    if "core/__init__.py" in files:
        m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', z.read(files["core/__init__.py"]).decode("utf-8", "replace"))
        version = m.group(1) if m else ""
        if not version:
            problems.append("APP_VERSION introuvable dans core/__init__.py.")
        elif _version_tuple(version) <= _version_tuple(APP_VERSION):
            problems.append("Version {} ≤ version en ligne {}. Correctif : Claude doit augmenter APP_VERSION.".format(version, APP_VERSION))
    for rel, info in files.items():
        if rel.endswith(".py"):
            text = z.read(info).decode("utf-8", "replace")
            try:
                compile(text, rel, "exec")
            except SyntaxError as exc:
                problems.append("{} ligne {} : erreur de syntaxe Python ({}).".format(rel, exc.lineno, exc.msg))
            if not rel.startswith("tests/"):  # only what the update ADDS: existing features and applied migrations stay
                old = (root / rel).read_text("utf-8", "replace") if (root / rel).is_file() else ""
                for found in sorted({m.group(0).upper() for m in DESTRUCTIVE.finditer(text)}):
                    added = len(re.findall(re.escape(found), text, re.IGNORECASE)) - len(re.findall(re.escape(found), old, re.IGNORECASE))
                    if added > 0:
                        problems.append("{} : « {} » ajouté ({}×) — une mise à jour ne supprime jamais de données. Correctif : "
                                        "migration additive seulement.".format(rel, found, added))
    problems += review.declared_changes(z)[1]
    current = set(code_files(root))
    changed = sorted(r for r in files if r in current and z.read(files[r]) != (root / r).read_bytes())
    log = ""
    for name in ("UPDATE_LOG.md", "docs/UPDATE_LOG.md"):
        info = next((i for i in z.infolist() if i.filename.endswith(name)), None)
        if info:
            log = z.read(info).decode("utf-8", "replace")[:20000]
            break
    return {"version": version, "current": APP_VERSION, "problems": problems,
            "added": sorted(set(files) - current), "changed": changed, "removed": sorted(current - set(files)),
            "files": files, "zip": z, "log": log}


def _public(report, token=None):
    cut = lambda items: {"count": len(items), "sample": items[:40]}
    return {"version": report["version"], "current": report["current"], "problems": report["problems"],
            "ok": not report["problems"], "added": cut(report["added"]), "changed": cut(report["changed"]),
            "removed": cut(report["removed"]), "log": report["log"][:4000], "token": token}


def _check_upload(ctx):
    permissions.require_admin(ctx.user)
    upload = getattr(ctx, "upload", None)
    if upload is None or not upload.data:
        raise ApiError(400, "Aucun fichier reçu. Correctif : choisissez le zip rendu par Claude.")
    return upload.data


def api_check(ctx):
    data = _check_upload(ctx)
    report = check(_cfg_root(ctx), data)
    token, steps = None, None
    if not report["problems"]:
        token = hashlib.sha256(data).hexdigest()[:32]
        folder = _dir(ctx, "incoming")
        (folder / (token + ".zip")).write_bytes(data)
        steps = review.summary(review.create(folder, token, report["version"], APP_VERSION, review.build_steps(report)))
    _log(ctx, "update_checked", {"version": report["version"], "problems": len(report["problems"])})
    return dict(_public(report, token), review=steps)


api_check.accepts_binary = True


def _snapshot_db(ctx, dest):
    src = sqlite3.connect(str(db._db_path))
    try:
        out = sqlite3.connect(str(dest))
        with out:
            src.backup(out)
        out.close()
    finally:
        src.close()


def _write(root, report):
    z = report["zip"]
    for rel, info in report["files"].items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".part")
        tmp.write_bytes(z.read(info))
        tmp.replace(target)
    for rel in report["removed"]:  # code only: data/ is never listed by code_files()
        try:
            (root / rel).unlink()
        except OSError:
            pass


def _restart(ctx):
    if ctx.config.get("update_restart", True) is False:
        return False
    def later():
        os.execv(sys.executable, [sys.executable] + sys.argv)
    threading.Timer(1.5, later).start()
    return True


def _apply(ctx, data, action, allow_same=False):
    root = _cfg_root(ctx)
    report = check(root, data)
    problems = [p for p in report["problems"] if not (allow_same and p.startswith("Version "))]
    if problems:
        raise ApiError(409, "Mise à jour refusée — {} problème(s) : {}".format(len(problems), " | ".join(problems[:10])))
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backups = _dir(ctx, "backups")
    code_backup = backups / "code_v{}_{}.zip".format(APP_VERSION, stamp)
    code_backup.write_bytes(_zip_code(root))
    # D-B-104: the data before the update is a restore point (3 kept), no more one database copy per update
    label = ("Avant le retour au code {}".format(report["version"]) if action == "rollback"
             else "Avant la mise à jour {} → {}".format(APP_VERSION, report["version"]))
    point = restorepoints.before(ctx, "avant-retour-code" if action == "rollback" else "avant-update", label)
    _write(root, report)
    history = _history(ctx)
    history.append({"version": report["version"], "from": APP_VERSION, "applied_at": db.utc_now(), "by": ctx.user["display_name"],
                    "action": action, "code_backup": code_backup.name, "point": point["name"], "log": report["log"],
                    "added": len(report["added"]), "changed": len(report["changed"]), "removed": len(report["removed"])})
    _save_history(ctx, history)
    pruned = prune_code_backups(ctx)
    _log(ctx, "update_" + action, {"from": APP_VERSION, "to": report["version"], "backup": code_backup.name,
                                   "point": point["name"], "code_backups_removed": pruned})
    return {"ok": True, "version": report["version"], "backup": code_backup.name, "point": point["name"],
            "restarting": _restart(ctx)}


CODE_RE = re.compile(r"code_v([\w.]+)_(\d{8}-\d{6})\.zip")


def prune_code_backups(ctx, keep=restorepoints.KEEP):
    """D-B-104: the 3 most recent copies of the code are kept (« 3 versions du Framework »), older ones removed."""
    found = sorted((p for p in _dir(ctx, "backups").glob("code_v*.zip") if CODE_RE.fullmatch(p.name)),
                   key=lambda p: CODE_RE.fullmatch(p.name).group(2), reverse=True)
    removed = []
    for path in found[keep:]:
        try:
            path.unlink()
            removed.append(path.name)
        except OSError:
            pass
    return removed


def code_versions(ctx):
    """The copies of the code one can go back to, newest first, with who replaced them and when."""
    by_backup = {h.get("code_backup"): h for h in _history(ctx)}
    out = []
    for path in _dir(ctx, "backups").glob("code_v*.zip"):
        m = CODE_RE.fullmatch(path.name)
        if not m:
            continue
        h = by_backup.get(path.name, {})
        when = dt.datetime.strptime(m.group(2), "%Y%m%d-%H%M%S")
        out.append({"backup": path.name, "version": m.group(1), "saved_at": when.strftime("%Y-%m-%d %H:%M"), "stamp": m.group(2),
                    "replaced_by": h.get("version"), "action": h.get("action"), "by": h.get("by", ""), "size": path.stat().st_size})
    return sorted(out, key=lambda c: c["stamp"], reverse=True)


def _incoming(ctx, token):
    folder = _dir(ctx, "incoming")
    token = re.sub(r"[^a-f0-9]", "", str(token or ""))[:32]
    path = folder / (token + ".zip")
    if not token or not path.exists():
        raise ApiError(404, "Vérification introuvable (expirée ou déjà appliquée). Correctif : vérifiez de nouveau le zip.")
    return folder, token, path


def api_apply(ctx):
    permissions.require_admin(ctx.user)
    folder, token, path = _incoming(ctx, ctx.body.get("token"))
    state = review.load(folder, token)
    review.require_ready(state)  # D-B-094: every step approved, never a one-click update
    result = _apply(ctx, path.read_bytes(), "applied")
    review.close(folder, state)
    path.unlink()
    return result


def api_review(ctx):
    permissions.require_admin(ctx.user)
    folder, token, _path = _incoming(ctx, ctx.params["token"])
    return review.summary(review.load(folder, token))


def api_review_step(ctx):
    """One step with the differences of its files; opening it is what allows approving it."""
    permissions.require_admin(ctx.user)
    folder, token, path = _incoming(ctx, ctx.params["token"])
    state = review.load(folder, token)
    step = review.step_of(state, ctx.params["n"])
    z = zipfile.ZipFile(path)
    files, _problems = _members(z)
    detail = review.framework_detail(step, _cfg_root(ctx), z, files)
    review.mark_seen(state, step, ctx.user)
    review.save(folder, state)
    _log(ctx, "review_opened", {"version": state["version"], "step": step["n"]})
    return {"step": {k: step.get(k) for k in ("n", "id", "title", "why", "kind", "status", "by", "at", "comment", "unknown")},
            "files": detail, "total": len(state["steps"])}


def api_review_decide(ctx):
    permissions.require_admin(ctx.user)
    folder, token, _path = _incoming(ctx, ctx.params["token"])
    state = review.load(folder, token)
    return review.decide(ctx, folder, state, ctx.params["n"], ctx.body.get("decision"), ctx.body.get("comment"))


def api_rollback(ctx):
    permissions.require_admin(ctx.user)
    name = Path(str(ctx.body.get("backup") or "")).name
    path = _dir(ctx, "backups") / name
    if not re.fullmatch(r"code_v[\w.]+_\d{8}-\d{6}\.zip", name) or not path.exists():
        raise ApiError(404, "Sauvegarde de code « {} » introuvable.".format(name))
    return _apply(ctx, path.read_bytes(), "rollback", allow_same=True)


def api_status(ctx):
    permissions.require_admin(ctx.user)
    backups = {c["backup"] for c in code_versions(ctx)}
    history = [dict(h, available=h.get("code_backup") in backups) for h in reversed(_history(ctx))]
    return {"version": APP_VERSION, "min_claude": MIN_CLAUDE, "history": history, "backups": sorted(backups, reverse=True),
            "prompt": PROMPT.format(min_claude=MIN_CLAUDE, version=APP_VERSION, date=dt.date.today().isoformat(),
                                    who=ctx.user["display_name"], root=ROOT, last_log="(joint au zip exporté)")}


# --------------------------------------------------------------------------
# [new] tags: what a person has already used (D-A-049)
# --------------------------------------------------------------------------
def _seen(conn, user_id):
    row = conn.execute("SELECT prefs FROM user_prefs WHERE user_id = ?", (user_id,)).fetchone()
    values = json.loads(row["prefs"]) if row else {}
    return values, list(values.get("seen_new") or [])


def api_seen(ctx):
    return {"seen": _seen(ctx.conn, ctx.user["id"])[1]}


def api_mark_seen(ctx):
    key = re.sub(r"[^A-Za-z0-9._-]", "", str(ctx.body.get("id") or ""))[:80]
    if not key:
        raise ApiError(400, "Identifiant [new] manquant.")
    values, seen = _seen(ctx.conn, ctx.user["id"])
    if key not in seen:
        values["seen_new"] = (seen + [key])[-500:]
        ctx.conn.execute("INSERT INTO user_prefs (user_id, prefs, updated_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE "
                         "SET prefs = excluded.prefs, updated_at = excluded.updated_at",
                         (ctx.user["id"], json.dumps(values), db.utc_now()))
    return {"ok": True}


ROUTES = [
    ("GET", r"/api/update/status", api_status, "user"),
    ("GET", r"/api/update/export\.zip", api_export, "user"),
    ("POST", r"/api/update/check", api_check, "user"),
    ("POST", r"/api/update/apply", api_apply, "user"),
    ("POST", r"/api/update/rollback", api_rollback, "user"),
    ("GET", r"/api/update/review/(?P<token>[a-f0-9]{32})", api_review, "user"),
    ("GET", r"/api/update/review/(?P<token>[a-f0-9]{32})/(?P<n>\d+)", api_review_step, "user"),
    ("POST", r"/api/update/review/(?P<token>[a-f0-9]{32})/(?P<n>\d+)", api_review_decide, "user"),
    ("GET", r"/api/new/seen", api_seen, "user"),
    ("POST", r"/api/new/seen", api_mark_seen, "user"),
]
