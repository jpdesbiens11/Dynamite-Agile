"""Annual objectives and development plan (core lot v0.11, D-B-048).

A private space per employee, by year:
- annual objectives (align expectations) and development objectives
  (skills to grow, with a target level on a 5-step ladder);
- a comment thread fed by both sides at any time, tagged « libre »,
  « revue de mi-année » or « revue de fin d'année ».
Who: the employee and HIS manager (the approver chosen in Settings) --
nobody else, administrators included (decision of the user). The employee
edits his objectives, progress and comments; the manager edits the target
level and his expectations, and comments. Closing the year archives it
(read-only) and carries the chosen development objectives to next year,
where the target level can be raised with a new expectation.
Every write is journalled WITHOUT its text (private content).
"""
import datetime as dt

from . import audit, db, prefs, validate
from .errors import ApiError

MIGRATIONS = [
    (8, """
        CREATE TABLE objectives (
            id           INTEGER PRIMARY KEY,
            user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            year         INTEGER NOT NULL,
            kind         TEXT NOT NULL DEFAULT 'annual',
            title        TEXT NOT NULL,
            description  TEXT NOT NULL DEFAULT '',
            target_level INTEGER,
            expectation  TEXT NOT NULL DEFAULT '',
            progress     INTEGER NOT NULL DEFAULT 0,
            status       TEXT NOT NULL DEFAULT 'active',
            carried_from INTEGER REFERENCES objectives(id) ON DELETE SET NULL,
            created_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL
        );
        CREATE INDEX idx_objectives_user_year ON objectives(user_id, year);
        CREATE TABLE objective_comments (
            id           INTEGER PRIMARY KEY,
            user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            year         INTEGER NOT NULL,
            objective_id INTEGER REFERENCES objectives(id) ON DELETE SET NULL,
            author_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
            context      TEXT NOT NULL DEFAULT 'libre',
            body         TEXT NOT NULL,
            created_at   TEXT NOT NULL
        );
        CREATE INDEX idx_objective_comments ON objective_comments(user_id, year);
        CREATE TABLE objective_years (
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            year        INTEGER NOT NULL,
            archived_at TEXT,
            archived_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            PRIMARY KEY (user_id, year)
        );
    """),
]

KINDS = {"annual": "Objectif annuel", "development": "Objectif de développement"}
STATUSES = {"active": "In Progress", "done": "Atteint", "dropped": "Abandonné"}
CONTEXTS = {"libre": "Commentaire", "mi-annee": "Revue de mi-année", "fin-annee": "Revue de fin d'année"}
LEVELS = {1: "1 · Notions", 2: "2 · Autonome avec aide", 3: "3 · Autonome", 4: "4 · Référence interne", 5: "5 · Expert reconnu"}
EMPLOYEE_FIELDS = ("title", "description", "progress", "status")
MANAGER_FIELDS = ("target_level", "expectation", "status")


def _person(conn, user_id):
    row = conn.execute("SELECT id, display_name FROM users WHERE id = ? AND is_active = 1", (user_id,)).fetchone()
    if row is None:
        raise ApiError(404, "Employé introuvable.")
    return row


def relation(conn, user, target_id):
    """'self', 'manager' or raise 403 -- administrators have no special access here."""
    if target_id == user["id"]:
        return "self"
    if prefs.get(conn, target_id).get("manager_id") == user["id"]:
        return "manager"
    raise ApiError(403, "Espace privé : seuls l'employé et son gestionnaire (choisi dans ses Paramètres) y ont accès.")


def _archived(conn, user_id, year):
    row = conn.execute("SELECT archived_at FROM objective_years WHERE user_id = ? AND year = ?", (user_id, year)).fetchone()
    return bool(row and row["archived_at"])


def _open_year(conn, user_id, year):
    if _archived(conn, user_id, year):
        raise ApiError(409, "Année {} archivée : lecture seule. Correctif : travaillez dans l'année suivante.".format(year))


def _log(ctx, action, target_id, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "objectives", target_id, details, ctx.ip)


def _year(ctx):
    try:
        year = int(ctx.params.get("year") or ctx.query.get("year") or dt.date.today().year)
    except ValueError:
        raise ApiError(400, "Année invalide.")
    if not 2000 <= year <= 2100:
        raise ApiError(400, "Année hors plage.")
    return year


