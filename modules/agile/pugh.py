"""Goldmine « Pugh Matrix » (D-B-062): classic Pugh concept selection whose
criteria are the Space's Goldmine requirements.

One matrix = concepts (columns) x requirements (rows). One concept is the
datum (reference): its column is « S » by definition. Every other cell is
+ (better than the datum), S (same) or - (worse), with an optional note.
Totals per concept: number of +, S, -, net score (+ minus -) and rank.
A new round copies the matrix (concepts kept, criteria, no scores) around a
new datum -- usually the best concept of the previous round. A decided
matrix is read-only until it is reopened. Everything is journalled.
"""
from core import db, validate
from core.errors import ApiError

from . import common as c
from . import goldmine

SCORES = ("+", "S", "-")
STATUS = {"draft": "In Progress", "decided": "Décidée"}
MAX_CONCEPTS, MAX_CRITERIA = 12, 300

MIGRATIONS = [
    (10, """
        -- D-B-062: Pugh matrices (concept selection against Goldmine requirements).
        CREATE TABLE goldmine_pugh (
            id                  INTEGER PRIMARY KEY,
            project_id          INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            title               TEXT NOT NULL,
            description         TEXT NOT NULL DEFAULT '',
            round               INTEGER NOT NULL DEFAULT 1,
            parent_id           INTEGER REFERENCES goldmine_pugh(id) ON DELETE SET NULL,
            datum_id            INTEGER,
            status              TEXT NOT NULL DEFAULT 'draft',
            decision_concept_id INTEGER,
            decision_note       TEXT NOT NULL DEFAULT '',
            created_by          INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at          TEXT NOT NULL,
            updated_by          INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at          TEXT NOT NULL
        );
        CREATE TABLE goldmine_pugh_concepts (
            id          INTEGER PRIMARY KEY,
            pugh_id     INTEGER NOT NULL REFERENCES goldmine_pugh(id) ON DELETE CASCADE,
            name        TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            position    INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE goldmine_pugh_criteria (
            id       INTEGER PRIMARY KEY,
            pugh_id  INTEGER NOT NULL REFERENCES goldmine_pugh(id) ON DELETE CASCADE,
            issue_id INTEGER NOT NULL REFERENCES agile_issues(id) ON DELETE CASCADE,
            position INTEGER NOT NULL DEFAULT 0,
            UNIQUE (pugh_id, issue_id)
        );
        CREATE TABLE goldmine_pugh_scores (
            criterion_id INTEGER NOT NULL REFERENCES goldmine_pugh_criteria(id) ON DELETE CASCADE,
            concept_id   INTEGER NOT NULL REFERENCES goldmine_pugh_concepts(id) ON DELETE CASCADE,
            score        TEXT NOT NULL CHECK (score IN ('+', 'S', '-')),
            note         TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (criterion_id, concept_id)
        );
        CREATE INDEX idx_goldmine_pugh_project ON goldmine_pugh(project_id);
    """),
]


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------
def _matrix(ctx, project_id, minimum="reader"):
    row = ctx.conn.execute("SELECT * FROM goldmine_pugh WHERE id = ? AND project_id = ?",
                           (validate.int_param(ctx.params, "mid"), project_id)).fetchone()
    if row is None:
        raise ApiError(404, "Pugh Matrix introuvable dans ce Space.")
    return row


def _editable(ctx, row):
    if row["status"] == "decided":
        raise ApiError(409, "Matrice décidée : lecture seule. Correctif : « Rouvrir » la matrice, ou lancez un nouveau tour.")


def _touch(ctx, matrix_id):
    ctx.conn.execute("UPDATE goldmine_pugh SET updated_by = ?, updated_at = ? WHERE id = ?",
                     (ctx.user["id"], db.utc_now(), matrix_id))


def totals(concepts, criteria, scores, datum_id):
    """{concept_id: {plus, same, minus, net, rated, rank}} -- the datum is all S by definition."""
    out = {}
    for concept in concepts:
        t = {"plus": 0, "same": 0, "minus": 0, "rated": 0}
        for crit in criteria:
            value = "S" if concept["id"] == datum_id else scores.get((crit["id"], concept["id"]), {}).get("score")
            if value:
                t["rated"] += 1
                t[{"+": "plus", "S": "same", "-": "minus"}[value]] += 1
        t["net"] = t["plus"] - t["minus"]
        out[concept["id"]] = t
    ordered = sorted({t["net"] for t in out.values()}, reverse=True)
    for t in out.values():
        t["rank"] = 1 + sum(1 for n in ordered if n > t["net"])
    return out


