"""« Caractéristiques » of Diamond (0.60.102, D-O-110, increment 2 of D-O-109): a special characteristic is not a row of a
table, it lives on an exact dimension of an exact part.

A characteristic C-n (number never reused; archived, never deleted): the DFMEA row it comes from -- its class is the class
confirmed there (nothing is typed twice) --, its nature (Product / Process), its label, its specification (char_spec.py),
the Diamond part that carries the dimension and, for an interface, the second part (the dimension goes on the part that
holds it, the other is cited), the drawing, sheet, zone and datum, how it is controlled (capability study, 100 % test,
or verified in design), the Cpk it must reach (else the customer's value for its class), the key test of the Test Base.
The summary of the special characteristics (char_export.py) is read from these links only.
"""
from core import audit, db, validate
from core.errors import ApiError

from . import char_links as CHL
from . import char_spec as SP
from . import classes as CL
from . import company_pn as PN
from . import dfmea as DF
from . import functions as F

TEXTS = {"label": ("Characteristic", 160), "prefix": ("Préfixe", 4), "unit": ("Unité", 16), "spec_text": ("Texte de spécification", 400),
         "drawing": ("Plan", 80), "sheet": ("Feuille", 16), "zone": ("Zone", 16), "datum": ("Datum", 40), "notes": ("Notes", 2000)}
MAX_ITEMS = 400


def _items(conn, pid, archived=0):
    return [dict(r) for r in conn.execute(
        "SELECT c.*, p.number AS part_number, p.name AS part_name, q.number AS part2_number, q.name AS part2_name, "
        "t.test_id AS test_code, t.title AS test_title FROM diamond_characteristics c "
        "LEFT JOIN diamond_parts p ON p.id = c.part_id LEFT JOIN diamond_parts q ON q.id = c.part2_id "
        "LEFT JOIN testing_tests t ON t.id = c.test_id WHERE c.project_id = ? AND c.archived = ? ORDER BY c.number", (pid, archived))]


def enrich(c, rows_by_id, cust):
    """The links read back: class and DFMEA line, specification, required Cpk, status, what is missing."""
    row = rows_by_id.get(c["dfmea_id"])
    cls = row["class_code"] if row and row["class_status"] == "confirmed" else ""
    key, label = SP.status(c, cls)
    c.update(code=CHL.code(c["number"]), spec=SP.spec(c), class_code=cls, class_symbol=CL.symbol(cust, cls, "process"),
             class_label=cust.get(cls.lower() + "_label", "") if cls else "", part=CHL.part_code(c["part_number"]),
             part2=CHL.part_code(c["part2_number"]), cpk_req=SP.cpk_required(c, cls, cust), status=key, status_label=label,
             missing=SP.missing(c), dfmea=None if row is None else {
                 "id": row["id"], "line": row["line"], "severity": row["severity"], "occurrence": row["occurrence"], "ap": row["ap"],
                 "function_number": row["function_number"], "function_text": row["function_text"], "failure_mode": row["failure_mode"],
                 "class_status": row["class_status"], "class_proposed": row["class_proposed"]})
    return c


def _order(c):
    return ({"CC": 0, "SC": 1}.get(c["class_code"], 2), c["number"])


def payload(conn, pid):
    rows = DF._rows(conn, pid)
    by_id = {r["id"]: r for r in rows}
    cust = CL.customer(conn, pid)
    pns = PN.links(conn, pid)  # 0.60.103 (D-O-112): the company PNs of the part, and of the second part of an interface
    items = [dict(enrich(c, by_id, cust), pns=[x["label"] for pid_ in (c["part_id"], c["part2_id"]) if pid_ for x in pns.get(pid_, [])])
             for c in _items(conn, pid)]
    from . import char_status  # 0.60.103 (D-O-115): PFMEA and control plan refs, Cpk, « à revoir », status
    char_status.apply(conn, pid, items, rows)
    summary = sorted([c for c in items if c["class_code"] in CL.CLASSES], key=_order)
    parts = [dict(r) for r in conn.execute("SELECT id, number, name FROM diamond_parts WHERE project_id = ? ORDER BY number", (pid,))]
    return {"items": items, "summary": summary, "archived": [enrich(c, by_id, cust) for c in _items(conn, pid, 1)],
            "counts": {k: sum(1 for c in summary if c["class_code"] == k) for k in CL.CLASSES},
            "customer": cust, "checks": checks(rows, items),
            "options": {"parts": parts, "tests": DF.tests(conn, pid),
                        "dfmea": [{"id": r["id"], "line": r["line"], "function_number": r["function_number"], "function_text": r["function_text"],
                                   "failure_mode": r["failure_mode"], "class_code": r["class_code"] if r["special"] else ""} for r in rows]},
            "labels": {"controls": SP.CONTROLS, "natures": SP.NATURES, "status": SP.STATUS, "texts": {k: v[0] for k, v in TEXTS.items()}}}


