"""Diamond « Plans de contrôle » (0.60.103, D-O-115, increment 6 of D-O-109): the AIAG Control Plans of the Space.

Several plans per Space, because the line may have several configurations: each plan PC-n has a scope -- the parts at
reception, or the assembly steps of one line configuration (process.py) -- and a phase (Prototype, Pre-launch,
Production: the same plan evolves through the APQP phases, its revision says which one). A row: No. (CP-30.1 for the first
row of OP30, CP-R.4 at reception), the part or the operation, machine / fixture, the characteristic (a C-n, its class and
specification read from it; or a process characteristic in words), the measurement technique, sample and frequency, the
control method and the Reaction Plan. A CC without a Reaction Plan is flagged. Process access of the Space; every write
journalled; the part can be turned off (core/features.py, « diamond_cplans »).
"""
from core import audit, db, validate
from core.errors import ApiError

from . import process as PR

SCOPES = {"assembly": "Étapes d'assemblage", "reception": "Pièces · réception"}
PHASES = {"prototype": "Prototype", "prelaunch": "Pré-lancement", "production": "Production"}
TEXTS = {"title": ("Titre", 160), "revision": ("Révision", 12), "char_label": ("Characteristic", 160), "equipment": ("Machine · Jig", 200),
         "technique": ("Measurement Technique", 200), "sample": ("Sample", 80), "frequency": ("Frequency", 80),
         "control_method": ("Control Method", 300), "reaction_plan": ("Reaction Plan", 600)}


def code(item, op):
    return "CP-{}.{}".format(op if op else "R", item["seq"])


def plans(conn, pid):
    return [dict(r) for r in conn.execute("SELECT * FROM diamond_control_plans WHERE project_id = ? AND archived = 0 ORDER BY number", (pid,))]


def items(conn, pid, chars):
    ops = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM diamond_operations WHERE project_id = ?", (pid,))}
    parts = {r["id"]: dict(r) for r in conn.execute("SELECT id, number, name FROM diamond_parts WHERE project_id = ?", (pid,))}
    from . import impact
    review = impact.flagged(conn, pid, "cp_item")  # the dimension of its C-n changed: « à revoir »
    out = []
    for r in conn.execute("SELECT * FROM diamond_cp_items WHERE project_id = ? ORDER BY plan_id, position, id", (pid,)):
        it = dict(r)
        it["review"] = it["id"] in review
        o, p, c = ops.get(it["operation_id"]), parts.get(it["part_id"]), chars.get(it["characteristic_id"])
        it.update(code=code(it, o["op"] if o else None), op=o["op"] if o else None, op_name=o["name"] if o else "",
                  part=("P-{} {}".format(p["number"], p["name"]) if p else ""), char_code=c["code"] if c else "",
                  characteristic=c["label"] if c else it["char_label"], class_code=c["class_code"] if c else "",
                  class_symbol=c["class_symbol"] if c else "", spec=c["spec"] if c else "", nature=c["nature"] if c else "process")
        out.append(it)
    return out


def payload(conn, user, pid):
    from . import characteristics as CH
    chars = {c["id"]: c for c in CH.payload(conn, pid)["items"]}
    proc = PR.payload(conn, user, pid)
    all_plans = plans(conn, pid)
    rows = items(conn, pid, chars)
    lines = {line["id"]: line for line in proc["lines"]}
    for p in all_plans:
        p["code"] = "PC-{}".format(p["number"])
        p["line"] = lines[p["line_id"]]["code"] + " · " + lines[p["line_id"]]["name"] if p["line_id"] in lines else ""
        p["items"] = [r for r in rows if r["plan_id"] == p["id"]]
    return {"plans": all_plans, "checks": checks(all_plans, chars),
            "lines": [{"id": line["id"], "code": line["code"], "name": line["name"], "operations": [{"id": o["id"], "op": o["op"], "name": o["name"],
                       "equipment": ", ".join(o["equipment_list"])} for o in line["operations"]]} for line in proc["lines"]],
            "characteristics": proc["characteristics"],
            "parts": [dict(r) for r in conn.execute("SELECT id, number, name FROM diamond_parts WHERE project_id = ? ORDER BY number", (pid,))],
            "labels": {"scopes": SCOPES, "phases": PHASES, "texts": {k: v[0] for k, v in TEXTS.items()}}}


