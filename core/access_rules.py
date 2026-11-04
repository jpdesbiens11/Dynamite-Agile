"""Access rules as a text script (core lot v0.6, D-B-016), and the expert
directory shown on the home page.

Administration → « Règles d'accès » exports and imports the platform's
internal rules -- users (name, global admin, active, job title, expertise,
when to route questions to them) and their rights on each project -- in a
plain text file that people and AI agents can read, diff and edit. Projects
themselves are not in it. Passwords never are: a user created by an import
gets a temporary password (shown once, in the import report) and must
change it at first login.

    # comment
    utilisateur lea | Léa | utilisateur | actif
    fonction    lea | Étudiante en génie électrique
    expertise   lea | Circuits, alimentation, capteurs, ...
    diriger     lea | une question d'alimentation ou de circuit, ...
    droit       lea | EQP | editeur          (lecteur | editeur | admin-projet | aucun)

Import is additive and idempotent: it creates or updates, never deletes a
user; "aucun" removes a project right. A dry run (« Vérifier ») reports
everything without writing.
"""
import unicodedata
from pathlib import Path

from . import audit, auth, db
from .errors import ApiError
from .files import RawFile

MIGRATIONS = [
    (2, """
        -- D-B-016: expert directory fields, exported with the access rules.
        ALTER TABLE users ADD COLUMN title TEXT NOT NULL DEFAULT '';
        ALTER TABLE users ADD COLUMN expertise TEXT NOT NULL DEFAULT '';
        ALTER TABLE users ADD COLUMN route_when TEXT NOT NULL DEFAULT '';
    """),
    (17, """
        -- 0.60.01: study profile of an account (« Profil d'études », e.g. génie mécanique, design industriel), to form a
        -- multidisciplinary team; set in Admin → Comptes or with the « profil » directive of the access rules.
        ALTER TABLE users ADD COLUMN study_profile TEXT NOT NULL DEFAULT '';
    """),
]

ROLE_WORDS = {"lecteur": "reader", "reader": "reader", "editeur": "editor", "editor": "editor",
              "admin-projet": "manager", "manager": "manager", "aucun": None, "none": None}
ROLE_OUT = {"reader": "lecteur", "editor": "editeur", "manager": "admin-projet"}
TEXT_FIELDS = {"fonction": ("title", 120), "profil": ("study_profile", 80), "expertise": ("expertise", 1000),
               "diriger": ("route_when", 1000)}
MAX_LINES = 5000


def _norm(word):
    word = unicodedata.normalize("NFKD", word.strip().lower())
    return "".join(ch for ch in word if not unicodedata.combining(ch))


def _clean(value):
    return value.replace("|", "/").replace("\n", " ").strip()


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------
def export_text(conn, author):
    lines = [
        "# Règles d'accès — Dynamite | Agile (Dynamite · Agile · Goldmine · Exploration)",
        "# Exporté le {} par {}. Import : Administration → Règles d'accès.".format(db.utc_now()[:10], author),
        "# Une directive par ligne, champs séparés par « | » ; les lignes # sont des commentaires.",
        "#   utilisateur <identifiant> | <nom affiché> | <admin|utilisateur> | <actif|inactif>",
        "#   fonction    <identifiant> | <rôle dans l'équipe>",
        "#   profil      <identifiant> | <profil d'études, ex. génie mécanique>",
        "#   expertise   <identifiant> | <domaines d'expertise>",
        "#   diriger     <identifiant> | <quand lui adresser une question>",
        "#   droit       <identifiant> | <CLÉ PROJET> | <lecteur|editeur|admin-projet|aucun>",
        "# Les mots de passe ne sont jamais exportés : un compte créé par import reçoit un mot de",
        "# passe temporaire, à changer à la première connexion.",
        "",
    ]
    users = conn.execute("SELECT * FROM users ORDER BY username").fetchall()
    rights = {}
    for r in conn.execute("SELECT m.user_id, p.key, m.role FROM memberships m JOIN projects p ON p.id = m.project_id "
                          "ORDER BY p.key"):
        rights.setdefault(r["user_id"], []).append((r["key"], r["role"]))
    for u in users:
        lines.append("utilisateur {} | {} | {} | {}".format(u["username"], _clean(u["display_name"]),
                                                            "admin" if u["is_admin"] else "utilisateur",
                                                            "actif" if u["is_active"] else "inactif"))
        for word, (column, _) in TEXT_FIELDS.items():
            if u[column]:
                lines.append("{:<11} {} | {}".format(word, u["username"], _clean(u[column])))
        for key, role in rights.get(u["id"], []):
            lines.append("droit       {} | {} | {}".format(u["username"], key, ROLE_OUT.get(role, role)))
        lines.append("")
    return "\n".join(lines)