def detail(conn, row):
    key = c.project_key(conn, row["project_id"])
    concepts = [dict(r) for r in conn.execute(
        "SELECT id, name, description, position FROM goldmine_pugh_concepts WHERE pugh_id = ? ORDER BY position, id", (row["id"],))]
    criteria = [dict(r) for r in conn.execute(
        "SELECT k.id, k.issue_id, k.position, i.number, i.title, r.statement, r.category, r.lifecycle, r.criticality, r.kind, "
        "r.external_id, s.name AS status_name FROM goldmine_pugh_criteria k JOIN agile_issues i ON i.id = k.issue_id "
        "JOIN agile_statuses s ON s.id = i.status_id LEFT JOIN agile_requirements r ON r.issue_id = i.id "
        "WHERE k.pugh_id = ? ORDER BY k.position, k.id", (row["id"],))]
    for crit in criteria:
        crit["key"] = "{}-{}".format(key, crit["number"])
    scores = {(r["criterion_id"], r["concept_id"]): {"score": r["score"], "note": r["note"]} for r in conn.execute(
        "SELECT s.* FROM goldmine_pugh_scores s JOIN goldmine_pugh_criteria k ON k.id = s.criterion_id WHERE k.pugh_id = ?",
        (row["id"],))}
    names = {r["id"]: r["display_name"] for r in conn.execute(
        "SELECT id, display_name FROM users WHERE id IN (?, ?)", (row["created_by"], row["updated_by"]))}
    return {"matrix": dict(row, status_label=STATUS.get(row["status"], row["status"]),
                           created_by_name=names.get(row["created_by"], ""), updated_by_name=names.get(row["updated_by"], "")),
            "concepts": concepts, "criteria": criteria,
            "scores": [{"criterion_id": k[0], "concept_id": k[1], **v} for k, v in scores.items()],
            "totals": {str(k): v for k, v in totals(concepts, criteria, scores, row["datum_id"]).items()},
            "labels": {"categories": goldmine.CATEGORIES, "lifecycle": goldmine.LIFECYCLE, "kinds": goldmine.KINDS}}


def api_list(ctx):
    project_id, _ = c.access(ctx)
    rows = ctx.conn.execute(
        "SELECT p.*, (SELECT COUNT(*) FROM goldmine_pugh_concepts WHERE pugh_id = p.id) AS n_concepts, "
        "(SELECT COUNT(*) FROM goldmine_pugh_criteria WHERE pugh_id = p.id) AS n_criteria, "
        "(SELECT name FROM goldmine_pugh_concepts WHERE id = p.decision_concept_id) AS decision_name, "
        "u.display_name AS updated_by_name FROM goldmine_pugh p LEFT JOIN users u ON u.id = p.updated_by "
        "WHERE p.project_id = ? ORDER BY p.updated_at DESC", (project_id,)).fetchall()
    return {"matrices": [dict(r, status_label=STATUS.get(r["status"], r["status"])) for r in rows]}


def api_get(ctx):
    project_id, _ = c.access(ctx)
    return detail(ctx.conn, _matrix(ctx, project_id))


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------
def _text(body, name, label, limit, required=False):
    value = str(body.get(name) or "").strip()
    if required and not value:
        raise ApiError(400, "{} obligatoire.".format(label))
    if len(value) > limit:
        raise ApiError(400, "{} : {} caractères au maximum.".format(label, limit))
    return value


def api_create(ctx):
    project_id, _ = c.access(ctx, "editor")
    if goldmine.requirement_type(ctx.conn, project_id) is None:
        raise ApiError(409, "Goldmine n'est pas activé sur ce Space : la matrice prend ses critères dans les requirements.")
    now = db.utc_now()
    mid = ctx.conn.execute(
        "INSERT INTO goldmine_pugh (project_id, title, description, created_by, created_at, updated_by, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)", (project_id, _text(ctx.body, "title", "Titre", 200, True),
                                         _text(ctx.body, "description", "Description", 4000),
                                         ctx.user["id"], now, ctx.user["id"], now)).lastrowid
    first = None
    for i, name in enumerate(ctx.body.get("concepts") or []):
        cid = _add_concept(ctx, mid, {"name": name}, i)
        first = first or cid
    if first:  # the first concept is the reference (datum) until changed
        ctx.conn.execute("UPDATE goldmine_pugh SET datum_id = ? WHERE id = ?", (first, mid))
    c.log(ctx, "pugh_create", "goldmine_pugh", mid, {"title": ctx.body.get("title")})
    return detail(ctx.conn, ctx.conn.execute("SELECT * FROM goldmine_pugh WHERE id = ?", (mid,)).fetchone())


