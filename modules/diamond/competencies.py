"""Diamond · « Compétences et équipe » (0.60.116, D-O-129): who the product needs, read from its functions.

Each function line of the tree that ends with a brick (CB-n, the standard concept known in the industry that carries it) gets
a dashed grid: one column per competency (Mechanical design, Thermal analysis, FEA, HW / PCB design…), a rating from 1 (almost
not involved) to 5 (at the heart of the development) of how much that competency is needed to develop a concept for this
function -- an assumption, refined by the team; an AI assistant may fill all of it at once through « ↔ IA » (rt_sections_d.py),
every cell stays editable by hand. The summary adds the points per competency over the lines: its share of the whole says
the ratio of the team to build, and the evaluator writes in the last column how many people to hire or to gather.

The catalogue of the competencies is the platform's (one list for every Space, held by the DEMO Space where the « Base de
connaissances (BDC) » lives): code, name, icon, and the content of its BDC page (competency_bdc.py). Only an administrator,
or an « Admin du Space » of DEMO, changes it; a competency is never deleted, only deactivated (its ratings stay).
Every write is journalled.
"""
import json
import re

from core import audit, db, permissions, validate
from core.errors import ApiError

from . import data_competencies as DC
from . import functions as F

CODE_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}$")
LIMITS = {"name": 60, "summary": 200, "detail": 1200, "note": 300}
MAX_PEOPLE = 999


def host_id(conn):
    """The DEMO Space, which holds the catalogue and the BDC (None before it exists)."""
    from modules.help.headlamp import project_id
    return project_id(conn)


def _public(code, name, icon, summary, details, position, active=1):
    return {"code": code, "name": name, "icon": icon, "summary": summary, "details": details, "position": position,
            "active": bool(active)}


def catalog(conn, active_only=False):
    """The competencies, in their order (the defaults, read-only, until the catalogue is seeded)."""
    rows = conn.execute("SELECT * FROM diamond_competencies ORDER BY position, code").fetchall()
    if rows:
        out = [_public(r["code"], r["name"], r["icon"], r["summary"], json.loads(r["details"] or "{}"), r["position"], r["active"])
               for r in rows]
    else:
        out = [_public(d[0], d[1], d[2], d[3], dict(zip(DC.DETAIL_KEYS, d[4:])), i + 1) for i, d in enumerate(DC.DEFAULTS)]
    return [c for c in out if c["active"]] if active_only else out


def seed(conn):
    """The default competencies the catalogue is missing (never overwrites what an administrator changed)."""
    pid = host_id(conn)
    if pid is None:
        return 0
    have = {r[0] for r in conn.execute("SELECT code FROM diamond_competencies")}
    now, added = db.utc_now(), 0
    for i, d in enumerate(DC.DEFAULTS):
        if d[0] not in have:
            conn.execute("INSERT INTO diamond_competencies (project_id, code, name, icon, summary, details, position, active, created_at, "
                         "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
                         (pid, d[0], d[1], d[2], d[3], json.dumps(dict(zip(DC.DETAIL_KEYS, d[4:])), ensure_ascii=False), i + 1, now, now))
            added += 1
    return added


def can_manage(conn, user):
    pid = host_id(conn)
    return pid is not None and permissions.is_project_manager(conn, user, pid)


# ---------------------------------------------------------------- the lines of the Space

def _tree_order(fns):
    """The functions in the order of the tree (depth first, siblings by position), then the others."""
    kids = {}
    for f in fns:
        kids.setdefault(f["parent_id"], []).append(f)
    out, seen = [], set()

    def walk(f):
        if f["id"] in seen:
            return
        seen.add(f["id"])
        out.append(f)
        for k in sorted((k for k in kids.get(f["id"], []) if not k["is_primary"]), key=lambda k: (k["position"], k["number"])):
            walk(k)
    for f in fns:
        if f["is_primary"]:
            walk(f)
    for f in fns:
        walk(f)
    return out


def lines(conn, pid):
    """[{function_id, code, text, level, brick, ratings}] -- the functions that end with a brick, in the order of the tree."""
    fns = F.rows(conn, pid)
    lv = F.levels(fns)
    bricks = {r["function_id"]: dict(r) for r in conn.execute(
        "SELECT l.function_id, c.id, c.number, c.name, c.kind, c.frozen, c.frozen_text FROM diamond_concept_functions l "
        "JOIN diamond_concepts c ON c.id = l.concept_id AND c.archived = 0 WHERE l.project_id = ?", (pid,))}
    ratings = {}
    for r in conn.execute("SELECT function_id, code, rating, source FROM diamond_competency_ratings WHERE project_id = ?", (pid,)):
        ratings.setdefault(r["function_id"], {})[r["code"]] = r["rating"]
    out = []
    for f in _tree_order(fns):
        b = bricks.get(f["id"])
        if b is None:
            continue
        out.append({"function_id": f["id"], "code": "F{}".format(f["number"]), "text": f["text"], "level": lv[f["id"]],
                    "brick": {"id": b["id"], "code": "CB-{}".format(b["number"]), "name": b["name"], "kind": b["kind"],
                              "frozen": bool(b["frozen"]), "frozen_text": b["frozen_text"]},
                    "ratings": ratings.get(f["id"], {})})
    return out


