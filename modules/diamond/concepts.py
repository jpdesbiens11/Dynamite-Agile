"""Diamond · « Concept / Brique technologique » (0.60.105, D-O-117).

The tree of the functions answers « what must the product do? »; the bricks answer « with what? ». A brick (CB-1, CB-2…,
numbers kept for ever) is the technological building block -- or the concept -- that carries one or several functions
of the tree: several tertiary functions often share the same brick, so a function belongs to one brick at most and a
brick is drawn once, in its own column after the tertiary functions, linked to each of its functions.

Each brick starts with an **initial concept with a name that speaks** (initial_name: « Sandwich froid », « Tête-radiateur »): the
idea the team rallies around before any sheet is drawn. Divergence (sheets) and convergence (Pugh) often pivot away from it; the
selected sheet is then shown next to the initial concept, and pivot_note says what changed and why -- the story of the idea.

A brick is « existing » (an off-the-shelf concept the team can refer to: a catalogue part, a known technology, a
previous product) or « to define » (to be invented: concept sheets, digital or scanned paper, then Pugh matrices that
judge groups of bricks against the needs, the functions and the requirements -- concept_sheets.py, concept_pugh.py).
An AI assistant may propose the bricks when the Space is generated (core/starter_diamond.py, source « ai ») and the team
edits them. Every write is journalled.
"""
from core import audit, db, validate
from core.errors import ApiError

from . import functions as F

KINDS = {"existing": "Concept existant", "to_define": "À définir"}
STATUS = {"proposed": "Proposed", "exploring": "Exploring", "evaluating": "Evaluating", "selected": "Selected",
          "dropped": "Dropped"}
SOURCES = {"team": "Équipe", "ai": "Brouillon IA"}
LIMITS = {"name": 120, "initial_name": 80, "pivot_note": 1000, "description": 2000, "reference": 300}
MAX_CONCEPTS = 120


def code(number):
    return "CB-{}".format(number)


def _clean(body, name, label, required=False):
    value = " ".join(str(body.get(name) or "").split()) if name not in ("description", "pivot_note") else str(body.get(name) or "").strip()
    if required and not value:
        raise ApiError(400, "{} obligatoire. Correctif : quelques mots (ex. « Module de cellules 21700 en parallèle »).".format(label))
    if len(value) > LIMITS[name]:
        raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, LIMITS[name], len(value)))
    return value


def _choice(body, name, options, label, default):
    value = str(body.get(name) or default)
    if value not in options:
        raise ApiError(400, "{} « {} » inconnu. Correctif : {}.".format(label, value[:30], ", ".join(options)))
    return value


def rows(conn, pid):
    items = [dict(r) for r in conn.execute(
        "SELECT * FROM diamond_concepts WHERE project_id = ? AND archived = 0 ORDER BY position, number", (pid,))]
    links = {}
    for r in conn.execute("SELECT l.concept_id, l.function_id FROM diamond_concept_functions l JOIN diamond_functions f "
                          "ON f.id = l.function_id AND f.archived = 0 WHERE l.project_id = ? ORDER BY f.position, f.number", (pid,)):
        links.setdefault(r["concept_id"], []).append(r["function_id"])
    sheets = {}
    for r in conn.execute("SELECT concept_id, COUNT(*) AS n, SUM(status = 'selected') AS chosen FROM diamond_concept_sheets "
                          "WHERE project_id = ? AND archived = 0 GROUP BY concept_id", (pid,)):
        sheets[r["concept_id"]] = (r["n"], r["chosen"] or 0)
    chosen = {}
    for r in conn.execute("SELECT concept_id, number, title FROM diamond_concept_sheets WHERE project_id = ? AND archived = 0 "
                          "AND status = 'selected' ORDER BY updated_at DESC", (pid,)):
        chosen.setdefault(r["concept_id"], r)
    pughs = {}
    for r in conn.execute("SELECT s.concept_id, p.id, p.title, p.round, p.status FROM diamond_pugh_scope s JOIN goldmine_pugh p "
                          "ON p.id = s.pugh_id WHERE s.project_id = ? ORDER BY p.created_at", (pid,)):
        pughs.setdefault(r["concept_id"], []).append({"id": r["id"], "title": r["title"], "round": r["round"], "status": r["status"]})
    for c in items:
        c["code"] = code(c["number"])
        c["function_ids"] = links.get(c["id"], [])
        c["sheets"], c["sheets_selected"] = sheets.get(c["id"], (0, 0))
        c["pughs"] = pughs.get(c["id"], [])
        s = chosen.get(c["id"])  # the sheet a decided Pugh matrix selected: where the initial concept landed after the pivots
        c["selected_sheet"] = {"code": "CB-{}.{}".format(c["number"], s["number"]), "title": s["title"]} if s else None
    return items