def checks(all_plans, chars):
    out = []
    for p in all_plans:
        bare = [r["code"] for r in p["items"] if r["class_code"] == "CC" and not r["reaction_plan"].strip()]
        if bare:
            out.append("{} : {} — CC sans Reaction Plan : écrivez la réaction, jusqu'au dernier bon contrôle.".format(p["code"], ", ".join(bare)))
    if all_plans:
        cited = {r["characteristic_id"] for p in all_plans for r in p["items"]}
        missing = [c["code"] for c in chars.values() if c["class_code"] and c["id"] not in cited]
        if missing:
            out.append("{} : caractéristique spéciale absente de tout plan de contrôle.".format(", ".join(missing)))
    return out


def _log(ctx, action, table, oid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, table, oid, details, ctx.ip)


def _texts(body, names):
    out = {}
    for name in names:
        if name in body:
            label, limit = TEXTS[name]
            value = str(body.get(name) or "").strip()
            if len(value) > limit:
                raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, limit, len(value)))
            out[name] = value
    return out


def _choice(body, name, options, label):
    value = str(body.get(name) or "")
    if value not in options:
        raise ApiError(400, "{} « {} » inconnu. Correctif : {}.".format(label, value, ", ".join(options.values())))
    return value


def _plan(ctx, pid):
    row = ctx.conn.execute("SELECT * FROM diamond_control_plans WHERE id = ? AND project_id = ?", (validate.int_param(ctx.params, "planid"), pid)).fetchone()
    if row is None:
        raise ApiError(404, "Plan de contrôle introuvable. Correctif : rechargez la page.")
    return dict(row)


def _line_ok(conn, pid, scope, line_id):
    if scope == "reception":
        return None
    if line_id in (None, "", 0):
        raise ApiError(400, "Un plan des étapes d'assemblage suit une configuration de ligne. Correctif : choisissez la ligne.")
    if not conn.execute("SELECT 1 FROM diamond_lines WHERE id = ? AND project_id = ?", (int(line_id), pid)).fetchone():
        raise ApiError(400, "Ligne introuvable dans ce Space.")
    return int(line_id)


def api_get(ctx):
    return payload(ctx.conn, ctx.user, PR.access(ctx))


def api_plan_create(ctx):
    pid = PR.access(ctx, "editor")
    scope = _choice(ctx.body, "scope", SCOPES, "Portée") if ctx.body.get("scope") else "assembly"
    phase = _choice(ctx.body, "phase", PHASES, "Phase") if ctx.body.get("phase") else "prototype"
    line_id = _line_ok(ctx.conn, pid, scope, ctx.body.get("line_id"))
    t = _texts(ctx.body, ("title", "revision"))
    number = ctx.conn.execute("SELECT COALESCE(MAX(number), 0) + 1 FROM diamond_control_plans WHERE project_id = ?", (pid,)).fetchone()[0]
    now = db.utc_now()
    plid = ctx.conn.execute("INSERT INTO diamond_control_plans (project_id, number, title, scope, line_id, phase, revision, created_by, created_at, "
                            "updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (pid, number, t.get("title") or SCOPES[scope], scope, line_id, phase, t.get("revision") or "A", ctx.user["id"], now,
                             ctx.user["id"], now)).lastrowid
    _log(ctx, "diamond_control_plan_create", "diamond_control_plans", plid, {"number": number, "scope": scope, "phase": phase})
    return dict(payload(ctx.conn, ctx.user, pid), created=plid)


