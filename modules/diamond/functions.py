"""« Arbre fonctionnel » of Diamond (0.60.11, D-O-023): the functions of a Space's product, as a tree.

Reading of the tree (course method):
  left -> right   « Comment ? » -- each function is carried out by the functions on its right;
  right -> left   « Pourquoi ? » -- back to the source, up to the primary function;
  top -> bottom   « Quand ? »   -- siblings in the order of the first use, from the box to the first service;
                                   the last branch is kept for the protection functions.
Levels: 1 primary (one per Space), 2 secondary (the sub-systems), 3 tertiary; a « technique » function may hang at
level 4, under a tertiary (shown apart: not in the tree proper). A function outside the tree (parent NULL, not
primary) waits in « Hors arbre » -- e.g. the « estime » functions. Its number (F12) is kept for ever, even archived
(never given again), for the follow-up in the DFMEA, the requirements and the tests. Every write is journalled.
"""
from core import audit, db, permissions, validate
from core.errors import ApiError

TYPES = {"usage": "Usage", "estime": "Estime", "technique": "Technique", "contrainte": "Contrainte"}
KANO = {"": "—", "B": "Base", "P": "Performance", "I": "Innovation", "C": "Contrainte"}
IMPORTANCE = {"": "—", "indispensable": "Indispensable", "importante": "Importante", "interessante": "Intéressante"}
LEVELS = {1: "Primaire", 2: "Secondaire", 3: "Tertiaire", 4: "Technique"}
MAX_LEVEL = 4
MAX_FUNCTIONS = 400


def access(ctx, minimum="reader"):
    pid = validate.int_param(ctx.params, "pid")
    permissions.require_project_role(ctx.conn, ctx.user, pid, minimum)
    return pid


def _text(body, name, label, limit, required=False):
    value = " ".join(str(body.get(name) or "").split())
    if required and not value:
        raise ApiError(400, "{} obligatoire. Correctif : un verbe à l'infinitif et son complément (ex. « Éclairer "
                            "une surface de travail »).".format(label))
    if len(value) > limit:
        raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, limit, len(value)))
    return value


def _choice(body, name, options, label):
    value = str(body.get(name) or "").strip()
    if value not in options:
        raise ApiError(400, "{} « {} » inconnu. Correctif : {}.".format(label, value, ", ".join(k for k in options if k)))
    return value


def rows(conn, pid):
    return [dict(r) for r in conn.execute(
        "SELECT * FROM diamond_functions WHERE project_id = ? AND archived = 0 ORDER BY position, number", (pid,))]


def _row(ctx, pid, fid=None):
    fid = fid if fid is not None else validate.int_param(ctx.params, "fid")
    row = ctx.conn.execute("SELECT * FROM diamond_functions WHERE id = ? AND project_id = ? AND archived = 0", (fid, pid)).fetchone()
    if row is None:
        raise ApiError(404, "Fonction introuvable dans ce Space (déjà archivée ?). Correctif : rechargez la page.")
    return dict(row)


def levels(items):
    """{id: level}; level 1 = primary or the root of a group « hors arbre »."""
    by_id = {f["id"]: f for f in items}
    out = {}

    def level(fid, seen=()):
        if fid in out:
            return out[fid]
        parent = by_id[fid]["parent_id"]
        value = 1 if parent not in by_id or fid in seen else level(parent, seen + (fid,)) + 1
        out[fid] = value
        return value
    for f in items:
        level(f["id"])
    return out


def in_tree(items):
    """Ids of the functions hanging from the primary function (the primary included)."""
    by_parent = {}
    for f in items:
        by_parent.setdefault(f["parent_id"], []).append(f["id"])
    roots = [f["id"] for f in items if f["is_primary"]]
    found, todo = set(), list(roots)
    while todo:
        fid = todo.pop()
        found.add(fid)
        todo += by_parent.get(fid, [])
    return found