def api_update(ctx):
    """Title, description, datum, status (draft / decided) and decision."""
    project_id, _ = c.access(ctx, "editor")
    row = _matrix(ctx, project_id)
    body, changes = ctx.body, {}
    reopening = body.get("status") == "draft" and row["status"] == "decided"
    if not reopening:
        _editable(ctx, row)
    concept_ids = {r[0] for r in ctx.conn.execute("SELECT id FROM goldmine_pugh_concepts WHERE pugh_id = ?", (row["id"],))}
    if "title" in body:
        changes["title"] = _text(body, "title", "Titre", 200, True)
    if "description" in body:
        changes["description"] = _text(body, "description", "Description", 4000)
    if "datum_id" in body:
        value = body.get("datum_id")
        if value not in (None, "") and int(value) not in concept_ids:
            raise ApiError(400, "La référence (datum) doit être un des concepts de la matrice.")
        changes["datum_id"] = int(value) if value not in (None, "") else None
    if "decision_note" in body:
        changes["decision_note"] = _text(body, "decision_note", "Rationale", 4000)
    if "status" in body:
        if body["status"] not in STATUS:
            raise ApiError(400, "Status inconnu : En cours (draft) ou Décidée (decided).")
        changes["status"] = body["status"]
        if body["status"] == "decided":
            chosen = body.get("decision_concept_id")
            if chosen in (None, "") or int(chosen) not in concept_ids:
                raise ApiError(400, "Décider demande le concept retenu. Correctif : choisissez-le dans la liste.")
            changes["decision_concept_id"] = int(chosen)
    if changes:
        sets = ", ".join("{} = ?".format(k) for k in changes)
        ctx.conn.execute("UPDATE goldmine_pugh SET {} WHERE id = ?".format(sets), tuple(changes.values()) + (row["id"],))
        _touch(ctx, row["id"])
        c.log(ctx, "pugh_update", "goldmine_pugh", row["id"], {"fields": sorted(changes)})
    return detail(ctx.conn, _matrix(ctx, project_id))


def api_delete(ctx):
    project_id, _ = c.access(ctx, "admin")
    row = _matrix(ctx, project_id)
    ctx.conn.execute("DELETE FROM goldmine_pugh WHERE id = ?", (row["id"],))
    c.log(ctx, "pugh_delete", "goldmine_pugh", row["id"], {"title": row["title"]})
    return {"ok": True}


def _add_concept(ctx, mid, body, position=None):
    n = ctx.conn.execute("SELECT COUNT(*) FROM goldmine_pugh_concepts WHERE pugh_id = ?", (mid,)).fetchone()[0]
    if n >= MAX_CONCEPTS:
        raise ApiError(409, "{} concepts au maximum par matrice.".format(MAX_CONCEPTS))
    return ctx.conn.execute(
        "INSERT INTO goldmine_pugh_concepts (pugh_id, name, description, position) VALUES (?, ?, ?, ?)",
        (mid, _text(body, "name", "Nom du concept", 80, True), _text(body, "description", "Description", 1000),
         n if position is None else position)).lastrowid


def api_concept_add(ctx):
    project_id, _ = c.access(ctx, "editor")
    row = _matrix(ctx, project_id)
    _editable(ctx, row)
    cid = _add_concept(ctx, row["id"], ctx.body)
    if row["datum_id"] is None:  # the first concept is the reference until changed
        ctx.conn.execute("UPDATE goldmine_pugh SET datum_id = ? WHERE id = ?", (cid, row["id"]))
    _touch(ctx, row["id"])
    c.log(ctx, "pugh_concept_add", "goldmine_pugh", row["id"], {"concept": ctx.body.get("name")})
    return detail(ctx.conn, _matrix(ctx, project_id))


