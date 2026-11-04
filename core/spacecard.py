"""Fiche d'un Space (core lot v0.34, D-B-133): Admin → Spaces → a Space, one at a time.

Everything an administrator does to ONE Space from one page: rename (name and description; the key never changes,
so the references already issued -- EQP-12, REQ-EQP-… -- stay right), duplicate (all of it, next free key, « (copie) »),
save as (all or some tabs, key and name chosen), export (backup .zip), archive / unarchive, delete (archived only,
backup first), members. The copies reuse « Copier / composer un Space » (spacecopy.compose, D-B-099): always a NEW Space,
one transaction, journalled. The card also counts what the Space holds, tab by tab, and who opens it by default.
"""
from . import admin, audit, backup, permissions, spacecopy, validate
from .errors import ApiError

PROJECT_ID = r"(?P<project_id>\d+)"
P = r"/api/admin/projects/" + PROJECT_ID
# what the card counts per tab: label -> tables (rows of the Space, from backup.collect)
CONTENT = [
    ("Dynamite", ("dynamite_pages",), "page", "pages"),
    ("Agile", ("agile_issues",), "ticket ou requirement", "tickets et requirements"),
    ("Goldmine", ("agile_requirements",), "requirement", "requirements"),
    ("Change Management", ("agile_changes",), "changement", "changements"),
    ("Testing", ("testing_tests",), "test (Test Base du Space)", "tests (Test Base du Space)"),
    ("Exploration", ("exploration_tasks",), "tâche du plan", "tâches du plan"),
    ("Tools", ("tools_ideation", "tools_kt"), "séance ou analyse", "séances et analyses"),
    ("Generator", ("codex_refs",), "référence", "références"),
    ("Timesheet", ("timesheet_entries",), "plage d'heures", "plages d'heures"),
    ("Membres", ("memberships",), "membre", "membres"),
]


def _project(conn, pid):
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    if row is None:
        raise ApiError(404, "Space introuvable.")
    return dict(row)


def next_key(conn, base):
    """First free key built on `base`: EQP -> EQP2, EQP3… (never a retired key, never more than 10 characters)."""
    taken = {r[0] for r in conn.execute("SELECT key FROM projects")} | \
        {r[0] for r in conn.execute("SELECT key FROM retired_project_keys")}
    for n in range(2, 1000):
        suffix = str(n)
        key = base[:10 - len(suffix)] + suffix
        if key not in taken:
            return key
    raise ApiError(409, "Aucune clé libre à partir de {}. Correctif : « Enregistrer sous » avec une clé choisie.".format(base))


def api_card(ctx):
    pid = validate.int_param(ctx.params, "project_id")
    project = _project(ctx.conn, pid)
    _info, rows = backup.collect(ctx.conn, pid)
    content = []
    for label, tables, one, many in CONTENT:
        n = sum(len(rows.get(t) or []) for t in tables)
        content.append({"tab": label, "count": n, "unit": one if n == 1 else many})
    default_for = ctx.conn.execute("SELECT COUNT(*) FROM user_prefs WHERE json_extract(prefs, '$.default_space') = ?",
                                   (project["key"],)).fetchone()[0]
    return {"project": {k: project[k] for k in ("id", "key", "name", "description", "is_archived", "created_at")},
            "content": content, "default_for": default_for, "suggested_key": next_key(ctx.conn, project["key"]),
            "parts": [{"part": p, "label": spacecopy.LABELS[p]} for p in spacecopy.PARTS]}


def api_copy(ctx):
    """Duplicate / save as: {key?, name?, description?, parts?: [part, ...]} -- all parts when none is given."""
    permissions.require_admin(ctx.user)
    pid = validate.int_param(ctx.params, "project_id")
    src = _project(ctx.conn, pid)
    key = str(ctx.body.get("key") or "").strip().upper() or next_key(ctx.conn, src["key"])
    name = str(ctx.body.get("name") or "").strip()[:100] or (src["name"] + " (copie)")[:100]
    description = str(ctx.body.get("description") if ctx.body.get("description") is not None else src["description"] or "")[:500]
    wanted = ctx.body.get("parts")
    if wanted is None:
        wanted = list(spacecopy.PARTS)
    if not isinstance(wanted, list) or any(p not in spacecopy.PARTS for p in wanted):
        raise ApiError(400, "Onglets inconnus. Correctif : choisissez parmi {}.".format(", ".join(spacecopy.PARTS)))
    parts = spacecopy._clean_parts(ctx.conn, {"parts": {p: src["key"] for p in wanted}})
    if not admin.PROJECT_KEY_RE.match(key):
        raise ApiError(400, "Clé « {} » invalide. Correctif : 2 à 10 lettres majuscules ou chiffres, une lettre d'abord.".format(key))
    made = spacecopy.compose(ctx, key, name, description, parts)
    audit.log_action(ctx.conn, ctx.user["id"], "space_saved_as", "project", made["project"]["id"],
                     {"from": src["key"], "to": key, "parts": sorted(wanted), "duplicate": ctx.body.get("parts") is None}, ctx.ip)
    return made


ROUTES = [
    ("GET", P + r"/card", api_card, "admin"),
    ("POST", P + r"/copy", api_copy, "admin"),
]