def checks(items):
    """Advice shown above the tree (never blocking): what the course method expects and is missing."""
    out = []
    tree = in_tree(items)
    lv = levels(items)
    primary = [f for f in items if f["is_primary"]]
    if not items:
        return out
    if not primary:
        out.append("Aucune fonction primaire : choisissez la fonction qui dit le plus simplement ce que le produit réalise.")
    elif not any(f["parent_id"] == primary[0]["id"] for f in items):
        out.append("La fonction primaire n'a aucune fonction secondaire : demandez-vous « comment ? » elle est réalisée.")
    for f in items:
        if f["id"] in tree and f["ftype"] == "technique" and lv[f["id"]] < 4:
            out.append("F{} est une fonction technique dans l'arbre proprement dit : placez-la sous une tertiaire (niveau 4) "
                       "ou reformulez-la en fonction d'usage.".format(f["number"]))
        if f["id"] in tree and f["ftype"] == "estime":
            out.append("F{} est une fonction d'estime : elle se note dans le CdCF, souvent hors de l'arbre.".format(f["number"]))
    outside = [f for f in items if f["id"] not in tree]
    if primary and outside:
        out.append("{} fonction(s) hors arbre : placez-les ou gardez-les pour le CdCF.".format(len(outside)))
    if primary and not any(f["critical"] for f in items):
        out.append("Aucun chemin critique : cochez les fonctions principales de chaque branche (flèches épaisses).")
    return out


def payload(conn, pid):
    items = rows(conn, pid)
    lv = levels(items)
    tree = in_tree(items)
    for f in items:
        f["level"] = lv[f["id"]]
        f["in_tree"] = f["id"] in tree
    nxt = conn.execute("SELECT COALESCE(MAX(number), 0) + 1 FROM diamond_functions WHERE project_id = ?", (pid,)).fetchone()[0]
    return {"functions": items, "checks": checks(items), "next_number": nxt,
            "labels": {"types": TYPES, "kano": KANO, "importance": IMPORTANCE, "levels": {str(k): v for k, v in LEVELS.items()}}}


def _log(ctx, action, fid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "diamond_functions", fid, details, ctx.ip)


def _siblings(conn, pid, parent_id, primary=False):
    if primary:
        return []
    sql = "SELECT id FROM diamond_functions WHERE project_id = ? AND archived = 0 AND is_primary = 0 AND parent_id {} ORDER BY position, number"
    if parent_id is None:
        return [r["id"] for r in conn.execute(sql.format("IS NULL"), (pid,))]
    return [r["id"] for r in conn.execute(sql.format("= ?"), (pid, parent_id))]


def _place(conn, pid, fid, parent_id, index):
    """Put fid among the children of parent_id at index (end when None) and renumber the positions."""
    ids = [i for i in _siblings(conn, pid, parent_id) if i != fid]
    index = len(ids) if index is None else max(0, min(int(index), len(ids)))
    ids.insert(index, fid)
    conn.execute("UPDATE diamond_functions SET parent_id = ? WHERE id = ?", (parent_id, fid))
    for pos, i in enumerate(ids):
        conn.execute("UPDATE diamond_functions SET position = ? WHERE id = ?", (pos, i))


def _check_parent(conn, pid, fid, parent_id):
    """A parent is a live function of the Space, not fid nor one of its descendants, and the moved branch stays within
    the levels (4 only for « technique »)."""
    items = rows(conn, pid)
    by_id = {f["id"]: f for f in items}
    if parent_id not in by_id:
        raise ApiError(400, "Fonction parente introuvable dans ce Space. Correctif : choisissez une fonction de l'arbre.")
    branch, todo = set(), [fid]
    while todo:
        cur = todo.pop()
        branch.add(cur)
        todo += [f["id"] for f in items if f["parent_id"] == cur]
    if parent_id in branch:
        raise ApiError(409, "F{} ne peut pas aller sous F{} : c'est elle-même ou l'une de ses fonctions « comment ». "
                            "Correctif : choisissez une fonction d'une autre branche.".format(by_id[fid]["number"], by_id[parent_id]["number"]))
    base = levels(items)[parent_id]
    for cur in branch:
        depth, walk = base + 1, cur
        while walk != fid:
            walk = by_id[walk]["parent_id"]
            depth += 1
        if depth > MAX_LEVEL or (depth == MAX_LEVEL and by_id[cur]["ftype"] != "technique"):
            raise ApiError(409, "F{} arriverait au niveau {} : l'arbre a trois niveaux (primaire, secondaire, tertiaire) ; "
                                "seule une fonction technique va au niveau 4. Correctif : placez-la plus à gauche, ou "
                                "changez son type.".format(by_id[cur]["number"], depth))


