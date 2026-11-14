"""Diamond « PFMEA » (0.60.103, D-O-114, increment 5 of D-O-109): the Process FMEA, AIAG-VDA, on the operations of the
assembly lines (process.py).

One row = one process failure chain of an operation: process step, product characteristic (C-n), process characteristic,
failure mode, effect, cause classed in 5M (man, method, material, machine, measurement), prevention, detection, S, O, D, AP
(dfmea_ap.py, the same table as the DFMEA), action, owner, due date, Agile ticket (actions.py). Code PF-<op>.<n>.
Severity: the S of the DFMEA row of the characteristic is inherited and locked -- the process cannot make an effect less
severe: a lower S is refused, an empty S shows the inherited one. A row has a state: « draft » (proposed by the AI,
pfmea_ai.py, never in the validated PFMEA until a person accepts it), « accepted », « rejected » (kept: one knows the
proposal was read). Reading and writing go through the process access of the Space (process.access); every write is
journalled. The part can be turned off for the platform (core/features.py, « diamond_pfmea »).
"""
from core import audit, db, validate
from core.errors import ApiError

from . import actions as ACT
from . import dfmea_ap as AP
from . import process as PR

CAUSES_5M = {"man": "Main-d'œuvre", "method": "Méthode", "material": "Matière", "machine": "Machine", "measurement": "Mesure"}
STATES = {"draft": "Brouillon", "accepted": "Validée", "rejected": "Rejetée"}
TEXTS = {"process_step": ("Process Step", 200), "process_char": ("Process Characteristic", 200), "failure_mode": ("Failure Mode", 400),
         "effect": ("Failure Effect", 400), "cause": ("Failure Cause", 400), "prevention": ("Prevention Controls", 1000),
         "detection_ctrl": ("Detection Controls", 400), "action": ("Actions", 600)}
RATINGS = {"severity": "Severity (S)", "occurrence": "Occurrence (O)", "detection": "Detection (D)"}
MAX_ROWS = 800


def rows(conn, pid):
    """Every row with its operation, line, characteristic, inherited S, effective S, RPN, AP, ticket."""
    from . import characteristics as CH
    chars = {c["id"]: c for c in CH.payload(conn, pid)["items"]}
    ops = {o["id"]: o for o in conn.execute("SELECT o.*, l.number AS line_number, l.name AS line_name FROM diamond_operations o "
                                            "JOIN diamond_lines l ON l.id = o.line_id WHERE o.project_id = ?", (pid,))}
    items = [dict(r) for r in conn.execute("SELECT p.*, u.display_name AS action_owner_name FROM diamond_pfmea p "
                                           "LEFT JOIN users u ON u.id = p.action_owner_id WHERE p.project_id = ? "
                                           "ORDER BY p.position, p.id", (pid,))]
    for r in items:
        o, c = ops.get(r["operation_id"]), chars.get(r["characteristic_id"])
        inherited = c["dfmea"]["severity"] if c and c["dfmea"] else None
        s = max(x for x in (r["severity"], inherited) if x) if (r["severity"] or inherited) else None
        r.update(op=o["op"] if o else None, op_name=o["name"] if o else "", line_id=o["line_id"] if o else None,
                 line_number=o["line_number"] if o else None, code="PF-{}.{}".format(o["op"], r["number"]) if o else "PF-?.{}".format(r["number"]),
                 char_code=c["code"] if c else "", char_label=c["label"] if c else "", char_spec=c["spec"] if c else "",
                 class_code=c["class_code"] if c else "", class_symbol=c["class_symbol"] if c else "",
                 dfmea_line=c["dfmea"]["line"] if c and c["dfmea"] else None, inherited_s=inherited, s=s,
                 rpn=AP.rpn(s, r["occurrence"], r["detection"]), ap=AP.action_priority(s, r["occurrence"], r["detection"]))
    return ACT.enrich(conn, items, "pfmea")


