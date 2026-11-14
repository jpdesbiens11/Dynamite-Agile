"""Diamond « Procédés » (0.60.103, D-O-113, increment 4 of D-O-109): the assembly line, described for the PFMEA and the
control plans.

A Space may have several line configurations (prototypes at school, pre-series at a partner…). A line has its operations
in order (OP10, OP20…; the number is the order), the equipment and fixtures of each one (one per line of text), whether it
closes the traceability of the CC (serial number ↔ test results), and its control points -- each one names the
characteristic C-n it protects, or a process check without a C-n, with its method and frequency.
Access (D-O-109 default, no change to the core): the process side of a Space (Procédés, PFMEA, Plans de contrôle) is shown
to the administrators, to the « Admin du projet » of the Space and to the members it lists (diamond_process_access); the
other members do not see it. Reading needs the reader role, writing the editor role, both on top of the list. Every write
is journalled. The part can be turned off for the platform (core/features.py, « diamond_process »).
"""
from core import audit, db, permissions, validate
from core.errors import ApiError

from . import functions as F

TEXTS = {"name": ("Nom", 120), "description": ("Description", 1000), "equipment": ("Équipements", 600), "label": ("Contrôle", 160),
         "method": ("Méthode", 160), "frequency": ("Fréquence", 80)}


def allowed(conn, user, pid):
    if user["is_admin"] or permissions.is_project_manager(conn, user, pid):
        return True
    return conn.execute("SELECT 1 FROM diamond_process_access WHERE project_id = ? AND user_id = ?", (pid, user["id"])).fetchone() is not None


def access(ctx, minimum="reader"):
    """The Space, if this account may see its process side (the editor role to write)."""
    pid = F.access(ctx, minimum)
    if not allowed(ctx.conn, ctx.user, pid):
        raise ApiError(403, "Procédés, PFMEA et plans de contrôle : réservés aux membres que l'Admin du Space a choisis. Correctif : "
                            "demandez-lui l'accès (Diamond → Procédés → Accès).")
    return pid


def _text(body, name):
    label, limit = TEXTS[name]
    value = str(body.get(name) or "").strip() if name in ("description", "equipment") else " ".join(str(body.get(name) or "").split())
    if len(value) > limit:
        raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, limit, len(value)))
    return value


def lines(conn, pid):
    return [dict(r) for r in conn.execute("SELECT * FROM diamond_lines WHERE project_id = ? AND archived = 0 ORDER BY number", (pid,))]


def operations(conn, pid):
    """Every operation of the Space, its control points (with the class of their C-n read from the DFMEA)."""
    from . import characteristics as CH  # characteristics -> dfmea; imported here, after both are loaded
    chars = {c["id"]: c for c in CH.payload(conn, pid)["items"]}
    ops = [dict(r) for r in conn.execute("SELECT * FROM diamond_operations WHERE project_id = ? ORDER BY line_id, op", (pid,))]
    points = {}
    for r in conn.execute("SELECT * FROM diamond_control_points WHERE project_id = ? ORDER BY position, id", (pid,)):
        p = dict(r)
        c = chars.get(p["characteristic_id"])
        p.update(code=c["code"] if c else "", class_code=c["class_code"] if c else "", class_symbol=c["class_symbol"] if c else "",
                 char_label=c["label"] if c else "", spec=c["spec"] if c else "", nature=c["nature"] if c else "process")
        points.setdefault(p["operation_id"], []).append(p)
    for o in ops:
        o["code"], o["points"] = "OP{}".format(o["op"]), points.get(o["id"], [])
        o["equipment_list"] = [x.strip() for x in o["equipment"].splitlines() if x.strip()]
    return ops, chars


def payload(conn, user, pid):
    ops, chars = operations(conn, pid)
    out = lines(conn, pid)
    for line in out:
        line["code"] = "L{}".format(line["number"])
        line["operations"] = [o for o in ops if o["line_id"] == line["id"]]
    covered = {p["characteristic_id"] for o in ops for p in o["points"] if p["characteristic_id"]}
    special = [c for c in chars.values() if c["class_code"]]
    manager = user["is_admin"] or permissions.is_project_manager(conn, user, pid)
    return {"lines": out, "characteristics": [{"id": c["id"], "code": c["code"], "label": c["label"], "class_code": c["class_code"],
                                              "class_symbol": c["class_symbol"], "spec": c["spec"], "nature": c["nature"]} for c in chars.values()],
            "checks": ["{} ({}) : aucun point de contrôle sur la ligne.".format(c["code"], c["class_code"]) for c in special if c["id"] not in covered],
            "manager": manager, "access": _access_list(conn, pid) if manager else None}


