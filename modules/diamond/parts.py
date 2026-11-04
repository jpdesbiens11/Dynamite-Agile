"""Parts on the functions of the « Structure fonctionnelle » (0.60.20, D-O-031): a high-level product architecture.

Each part (P-1, P-2…) is tagged on the function(s) it carries out. Read both ways, the allocation shows where the
architecture can shrink: a part that carries several functions is an integrated part (fewer parts, lower cost -- check
in the DFMEA that one failure does not take them all); a function that needs several parts is a candidate to be
carried by one; a part that carries no function of the tree is a candidate to remove (« the best part is no part »,
Golden Nuggets); a function no part carries yet is not designed. The functions offered are those of the structure
(the sub-systems of the general view and the functions of the detail view). Every write is journalled.
"""
from core import audit, db, validate
from core.errors import ApiError

from . import functions as F

KINDS = {"designed": "Conçue", "bought": "Achetée", "standard": "Normalisée"}
MAX_PARTS = 200


def _text(body, name, label, limit, required=True):
    value = " ".join(str(body.get(name) or "").split())
    if required and not value:
        raise ApiError(400, "{} obligatoire. Correctif : quelques mots (ex. « Boîtier de tête en aluminium »).".format(label))
    if len(value) > limit:
        raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, limit, len(value)))
    return value


def _kind(body):
    value = str(body.get("kind") or "designed")
    if value not in KINDS:
        raise ApiError(400, "Type de pièce « {} » inconnu. Correctif : {}.".format(value, ", ".join(KINDS)))
    return value


def taggable(view_nodes):
    """{function id: function} -- the functions of the structure, both views."""
    return {**view_nodes["general"], **view_nodes["detail"]}


def rows(conn, pid, live):
    parts = [dict(r) for r in conn.execute("SELECT id, number, name, kind, notes, position FROM diamond_parts "
                                           "WHERE project_id = ? ORDER BY position, number", (pid,))]
    links = {}
    for r in conn.execute("SELECT part_id, function_id FROM diamond_part_functions WHERE project_id = ?", (pid,)):
        if r["function_id"] in live:
            links.setdefault(r["part_id"], []).append(r["function_id"])
    for p in parts:
        p["functions"] = sorted(links.get(p["id"], []))
    return parts


def analysis(parts, view_nodes):
    """(checks, stats): what the allocation says about the architecture (detail functions are the reference)."""
    detail = view_nodes["detail"]
    by_fn = {fid: [] for fid in detail}
    for p in parts:
        for fid in p["functions"]:
            if fid in by_fn:
                by_fn[fid].append(p)
    code = lambda p: "P-{}".format(p["number"])  # noqa: E731
    fname = lambda fid: "F{} « {} »".format(detail[fid]["number"], detail[fid]["text"])  # noqa: E731
    out = []
    if not parts:
        return [], {"parts": 0, "functions": len(detail), "covered": 0, "integrated": 0, "shared": 0, "ratio": 0}
    integrated = [p for p in parts if len([f for f in p["functions"] if f in detail]) >= 2]
    shared = [fid for fid, ps in by_fn.items() if len(ps) >= 2]
    for p in integrated[:6]:
        out.append("{} « {} » réalise {} fonctions : pièce intégrée, bon pour le coût et l'assemblage. Vérifiez dans le DFMEA "
                   "qu'une seule défaillance ne les emporte pas toutes.".format(code(p), p["name"], len(p["functions"])))
    for fid in shared[:6]:
        out.append("{} demande {} pièces ({}) : une seule pièce pourrait-elle la réaliser ? Moins de pièces, moins "
                   "d'interfaces.".format(fname(fid), len(by_fn[fid]), ", ".join(code(p) for p in by_fn[fid])))
    idle = [p for p in parts if not p["functions"]]
    if idle:
        out.append("{} : aucune fonction de l'arbre. La meilleure pièce est celle qu'on n'a pas : à retirer, ou à rattacher à "
                   "la fonction qu'elle sert (et à ajouter à l'arbre si elle manque).".format(
                       ", ".join("{} « {} »".format(code(p), p["name"]) for p in idle[:5])))
    bare = [fid for fid, ps in by_fn.items() if not ps]
    if bare:
        out.append("Fonction(s) sans pièce : {}. Une fonction qu'aucune pièce ne réalise n'est pas encore conçue.".format(
            ", ".join("F{}".format(detail[fid]["number"]) for fid in bare[:8]) + (" …" if len(bare) > 8 else "")))
    covered = len([fid for fid, ps in by_fn.items() if ps])
    links = sum(len([f for f in p["functions"] if f in detail]) for p in parts)
    stats = {"parts": len(parts), "functions": len(detail), "covered": covered, "integrated": len(integrated),
             "shared": len(shared), "ratio": round(links / len(parts), 2) if parts else 0}
    return out, stats