def checks(items):
    out = []
    live = [r for r in items if r["state"] == "accepted"]
    drafts = [r for r in items if r["state"] == "draft"]
    if drafts:
        out.append("{} ligne(s) en brouillon (proposées par l'IA) : à accepter ou rejeter, une par une.".format(len(drafts)))
    high = [r for r in live if r["ap"] == "H" and not r["action"].strip()]
    if high:
        out.append("{} : AP High sans action.".format(", ".join(r["code"] for r in high[:12])))
    nodet = [r for r in live if r["class_code"] and not r["detection_ctrl"].strip()]
    if nodet:
        out.append("{} : caractéristique spéciale sans contrôle de détection.".format(", ".join(r["code"] for r in nodet[:12])))
    unrated = [r for r in live if r["failure_mode"] and not r["ap"]]
    if unrated:
        out.append("{} : cotation S, O, D incomplète.".format(", ".join(r["code"] for r in unrated[:12])))
    return out


def payload(conn, user, pid):
    items = rows(conn, pid)
    proc = PR.payload(conn, user, pid)
    return {"rows": items, "checks": checks(items), "lines": [{"id": line["id"], "number": line["number"], "code": line["code"], "name": line["name"],
                                                               "operations": [{"id": o["id"], "op": o["op"], "name": o["name"]} for o in line["operations"]]}
                                                              for line in proc["lines"]],
            "characteristics": proc["characteristics"], "members": ACT.members(conn, pid),
            "labels": {"causes": CAUSES_5M, "states": STATES, "ap": AP.AP_LABELS, "statuses": ACT.DFMEA_STATUSES,
                       "texts": {k: v[0] for k, v in TEXTS.items()}}}


def _log(ctx, action, oid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "diamond_pfmea", oid, details, ctx.ip)


def _row(ctx, pid):
    row = next((r for r in rows(ctx.conn, pid) if r["id"] == validate.int_param(ctx.params, "rid")), None)
    if row is None:
        raise ApiError(404, "Ligne du PFMEA introuvable. Correctif : rechargez la page.")
    return row


def fields(conn, pid, body, current):
    out = {}
    for name, (label, limit) in TEXTS.items():
        if name in body:
            value = str(body.get(name) or "").strip()
            if len(value) > limit:
                raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, limit, len(value)))
            out[name] = value
    if "cause_5m" in body:
        value = str(body.get("cause_5m") or "")
        value = next((k for k, v in CAUSES_5M.items() if value in (k, v) or value.lower() == v.lower()), value)
        if value and value not in CAUSES_5M:
            raise ApiError(400, "Cause 5M « {} » inconnue. Correctif : {}.".format(body.get("cause_5m"), ", ".join(CAUSES_5M.values())))
        out["cause_5m"] = value
    for name, label in RATINGS.items():
        if name in body:
            value = body.get(name)
            if value in (None, "", 0, "0"):
                out[name] = None
                continue
            try:
                value = int(value)
            except (TypeError, ValueError):
                value = -1
            if not 1 <= value <= 10:
                raise ApiError(400, "{} « {} » : de 1 à 10.".format(label, body.get(name)))
            out[name] = value
    if "operation_id" in body:
        out["operation_id"] = _ref(conn, pid, "diamond_operations", body.get("operation_id"), "Opération")
    if "characteristic_id" in body:
        out["characteristic_id"] = _ref(conn, pid, "diamond_characteristics", body.get("characteristic_id"), "Caractéristique")
    if "action_owner_id" in body:
        out["action_owner_id"] = ACT.owner(conn, pid, body.get("action_owner_id"))
    if "action_due" in body:
        out["action_due"] = ACT.due(body.get("action_due"))
    if "action_status" in body:
        if body.get("action_status") not in ACT.DFMEA_STATUSES:
            raise ApiError(400, "Status de l'action inconnu. Correctif : {}.".format(", ".join(ACT.DFMEA_STATUSES.values())))
        out["action_status"] = body["action_status"]
    _locked_s(conn, pid, dict(current, **out))
    return out


def _ref(conn, pid, table, value, label):
    if value in (None, "", 0, "0"):
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = -1
    if not conn.execute("SELECT 1 FROM {} WHERE id = ? AND project_id = ?".format(table), (value, pid)).fetchone():
        raise ApiError(400, "{} introuvable dans ce Space. Correctif : choisissez dans la liste.".format(label))
    return value


def inherited(conn, cid):
    """The S of the DFMEA row of a characteristic (None: no characteristic or no rated row)."""
    if not cid:
        return None
    row = conn.execute("SELECT d.severity FROM diamond_characteristics c JOIN diamond_dfmea d ON d.id = c.dfmea_id WHERE c.id = ?", (cid,)).fetchone()
    return row["severity"] if row else None