def payload(conn, pid):
    fns = F.rows(conn, pid)
    lv, tree = F.levels(fns), F.in_tree(fns)
    return {"concepts": rows(conn, pid),
            "functions": [{"id": f["id"], "number": f["number"], "text": f["text"], "level": lv[f["id"]], "kano": f["kano"],
                           "ftype": f["ftype"], "in_tree": f["id"] in tree, "parent_id": f["parent_id"]} for f in fns],
            "labels": {"kinds": KINDS, "status": STATUS, "sources": SOURCES, "kano": F.KANO, "types": F.TYPES}}


def _concept(conn, pid, cid):
    row = conn.execute("SELECT * FROM diamond_concepts WHERE id = ? AND project_id = ? AND archived = 0", (cid, pid)).fetchone()
    if row is None:
        raise ApiError(404, "Brique introuvable dans ce Space (archivée ?). Correctif : rechargez la page.")
    return dict(row)


def _functions_of(conn, pid, ids):
    """The function ids of the body, checked: functions of this Space, not archived."""
    if not isinstance(ids, list):
        raise ApiError(400, "function_ids : liste d'identifiants de fonctions attendue.")
    out = []
    for value in ids:
        fid = int(value)
        if not conn.execute("SELECT 1 FROM diamond_functions WHERE id = ? AND project_id = ? AND archived = 0", (fid, pid)).fetchone():
            raise ApiError(400, "Fonction {} introuvable dans ce Space. Correctif : rechargez l'arbre.".format(fid))
        out.append(fid)
    return list(dict.fromkeys(out))


def link(conn, pid, cid, fids):
    """The functions join the brick (a function belongs to one brick at most: it leaves its former one)."""
    for fid in fids:
        conn.execute("INSERT INTO diamond_concept_functions (project_id, concept_id, function_id) VALUES (?, ?, ?) "
                     "ON CONFLICT(function_id) DO UPDATE SET concept_id = excluded.concept_id", (pid, cid, fid))


def add(conn, user_id, pid, fields, fids=(), source="team"):
    """Creates a brick (also used by the Project Starter and the AI import); returns its id."""
    n = conn.execute("SELECT COUNT(*) FROM diamond_concepts WHERE project_id = ? AND archived = 0", (pid,)).fetchone()[0]
    if n >= MAX_CONCEPTS:
        raise ApiError(409, "{} briques au maximum par Space. Correctif : regroupez les fonctions qui partagent une brique.".format(MAX_CONCEPTS))
    number = conn.execute("SELECT COALESCE(MAX(number), 0) + 1 FROM diamond_concepts WHERE project_id = ?", (pid,)).fetchone()[0]
    now = db.utc_now()
    cid = conn.execute(
        "INSERT INTO diamond_concepts (project_id, number, name, initial_name, description, kind, reference, status, source, position, "
        "created_by, created_at, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (pid, number, fields["name"], fields.get("initial_name", ""), fields.get("description", ""), fields.get("kind", "to_define"), fields.get("reference", ""),
         fields.get("status", "proposed"), source, number, user_id, now, user_id, now)).lastrowid
    link(conn, pid, cid, fids)
    return cid


def _fields(body, partial=False):
    out = {}
    if not partial or "name" in body:
        out["name"] = _clean(body, "name", "Nom de la brique", required=True)
    for name, label in (("initial_name", "Concept initial"), ("pivot_note", "Pivot"), ("description", "Description"), ("reference", "Référence")):
        if not partial or name in body:
            out[name] = _clean(body, name, label)
    if not partial or "kind" in body:
        out["kind"] = _choice(body, "kind", KINDS, "Nature", "to_define")
    if not partial or "status" in body:
        out["status"] = _choice(body, "status", STATUS, "Status", "proposed")
    return out