def _access_list(conn, pid):
    granted = {r["user_id"] for r in conn.execute("SELECT user_id FROM diamond_process_access WHERE project_id = ?", (pid,))}
    rows = conn.execute("SELECT u.id, u.display_name, m.role FROM memberships m JOIN users u ON u.id = m.user_id "
                        "WHERE m.project_id = ? AND u.is_active = 1 ORDER BY u.display_name", (pid,)).fetchall()
    return [{"id": r["id"], "name": r["display_name"], "role": r["role"], "granted": r["role"] == "manager" or r["id"] in granted,
             "manager": r["role"] == "manager"} for r in rows]


def _log(ctx, action, table, oid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, table, oid, details, ctx.ip)


def _row(ctx, pid, table, key):
    row = ctx.conn.execute("SELECT * FROM {} WHERE id = ? AND project_id = ?".format(table), (validate.int_param(ctx.params, key), pid)).fetchone()
    if row is None:
        raise ApiError(404, "Élément introuvable (déjà retiré ?). Correctif : rechargez la page.")
    return dict(row)


def api_get(ctx):
    return payload(ctx.conn, ctx.user, access(ctx))


def api_line_create(ctx):
    pid = access(ctx, "editor")
    name = _text(ctx.body, "name") or "Ligne d'assemblage"
    number = ctx.conn.execute("SELECT COALESCE(MAX(number), 0) + 1 FROM diamond_lines WHERE project_id = ?", (pid,)).fetchone()[0]
    now = db.utc_now()
    lid = ctx.conn.execute("INSERT INTO diamond_lines (project_id, number, name, description, created_by, created_at, updated_by, updated_at) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (pid, number, name, _text(ctx.body, "description"), ctx.user["id"], now, ctx.user["id"], now)).lastrowid
    _log(ctx, "diamond_line_create", "diamond_lines", lid, {"name": name})
    return dict(payload(ctx.conn, ctx.user, pid), created=lid)


def api_line_update(ctx):
    pid = access(ctx, "editor")
    line = _row(ctx, pid, "diamond_lines", "lid")
    changes = {k: _text(ctx.body, k) for k in ("name", "description") if k in ctx.body}
    if "archived" in ctx.body:
        changes["archived"] = 1 if ctx.body.get("archived") else 0
    if changes.get("name") == "":
        raise ApiError(400, "Nom de la ligne obligatoire.")
    if changes:
        ctx.conn.execute("UPDATE diamond_lines SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                         list(changes.values()) + [ctx.user["id"], db.utc_now(), line["id"]])
        _log(ctx, "diamond_line_update", "diamond_lines", line["id"], changes)
    return payload(ctx.conn, ctx.user, pid)


def _op_number(value):
    try:
        op = int(str(value).upper().replace("OP", "").strip())
    except (TypeError, ValueError):
        op = -1
    if not 1 <= op <= 9990:
        raise ApiError(400, "Numéro d'opération « {} » : un nombre de 1 à 9990 (OP10, OP20…).".format(value))
    return op


def api_op_create(ctx):
    pid = access(ctx, "editor")
    line = _row(ctx, pid, "diamond_lines", "lid")
    last = ctx.conn.execute("SELECT COALESCE(MAX(op), 0) FROM diamond_operations WHERE line_id = ?", (line["id"],)).fetchone()[0]
    op = _op_number(ctx.body["op"]) if ctx.body.get("op") not in (None, "") else (last // 10 + 1) * 10
    if ctx.conn.execute("SELECT 1 FROM diamond_operations WHERE line_id = ? AND op = ?", (line["id"], op)).fetchone():
        raise ApiError(409, "OP{} existe déjà sur cette ligne. Correctif : un autre numéro (OP{} par exemple).".format(op, op + 5))
    now = db.utc_now()
    oid = ctx.conn.execute("INSERT INTO diamond_operations (project_id, line_id, op, name, description, equipment, traceability, created_at, updated_at) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (pid, line["id"], op, _text(ctx.body, "name") or "Opération", _text(ctx.body, "description"),
                                                                  _text(ctx.body, "equipment"), 1 if ctx.body.get("traceability") else 0, now, now)).lastrowid
    _log(ctx, "diamond_operation_create", "diamond_operations", oid, {"op": op, "line": line["number"]})
    return dict(payload(ctx.conn, ctx.user, pid), created=oid)


def api_op_update(ctx):
    pid = access(ctx, "editor")
    o = _row(ctx, pid, "diamond_operations", "oid")
    changes = {k: _text(ctx.body, k) for k in ("name", "description", "equipment") if k in ctx.body}
    if "op" in ctx.body:
        changes["op"] = _op_number(ctx.body["op"])
        if changes["op"] != o["op"] and ctx.conn.execute("SELECT 1 FROM diamond_operations WHERE line_id = ? AND op = ?", (o["line_id"], changes["op"])).fetchone():
            raise ApiError(409, "OP{} existe déjà sur cette ligne.".format(changes["op"]))
    if "traceability" in ctx.body:
        changes["traceability"] = 1 if ctx.body.get("traceability") else 0
    if changes:
        ctx.conn.execute("UPDATE diamond_operations SET {}, updated_at = ? WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                         list(changes.values()) + [db.utc_now(), o["id"]])
        _log(ctx, "diamond_operation_update", "diamond_operations", o["id"], changes)
    return payload(ctx.conn, ctx.user, pid)


def api_op_delete(ctx):
    pid = access(ctx, "editor")
    o = _row(ctx, pid, "diamond_operations", "oid")
    used = ctx.conn.execute("SELECT 1 FROM diamond_pfmea WHERE operation_id = ? LIMIT 1", (o["id"],)).fetchone() if _has(ctx.conn, "diamond_pfmea") else None
    if used:
        raise ApiError(409, "OP{} a des lignes de PFMEA. Correctif : déplacez-les ou retirez-les d'abord.".format(o["op"]))
    ctx.conn.execute("DELETE FROM diamond_operations WHERE id = ?", (o["id"],))
    _log(ctx, "diamond_operation_delete", "diamond_operations", o["id"], {"op": o["op"], "name": o["name"]})
    return payload(ctx.conn, ctx.user, pid)


def _has(conn, table):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone() is not None


def api_point_create(ctx):
    pid = access(ctx, "editor")
    o = _row(ctx, pid, "diamond_operations", "oid")
    cid = ctx.body.get("characteristic_id")
    if cid not in (None, "", 0):
        if not ctx.conn.execute("SELECT 1 FROM diamond_characteristics WHERE id = ? AND project_id = ?", (int(cid), pid)).fetchone():
            raise ApiError(400, "Caractéristique introuvable dans ce Space.")
        cid = int(cid)
    else:
        cid = None
    label = _text(ctx.body, "label")
    if cid is None and not label:
        raise ApiError(400, "Un point de contrôle protège une caractéristique C-n, ou nomme ce qu'il vérifie. Correctif : choisissez la C-n "
                            "ou écrivez le contrôle (ex. « étanchéité »).")
    pid_ = ctx.conn.execute("INSERT INTO diamond_control_points (project_id, operation_id, characteristic_id, label, method, frequency, position, created_at) "
                            "VALUES (?, ?, ?, ?, ?, ?, (SELECT COUNT(*) FROM diamond_control_points WHERE operation_id = ?), ?)",
                            (pid, o["id"], cid, label, _text(ctx.body, "method"), _text(ctx.body, "frequency"), o["id"], db.utc_now())).lastrowid
    _log(ctx, "diamond_control_point_create", "diamond_control_points", pid_, {"op": o["op"], "characteristic_id": cid})
    return payload(ctx.conn, ctx.user, pid)


def api_point_delete(ctx):
    pid = access(ctx, "editor")
    p = _row(ctx, pid, "diamond_control_points", "cpid")
    ctx.conn.execute("DELETE FROM diamond_control_points WHERE id = ?", (p["id"],))
    _log(ctx, "diamond_control_point_delete", "diamond_control_points", p["id"], {"characteristic_id": p["characteristic_id"], "label": p["label"]})
    return payload(ctx.conn, ctx.user, pid)


def api_access(ctx):
    """PUT {user_ids: [...]}: the members who see the process side (Admin du projet or administrator only)."""
    pid = F.access(ctx, "editor")
    if not (ctx.user["is_admin"] or permissions.is_project_manager(ctx.conn, ctx.user, pid)):
        raise ApiError(403, "Seul l'Admin du Space (ou un administrateur) choisit qui voit les procédés.")
    members = {m["id"] for m in _access_list(ctx.conn, pid)}
    try:
        ids = {int(i) for i in ctx.body.get("user_ids") or []}
    except (TypeError, ValueError):
        ids = {-1}
    if ids - members:
        raise ApiError(400, "Seuls les membres du Space peuvent recevoir l'accès. Correctif : ajoutez-les d'abord au Space.")
    ctx.conn.execute("DELETE FROM diamond_process_access WHERE project_id = ?", (pid,))
    now = db.utc_now()
    ctx.conn.executemany("INSERT INTO diamond_process_access (project_id, user_id, granted_by, granted_at) VALUES (?, ?, ?, ?)",
                         [(pid, uid, ctx.user["id"], now) for uid in sorted(ids)])
    _log(ctx, "diamond_process_access", "project", pid, {"user_ids": sorted(ids)})
    return payload(ctx.conn, ctx.user, pid)


def point_label(p):
    """« C-14 SC · poka-yoke + X̄-R »"""
    head = " ".join(x for x in (p.get("code"), p.get("class_symbol")) if x) or p.get("label") or ""
    return " · ".join(x for x in (head, p.get("method"), p.get("frequency")) if x)

