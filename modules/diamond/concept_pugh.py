"""Diamond · Pugh matrices of the bricks (0.60.105, D-O-117): the Pugh matrix of Goldmine (modules/agile/pugh.py, D-B-062)
opened from Diamond, where it judges a group of bricks (diamond_pugh_scope) -- not a single one: its columns are options,
often combinations of concept sheets written « CB-1.2 + CB-3.1 » (diamond_pugh_option_sheets) -- and where its criteria
are, in this order:
    1. the needs of Goldmine (kind « need »),
    2. the functions of the tree: estime, then base (Kano B), performance (P), innovation (I), constraint (certifiable,
       producible, maintainable…), the others (diamond_pugh_fcriteria / diamond_pugh_fscores: the functions of the bricks
       judged, and every estime or constraint function),
    3. the requirements of Goldmine.
Every Pugh route of Goldmine has its twin here: the twin calls Goldmine's handler, then answers the merged matrix (both
kinds of criteria, totals over all of them). A criterion of a function has the id « f<n> ». Deciding the matrix selects
the concept sheets of the chosen column, and their bricks. Every write is journalled.
"""
import re

from core import audit, validate
from core.errors import ApiError
from core.files import RawFile

from modules.agile import pugh as G
from modules.agile import pugh_xlsx

from . import concepts as C
from . import functions as F

GROUPS = {"need": "Besoins (needs)", "estime": "Fonctions d'estime", "base": "Fonctions de base (Kano B)",
          "performance": "Fonctions de performance (Kano P)", "innovation": "Fonctions d'innovation (Kano I)",
          "constraint": "Fonctions contraintes (certifiable, productible, maintenable…)", "function": "Autres fonctions",
          "requirement": "Requirements"}
ORDER = list(GROUPS)
SHEET_RE = re.compile(r"CB-(\d+)\.(\d+)")
TOP_CRITICALITY = ("A", "B")


def _group(f):
    if f["ftype"] == "estime":
        return "estime"
    if f["ftype"] == "contrainte" or f["kano"] == "C":
        return "constraint"
    return {"B": "base", "P": "performance", "I": "innovation"}.get(f["kano"], "function")


def _mid(ctx, pid):
    row = ctx.conn.execute("SELECT * FROM goldmine_pugh WHERE id = ? AND project_id = ?",
                           (validate.int_param(ctx.params, "mid"), pid)).fetchone()
    if row is None:
        raise ApiError(404, "Pugh Matrix introuvable dans ce Space.")
    return row


def merged(conn, pid, mid):
    """Goldmine's detail of the matrix, with the criteria of the functions and the group of every criterion."""
    row = conn.execute("SELECT * FROM goldmine_pugh WHERE id = ? AND project_id = ?", (mid, pid)).fetchone()
    data = G.detail(conn, row)
    for k in data["criteria"]:
        k["group"] = "need" if k.get("kind") == "need" else "requirement"
    fcrit = [dict(r) for r in conn.execute(
        "SELECT k.id, k.function_id, k.position, f.number, f.text, f.kano, f.ftype FROM diamond_pugh_fcriteria k "
        "JOIN diamond_functions f ON f.id = k.function_id WHERE k.pugh_id = ? ORDER BY k.position, k.id", (mid,))]
    for k in fcrit:
        k.update(id="f{}".format(k["id"]), fn=True, key="F{}".format(k["number"]), title=k["text"], group=_group(k),
                 external_id="", statement="", category="", lifecycle="", status_name="", criticality="",
                 kano_label=F.KANO.get(k["kano"], ""))
    data["criteria"] = sorted(data["criteria"] + fcrit, key=lambda k: (ORDER.index(k["group"]), k["position"]))
    for s in conn.execute("SELECT s.* FROM diamond_pugh_fscores s JOIN diamond_pugh_fcriteria k ON k.id = s.criterion_id "
                          "WHERE k.pugh_id = ?", (mid,)):
        data["scores"].append({"criterion_id": "f{}".format(s["criterion_id"]), "concept_id": s["option_id"],
                               "score": s["score"], "note": s["note"]})
    scores = {(s["criterion_id"], s["concept_id"]): s for s in data["scores"]}
    data["totals"] = {str(k): v for k, v in G.totals(data["concepts"], data["criteria"], scores, row["datum_id"]).items()}
    data["scope"] = [dict(r, code=C.code(r["number"])) for r in conn.execute(
        "SELECT c.id, c.number, c.name, c.initial_name FROM diamond_pugh_scope s JOIN diamond_concepts c ON c.id = s.concept_id "
        "WHERE s.pugh_id = ? ORDER BY c.number", (mid,))]
    sheets = {}
    for r in conn.execute("SELECT o.option_id, s.id, s.number, c.number AS cn, s.title FROM diamond_pugh_option_sheets o "
                          "JOIN diamond_concept_sheets s ON s.id = o.sheet_id JOIN diamond_concepts c ON c.id = s.concept_id "
                          "WHERE o.project_id = ? ORDER BY c.number, s.number", (pid,)):
        sheets.setdefault(r["option_id"], []).append({"id": r["id"], "code": "CB-{}.{}".format(r["cn"], r["number"]), "title": r["title"]})
    for concept in data["concepts"]:
        concept["sheets"] = sheets.get(concept["id"], [])
    data["groups"] = GROUPS
    data["diamond"] = True
    return data