def columns(conn, pid, rows=None):
    """The competencies of the grid of this Space, in order: those the team added (diamond_competency_columns), then any other
    one a line rates (an AI answer may bring one). 0.60.117 (D-O-130): a Space shows the 4 or 5 it needs, not the whole catalogue."""
    out = [r[0] for r in conn.execute("SELECT code FROM diamond_competency_columns WHERE project_id = ? ORDER BY position, code", (pid,))]
    rated = set()
    for ln in rows if rows is not None else lines(conn, pid):
        rated.update(ln["ratings"])
    order = {c["code"]: c["position"] for c in catalog(conn)}
    return out + sorted((c for c in rated if c not in out), key=lambda c: (order.get(c, 999), c))


def staff(conn, pid):
    return {r["code"]: {"people": r["people"], "note": r["note"]} for r in
            conn.execute("SELECT code, people, note FROM diamond_competency_staff WHERE project_id = ?", (pid,))}


def summary(cat, rows, people):
    """Points per competency over the lines, its share of the whole, and the people the evaluator plans."""
    total = sum(sum(r["ratings"].values()) for r in rows)
    out = []
    for c in cat:
        values = [r["ratings"][c["code"]] for r in rows if c["code"] in r["ratings"]]
        plan = people.get(c["code"], {})
        if not values and not plan.get("people") and not plan.get("note"):
            continue
        points = sum(values)
        out.append({"code": c["code"], "name": c["name"], "icon": c["icon"], "lines": len(values), "points": points,
                    "share": round(100.0 * points / total, 1) if total else 0.0,
                    "average": round(points / len(values), 1) if values else 0.0, "high": sum(1 for v in values if v >= 4),
                    "people": plan.get("people", 0), "note": plan.get("note", "")})
    out.sort(key=lambda s: (-s["points"], s["code"]))
    return out, total


def payload(conn, pid, user=None):
    from . import competency_bdc
    cat = catalog(conn)
    rows, people = lines(conn, pid), staff(conn, pid)
    rows_summary, total = summary(cat, rows, people)
    links = competency_bdc.page_links(conn)
    for c in cat:
        c["bdc"] = links.get(c["code"])
    return {"catalog": cat, "lines": rows, "columns": columns(conn, pid, rows), "summary": rows_summary, "total_points": total,
            "people_total": round(sum(s["people"] for s in rows_summary), 1),
            "can_manage": bool(user) and can_manage(conn, user), "icons": list(DC.ICONS), "detail_labels": DC.DETAIL_LABELS,
            "bdc_hub": links.get("_hub")}


# ---------------------------------------------------------------- routes of a Space

def api_get(ctx):
    pid = F.access(ctx)
    return payload(ctx.conn, pid, ctx.user)


def _known_code(conn, value, keep=()):
    code = str(value or "").strip().upper()
    cat = {c["code"]: c for c in catalog(conn)}
    if code not in cat:
        raise ApiError(400, "Compétence « {} » inconnue. Correctif : un code du catalogue ({}).".format(code[:12], ", ".join(cat)))
    if not cat[code]["active"] and code not in keep:
        raise ApiError(400, "Compétence {} désactivée dans le catalogue. Correctif : choisissez-en une autre, ou réactivez-la "
                            "(⚙ catalogue de « Compétences et équipe »).".format(code))
    return code


def _line(conn, pid, fid):
    """A function of this Space that ends with a brick (only those lines are rated)."""
    row = conn.execute("SELECT f.number FROM diamond_functions f JOIN diamond_concept_functions l ON l.function_id = f.id "
                       "JOIN diamond_concepts c ON c.id = l.concept_id AND c.archived = 0 WHERE f.id = ? AND f.project_id = ? "
                       "AND f.archived = 0", (fid, pid)).fetchone()
    if row is None:
        raise ApiError(400, "Fonction {} sans brique technologique dans ce Space. Correctif : donnez-lui d'abord sa brique "
                            "(CB-n), puis notez les compétences de sa ligne.".format(fid))
    return row["number"]


def _rating(value):
    if value in (None, "", 0, "0"):
        return 0
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ApiError(400, "Note « {} » : un entier de 1 à 5 attendu (0 ou vide retire la compétence).".format(str(value)[:10]))
    if not 0 <= n <= 5:
        raise ApiError(400, "Note {} : de 1 (presque pas impliquée) à 5 (au cœur du développement), 0 pour retirer.".format(n))
    return n


def write_line(conn, user_id, pid, fid, ratings, source="team"):
    """Sets the ratings of one line: {code: 1..5 (0 removes)}; the codes left out keep their rating."""
    for code, value in ratings.items():
        n = _rating(value)
        if n == 0:
            conn.execute("DELETE FROM diamond_competency_ratings WHERE function_id = ? AND code = ?", (fid, code))
        else:
            conn.execute("INSERT INTO diamond_competency_ratings (project_id, function_id, code, rating, source, updated_by, updated_at) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(function_id, code) DO UPDATE SET rating = excluded.rating, "
                         "source = excluded.source, updated_by = excluded.updated_by, updated_at = excluded.updated_at",
                         (pid, fid, code, n, source, user_id, db.utc_now()))