def api_list(ctx):
    pid = F.access(ctx)
    return payload(ctx.conn, pid)


def api_get(ctx):
    """One brick with its functions, its concept sheets and the Pugh matrices that judge it."""
    from . import concept_sheets as S
    pid = F.access(ctx)
    c = next((x for x in rows(ctx.conn, pid) if x["id"] == validate.int_param(ctx.params, "cid")), None)
    if c is None:
        raise ApiError(404, "Brique introuvable dans ce Space (archivée ?). Correctif : rechargez la page.")
    data = payload(ctx.conn, pid)
    data["concept"] = c
    data["sheets"] = S.rows(ctx.conn, pid, c["id"])
    return data


def api_create(ctx):
    pid = F.access(ctx, "editor")
    fields = _fields(ctx.body)
    fids = _functions_of(ctx.conn, pid, ctx.body.get("function_ids") or [])
    cid = add(ctx.conn, ctx.user["id"], pid, fields, fids)
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_concept_create", "diamond_concept", cid,
                     {"name": fields["name"], "functions": fids}, ctx.ip)
    data = payload(ctx.conn, pid)
    data["created"] = cid
    return data


def api_update(ctx):
    """Fields, and function_ids (the full list of the brick's functions) when given."""
    pid = F.access(ctx, "editor")
    c = _concept(ctx.conn, pid, validate.int_param(ctx.params, "cid"))
    fields = _fields(ctx.body, partial=True)
    if fields:
        sets = ", ".join("{} = ?".format(k) for k in fields)
        ctx.conn.execute("UPDATE diamond_concepts SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(sets),
                         tuple(fields.values()) + (ctx.user["id"], db.utc_now(), c["id"]))
    if "function_ids" in ctx.body:
        fids = _functions_of(ctx.conn, pid, ctx.body["function_ids"])
        ctx.conn.execute("DELETE FROM diamond_concept_functions WHERE concept_id = ?", (c["id"],))
        link(ctx.conn, pid, c["id"], fids)
        fields["functions"] = fids
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_concept_update", "diamond_concept", c["id"], {"fields": sorted(fields)}, ctx.ip)
    return payload(ctx.conn, pid)


def api_link(ctx):
    """{function_id, concept_id | null}: the brick of one function, from the panel of the tree."""
    pid = F.access(ctx, "editor")
    fid = _functions_of(ctx.conn, pid, [ctx.body.get("function_id")])[0]
    target = ctx.body.get("concept_id")
    if target in (None, ""):
        ctx.conn.execute("DELETE FROM diamond_concept_functions WHERE function_id = ? AND project_id = ?", (fid, pid))
        cid = None
    else:
        cid = _concept(ctx.conn, pid, int(target))["id"]
        link(ctx.conn, pid, cid, [fid])
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_concept_link", "diamond_function", fid, {"concept_id": cid}, ctx.ip)
    return payload(ctx.conn, pid)


def api_archive(ctx):
    """The brick leaves the column and the list; its number is never given again, its sheets and matrices stay."""
    pid = F.access(ctx, "editor")
    c = _concept(ctx.conn, pid, validate.int_param(ctx.params, "cid"))
    ctx.conn.execute("UPDATE diamond_concepts SET archived = 1, updated_by = ?, updated_at = ? WHERE id = ?",
                     (ctx.user["id"], db.utc_now(), c["id"]))
    ctx.conn.execute("DELETE FROM diamond_concept_functions WHERE concept_id = ?", (c["id"],))
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_concept_archive", "diamond_concept", c["id"], {"name": c["name"]}, ctx.ip)
    return payload(ctx.conn, pid)


def api_move(ctx):
    """{order: [concept ids]} -- the order of the bricks on the overview page."""
    pid = F.access(ctx, "editor")
    order = ctx.body.get("order")
    if not isinstance(order, list):
        raise ApiError(400, "order : liste des briques dans le nouvel ordre attendue.")
    for i, value in enumerate(order):
        ctx.conn.execute("UPDATE diamond_concepts SET position = ? WHERE id = ? AND project_id = ?", (i + 1, int(value), pid))
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_concept_move", "project", pid, {"count": len(order)}, ctx.ip)
    return payload(ctx.conn, pid)