def link_options(conn, pid, mid):
    """The concept sheets named in the column names (« CB-1.2 + CB-3.1 ») are linked to their column."""
    for option in conn.execute("SELECT id, name FROM goldmine_pugh_concepts WHERE pugh_id = ?", (mid,)).fetchall():
        conn.execute("DELETE FROM diamond_pugh_option_sheets WHERE option_id = ?", (option["id"],))
        for cn, sn in SHEET_RE.findall(option["name"]):
            sheet = conn.execute("SELECT s.id FROM diamond_concept_sheets s JOIN diamond_concepts c ON c.id = s.concept_id "
                                 "WHERE s.project_id = ? AND c.number = ? AND s.number = ? AND s.archived = 0",
                                 (pid, int(cn), int(sn))).fetchone()
            if sheet:
                conn.execute("INSERT OR IGNORE INTO diamond_pugh_option_sheets (project_id, option_id, sheet_id) VALUES (?, ?, ?)",
                             (pid, option["id"], sheet["id"]))


def add_functions(conn, pid, mid, fids):
    position = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM diamond_pugh_fcriteria WHERE pugh_id = ?", (mid,)).fetchone()[0]
    added = 0
    for fid in fids:
        cur = conn.execute("INSERT OR IGNORE INTO diamond_pugh_fcriteria (project_id, pugh_id, function_id, position) VALUES (?, ?, ?, ?)",
                           (pid, mid, fid, position + added))
        added += cur.rowcount
    return added


def fill(conn, pid, mid):
    """The criteria a matrix of bricks starts with: every need, the functions of the bricks judged, every estime and constraint function,
    the requirements of criticality A or B. Returns how many were added (what is already there stays)."""
    base = ("SELECT i.id FROM agile_issues i JOIN agile_issue_types t ON t.id = i.type_id AND t.is_requirement = 1 "
            "JOIN agile_statuses s ON s.id = i.status_id LEFT JOIN agile_requirements r ON r.issue_id = i.id "
            "WHERE i.project_id = ? AND s.name NOT IN ('Rejected', 'Obsolete') ")
    issues = [r[0] for r in conn.execute(base + "AND COALESCE(r.kind, 'requirement') = 'need' ORDER BY i.number", (pid,))]
    issues += [r[0] for r in conn.execute(base + "AND COALESCE(r.kind, 'requirement') = 'requirement' AND r.criticality IN (?, ?) "
                                          "ORDER BY i.number", (pid,) + TOP_CRITICALITY)]
    position = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM goldmine_pugh_criteria WHERE pugh_id = ?", (mid,)).fetchone()[0]
    added = 0
    for issue_id in issues[:G.MAX_CRITERIA]:
        added += conn.execute("INSERT OR IGNORE INTO goldmine_pugh_criteria (pugh_id, issue_id, position) VALUES (?, ?, ?)",
                              (mid, issue_id, position + added)).rowcount
    fids = [r[0] for r in conn.execute(
        "SELECT l.function_id FROM diamond_concept_functions l JOIN diamond_pugh_scope s ON s.concept_id = l.concept_id "
        "JOIN diamond_functions f ON f.id = l.function_id WHERE s.pugh_id = ? AND f.archived = 0 ORDER BY f.position, f.number", (mid,))]
    fids += [r[0] for r in conn.execute("SELECT id FROM diamond_functions WHERE project_id = ? AND archived = 0 "
                                        "AND ftype IN ('estime', 'contrainte') ORDER BY number", (pid,))]
    return added + add_functions(conn, pid, mid, list(dict.fromkeys(fids)))


def _scope(conn, pid, mid, ids):
    conn.execute("DELETE FROM diamond_pugh_scope WHERE pugh_id = ?", (mid,))
    for cid in ids:
        conn.execute("INSERT OR IGNORE INTO diamond_pugh_scope (project_id, pugh_id, concept_id) VALUES (?, ?, ?)",
                     (pid, mid, C._concept(conn, pid, int(cid))["id"]))


