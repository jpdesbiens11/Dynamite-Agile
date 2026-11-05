"""« Compléter le DFMEA » (0.60.28, D-O-037): no function of the tree is skipped, every row gets its key test and the
industry good practices of its prevention.

complete(conn, user_id, pid) runs at the end of « Commencer » (Project Starter) and from the DFMEA screen:
  1. every function of the tree (primary, secondary, tertiary, technique) without a row gets one: officially every
     function can fail. The failure mode names the four AIAG-VDA kinds (loss, partial, intermittent, unintended); a
     parent function points to the rows of its children for its causes. « Rien à signaler (RAS) » stays the team's
     explicit, justified choice -- never written by the tool;
  2. a row without a key test gets the most relevant test: the subjects called by the themes of its function
     (dfmea_practices), then the words shared with the test; the Test Base of the Space first, then the catalogue;
  3. a row whose prevention does not list the good practices yet gets them (dfmea_practices.block), after the team's text.
Rows already complete are left as they are. Returns the counts; the API journals them.
"""
from core import audit, db

from . import dfmea as DF
from . import dfmea_practices as GP
from . import functions as F

LIMIT = 4000  # Prevention Controls (dfmea.TEXTS)
MAX_THEMES = 3


def _tree(conn, pid):
    """The functions of the tree, depth first (the order of the tree screen), then those outside the tree (estime)."""
    items = F.rows(conn, pid)
    lv, tree = F.levels(items), F.in_tree(items)
    kids = {}
    for f in sorted(items, key=lambda f: (f["position"], f["number"])):
        f["level"], f["in_tree"] = lv[f["id"]], f["id"] in tree
        kids.setdefault(f["parent_id"], []).append(f)
    out = []

    def walk(parent):
        for f in kids.get(parent, []):
            out.append(f)
            walk(f["id"])
    roots = [f for f in kids.get(None, [])]
    for r in sorted(roots, key=lambda f: (not f["in_tree"], not f["is_primary"], f["position"])):
        out.append(r)
        walk(r["id"])
    return out, kids


def _context(conn, pid):
    """{function id: words of its flows and parts} and {function id: kinds of its parts}."""
    extra, kinds = {}, {}
    for r in conn.execute("SELECT label, src_function_id AS a, dst_function_id AS b FROM diamond_flows WHERE project_id = ?", (pid,)):
        for fid in (r["a"], r["b"]):
            if fid:
                extra[fid] = extra.get(fid, "") + " " + r["label"]
    for r in conn.execute("SELECT p.name, p.kind, l.function_id FROM diamond_parts p JOIN diamond_part_functions l ON l.part_id = p.id "
                          "WHERE p.project_id = ?", (pid,)):
        extra[r["function_id"]] = extra.get(r["function_id"], "") + " " + r["name"]
        kinds.setdefault(r["function_id"], set()).add(r["kind"])
    return extra, kinds


def _candidates(conn, pid):
    rows = conn.execute("SELECT t.id, t.test_id AS code, t.title, t.subject, t.objective, t.standard, t.project_id = ? AS own "
                        "FROM testing_tests t JOIN projects p ON p.id = t.project_id WHERE t.project_id = ? OR p.key = ?",
                        (pid, pid, DF.CATALOGUE)).fetchall()
    return [dict(r, words=GP.words(r["title"] + " " + r["objective"])) for r in rows]


def pick(cands, subjects, row_words):
    """The key test of a row: subject of its themes (best first), words shared, the Space's own tests first."""
    best = None
    for c in cands:
        rank = subjects.index(c["subject"]) if c["subject"] in subjects else None
        overlap = len(row_words & c["words"])
        if rank is None and overlap < 2:
            continue
        score = 3 * overlap + (10 - 4 * min(rank, 2) if rank is not None else 0) + (3 if c["own"] else 0)
        key = (score, c["own"], -c["id"])
        if best is None or key > best[0]:
            best = (key, c)
    return best[1] if best else None


def _subjects(keys, level):
    out = ["func"] if level == 1 else []  # the primary function: the test of the reference use case first
    for k in keys:
        out += [s for s in GP.THEMES[k]["subjects"] if s not in out]
    return out + ([] if "func" in out else ["func"])