def api_concept_update(ctx):
    project_id, _ = c.access(ctx, "editor")
    row = _matrix(ctx, project_id)
    _editable(ctx, row)
    cid = validate.int_param(ctx.params, "cid")
    if ctx.body.get("delete"):
        ctx.conn.execute("DELETE FROM goldmine_pugh_concepts WHERE id = ? AND pugh_id = ?", (cid, row["id"]))
        if row["datum_id"] == cid:
            ctx.conn.execute("UPDATE goldmine_pugh SET datum_id = NULL WHERE id = ?", (row["id"],))
        action = "pugh_concept_delete"
    else:
        ctx.conn.execute("UPDATE goldmine_pugh_concepts SET name = ?, description = ? WHERE id = ? AND pugh_id = ?",
                         (_text(ctx.body, "name", "Nom du concept", 80, True),
                          _text(ctx.body, "description", "Description", 1000), cid, row["id"]))
        action = "pugh_concept_update"
    _touch(ctx, row["id"])
    c.log(ctx, action, "goldmine_pugh", row["id"], {"concept_id": cid})
    return detail(ctx.conn, _matrix(ctx, project_id))


def api_criteria_add(ctx):
    """Add requirements as criteria: {numbers: [12, 13]} or {lifecycle: "assembly"} or {category: "..."}."""
    project_id, _ = c.access(ctx, "editor")
    row = _matrix(ctx, project_id)
    _editable(ctx, row)
    base = ("SELECT i.id FROM agile_issues i JOIN agile_issue_types t ON t.id = i.type_id AND t.is_requirement = 1 "
            "JOIN agile_statuses s ON s.id = i.status_id LEFT JOIN agile_requirements r ON r.issue_id = i.id "
            "WHERE i.project_id = ? AND s.name NOT IN ('Rejected', 'Obsolete')")
    if ctx.body.get("numbers"):
        numbers = [int(n) for n in ctx.body["numbers"]][:MAX_CRITERIA]
        ids = [r[0] for r in ctx.conn.execute(base + " AND i.number IN ({}) ORDER BY i.number".format(
            ",".join("?" * len(numbers))), [project_id] + numbers)]
        if len(ids) != len(set(numbers)):
            raise ApiError(400, "Seules les requirements Goldmine actives de ce Space peuvent servir de critères.")
    elif ctx.body.get("lifecycle"):
        ids = [r[0] for r in ctx.conn.execute(base + " AND r.lifecycle = ? ORDER BY i.number", (project_id, ctx.body["lifecycle"]))]
    elif ctx.body.get("kind") in goldmine.KINDS:  # D-B-064: every stakeholder need (or every requirement)
        ids = [r[0] for r in ctx.conn.execute(base + " AND COALESCE(r.kind, 'requirement') = ? ORDER BY i.number",
                                              (project_id, ctx.body["kind"]))]
    elif ctx.body.get("category"):
        ids = [r[0] for r in ctx.conn.execute(base + " AND r.category = ? ORDER BY i.number", (project_id, ctx.body["category"]))]
    else:
        raise ApiError(400, "Choisissez un requirement, une phase ou une category à ajouter.")
    position = ctx.conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM goldmine_pugh_criteria WHERE pugh_id = ?",
                                (row["id"],)).fetchone()[0]
    added = 0
    for issue_id in ids:
        if ctx.conn.execute("SELECT COUNT(*) FROM goldmine_pugh_criteria WHERE pugh_id = ?", (row["id"],)).fetchone()[0] >= MAX_CRITERIA:
            raise ApiError(409, "{} critères au maximum par matrice.".format(MAX_CRITERIA))
        cur = ctx.conn.execute("INSERT OR IGNORE INTO goldmine_pugh_criteria (pugh_id, issue_id, position) VALUES (?, ?, ?)",
                               (row["id"], issue_id, position + added))
        added += cur.rowcount
    _touch(ctx, row["id"])
    c.log(ctx, "pugh_criteria_add", "goldmine_pugh", row["id"], {"added": added})
    result = detail(ctx.conn, _matrix(ctx, project_id))
    result["added"] = added
    return result


def api_criterion_delete(ctx):
    project_id, _ = c.access(ctx, "editor")
    row = _matrix(ctx, project_id)
    _editable(ctx, row)
    ctx.conn.execute("DELETE FROM goldmine_pugh_criteria WHERE id = ? AND pugh_id = ?",
                     (validate.int_param(ctx.params, "kid"), row["id"]))
    _touch(ctx, row["id"])
    c.log(ctx, "pugh_criterion_delete", "goldmine_pugh", row["id"], {"criterion_id": ctx.params.get("kid")})
    return detail(ctx.conn, _matrix(ctx, project_id))