def checks(rows, items):
    out = []
    bare = [r for r in rows if CL.no_characteristic(r)]
    if bare:
        out.append("Ligne(s) {} du DFMEA : CC ou SC confirmée sans caractéristique C-n — « + Caractéristique » dans le DFMEA, ou "
                   "« Nouvelle caractéristique » ici.".format(", ".join(str(r["line"]) for r in bare[:12])))
    for c in items:
        if c["class_code"] and c["missing"]:
            out.append("{} ({}) : {} à préciser.".format(c["code"], c["class_code"], ", ".join(c["missing"])))
    orphan = [c for c in items if not c["dfmea_id"]]
    if orphan:
        out.append("{} sans ligne du DFMEA : sa classe ne peut venir de nulle part.".format(", ".join(c["code"] for c in orphan[:12])))
    return out


def _log(ctx, action, oid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "diamond_characteristics", oid, details, ctx.ip)


def _one(ctx, pid):
    row = ctx.conn.execute("SELECT * FROM diamond_characteristics WHERE id = ? AND project_id = ?",
                           (validate.int_param(ctx.params, "cid"), pid)).fetchone()
    if row is None:
        raise ApiError(404, "Caractéristique introuvable. Correctif : rechargez la page.")
    return dict(row)


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


def _fields(conn, pid, body, current):
    out = {}
    for name, (label, limit) in TEXTS.items():
        if name in body:
            value = str(body.get(name) or "").strip() if name == "notes" else " ".join(str(body.get(name) or "").split())
            if len(value) > limit:
                raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, limit, len(value)))
            out[name] = value
    if "label" in out and not out["label"]:
        raise ApiError(400, "Characteristic obligatoire. Correctif : nommez la cote, le seuil ou le temps (ex. « Entrefer aimant–capteur »).")
    for name, options, label in (("nature", SP.NATURES, "Nature"), ("control", SP.CONTROLS, "Contrôle")):
        if name in body:
            value = str(body.get(name) or "")
            if value not in options:
                raise ApiError(400, "{} « {} » inconnu. Correctif : {}.".format(label, value, ", ".join(options.values())))
            out[name] = value
    if "dfmea_id" in body:
        out["dfmea_id"] = _ref(conn, pid, "diamond_dfmea", body.get("dfmea_id"), "Ligne du DFMEA")
    for name, label in (("part_id", "Pièce"), ("part2_id", "Seconde pièce de l'interface")):
        if name in body:
            out[name] = _ref(conn, pid, "diamond_parts", body.get(name), label)
    part, part2 = out.get("part_id", current.get("part_id")), out.get("part2_id", current.get("part2_id"))
    if part2 and part2 == part:
        raise ApiError(400, "La seconde pièce de l'interface est la même que la première. Correctif : choisissez l'autre pièce, ou aucune.")
    if "test_id" in body:
        tid = body.get("test_id")
        out["test_id"] = None if tid in (None, "", 0, "0") else int(tid) if str(tid).isdigit() else -1
        if out["test_id"] is not None and out["test_id"] not in {t["id"] for t in DF.tests(conn, pid)}:
            raise ApiError(400, "Essai introuvable dans la Test Base de ce Space. Correctif : choisissez un essai de la liste.")
    if "cpk_required" in body:
        value, _d = SP.number(body.get("cpk_required"), "Cpk exigé")
        if value is not None and not 0.5 <= value <= 5:
            raise ApiError(400, "Cpk exigé « {} » : de 0,5 à 5, ou vide pour la valeur du client.".format(body.get("cpk_required")))
        out["cpk_required"] = value
    out.update(SP.limits(body, current))
    return out