def _log(ctx, action, oid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "diamond_parts", oid, details, ctx.ip)


def _part(ctx, pid):
    row = ctx.conn.execute("SELECT * FROM diamond_parts WHERE id = ? AND project_id = ?",
                           (validate.int_param(ctx.params, "oid"), pid)).fetchone()
    if row is None:
        raise ApiError(404, "Pièce introuvable dans ce Space. Correctif : rechargez la page.")
    return dict(row)


def _function(conn, pid, value):
    from . import structure
    try:
        fid = int(value)
    except (TypeError, ValueError):
        raise ApiError(400, "Fonction manquante. Correctif : choisissez une fonction de la structure.")
    view_nodes, _items = structure.nodes(conn, pid)
    if fid not in taggable(view_nodes):
        raise ApiError(409, "Cette fonction n'est pas dans la structure fonctionnelle (fonction secondaire ou tertiaire de "
                            "l'arbre, sans les fonctions techniques). Correctif : choisissez une fonction de la liste.")
    return fid


def add_part(conn, user_id, pid, name, kind, notes=""):
    if conn.execute("SELECT COUNT(*) FROM diamond_parts WHERE project_id = ?", (pid,)).fetchone()[0] >= MAX_PARTS:
        raise ApiError(409, "{} pièces au maximum par Space. Correctif : regroupez-les en sous-ensembles.".format(MAX_PARTS))
    number, pos = conn.execute("SELECT COALESCE(MAX(number), 0) + 1, COALESCE(MAX(position), -1) + 1 FROM diamond_parts "
                               "WHERE project_id = ?", (pid,)).fetchone()
    now = db.utc_now()
    return conn.execute("INSERT INTO diamond_parts (project_id, number, name, kind, notes, position, created_by, created_at, "
                        "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (pid, number, name, kind, notes, pos, user_id, now, now)).lastrowid


def tag(conn, pid, part_id, fid, on=True):
    if on:
        conn.execute("INSERT OR IGNORE INTO diamond_part_functions (project_id, part_id, function_id) VALUES (?, ?, ?)", (pid, part_id, fid))
    else:
        conn.execute("DELETE FROM diamond_part_functions WHERE part_id = ? AND function_id = ?", (part_id, fid))


def api_create(ctx):
    from . import structure
    pid = F.access(ctx, "editor")
    name, kind = _text(ctx.body, "name", "Nom de la pièce", 80), _kind(ctx.body)
    fids = [_function(ctx.conn, pid, v) for v in (ctx.body.get("functions") or [])][:40]
    oid = add_part(ctx.conn, ctx.user["id"], pid, name, kind, _text(ctx.body, "notes", "Notes", 1000, required=False))
    for fid in fids:
        tag(ctx.conn, pid, oid, fid)
    _log(ctx, "diamond_part_create", oid, {"name": name, "kind": kind, "functions": fids})
    return structure.payload(ctx.conn, pid)


def api_update(ctx):
    from . import structure
    pid = F.access(ctx, "editor")
    row = _part(ctx, pid)
    changes = {}
    if "name" in ctx.body:
        changes["name"] = _text(ctx.body, "name", "Nom de la pièce", 80)
    if "kind" in ctx.body:
        changes["kind"] = _kind(ctx.body)
    if "notes" in ctx.body:
        changes["notes"] = _text(ctx.body, "notes", "Notes", 1000, required=False)
    if changes:
        changes["updated_at"] = db.utc_now()
        ctx.conn.execute("UPDATE diamond_parts SET {} WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                         list(changes.values()) + [row["id"]])
        _log(ctx, "diamond_part_update", row["id"], {k: v for k, v in changes.items() if k != "updated_at"})
    return structure.payload(ctx.conn, pid)


def api_tag(ctx):
    """{function_id, on}: the part carries out this function (on) or no longer (off)."""
    from . import structure
    pid = F.access(ctx, "editor")
    row = _part(ctx, pid)
    fid = _function(ctx.conn, pid, ctx.body.get("function_id"))
    on = validate.boolean(ctx.body, "on", default=True)
    tag(ctx.conn, pid, row["id"], fid, on)
    _log(ctx, "diamond_part_tag" if on else "diamond_part_untag", row["id"], {"part": row["number"], "function_id": fid})
    return structure.payload(ctx.conn, pid)


def api_delete(ctx):
    from . import structure
    pid = F.access(ctx, "editor")
    row = _part(ctx, pid)
    n = ctx.conn.execute("SELECT COUNT(*) FROM diamond_part_functions WHERE part_id = ?", (row["id"],)).fetchone()[0]
    ctx.conn.execute("DELETE FROM diamond_parts WHERE id = ?", (row["id"],))  # its tags go with it (CASCADE)
    _log(ctx, "diamond_part_delete", row["id"], {"number": row["number"], "name": row["name"], "functions": n})
    return structure.payload(ctx.conn, pid)