TEMPLATES = ("L'utilisateur est déçu : le produit perd de sa valeur à ses yeux (à préciser). Le produit ne rend pas son service à l'utilisateur (à préciser). Perte ou dégradation de (à préciser). "
             "Défaillance d'une fonction de niveau inférieur ou de leurs interfaces : voir leurs lignes. "
             "À préciser : matériau, dimension, composant, logiciel, interface ou usage hors de la spécification. "
             "Ne réalise pas : perte, réalisation partielle, intermittente ou non voulue (à préciser).")
BOILER = GP.words(TEMPLATES)  # the words of the rows written by the tool never choose a test


def _new_row(f, by_id, kids, project):
    if not f["in_tree"]:
        focus, effect = "Fonction hors arbre · " + project, "L'utilisateur est déçu : le produit perd de sa valeur à ses yeux (à préciser)."
    elif f["level"] == 1:
        focus, effect = "Produit · " + project, "Le produit ne rend pas son service à l'utilisateur (à préciser)."
    else:
        sub = f
        while sub["level"] > 2 and sub["parent_id"] in by_id:
            sub = by_id[sub["parent_id"]]
        parent = by_id[f["parent_id"]]
        focus = "Sous-système F{} · {}".format(sub["number"], sub["text"])
        effect = "Perte ou dégradation de F{} « {} » (à préciser).".format(parent["number"], parent["text"])
    children = kids.get(f["id"], [])
    cause = ("Défaillance d'une fonction de niveau inférieur ({}) ou de leurs interfaces : voir leurs lignes.".format(
        ", ".join("F{}".format(c["number"]) for c in children)) if children else
        "À préciser : matériau, dimension, composant, logiciel, interface ou usage hors de la spécification.")
    return {"higher": project[:160], "focus": focus[:160], "function_id": f["id"], "effect": effect[:400], "cause": cause[:400],
            "failure_mode": "Ne réalise pas « {} » : perte, réalisation partielle, intermittente ou non voulue (à préciser).".format(
                f["text"])[:400]}


def complete(conn, user_id, pid):
    project = conn.execute("SELECT name FROM projects WHERE id = ?", (pid,)).fetchone()["name"]
    tree, kids = _tree(conn, pid)
    by_id = {f["id"]: f for f in tree}
    covered = {r["function_id"] for r in conn.execute("SELECT function_id FROM diamond_dfmea WHERE project_id = ?", (pid,))}
    added = 0
    for f in tree:
        if f["id"] not in covered:
            DF.insert(conn, user_id, pid, _new_row(f, by_id, kids, project))
            added += 1
    extra, kinds = _context(conn, pid)
    cands = _candidates(conn, pid)
    tested = practiced = 0
    for r in conn.execute("SELECT * FROM diamond_dfmea WHERE project_id = ? ORDER BY position, id", (pid,)).fetchall():
        if r["failure_mode"] == GP.RAS:
            continue
        f = by_id.get(r["function_id"])
        own = (f["text"] if f else "") + " " + (extra.get(r["function_id"], "") if f else "")
        keys = GP.themes(own)[:MAX_THEMES] or GP.themes(r["failure_mode"] + " " + r["cause"] + " " + r["focus"])[:MAX_THEMES]
        changes = {}
        if r["test_id"] is None and cands:
            row_words = GP.words(" ".join([own, r["requirement"], r["failure_mode"], r["cause"], r["effect"]])) - BOILER
            best = pick(cands, _subjects(keys, f["level"] if f and f["in_tree"] else 0), row_words)
            if best:
                changes["test_id"] = best["id"]
                tested += 1
        if GP.MARK not in r["prevention"]:
            text = (r["prevention"].strip() + "\n" if r["prevention"].strip() else "") + GP.block(keys, kinds.get(r["function_id"], ()))
            changes["prevention"] = text[:LIMIT]
            practiced += 1
        if changes:
            conn.execute("UPDATE diamond_dfmea SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(
                ", ".join(k + " = ?" for k in changes)), list(changes.values()) + [user_id, db.utc_now(), r["id"]])
    return {"added": added, "tested": tested, "practices": practiced}


def api_complete(ctx):
    pid = F.access(ctx, "editor")
    counts = complete(ctx.conn, ctx.user["id"], pid)
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_dfmea_complete", "diamond_dfmea", pid, counts, ctx.ip)
    return dict(DF.payload(ctx.conn, pid), completed=counts)