def api_plan_update(ctx):
    pid = PR.access(ctx, "editor")
    plan = _plan(ctx, pid)
    changes = _texts(ctx.body, ("title", "revision"))
    if "phase" in ctx.body:
        changes["phase"] = _choice(ctx.body, "phase", PHASES, "Phase")
    if "line_id" in ctx.body:
        changes["line_id"] = _line_ok(ctx.conn, pid, plan["scope"], ctx.body.get("line_id"))
    if "archived" in ctx.body:
        changes["archived"] = 1 if ctx.body.get("archived") else 0
    if changes:
        ctx.conn.execute("UPDATE diamond_control_plans SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                         list(changes.values()) + [ctx.user["id"], db.utc_now(), plan["id"]])
        _log(ctx, "diamond_control_plan_update", "diamond_control_plans", plan["id"], changes)
    return payload(ctx.conn, ctx.user, pid)


def _item_fields(conn, pid, plan, body):
    out = _texts(body, ("char_label", "equipment", "technique", "sample", "frequency", "control_method", "reaction_plan"))
    for name, table, label in (("operation_id", "diamond_operations", "Opération"), ("part_id", "diamond_parts", "Pièce"),
                               ("characteristic_id", "diamond_characteristics", "Caractéristique")):
        if name in body:
            value = body.get(name)
            if value in (None, "", 0, "0"):
                out[name] = None
                continue
            if not conn.execute("SELECT 1 FROM {} WHERE id = ? AND project_id = ?".format(table), (int(value), pid)).fetchone():
                raise ApiError(400, "{} introuvable dans ce Space.".format(label))
            out[name] = int(value)
    if out.get("operation_id") and plan["line_id"] and not conn.execute("SELECT 1 FROM diamond_operations WHERE id = ? AND line_id = ?",
                                                                         (out["operation_id"], plan["line_id"])).fetchone():
        raise ApiError(400, "Cette opération n'est pas sur la ligne du plan. Correctif : une opération de sa ligne.")
    return out


def api_item_create(ctx):
    pid = PR.access(ctx, "editor")
    plan = _plan(ctx, pid)
    values = _item_fields(ctx.conn, pid, plan, ctx.body)
    if not values.get("characteristic_id") and not values.get("char_label"):
        raise ApiError(400, "Une ligne contrôle une caractéristique C-n, ou nomme la caractéristique de procédé. Correctif : choisissez la C-n.")
    iid = insert_item(ctx.conn, pid, plan, values)
    _log(ctx, "diamond_cp_item_create", "diamond_cp_items", iid, {"plan": plan["number"], "characteristic_id": values.get("characteristic_id")})
    return payload(ctx.conn, ctx.user, pid)


def next_seq(conn, plan_id, operation_id):
    return conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM diamond_cp_items WHERE plan_id = ? AND operation_id IS ?",
                        (plan_id, operation_id)).fetchone()[0]


def insert_item(conn, pid, plan, values):
    """A row at the end of the plan, numbered after the last one of its operation (CP-30.2), or of the reception (CP-R.5)."""
    now = db.utc_now()
    cols = list(values)
    return conn.execute("INSERT INTO diamond_cp_items (project_id, plan_id, seq, position, {}created_at, updated_at) VALUES (?, ?, ?, "
                        "(SELECT COUNT(*) FROM diamond_cp_items WHERE plan_id = ?), {}?, ?)".format("".join(c + ", " for c in cols), "?, " * len(cols)),
                        [pid, plan["id"], next_seq(conn, plan["id"], values.get("operation_id")), plan["id"]] + [values[c] for c in cols]
                        + [now, now]).lastrowid


def api_item_update(ctx):
    pid = PR.access(ctx, "editor")
    row = ctx.conn.execute("SELECT * FROM diamond_cp_items WHERE id = ? AND project_id = ?", (validate.int_param(ctx.params, "iid"), pid)).fetchone()
    if row is None:
        raise ApiError(404, "Ligne du plan introuvable. Correctif : rechargez la page.")
    plan = dict(ctx.conn.execute("SELECT * FROM diamond_control_plans WHERE id = ?", (row["plan_id"],)).fetchone())
    if ctx.body.get("delete"):
        ctx.conn.execute("DELETE FROM diamond_cp_items WHERE id = ?", (row["id"],))
        _log(ctx, "diamond_cp_item_delete", "diamond_cp_items", row["id"], {"plan": plan["number"]})
        return payload(ctx.conn, ctx.user, pid)
    changes = _item_fields(ctx.conn, pid, plan, ctx.body)
    if changes:
        ctx.conn.execute("UPDATE diamond_cp_items SET {}, updated_at = ? WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                         list(changes.values()) + [db.utc_now(), row["id"]])
        _log(ctx, "diamond_cp_item_update", "diamond_cp_items", row["id"], changes)
    return payload(ctx.conn, ctx.user, pid)


def refs(conn, pid):
    """{characteristic_id: ["PC-2 CP-30.1", …]} for the summary of the special characteristics."""
    ops = {r["id"]: r["op"] for r in conn.execute("SELECT id, op FROM diamond_operations WHERE project_id = ?", (pid,))}
    out = {}
    for r in conn.execute("SELECT i.*, p.number AS plan_number FROM diamond_cp_items i JOIN diamond_control_plans p ON p.id = i.plan_id "
                          "WHERE i.project_id = ? AND p.archived = 0 AND i.characteristic_id IS NOT NULL ORDER BY p.number, i.position", (pid,)):
        out.setdefault(r["characteristic_id"], []).append("PC-{} {}".format(r["plan_number"], code(dict(r), ops.get(r["operation_id"]))))
    return out