def api_people(ctx):
    """Me, plus the people who chose me as their manager."""
    from modules.timesheet import leave
    ids = [ctx.user["id"]] + leave.reports_of(ctx.conn, ctx.user["id"])
    rows = [dict(_person(ctx.conn, i)) for i in ids if ctx.conn.execute("SELECT 1 FROM users WHERE id = ? AND is_active = 1", (i,)).fetchone()]
    return {"people": rows, "me": ctx.user["id"]}


def api_get(ctx):
    target = validate.int_param(ctx.params, "uid")
    rel = relation(ctx.conn, ctx.user, target)
    year = _year(ctx)
    conn = ctx.conn
    items = db.rows(conn.execute(
        "SELECT o.*, c.year AS carried_year FROM objectives o LEFT JOIN objectives c ON c.id = o.carried_from "
        "WHERE o.user_id = ? AND o.year = ? ORDER BY o.kind, o.id", (target, year)).fetchall())
    comments = db.rows(conn.execute(
        "SELECT m.*, u.display_name AS author FROM objective_comments m LEFT JOIN users u ON u.id = m.author_id "
        "WHERE m.user_id = ? AND m.year = ? ORDER BY m.id", (target, year)).fetchall())
    years = sorted({r[0] for r in conn.execute("SELECT year FROM objectives WHERE user_id = ? UNION SELECT year FROM "
                                               "objective_comments WHERE user_id = ?", (target, target))} | {dt.date.today().year, year})
    manager_id = prefs.get(conn, target).get("manager_id")
    manager = conn.execute("SELECT display_name FROM users WHERE id = ?", (manager_id,)).fetchone() if manager_id else None
    _log(ctx, "objectives_viewed", target, {"year": year, "as": rel})
    return {"person": dict(_person(conn, target)), "relation": rel, "year": year, "years": years,
            "archived": _archived(conn, target, year), "objectives": items, "comments": comments,
            "manager": manager["display_name"] if manager else None,
            "kinds": KINDS, "statuses": STATUSES, "contexts": CONTEXTS, "levels": LEVELS}


def _clean(body, fields):
    out = {}
    if "title" in body and "title" in fields:
        out["title"] = validate.text(body, "title", 200)
    if "description" in body and "description" in fields:
        out["description"] = validate.text(body, "description", 4000, required=False)
    if "expectation" in body and "expectation" in fields:
        out["expectation"] = validate.text(body, "expectation", 4000, required=False)
    if "progress" in body and "progress" in fields:
        try:
            out["progress"] = max(0, min(100, int(body["progress"])))
        except (TypeError, ValueError):
            raise ApiError(400, "Avancement invalide. Correctif : 0 à 100.")
    if "status" in body and "status" in fields:
        if body["status"] not in STATUSES:
            raise ApiError(400, "Statut inconnu. Correctif : " + ", ".join(STATUSES) + ".")
        out["status"] = body["status"]
    if "target_level" in body and "target_level" in fields:
        value = body["target_level"]
        if value in (None, ""):
            out["target_level"] = None
        elif int(value) in LEVELS:
            out["target_level"] = int(value)
        else:
            raise ApiError(400, "Niveau visé : 1 à 5.")
    return out


def api_create(ctx):
    target = validate.int_param(ctx.params, "uid")
    rel = relation(ctx.conn, ctx.user, target)
    year = _year(ctx)
    _open_year(ctx.conn, target, year)
    kind = ctx.body.get("kind", "annual")
    if kind not in KINDS:
        raise ApiError(400, "Type d'objectif inconnu.")
    fields = _clean(ctx.body, EMPLOYEE_FIELDS + MANAGER_FIELDS)
    if "title" not in fields:
        raise ApiError(400, "Titre manquant. Correctif : un objectif clair et mesurable.")
    now = db.utc_now()
    oid = ctx.conn.execute(
        "INSERT INTO objectives (user_id, year, kind, title, description, target_level, expectation, progress, status, created_by, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'active', ?, ?, ?)",
        (target, year, kind, fields["title"], fields.get("description", ""), fields.get("target_level"),
         fields.get("expectation", ""), ctx.user["id"], now, now)).lastrowid
    _log(ctx, "objective_created", target, {"year": year, "kind": kind, "by": rel})
    return {"id": oid}