def _fields(body, partial):
    out = {}
    if not partial or "text" in body:
        out["text"] = _text(body, "text", "Fonction", 160, True)
    if not partial or "ftype" in body:
        out["ftype"] = _choice(dict(body, ftype=body.get("ftype") or "usage"), "ftype", TYPES, "Type")
    if "kano" in body:
        out["kano"] = _choice(body, "kano", KANO, "Kano")
    if "importance" in body:
        out["importance"] = _choice(body, "importance", IMPORTANCE, "Importance")
    if "notes" in body:
        out["notes"] = _text(body, "notes", "Notes", 2000)
    if "critical" in body:
        out["critical"] = 1 if body.get("critical") else 0
    return out


def api_list(ctx):
    return payload(ctx.conn, access(ctx))


def create(conn, user_id, pid, fields, parent_id=None, index=None, primary=False, number=None):
    """Shared by the API and the example: insert one function and place it. Returns its id."""
    if conn.execute("SELECT COUNT(*) FROM diamond_functions WHERE project_id = ? AND archived = 0", (pid,)).fetchone()[0] >= MAX_FUNCTIONS:
        raise ApiError(409, "{} fonctions au maximum par Space. Correctif : archivez celles qui ne servent plus.".format(MAX_FUNCTIONS))
    if number is None:
        number = conn.execute("SELECT COALESCE(MAX(number), 0) + 1 FROM diamond_functions WHERE project_id = ?", (pid,)).fetchone()[0]
    now = db.utc_now()
    fid = conn.execute(
        "INSERT INTO diamond_functions (project_id, number, text, ftype, kano, importance, notes, critical, is_primary, "
        "position, created_by, created_at, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)",
        (pid, number, fields["text"], fields.get("ftype", "usage"), fields.get("kano", ""), fields.get("importance", ""),
         fields.get("notes", ""), fields.get("critical", 0), 1 if primary else 0, user_id, now, user_id, now)).lastrowid
    if not primary:
        _place(conn, pid, fid, parent_id, index)
    return fid


def api_create(ctx):
    pid = access(ctx, "editor")
    body = ctx.body
    fields = _fields(body, partial=False)
    primary = bool(body.get("primary"))
    parent_id = body.get("parent_id")
    if primary:
        if ctx.conn.execute("SELECT 1 FROM diamond_functions WHERE project_id = ? AND archived = 0 AND is_primary = 1", (pid,)).fetchone():
            raise ApiError(409, "Ce Space a déjà sa fonction primaire. Correctif : ajoutez une fonction secondaire à sa droite.")
        parent_id = None
    elif parent_id is not None:
        parent_id = int(parent_id)
        _check_parent_new(ctx.conn, pid, parent_id, fields["ftype"])
    fid = create(ctx.conn, ctx.user["id"], pid, fields, parent_id, body.get("index"), primary)
    _log(ctx, "diamond_function_create", fid, {"text": fields["text"], "parent_id": parent_id, "primary": primary})
    return payload(ctx.conn, pid)


def _check_parent_new(conn, pid, parent_id, ftype):
    items = rows(conn, pid)
    if parent_id not in {f["id"] for f in items}:
        raise ApiError(400, "Fonction parente introuvable dans ce Space. Correctif : rechargez la page.")
    depth = levels(items)[parent_id] + 1
    if depth > MAX_LEVEL or (depth == MAX_LEVEL and ftype != "technique"):
        raise ApiError(409, "Niveau {} : l'arbre a trois niveaux ; seule une fonction technique va au niveau 4, sous une "
                            "tertiaire. Correctif : ajoutez-la plus à gauche, ou choisissez le type « Technique ».".format(depth))


def api_update(ctx):
    pid = access(ctx, "editor")
    row = _row(ctx, pid)
    body = ctx.body
    changes = _fields(body, partial=True)
    if "ftype" in changes and changes["ftype"] != "technique" and levels(rows(ctx.conn, pid))[row["id"]] == MAX_LEVEL:
        raise ApiError(409, "F{} est au niveau 4, réservé aux fonctions techniques. Correctif : déplacez-la d'abord plus à "
                            "gauche.".format(row["number"]))
    if "feedback_to" in body:
        target = body.get("feedback_to")
        if target in (None, "", 0):
            changes["feedback_to"] = None
        else:
            target = _row(ctx, pid, int(target))
            if target["id"] == row["id"]:
                raise ApiError(400, "Une rétroaction relie deux fonctions différentes. Correctif : choisissez une autre fonction.")
            changes["feedback_to"] = target["id"]
    if "number" in body:
        number = validate.int_param({"n": body.get("number")}, "n")
        if not 1 <= number <= 999:
            raise ApiError(400, "Numéro {} : de 1 à 999. Correctif : F1 à F999.".format(number))
        taken = ctx.conn.execute("SELECT archived FROM diamond_functions WHERE project_id = ? AND number = ? AND id != ?",
                                 (pid, number, row["id"])).fetchone()
        if taken:
            raise ApiError(409, "F{} est déjà pris{}. Correctif : gardez F{} ou choisissez un numéro libre.".format(
                number, " (fonction archivée : un numéro n'est jamais redonné)" if taken["archived"] else "", row["number"]))
        changes["number"] = number
    if not changes:
        return payload(ctx.conn, pid)
    sets = ", ".join("{} = ?".format(k) for k in changes)
    ctx.conn.execute("UPDATE diamond_functions SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(sets),
                     list(changes.values()) + [ctx.user["id"], db.utc_now(), row["id"]])
    _log(ctx, "diamond_function_update", row["id"], {k: v for k, v in changes.items() if k != "notes"})
    return payload(ctx.conn, pid)


