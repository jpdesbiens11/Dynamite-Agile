"""Platform configuration snapshots (core lot v0.11, D-B-047).

Administration → « Configuration »: every platform SETTING -- never the
content of the tabs (no page, ticket, requirement, hour) -- in one light
Markdown file an administrator can download, discuss with an approved AI
assistant to tune a setting or diagnose the interface, then load back.

- The file: readable sections; the applicable ones hold a fenced block
  tagged ``da:<section>`` (JSON or text) that the platform reads back.
  Applicable (with a preview of the differences, then confirmation):
  privacy policy, accounts and rights (as access rules), Timesheet
  organisms / contracts / task sets, display preferences and manager of
  each account. Read-only (for diagnosis): projects, Agile workflows,
  types and labels, migrations, table sizes, non-secret server settings.
- Versions: every download, load and application keeps a dated snapshot
  (« config_JJMMAAAA-HHMMSS »); an older one can be re-applied (e.g. the
  one before an unsuccessful change). Snapshots older than 3 months are
  deleted when a new configuration is loaded.
"""
import datetime as dt
import hashlib
import json
import platform
import re

from . import APP_VERSION, access_rules, audit, db, modules, prefs
from .errors import ApiError
from .files import RawFile

MIGRATIONS = [
    (7, """
        CREATE TABLE config_snapshots (
            id         INTEGER PRIMARY KEY,
            name       TEXT NOT NULL,
            source     TEXT NOT NULL,
            note       TEXT NOT NULL DEFAULT '',
            content    TEXT NOT NULL,
            sha256     TEXT NOT NULL,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL
        );
    """),
]

RETENTION_DAYS = 92  # « maximum 3 months »
FENCE = re.compile(r"```(\w+) da:([a-z\-]+)\n(.*?)\n```", re.S)
SECRET = re.compile(r"secret|password|token|key|cert", re.I)
PREF_KEYS = ("theme", "font", "font_size", "density", "landing", "my_items", "initials")
SOURCES = {"export": "Téléchargée", "import": "Chargée", "before": "Avant application", "manual": "Instantané"}


# --------------------------------------------------------------------------
# Build the Markdown
# --------------------------------------------------------------------------
def _block(lang, tag, data):
    body = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2)
    return "```{} da:{}\n{}\n```".format(lang, tag, body.rstrip("\n"))


def _task_set(conn, value):
    """A set of time codes that exists (0.60.01: « pdp » by default; any set an administrator made)."""
    try:
        from modules.timesheet import budget
        return value if value in budget.structure(conn) else "pdp"
    except Exception:
        return "pdp"


def _timesheet(conn):
    rows = conn.execute("SELECT p.key, t.organism, t.contract_ref, t.task_set, t.open_to_all, t.enabled FROM timesheet_projects t "
                        "JOIN projects p ON p.id = t.project_id ORDER BY p.key").fetchall()
    return [{"projet": r["key"], "organisme": r["organism"], "contrat": r["contract_ref"], "taches": r["task_set"],
             "ouvert_a_tous": bool(r["open_to_all"]), "actif": bool(r["enabled"])} for r in rows]


def _user_prefs(conn):
    users = {r["id"]: r["username"] for r in conn.execute("SELECT id, username FROM users WHERE is_active = 1")}
    out = {}
    for uid, username in sorted(users.items(), key=lambda x: x[1]):
        p = prefs.get(conn, uid)
        entry = {k: p[k] for k in PREF_KEYS if p.get(k) not in (None, "") and p[k] != prefs.DEFAULTS.get(k)}
        if p.get("manager_id") in users:
            entry["gestionnaire"] = users[p["manager_id"]]
        if entry:
            out[username] = entry
    return out


def _agile(conn):
    out = {}
    for proj in conn.execute("SELECT id, key FROM projects WHERE is_archived = 0 ORDER BY key"):
        wfs = {}
        for s in conn.execute("SELECT w.name AS wf, s.name, s.category FROM agile_statuses s JOIN agile_workflows w "
                              "ON w.id = s.workflow_id WHERE w.project_id = ? ORDER BY w.id, s.position", (proj["id"],)):
            wfs.setdefault(s["wf"], []).append("{} ({})".format(s["name"], s["category"]))
        types = [r["name"] for r in conn.execute("SELECT name FROM agile_issue_types WHERE project_id = ? ORDER BY position",
                                                  (proj["id"],))]
        labels = [r["name"] for r in conn.execute("SELECT name FROM agile_labels WHERE project_id = ? ORDER BY name", (proj["id"],))]
        if wfs or types:
            out[proj["key"]] = {"workflows": wfs, "types": types, "labels": labels}
    return out