def api_export(ctx):
    text = export_text(ctx.conn, ctx.user["username"])
    audit.log_action(ctx.conn, ctx.user["id"], "access_rules_exported", "platform", None, None, ctx.ip)
    return RawFile(text.encode("utf-8"), "regles_acces_{}.txt".format(db.utc_now()[:10]), "text/plain; charset=utf-8")


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------
def _parse(text):
    """[(line_number, directive, [fields])] or raise with the line to fix."""
    out = []
    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if len(lines) > MAX_LINES:
        raise ApiError(400, "Fichier de {} lignes. Correctif : {} au maximum ; découpez-le.".format(len(lines), MAX_LINES))
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        head, _, rest = line.partition(" ")
        fields = [f.strip() for f in rest.split("|")]
        out.append((number, _norm(head), fields))
    return out


def _entry(number, action, detail="", ok=True):
    return {"line": number, "action": action, "detail": detail, "ok": ok}


def _apply_user(conn, ctx, number, fields, created, dry):
    from .admin import USERNAME_RE  # local import: admin imports this module
    if len(fields) < 2:
        return _entry(number, "refusée", "Il faut au moins « identifiant | nom affiché ».", False)
    username = fields[0].lower()
    if not USERNAME_RE.match(username):
        return _entry(number, "refusée", "Identifiant « {} » invalide : 2 à 32 minuscules, chiffres, point, tiret, "
                                         "soulignement.".format(fields[0]), False)
    name = fields[1][:80]
    is_admin = len(fields) > 2 and _norm(fields[2]) == "admin"
    active = not (len(fields) > 3 and _norm(fields[3]) == "inactif")
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        temp = auth.generate_temp_password()
        if not dry:
            uid = conn.execute("INSERT INTO users (username, display_name, password_hash, is_admin, is_active, "
                               "must_change_password, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
                               (username, name, auth.hash_password(temp), int(is_admin), int(active),
                                db.utc_now())).lastrowid
            from . import prefs
            prefs.ensure_initials(conn, uid)  # 0.60.19 (D-O-030)
            audit.log_action(conn, ctx.user["id"], "user_created", "user", uid,
                             {"username": username, "via": "access_rules"}, ctx.ip)
        created[username] = temp
        return _entry(number, "compte créé", "{} — mot de passe temporaire : {}".format(username, temp if not dry else "(généré à l'import)"))
    changes = {}
    if row["display_name"] != name:
        changes["display_name"] = name
    if bool(row["is_admin"]) != is_admin:
        changes["is_admin"] = int(is_admin)
    if bool(row["is_active"]) != active:
        changes["is_active"] = int(active)
    losing = (row["is_admin"] and row["is_active"]) and (changes.get("is_admin") == 0 or changes.get("is_active") == 0)
    if losing and row["id"] == ctx.user["id"]:
        return _entry(number, "refusée", "Votre propre compte perdrait ses droits d'administrateur. Correctif : "
                                         "gardez « admin | actif » sur votre ligne.", False)
    if losing and conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1 AND is_active = 1 AND id <> ?",
                               (row["id"],)).fetchone()[0] == 0:
        return _entry(number, "refusée", "Il doit rester au moins un administrateur actif.", False)
    if not changes:
        return _entry(number, "inchangé", username)
    if not dry:
        conn.execute("UPDATE users SET {} WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                     list(changes.values()) + [row["id"]])
        if changes.get("is_active") == 0:
            auth.delete_user_sessions(conn, row["id"])
        audit.log_action(conn, ctx.user["id"], "user_updated", "user", row["id"], dict(changes, via="access_rules"), ctx.ip)
    return _entry(number, "compte mis à jour", "{} : {}".format(username, ", ".join(sorted(changes))))


def _user_id(conn, username, created, number):
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username.lower(),)).fetchone()
    if row:
        return row["id"], None
    if username.lower() in created:
        return 0, None  # dry run: account will exist
    return None, _entry(number, "refusée", "Utilisateur « {} » inconnu. Correctif : ajoutez sa ligne « utilisateur » "
                                           "plus haut dans le fichier.".format(username), False)


def _apply_field(conn, ctx, number, word, fields, created, dry):
    column, limit = TEXT_FIELDS[word]
    if len(fields) < 2:
        return _entry(number, "refusée", "Format : {} identifiant | texte.".format(word), False)
    uid, error = _user_id(conn, fields[0], created, number)
    if error:
        return error
    value = " | ".join(fields[1:]).strip()[:limit]
    if uid and conn.execute("SELECT {} FROM users WHERE id = ?".format(column), (uid,)).fetchone()[0] == value:
        return _entry(number, "inchangé", "{} de {}".format(word, fields[0]))
    if not dry and uid:
        conn.execute("UPDATE users SET {} = ? WHERE id = ?".format(column), (value, uid))
    return _entry(number, "{} définie".format(word), fields[0])