# --------------------------------------------------------------------------
# Routes: the twins of Goldmine's, answering the merged matrix
# --------------------------------------------------------------------------
def api_list(ctx):
    pid = F.access(ctx)
    data = G.api_list(ctx)
    scope = {}
    for r in ctx.conn.execute("SELECT s.pugh_id, c.number FROM diamond_pugh_scope s JOIN diamond_concepts c ON c.id = s.concept_id "
                              "WHERE s.project_id = ? ORDER BY c.number", (pid,)):
        scope.setdefault(r["pugh_id"], []).append(C.code(r["number"]))
    for m in data["matrices"]:
        m["scope"] = scope.get(m["id"], [])
        m["n_criteria"] += ctx.conn.execute("SELECT COUNT(*) FROM diamond_pugh_fcriteria WHERE pugh_id = ?", (m["id"],)).fetchone()[0]
    return data


def api_create(ctx):
    """{title, description, concepts: [column names], concept_ids: [bricks judged], fill: true}"""
    pid = F.access(ctx, "editor")
    ids = ctx.body.get("concept_ids") or []
    if not isinstance(ids, list):
        raise ApiError(400, "concept_ids : liste des briques jugées attendue.")
    for cid in ids:
        C._concept(ctx.conn, pid, int(cid))
    mid = G.api_create(ctx)["matrix"]["id"]
    _scope(ctx.conn, pid, mid, ids)
    link_options(ctx.conn, pid, mid)
    added = fill(ctx.conn, pid, mid) if ctx.body.get("fill", True) else 0
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_pugh_create", "goldmine_pugh", mid, {"bricks": ids, "criteria": added}, ctx.ip)
    return merged(ctx.conn, pid, mid)


def api_get(ctx):
    pid = F.access(ctx)
    G.c.access(ctx)
    return merged(ctx.conn, pid, _mid(ctx, pid)["id"])


def _twin(handler, relink=False):
    def run(ctx):
        pid = F.access(ctx, "editor")
        mid = _mid(ctx, pid)["id"]
        handler(ctx)
        if relink:
            link_options(ctx.conn, pid, mid)
        return merged(ctx.conn, pid, mid)
    return run


api_concept_add = _twin(G.api_concept_add, relink=True)
api_concept_update = _twin(G.api_concept_update, relink=True)


def api_update(ctx):
    """Goldmine's update; deciding also selects the concept sheets of the chosen column, and their bricks."""
    pid = F.access(ctx, "editor")
    mid = _mid(ctx, pid)["id"]
    G.api_update(ctx)
    if "concept_ids" in ctx.body:
        G._editable(ctx, _mid(ctx, pid))
        _scope(ctx.conn, pid, mid, ctx.body.get("concept_ids") or [])
    row = _mid(ctx, pid)
    if ctx.body.get("status") == "decided" and row["decision_concept_id"]:
        sheets = [r[0] for r in ctx.conn.execute("SELECT sheet_id FROM diamond_pugh_option_sheets WHERE option_id = ?",
                                                 (row["decision_concept_id"],))]
        for sid in sheets:
            ctx.conn.execute("UPDATE diamond_concept_sheets SET status = 'selected' WHERE id = ? AND project_id = ?", (sid, pid))
            ctx.conn.execute("UPDATE diamond_concepts SET status = 'selected' WHERE id = (SELECT concept_id FROM "
                             "diamond_concept_sheets WHERE id = ?)", (sid,))
        audit.log_action(ctx.conn, ctx.user["id"], "diamond_pugh_decide", "goldmine_pugh", mid, {"sheets": sheets}, ctx.ip)
    return merged(ctx.conn, pid, mid)


def api_delete(ctx):
    return G.api_delete(ctx)


def api_criteria_add(ctx):
    """Goldmine's criteria, or {function_ids: [...]}, or {fill: true} (needs, functions of the bricks, requirements A / B)."""
    pid = F.access(ctx, "editor")
    row = _mid(ctx, pid)
    G._editable(ctx, row)
    if ctx.body.get("fill"):
        added = fill(ctx.conn, pid, row["id"])
    elif ctx.body.get("function_ids"):
        from .concepts import _functions_of
        added = add_functions(ctx.conn, pid, row["id"], _functions_of(ctx.conn, pid, ctx.body["function_ids"]))
    else:
        added = G.api_criteria_add(ctx).get("added", 0)
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_pugh_criteria", "goldmine_pugh", row["id"], {"added": added}, ctx.ip)
    data = merged(ctx.conn, pid, row["id"])
    data["added"] = added
    return data