def api_update(ctx):
    oid = validate.int_param(ctx.params, "oid")
    row = ctx.conn.execute("SELECT * FROM objectives WHERE id = ?", (oid,)).fetchone()
    if row is None:
        raise ApiError(404, "Objectif introuvable.")
    rel = relation(ctx.conn, ctx.user, row["user_id"])
    _open_year(ctx.conn, row["user_id"], row["year"])
    allowed = EMPLOYEE_FIELDS if rel == "self" else MANAGER_FIELDS
    refused = [k for k in ctx.body if k not in allowed]
    if refused:
        raise ApiError(403, "Champ(s) {} réservé(s) à {}.".format(", ".join(refused), "votre gestionnaire" if rel == "self"
                                                                  else "l'employé"))
    changes = _clean(ctx.body, allowed)
    if not changes:
        raise ApiError(400, "Aucune modification demandée.")
    ctx.conn.execute("UPDATE objectives SET {}, updated_at = ? WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                     list(changes.values()) + [db.utc_now(), oid])
    _log(ctx, "objective_updated", row["user_id"], {"fields": sorted(changes), "by": rel})
    return {"ok": True}


def api_comment(ctx):
    target = validate.int_param(ctx.params, "uid")
    rel = relation(ctx.conn, ctx.user, target)
    year = _year(ctx)
    _open_year(ctx.conn, target, year)
    body = validate.text(ctx.body, "body", 4000)
    context = ctx.body.get("context", "libre")
    if context not in CONTEXTS:
        raise ApiError(400, "Contexte inconnu.")
    objective_id = ctx.body.get("objective_id") or None
    if objective_id and not ctx.conn.execute("SELECT 1 FROM objectives WHERE id = ? AND user_id = ? AND year = ?",
                                             (objective_id, target, year)).fetchone():
        raise ApiError(400, "Objectif introuvable pour cette année.")
    ctx.conn.execute("INSERT INTO objective_comments (user_id, year, objective_id, author_id, context, body, created_at) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)", (target, year, objective_id, ctx.user["id"], context, body, db.utc_now()))
    _log(ctx, "objective_comment", target, {"year": year, "context": context, "by": rel})
    return {"ok": True}


def api_archive(ctx):
    """Close the year: read-only from now on; chosen development objectives continue next year."""
    target = validate.int_param(ctx.params, "uid")
    rel = relation(ctx.conn, ctx.user, target)
    year = _year(ctx)
    _open_year(ctx.conn, target, year)
    from . import reviews  # core lot v0.30 (D-B-111): every item evaluated and the end phase signed by both
    blockers = reviews.can_close(ctx.conn, target, year)
    if blockers:
        raise ApiError(409, "Année {} pas encore close. Correctif : {}".format(year, " ".join(blockers)))
    carry = [int(i) for i in ctx.body.get("carry") or []]
    now = db.utc_now()
    carried = 0
    for oid in carry:
        row = ctx.conn.execute("SELECT * FROM objectives WHERE id = ? AND user_id = ? AND year = ?", (oid, target, year)).fetchone()
        if row is None:
            continue
        ctx.conn.execute(
            "INSERT INTO objectives (user_id, year, kind, title, description, target_level, expectation, progress, status, "
            "carried_from, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'active', ?, ?, ?, ?)",
            (target, year + 1, row["kind"], row["title"], row["description"], row["target_level"], row["expectation"], oid,
             ctx.user["id"], now, now))
        carried += 1
    ctx.conn.execute("INSERT INTO objective_years (user_id, year, archived_at, archived_by) VALUES (?, ?, ?, ?) "
                     "ON CONFLICT(user_id, year) DO UPDATE SET archived_at = excluded.archived_at, archived_by = excluded.archived_by",
                     (target, year, now, ctx.user["id"]))
    _log(ctx, "objectives_year_archived", target, {"year": year, "carried": carried, "by": rel})
    return {"archived": year, "carried": carried, "next_year": year + 1}


ROUTES = [
    ("GET", r"/api/objectives/people", api_people, "user"),
    ("GET", r"/api/objectives/(?P<uid>\d+)", api_get, "user"),
    ("POST", r"/api/objectives/(?P<uid>\d+)/(?P<year>\d{4})", api_create, "user"),
    ("POST", r"/api/objectives/(?P<uid>\d+)/(?P<year>\d{4})/comments", api_comment, "user"),
    ("POST", r"/api/objectives/(?P<uid>\d+)/(?P<year>\d{4})/archive", api_archive, "user"),
    ("PATCH", r"/api/objectives/item/(?P<oid>\d+)", api_update, "user"),
]