def api_score(ctx):
    """{criterion_id, concept_id, score: + | S | - | "" (clear), note}"""
    project_id, _ = c.access(ctx, "editor")
    row = _matrix(ctx, project_id)
    _editable(ctx, row)
    crit, concept = int(ctx.body.get("criterion_id") or 0), int(ctx.body.get("concept_id") or 0)
    if not ctx.conn.execute("SELECT 1 FROM goldmine_pugh_criteria WHERE id = ? AND pugh_id = ?", (crit, row["id"])).fetchone() \
            or not ctx.conn.execute("SELECT 1 FROM goldmine_pugh_concepts WHERE id = ? AND pugh_id = ?", (concept, row["id"])).fetchone():
        raise ApiError(400, "Case introuvable dans cette matrice.")
    if concept == row["datum_id"]:
        raise ApiError(400, "La colonne de référence (datum) vaut « S » par définition.")
    score = str(ctx.body.get("score") or "").strip().upper()
    note = _text(ctx.body, "note", "Note", 1000)
    if score == "":
        ctx.conn.execute("DELETE FROM goldmine_pugh_scores WHERE criterion_id = ? AND concept_id = ?", (crit, concept))
    elif score not in SCORES:
        raise ApiError(400, "Note « {} » refusée : + (meilleur), S (pareil) ou - (moins bon) que la référence.".format(score))
    else:
        ctx.conn.execute("INSERT INTO goldmine_pugh_scores (criterion_id, concept_id, score, note) VALUES (?, ?, ?, ?) "
                         "ON CONFLICT(criterion_id, concept_id) DO UPDATE SET score = excluded.score, note = excluded.note",
                         (crit, concept, score, note))
    _touch(ctx, row["id"])
    c.log(ctx, "pugh_score", "goldmine_pugh", row["id"], {"criterion_id": crit, "concept_id": concept, "score": score})
    return detail(ctx.conn, _matrix(ctx, project_id))


def api_round(ctx):
    """New round: {datum_id, keep: [concept ids]} -- concepts kept, same criteria, empty scores."""
    project_id, _ = c.access(ctx, "editor")
    row = _matrix(ctx, project_id)
    concepts = ctx.conn.execute("SELECT * FROM goldmine_pugh_concepts WHERE pugh_id = ? ORDER BY position, id", (row["id"],)).fetchall()
    keep = {int(x) for x in (ctx.body.get("keep") or [r["id"] for r in concepts])}
    datum = int(ctx.body.get("datum_id") or 0)
    if datum not in keep:
        raise ApiError(400, "La nouvelle référence doit être un des concepts gardés.")
    now = db.utc_now()
    mid = ctx.conn.execute(
        "INSERT INTO goldmine_pugh (project_id, title, description, round, parent_id, created_by, created_at, updated_by, "
        "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (project_id, row["title"], row["description"], row["round"] + 1, row["id"], ctx.user["id"], now, ctx.user["id"], now)).lastrowid
    new_datum = None
    for i, concept in enumerate(r for r in concepts if r["id"] in keep):
        cid = ctx.conn.execute("INSERT INTO goldmine_pugh_concepts (pugh_id, name, description, position) VALUES (?, ?, ?, ?)",
                               (mid, concept["name"], concept["description"], i)).lastrowid
        if concept["id"] == datum:
            new_datum = cid
    ctx.conn.execute("UPDATE goldmine_pugh SET datum_id = ? WHERE id = ?", (new_datum, mid))
    ctx.conn.execute("INSERT INTO goldmine_pugh_criteria (pugh_id, issue_id, position) "
                     "SELECT ?, issue_id, position FROM goldmine_pugh_criteria WHERE pugh_id = ?", (mid, row["id"]))
    c.log(ctx, "pugh_round", "goldmine_pugh", mid, {"from": row["id"], "round": row["round"] + 1})
    return detail(ctx.conn, ctx.conn.execute("SELECT * FROM goldmine_pugh WHERE id = ?", (mid,)).fetchone())


def on_restore(conn, maps, old_key, new_key):
    """Backup restore (core lot v0.10): the datum and the decision point to concepts by id, not by foreign key."""
    concepts = maps.get("goldmine_pugh_concepts", {})
    for old_id, new_id in maps.get("goldmine_pugh", {}).items():
        row = conn.execute("SELECT datum_id, decision_concept_id FROM goldmine_pugh WHERE id = ?", (new_id,)).fetchone()
        if row:
            conn.execute("UPDATE goldmine_pugh SET datum_id = ?, decision_concept_id = ? WHERE id = ?",
                         (concepts.get(row["datum_id"]), concepts.get(row["decision_concept_id"]), new_id))