def api_criterion_delete(ctx):
    pid = F.access(ctx, "editor")
    row = _mid(ctx, pid)
    kid = str(ctx.params.get("kid") or "")
    if kid.startswith("f"):
        G._editable(ctx, row)
        ctx.conn.execute("DELETE FROM diamond_pugh_fcriteria WHERE id = ? AND pugh_id = ?", (int(kid[1:]), row["id"]))
        audit.log_action(ctx.conn, ctx.user["id"], "diamond_pugh_fcriterion_delete", "goldmine_pugh", row["id"], {"criterion": kid}, ctx.ip)
    else:
        G.api_criterion_delete(ctx)
    return merged(ctx.conn, pid, row["id"])


def api_score(ctx):
    """{criterion_id: 12 | "f3", concept_id, score, note}"""
    pid = F.access(ctx, "editor")
    row = _mid(ctx, pid)
    crit = str(ctx.body.get("criterion_id") or "")
    if not crit.startswith("f"):
        G.api_score(ctx)
        return merged(ctx.conn, pid, row["id"])
    G._editable(ctx, row)
    kid, option = int(crit[1:]), int(ctx.body.get("concept_id") or 0)
    if not ctx.conn.execute("SELECT 1 FROM diamond_pugh_fcriteria WHERE id = ? AND pugh_id = ?", (kid, row["id"])).fetchone() \
            or not ctx.conn.execute("SELECT 1 FROM goldmine_pugh_concepts WHERE id = ? AND pugh_id = ?", (option, row["id"])).fetchone():
        raise ApiError(400, "Case introuvable dans cette matrice.")
    if option == row["datum_id"]:
        raise ApiError(400, "La colonne de référence (datum) vaut « S » par définition.")
    score = str(ctx.body.get("score") or "").strip().upper()
    note = G._text(ctx.body, "note", "Note", 1000)
    if score == "":
        ctx.conn.execute("DELETE FROM diamond_pugh_fscores WHERE criterion_id = ? AND option_id = ?", (kid, option))
    elif score not in G.SCORES:
        raise ApiError(400, "Note « {} » refusée : + (meilleur), S (pareil) ou - (moins bon) que la référence.".format(score))
    else:
        ctx.conn.execute("INSERT INTO diamond_pugh_fscores (project_id, criterion_id, option_id, score, note) VALUES (?, ?, ?, ?, ?) "
                         "ON CONFLICT(criterion_id, option_id) DO UPDATE SET score = excluded.score, note = excluded.note",
                         (pid, kid, option, score, note))
    G._touch(ctx, row["id"])
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_pugh_fscore", "goldmine_pugh", row["id"],
                     {"criterion": crit, "option": option, "score": score}, ctx.ip)
    return merged(ctx.conn, pid, row["id"])


def api_round(ctx):
    """Goldmine's new round, plus the bricks judged and the criteria of the functions."""
    pid = F.access(ctx, "editor")
    old = _mid(ctx, pid)["id"]
    new = G.api_round(ctx)["matrix"]["id"]
    ctx.conn.execute("INSERT INTO diamond_pugh_scope (project_id, pugh_id, concept_id) SELECT project_id, ?, concept_id "
                     "FROM diamond_pugh_scope WHERE pugh_id = ?", (new, old))
    ctx.conn.execute("INSERT INTO diamond_pugh_fcriteria (project_id, pugh_id, function_id, position) SELECT project_id, ?, "
                     "function_id, position FROM diamond_pugh_fcriteria WHERE pugh_id = ?", (new, old))
    link_options(ctx.conn, pid, new)
    return merged(ctx.conn, pid, new)


def api_export(ctx):
    pid = F.access(ctx)
    G.c.access(ctx)
    data = merged(ctx.conn, pid, _mid(ctx, pid)["id"])
    for k in data["criteria"]:
        if k.get("fn"):
            k["category"], k["status_name"] = GROUPS[k["group"]], "Function"
    key = G.c.project_key(ctx.conn, pid)
    G.c.log(ctx, "pugh_export", "goldmine_pugh", data["matrix"]["id"], {"from": "diamond"})
    name = re.sub(r"[^\w\-]+", "_", "{}_Pugh_{}_tour{}".format(key, data["matrix"]["title"], data["matrix"]["round"]),
                  flags=re.UNICODE).strip("_")[:90]
    return RawFile(pugh_xlsx.build(data, key), name + ".xlsx", pugh_xlsx.XLSX)