def _apply_right(conn, ctx, number, fields, created, dry):
    if len(fields) < 3:
        return _entry(number, "refusée", "Format : droit identifiant | CLÉ PROJET | lecteur, editeur, admin-projet ou aucun.", False)
    uid, error = _user_id(conn, fields[0], created, number)
    if error:
        return error
    project = conn.execute("SELECT id, key FROM projects WHERE key = ?", (fields[1].upper(),)).fetchone()
    if project is None:
        return _entry(number, "ignorée", "Projet « {} » inexistant ici : créez-le d'abord (Administration → Projets), "
                                         "puis réimportez.".format(fields[1]), False)
    word = _norm(fields[2])
    if word not in ROLE_WORDS:
        return _entry(number, "refusée", "Droit « {} » inconnu. Correctif : lecteur, editeur, admin-projet ou aucun.".format(fields[2]), False)
    role = ROLE_WORDS[word]
    current = conn.execute("SELECT role FROM memberships WHERE user_id = ? AND project_id = ?",
                           (uid, project["id"])).fetchone() if uid else None
    if (current["role"] if current else None) == role:
        return _entry(number, "inchangé", "{} sur {}".format(fields[0], project["key"]))
    if not dry and uid:
        if role is None:
            conn.execute("DELETE FROM memberships WHERE user_id = ? AND project_id = ?", (uid, project["id"]))
        else:
            conn.execute("INSERT OR REPLACE INTO memberships (user_id, project_id, role) VALUES (?, ?, ?)",
                         (uid, project["id"], role))
        audit.log_action(conn, ctx.user["id"], "member_set" if role else "member_removed", "project", project["id"],
                         {"user_id": uid, "role": role, "via": "access_rules"}, ctx.ip)
    return _entry(number, "droit retiré" if role is None else "droit défini",
                  "{} : {} sur {}".format(fields[0], ROLE_OUT.get(role, "aucun"), project["key"]))


def import_text(ctx, text, dry=False):
    conn = ctx.conn
    report, created = [], {}
    for number, word, fields in _parse(text):
        if word == "utilisateur":
            report.append(_apply_user(conn, ctx, number, fields, created, dry))
        elif word in TEXT_FIELDS:
            report.append(_apply_field(conn, ctx, number, word, fields, created, dry))
        elif word == "droit":
            report.append(_apply_right(conn, ctx, number, fields, created, dry))
        else:
            report.append(_entry(number, "refusée", "Directive « {} » inconnue. Correctif : utilisateur, fonction, profil, "
                                                    "expertise, diriger ou droit.".format(word), False))
    if not dry:
        audit.log_action(conn, ctx.user["id"], "access_rules_imported", "platform", None,
                         {"lines": len(report), "created": len(created)}, ctx.ip)
    return {"dry_run": dry, "report": report,
            "created": [] if dry else [{"username": u, "temp_password": p} for u, p in created.items()],
            "summary": {"ok": sum(1 for r in report if r["ok"]), "problems": sum(1 for r in report if not r["ok"])}}


def api_import(ctx):
    text = ctx.body.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ApiError(400, "Fichier vide. Correctif : collez le contenu exporté, ou choisissez un fichier .txt.")
    return import_text(ctx, text, bool(ctx.body.get("dry_run")))


DEFAULT_FILE = Path(__file__).resolve().parent.parent / "deploy" / "utilisateurs_exemple.txt"


def api_default(ctx):
    """The example team shipped with the tool (4 fictitious students), for review before import."""
    try:
        return {"text": DEFAULT_FILE.read_text(encoding="utf-8")}
    except OSError:
        raise ApiError(404, "Fichier deploy/utilisateurs_exemple.txt absent de cette installation.")


def api_directory(ctx):
    """Who to ask (all signed-in users): active accounts with a job title."""
    rows = ctx.conn.execute("SELECT display_name, title, study_profile, expertise, route_when FROM users "
                            "WHERE is_active = 1 AND title != '' ORDER BY display_name").fetchall()
    return {"people": db.rows(rows)}


ROUTES = [
    ("GET", r"/api/directory", api_directory, "user"),
    ("GET", r"/api/admin/access-rules/default", api_default, "admin"),
    ("GET", r"/api/admin/access-rules", api_export, "admin"),
    ("POST", r"/api/admin/access-rules", api_import, "admin"),
]