def api_rate(ctx):
    """{function_id, code, rating}: one cell of the grid (rating 0 or empty removes the competency from the line)."""
    pid = F.access(ctx, "editor")
    fid = int(ctx.body.get("function_id") or 0)
    number = _line(ctx.conn, pid, fid)
    current = {r[0] for r in ctx.conn.execute("SELECT code FROM diamond_competency_ratings WHERE function_id = ?", (fid,))}
    code = _known_code(ctx.conn, ctx.body.get("code"), keep=current)
    rating = _rating(ctx.body.get("rating"))
    write_line(ctx.conn, ctx.user["id"], pid, fid, {code: rating})
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_competency_rate", "diamond_function", fid,
                     {"function": "F{}".format(number), "code": code, "rating": rating}, ctx.ip)
    return payload(ctx.conn, pid, ctx.user)


def api_line(ctx):
    """{ratings: {code: 1..5}}: the whole line of a function -- the codes left out leave the line (the « ↔ IA » import)."""
    pid = F.access(ctx, "editor")
    fid = validate.int_param(ctx.params, "fid")
    number = _line(ctx.conn, pid, fid)
    given = ctx.body.get("ratings")
    if not isinstance(given, dict):
        raise ApiError(400, "ratings : un objet {code de compétence : note de 1 à 5} attendu.")
    current = {r[0] for r in ctx.conn.execute("SELECT code FROM diamond_competency_ratings WHERE function_id = ?", (fid,))}
    clean = {_known_code(ctx.conn, k, keep=current): _rating(v) for k, v in given.items()}
    clean.update({c: 0 for c in current if c not in clean})
    write_line(ctx.conn, ctx.user["id"], pid, fid, clean, source=str(ctx.body.get("source") or "team")[:8])
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_competency_line", "diamond_function", fid,
                     {"function": "F{}".format(number), "ratings": {k: v for k, v in clean.items() if v}}, ctx.ip)
    return payload(ctx.conn, pid, ctx.user)


def api_staff(ctx):
    """{code, people, note}: the people to hire or to gather for one competency (the last column of the summary)."""
    pid = F.access(ctx, "editor")
    code = _known_code(ctx.conn, ctx.body.get("code"), keep=set(staff(ctx.conn, pid)))
    try:
        people = round(float(ctx.body.get("people") or 0), 1)
    except (TypeError, ValueError):
        raise ApiError(400, "Personnes : un nombre attendu (ex. 1, 0.5 pour une demi-personne).")
    if not 0 <= people <= MAX_PEOPLE:
        raise ApiError(400, "Personnes : de 0 à {}.".format(MAX_PEOPLE))
    note = " ".join(str(ctx.body.get("note") or "").split())
    if len(note) > LIMITS["note"]:
        raise ApiError(400, "Note : {} caractères au maximum.".format(LIMITS["note"]))
    ctx.conn.execute("INSERT INTO diamond_competency_staff (project_id, code, people, note, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?) "
                     "ON CONFLICT(project_id, code) DO UPDATE SET people = excluded.people, note = excluded.note, "
                     "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
                     (pid, code, people, note, ctx.user["id"], db.utc_now()))
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_competency_staff", "project", pid, {"code": code, "people": people}, ctx.ip)
    return payload(ctx.conn, pid, ctx.user)


def api_column_add(ctx):
    """{code}: the competency becomes a column of the grid of this Space (at the end)."""
    pid = F.access(ctx, "editor")
    code = _known_code(ctx.conn, ctx.body.get("code"))
    current = columns(ctx.conn, pid)
    if code not in current:
        current.append(code)
    _save_columns(ctx.conn, pid, current)
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_competency_column_add", "project", pid, {"code": code}, ctx.ip)
    return payload(ctx.conn, pid, ctx.user)


def api_column_remove(ctx):
    """The competency leaves the grid of this Space, with its ratings on the lines (the people planned for it stay)."""
    pid = F.access(ctx, "editor")
    code = str(ctx.params.get("code") or "").upper()
    current = columns(ctx.conn, pid)
    if code not in current:
        raise ApiError(404, "{} n'est pas une colonne de la grille de ce Space. Correctif : rechargez la page.".format(code[:12]))
    removed = ctx.conn.execute("DELETE FROM diamond_competency_ratings WHERE project_id = ? AND code = ?", (pid, code)).rowcount
    _save_columns(ctx.conn, pid, [c for c in current if c != code])
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_competency_column_remove", "project", pid, {"code": code, "ratings": removed}, ctx.ip)
    return payload(ctx.conn, pid, ctx.user)


def _save_columns(conn, pid, codes):
    conn.execute("DELETE FROM diamond_competency_columns WHERE project_id = ?", (pid,))
    for i, code in enumerate(codes):
        conn.execute("INSERT INTO diamond_competency_columns (project_id, code, position) VALUES (?, ?, ?)", (pid, code, i + 1))