def _prefill(conn, pid, did):
    """A characteristic made from a DFMEA row: its requirement as label, its key test, the part of its function when only one."""
    row = conn.execute("SELECT * FROM diamond_dfmea WHERE id = ?", (did,)).fetchone()
    parts = [r["part_id"] for r in conn.execute("SELECT part_id FROM diamond_part_functions WHERE function_id = ?", (row["function_id"],))] \
        if row["function_id"] else []
    return {"label": (row["requirement"] or row["failure_mode"] or "Caractéristique")[:160], "test_id": row["test_id"],
            "part_id": parts[0] if len(parts) == 1 else None}


def insert(conn, user_id, pid, fields):
    if conn.execute("SELECT COUNT(*) FROM diamond_characteristics WHERE project_id = ?", (pid,)).fetchone()[0] >= MAX_ITEMS:
        raise ApiError(409, "{} caractéristiques au plus par Space. Correctif : retirez celles qui ne servent plus.".format(MAX_ITEMS))
    number = fields.pop("number", None) or (conn.execute("SELECT COALESCE(MAX(number), 0) FROM diamond_characteristics WHERE project_id = ?",
                                                        (pid,)).fetchone()[0] + 1)
    now = db.utc_now()
    cols = list(fields)
    return conn.execute("INSERT INTO diamond_characteristics (project_id, number, {}created_by, created_at, updated_by, updated_at) "
                        "VALUES (?, ?, {}?, ?, ?, ?)".format("".join(c + ", " for c in cols), "?, " * len(cols)),
                        [pid, number] + [fields[c] for c in cols] + [user_id, now, user_id, now]).lastrowid, number


def api_list(ctx):
    return payload(ctx.conn, F.access(ctx))


def api_create(ctx):
    pid = F.access(ctx, "editor")
    body = dict(ctx.body)
    base = {}
    if body.get("dfmea_id"):
        base = _prefill(ctx.conn, pid, _ref(ctx.conn, pid, "diamond_dfmea", body["dfmea_id"], "Ligne du DFMEA"))
    fields = _fields(ctx.conn, pid, dict(base, **body), {})  # what the body says wins over what the row suggests
    fields.setdefault("label", "Nouvelle caractéristique")
    cid, number = insert(ctx.conn, ctx.user["id"], pid, fields)
    _log(ctx, "diamond_characteristic_create", cid, {"code": CHL.code(number), "dfmea_id": fields.get("dfmea_id")})
    return dict(payload(ctx.conn, pid), created=CHL.code(number), created_id=cid)


def api_update(ctx):
    pid = F.access(ctx, "editor")
    current = _one(ctx, pid)
    changes = _fields(ctx.conn, pid, ctx.body, current)
    changes = {k: v for k, v in changes.items() if current.get(k) != v}
    if changes:
        ctx.conn.execute("UPDATE diamond_characteristics SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(
            ", ".join(k + " = ?" for k in changes)), list(changes.values()) + [ctx.user["id"], db.utc_now(), current["id"]])
        from . import impact  # 0.60.103 (D-O-115): a new dimension -- everything citing the C-n is « à revoir »
        flagged = impact.raise_for(ctx.conn, ctx.user["id"], pid, current, dict(current, **changes))
        _log(ctx, "diamond_characteristic_update", current["id"], dict(changes, code=CHL.code(current["number"]), flagged=flagged))
    return payload(ctx.conn, pid)


def api_archive(ctx):
    """{archived: true | false}: a characteristic is taken out of service, never deleted -- its number is never given again."""
    pid = F.access(ctx, "editor")
    current = _one(ctx, pid)
    value = 1 if ctx.body.get("archived", True) else 0
    ctx.conn.execute("UPDATE diamond_characteristics SET archived = ?, updated_by = ?, updated_at = ? WHERE id = ?",
                     (value, ctx.user["id"], db.utc_now(), current["id"]))
    _log(ctx, "diamond_characteristic_archive" if value else "diamond_characteristic_restore", current["id"], {"code": CHL.code(current["number"])})
    return payload(ctx.conn, pid)