def _locked_s(conn, pid, row):
    s, base = row.get("severity"), inherited(conn, row.get("characteristic_id"))
    if s and base and s < base:
        raise ApiError(400, "S {} refusée : la sévérité vient du DFMEA ({}) et le procédé ne peut pas rendre un effet moins grave. "
                            "Correctif : laissez S vide (héritée) ou une valeur de {} à 10.".format(s, base, base))


def insert(conn, user_id, pid, values, state="accepted", source="manual"):
    if conn.execute("SELECT COUNT(*) FROM diamond_pfmea WHERE project_id = ?", (pid,)).fetchone()[0] >= MAX_ROWS:
        raise ApiError(409, "{} lignes au plus par PFMEA.".format(MAX_ROWS))
    number = conn.execute("SELECT COALESCE(MAX(number), 0) + 1 FROM diamond_pfmea WHERE project_id = ? AND operation_id IS ?",
                          (pid, values.get("operation_id"))).fetchone()[0]
    position = conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM diamond_pfmea WHERE project_id = ?", (pid,)).fetchone()[0]
    now = db.utc_now()
    cols = list(values)
    return conn.execute("INSERT INTO diamond_pfmea (project_id, number, position, state, source, {}created_by, created_at, updated_by, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, {}?, ?, ?, ?)".format("".join(c + ", " for c in cols), "?, " * len(cols)),
                        [pid, number, position, state, source] + [values[c] for c in cols] + [user_id, now, user_id, now]).lastrowid


def api_list(ctx):
    pid = PR.access(ctx)
    return payload(ctx.conn, ctx.user, pid)


def api_create(ctx):
    pid = PR.access(ctx, "editor")
    values = fields(ctx.conn, pid, ctx.body, {})
    rid = insert(ctx.conn, ctx.user["id"], pid, values)
    _log(ctx, "diamond_pfmea_create", rid, {k: v for k, v in values.items() if k in ("operation_id", "characteristic_id", "failure_mode")})
    return dict(payload(ctx.conn, ctx.user, pid), created=rid)


def api_update(ctx):
    pid = PR.access(ctx, "editor")
    row = _row(ctx, pid)
    changes = fields(ctx.conn, pid, ctx.body, {k: row[k] for k in ("severity", "characteristic_id")})
    if "operation_id" in changes and changes["operation_id"] != row["operation_id"]:
        changes["number"] = ctx.conn.execute("SELECT COALESCE(MAX(number), 0) + 1 FROM diamond_pfmea WHERE project_id = ? AND operation_id IS ?",
                                             (pid, changes["operation_id"])).fetchone()[0]
    if changes:
        ctx.conn.execute("UPDATE diamond_pfmea SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                         list(changes.values()) + [ctx.user["id"], db.utc_now(), row["id"]])
        _log(ctx, "diamond_pfmea_update", row["id"], dict(changes, code=row["code"]))
    return payload(ctx.conn, ctx.user, pid)


def api_review(ctx):
    """{state: accepted | rejected | draft}: a person accepts or rejects a row proposed by the AI (or puts it back to draft)."""
    pid = PR.access(ctx, "editor")
    row = _row(ctx, pid)
    state = str(ctx.body.get("state") or "")
    if state not in STATES:
        raise ApiError(400, "État « {} » inconnu. Correctif : {}.".format(state, ", ".join(STATES)))
    ctx.conn.execute("UPDATE diamond_pfmea SET state = ?, updated_by = ?, updated_at = ? WHERE id = ?", (state, ctx.user["id"], db.utc_now(), row["id"]))
    _log(ctx, "diamond_pfmea_review", row["id"], {"code": row["code"], "from": row["state"], "to": state})
    return payload(ctx.conn, ctx.user, pid)


def api_accept_all(ctx):
    pid = PR.access(ctx, "editor")
    n = ctx.conn.execute("UPDATE diamond_pfmea SET state = 'accepted', updated_by = ?, updated_at = ? WHERE project_id = ? AND state = 'draft'",
                         (ctx.user["id"], db.utc_now(), pid)).rowcount
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_pfmea_accept_all", "project", pid, {"rows": n}, ctx.ip)
    return dict(payload(ctx.conn, ctx.user, pid), accepted=n)