def api_move(ctx):
    """{parent_id: id | null, index?: n} -- null puts the branch « hors arbre »; {primary: true} makes it the primary."""
    pid = access(ctx, "editor")
    row = _row(ctx, pid)
    body = ctx.body
    if body.get("primary"):
        other = ctx.conn.execute("SELECT number FROM diamond_functions WHERE project_id = ? AND archived = 0 AND is_primary = 1 "
                                 "AND id != ?", (pid, row["id"])).fetchone()
        if other:
            raise ApiError(409, "F{} est déjà la fonction primaire. Correctif : retirez-la d'abord de l'arbre.".format(other["number"]))
        sub_levels = levels([dict(f, parent_id=None if f["id"] == row["id"] else f["parent_id"]) for f in rows(ctx.conn, pid)])
        _branch_ok(ctx.conn, pid, row["id"], sub_levels)
        ctx.conn.execute("UPDATE diamond_functions SET is_primary = 1, parent_id = NULL WHERE id = ?", (row["id"],))
    else:
        parent_id = body.get("parent_id")
        parent_id = None if parent_id in (None, "") else int(parent_id)
        if parent_id is not None:
            _check_parent(ctx.conn, pid, row["id"], parent_id)
        ctx.conn.execute("UPDATE diamond_functions SET is_primary = 0 WHERE id = ?", (row["id"],))
        _place(ctx.conn, pid, row["id"], parent_id, body.get("index"))
    ctx.conn.execute("UPDATE diamond_functions SET updated_by = ?, updated_at = ? WHERE id = ?", (ctx.user["id"], db.utc_now(), row["id"]))
    _log(ctx, "diamond_function_move", row["id"], {"parent_id": body.get("parent_id"), "index": body.get("index"),
                                                    "primary": bool(body.get("primary"))})
    return payload(ctx.conn, pid)


def _branch_ok(conn, pid, fid, lv):
    for f in rows(conn, pid):
        depth = lv.get(f["id"], 1)
        if depth > MAX_LEVEL or (depth == MAX_LEVEL and f["ftype"] != "technique"):
            raise ApiError(409, "F{} arriverait au niveau {}. Correctif : raccourcissez la branche avant d'en faire la primaire."
                           .format(f["number"], depth))


def api_archive(ctx):
    """The function leaves the tree: its « comment » functions take its place under its parent; its number stays taken."""
    pid = access(ctx, "editor")
    row = _row(ctx, pid)
    children = _siblings(ctx.conn, pid, row["id"])
    if row["is_primary"] and children:
        raise ApiError(409, "F{} est la fonction primaire et porte {} fonction(s). Correctif : choisissez d'abord une autre "
                            "primaire, ou archivez ses fonctions secondaires.".format(row["number"], len(children)))
    spot = _siblings(ctx.conn, pid, row["parent_id"]).index(row["id"]) if not row["is_primary"] else 0
    ctx.conn.execute("UPDATE diamond_functions SET archived = 1, is_primary = 0, updated_by = ?, updated_at = ? WHERE id = ?",
                     (ctx.user["id"], db.utc_now(), row["id"]))
    ctx.conn.execute("UPDATE diamond_functions SET feedback_to = NULL WHERE feedback_to = ?", (row["id"],))
    for offset, child in enumerate(children):
        _place(ctx.conn, pid, child, row["parent_id"], spot + offset)
    _log(ctx, "diamond_function_archive", row["id"], {"number": row["number"], "text": row["text"]})
    return payload(ctx.conn, pid)