def _diagnostic(conn, config):
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                                         "ORDER BY name")]
    return {"version": APP_VERSION, "python": platform.python_version(),
            "serveur": {k: v for k, v in (config or {}).items() if not SECRET.search(k)},
            "modules": [{"cle": m["key"], "libelle": m["label"], "actif": m["module"] is not None,
                         "placement": m.get("placement", "main")} for m in modules.MODULE_MANIFEST],
            "migrations": {r["module"]: r["v"] for r in conn.execute(
                "SELECT module, MAX(version) AS v FROM schema_migrations GROUP BY module ORDER BY module")},
            "lignes_par_table": {t: conn.execute('SELECT COUNT(*) FROM "{}"'.format(t)).fetchone()[0] for t in tables}}


def build(conn, config, author):
    now = dt.datetime.now()
    projects = [{"cle": r["key"], "nom": r["name"], "archive": bool(r["is_archived"]), "membres": r["n"]} for r in conn.execute(
        "SELECT p.key, p.name, p.is_archived, (SELECT COUNT(*) FROM memberships m WHERE m.project_id = p.id) AS n "
        "FROM projects p ORDER BY p.key")]
    parts = [
        "# Configuration de Dynamite | Agile — {}".format(now.strftime("%Y-%m-%d %H:%M")),
        "",
        "> Version {} · générée par {}. **Réglages seulement** : aucun contenu des onglets (pages, tickets, exigences, heures).".format(
            APP_VERSION, author),
        "> Contient les noms des comptes : à discuter seulement avec un assistant IA **approuvé par votre établissement**.",
        "> Les blocs marqués `da:…` sont relus au chargement ; modifiez leur contenu, pas leurs balises.",
        "",
        "## 1. Confidentialité (applicable)",
        "Filigrane, blocage de l'impression, blocage copier / clic droit, flou hors focus : `true` ou `false`.",
        _block("json", "privacy", prefs.policy(conn)),
        "",
        "## 2. Comptes et droits (applicable — format « Règles d'accès »)",
        "Une directive par ligne. Les mots de passe ne sont jamais inclus.",
        _block("text", "access-rules", access_rules.export_text(conn, author)),
        "",
        "## 3. Timesheet — projets, organismes, contrats (applicable)",
        "`taches` : jeu de codes de temps (pdp par défaut) ; `ouvert_a_tous` : saisie sans être membre.",
        _block("json", "timesheet-projects", _timesheet(conn)),
        "",
        "## 4. Préférences des comptes (applicable)",
        "Seules les valeurs différentes du défaut sont listées ; `gestionnaire` = identifiant de l'approbateur.",
        _block("json", "user-prefs", _user_prefs(conn)),
        "",
        "## 5. Projets (lecture seule)",
        _block("json", "projects", projects),
        "",
        "## 6. Agile — workflows, types, labels (lecture seule)",
        _block("json", "agile", _agile(conn)),
        "",
        "## 7. Diagnostic (lecture seule)",
        _block("json", "diagnostic", _diagnostic(conn, config)),
        "",
    ]
    return "\n".join(parts)


# --------------------------------------------------------------------------
# Snapshots
# --------------------------------------------------------------------------
def _store(conn, content, source, user_id, note=""):
    now = dt.datetime.now()
    name = "config_{}.md".format(now.strftime("%d%m%Y-%H%M%S"))
    sid = conn.execute("INSERT INTO config_snapshots (name, source, note, content, sha256, created_by, created_at) "
                       "VALUES (?, ?, ?, ?, ?, ?, ?)", (name, source, note[:200], content,
                                                        hashlib.sha256(content.encode("utf-8")).hexdigest(), user_id,
                                                        db.utc_now())).lastrowid
    return sid, name


def purge(conn):
    limit = (dt.datetime.utcnow() - dt.timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%dT%H:%M:%S")
    return conn.execute("DELETE FROM config_snapshots WHERE created_at < ?", (limit,)).rowcount


def api_list(ctx):
    rows = ctx.conn.execute("SELECT s.id, s.name, s.source, s.note, s.sha256, s.created_at, LENGTH(s.content) AS size, "
                            "u.display_name AS by FROM config_snapshots s LEFT JOIN users u ON u.id = s.created_by "
                            "ORDER BY s.id DESC").fetchall()
    return {"snapshots": [dict(db.rows([r])[0], source_label=SOURCES.get(r["source"], r["source"])) for r in rows],
            "retention_days": RETENTION_DAYS}


def api_download_current(ctx):
    content = build(ctx.conn, ctx.config, ctx.user["username"])
    _sid, name = _store(ctx.conn, content, "export", ctx.user["id"], "Téléchargement")
    audit.log_action(ctx.conn, ctx.user["id"], "config_exported", "platform", None, {"name": name}, ctx.ip)
    return RawFile(content.encode("utf-8"), name, "text/markdown; charset=utf-8")


def _snapshot(ctx):
    row = ctx.conn.execute("SELECT * FROM config_snapshots WHERE id = ?", (int(ctx.params["sid"]),)).fetchone()
    if row is None:
        raise ApiError(404, "Version de configuration introuvable (effacée après 3 mois ?).")
    return row


def api_download(ctx):
    row = _snapshot(ctx)
    return RawFile(row["content"].encode("utf-8"), row["name"], "text/markdown; charset=utf-8")


# --------------------------------------------------------------------------
# Apply (preview first)
# --------------------------------------------------------------------------
def sections(text):
    return {tag: body for _lang, tag, body in FENCE.findall(text or "")}


def _removed_rights(conn, text):
    """Rights that exist here but not in the file, for the accounts the file lists: « aucun » lines,
    so that re-applying an older version really puts the rights back as they were."""
    listed, rights = set(), set()
    for line in text.splitlines():
        words = line.split(None, 1)
        if len(words) < 2:
            continue
        fields = [f.strip() for f in words[1].split("|")]
        if words[0] == "utilisateur":
            listed.add(fields[0].lower())
        elif words[0] == "droit" and len(fields) >= 2:
            rights.add((fields[0].lower(), fields[1].upper()))
    extra = []
    for r in conn.execute("SELECT u.username, p.key FROM memberships m JOIN users u ON u.id = m.user_id "
                          "JOIN projects p ON p.id = m.project_id ORDER BY u.username, p.key"):
        if r["username"] in listed and (r["username"], r["key"]) not in rights:
            extra.append("droit       {} | {} | aucun".format(r["username"], r["key"]))
    return ("\n" + "\n".join(extra)) if extra else ""


def plan(ctx, text, dry):
    """Differences between the file and the platform, applied when not `dry`."""
    conn = ctx.conn
    found = sections(text)
    if not any(t in found for t in ("privacy", "access-rules", "timesheet-projects", "user-prefs")):
        raise ApiError(400, "Aucun bloc applicable (da:privacy, da:access-rules, da:timesheet-projects, da:user-prefs). "
                            "Correctif : partez d'un fichier téléchargé ici, sans retirer les balises des blocs.")
    out = []

    def load(tag):
        try:
            return json.loads(found[tag])
        except ValueError as exc:
            raise ApiError(400, "Bloc da:{} illisible ({}). Correctif : JSON valide (guillemets doubles, virgules).".format(tag, exc))

    if "privacy" in found:
        wanted, current = load("privacy"), prefs.policy(conn)
        diff = {k: bool(v) for k, v in wanted.items() if k in current and bool(v) != current[k]}
        for k, v in diff.items():
            out.append({"section": "Confidentialité", "item": k, "change": "{} → {}".format(current[k], v)})
        if diff and not dry:
            current.update(diff)
            conn.execute("INSERT INTO app_settings (key, value, updated_by, updated_at) VALUES ('privacy', ?, ?, ?) "
                         "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_by = excluded.updated_by, "
                         "updated_at = excluded.updated_at", (json.dumps(current), ctx.user["id"], db.utc_now()))
    if "access-rules" in found:
        found["access-rules"] += _removed_rights(conn, found["access-rules"])
        report = access_rules.import_text(ctx, found["access-rules"], dry=True)
        changes = [r for r in report["report"] if r.get("action") not in ("inchangée", "inchangé")]
        for r in changes:
            out.append({"section": "Comptes et droits", "item": "ligne {}".format(r.get("line", "")),
                        "change": "{} {}".format(r.get("action", ""), r.get("detail", "")).strip(), "ok": r.get("ok", True)})
        if changes and not dry:
            done = access_rules.import_text(ctx, found["access-rules"], dry=False)
            for c in done.get("created", []):
                out.append({"section": "Comptes et droits", "item": c["username"],
                            "change": "compte créé — mot de passe temporaire : " + c["temp_password"]})
    if "timesheet-projects" in found:
        from modules.timesheet import manage
        current = {r["projet"]: r for r in _timesheet(conn)}
        for row in load("timesheet-projects"):
            key = str(row.get("projet", "")).upper()
            proj = conn.execute("SELECT id FROM projects WHERE key = ?", (key,)).fetchone()
            if proj is None:
                out.append({"section": "Timesheet", "item": key, "change": "projet inconnu, ignoré", "ok": False})
                continue
            before = current.get(key, {})
            values = {"organism": str(row.get("organisme", before.get("organisme", "")))[:80],
                      "contract_ref": str(row.get("contrat", before.get("contrat", "")))[:80],
                      "task_set": _task_set(conn, row.get("taches", before.get("taches", "pdp"))),
                      "open_to_all": bool(row.get("ouvert_a_tous", before.get("ouvert_a_tous", False))),
                      "enabled": bool(row.get("actif", before.get("actif", True)))}
            old = {"organism": before.get("organisme"), "contract_ref": before.get("contrat"), "task_set": before.get("taches"),
                   "open_to_all": before.get("ouvert_a_tous"), "enabled": before.get("actif")}
            diff = {k: v for k, v in values.items() if old.get(k) != v}
            if diff:
                out.append({"section": "Timesheet", "item": key, "change": ", ".join("{} → {}".format(k, v) for k, v in diff.items())})
                if not dry:
                    manage.save_settings(conn, proj["id"], **values)
    if "user-prefs" in found:
        users = {r["username"]: r["id"] for r in conn.execute("SELECT id, username FROM users WHERE is_active = 1")}
        for username, entry in load("user-prefs").items():
            uid = users.get(username)
            if uid is None:
                out.append({"section": "Préférences", "item": username, "change": "compte inconnu ou inactif, ignoré", "ok": False})
                continue
            body = {k: entry[k] for k in PREF_KEYS if k in entry}
            if "gestionnaire" in entry:
                body["manager_id"] = users.get(entry["gestionnaire"])
            current = prefs.get(conn, uid)
            diff = {k: v for k, v in body.items() if current.get(k) != v}
            if diff:
                out.append({"section": "Préférences", "item": username,
                            "change": ", ".join("{} → {}".format(k, v) for k, v in diff.items())})
                if not dry:
                    try:
                        prefs.update(ctx, uid, diff)
                    except ApiError as exc:
                        out[-1].update(ok=False, change=out[-1]["change"] + " — refusé : " + exc.message)
    return out


def _apply(ctx, text, dry, source, note):
    changes = plan(ctx, text, True)
    result = {"dry_run": dry, "changes": changes, "stored": None, "purged": 0}
    if dry:
        return result
    if changes:  # D-B-104: accounts and rights may change -- a restore point of the data first
        from . import restorepoints
        result["point"] = restorepoints.before(ctx, "avant-config")["name"]
    before_id, _ = _store(ctx.conn, build(ctx.conn, ctx.config, ctx.user["username"]), "before", ctx.user["id"],
                          "État avant application")
    result["changes"] = plan(ctx, text, False)
    if source:
        _sid, result["stored"] = _store(ctx.conn, text, source, ctx.user["id"], note)
    result["purged"] = purge(ctx.conn)
    audit.log_action(ctx.conn, ctx.user["id"], "config_applied", "platform", None,
                     {"changes": len(changes), "before_snapshot": before_id, "stored": result["stored"]}, ctx.ip)
    return result


def api_import(ctx):
    """Body {text, note, dry_run}: a configuration file (possibly tuned with an AI assistant)."""
    text = ctx.body.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ApiError(400, "Fichier vide. Correctif : choisissez le fichier .md de configuration.")
    if len(text) > 2_000_000:
        raise ApiError(413, "Fichier de plus de 2 Mo.")
    return _apply(ctx, text, bool(ctx.body.get("dry_run", True)), "import", str(ctx.body.get("note") or "Chargée"))


def api_reapply(ctx):
    row = _snapshot(ctx)
    return _apply(ctx, row["content"], bool(ctx.body.get("dry_run", True)), None, "")


ROUTES = [
    ("GET", r"/api/admin/config", api_list, "admin"),
    ("GET", r"/api/admin/config/current\.md", api_download_current, "admin"),
    ("GET", r"/api/admin/config/(?P<sid>\d+)\.md", api_download, "admin"),
    ("POST", r"/api/admin/config/import", api_import, "admin"),
    ("POST", r"/api/admin/config/(?P<sid>\d+)/apply", api_reapply, "admin"),
]
