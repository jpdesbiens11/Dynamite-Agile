"""Diamond · control plans ↔ spreadsheet and AI assistant (0.60.104, D-O-116).

GET  …/cplans/export.csv  every row of every plan (or of one plan: ?plan=2), with its plan PC-2 and its code CP-30.1.
POST …/cplans/import      the CSV edited in a spreadsheet, or the answer of an assistant (a ```json block, the keys being the
                          headers of the CSV).
A row names its plan by « Plan » (PC-2, it must exist: a plan is created on the screen, with its scope, line and phase) and its
row by « Code » (empty: a new row). « Opération » (OP30) places an assembly row on the line of its plan; « Pièce » (P-21) names
the part of a reception row; « Product Characteristic » the C-n (class and specification read from it, never typed), or
« Process Characteristic » in words. Class, specification, phase and revision are read-only. The rules are those of the
screen (control_plans._item_fields); a CC without a Reaction Plan stays flagged by the advice of the page. Process access of
the Space; every write journalled; nothing deleted.
"""
from core import audit, db

from . import ai_io as IO
from . import control_plans as CPL
from . import dfmea_io as DIO
from . import process as PR

HEADERS = ["Plan", "Code", "Opération", "Pièce", "Product Characteristic", "Process Characteristic", "Class", "Spec / Tolerance", "Machine · Jig",
           "Measurement Technique", "Sample", "Frequency", "Control Method", "Reaction Plan", "Phase", "Révision"]
TEXTS = {"equipment": ("Machine · Jig", "Machine", "Jig", "equipment"), "technique": ("Measurement Technique", "technique"),
         "sample": ("Sample", "Échantillon"), "frequency": ("Frequency", "Fréquence"), "control_method": ("Control Method", "control_method"),
         "reaction_plan": ("Reaction Plan", "reaction_plan")}
LABELS = dict({k: v[0] for k, v in TEXTS.items()}, operation_id="Opération", part_id="Pièce", characteristic_id="Product Characteristic",
              char_label="Process Characteristic")


def _data(conn, user, pid):
    return CPL.payload(conn, user, pid)


def api_export(ctx):
    pid = PR.access(ctx)
    key = ctx.conn.execute("SELECT key FROM projects WHERE id = ?", (pid,)).fetchone()["key"]
    d = _data(ctx.conn, ctx.user, pid)
    only = IO.number(ctx.query.get("plan"), "PC") if ctx.query.get("plan") else None
    out = []
    for p in d["plans"]:
        if only and p["number"] != only:
            continue
        for r in p["items"]:
            out.append([p["code"], r["code"], "OP{}".format(r["op"]) if r["op"] else "", (r["part"] or "").split(" ")[0], r["char_code"],
                        "" if r["char_code"] else r["characteristic"], r["class_symbol"] or r["class_code"], r["spec"], r["equipment"], r["technique"],
                        r["sample"], r["frequency"], r["control_method"], r["reaction_plan"], d["labels"]["phases"][p["phase"]], p["revision"]])
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_cplans_export", "project", pid, {"rows": len(out), "plan": only}, ctx.ip)
    return IO.csv_file(HEADERS, out, "plans_de_controle_{}{}.csv".format(key, "_PC-{}".format(only) if only else ""))


def _wanted(row, cur, plan, data):
    d, chars, parts = data
    cur = cur or {}
    body, changes = {}, []

    def put(field, new, old, shown_old=None, shown_new=None):
        if cur and IO.same(old if old is not None else "", new if new is not None else ""):
            return
        body[field] = new
        changes.append([LABELS[field], IO.cell(shown_old if shown_old is not None else old), IO.cell(shown_new if shown_new is not None else new)])

    ok, v = IO.get(row, "Opération", "Operation", "op")
    if ok and v.strip():
        if plan["scope"] != "assembly":
            raise DIO.Refused("{} : un plan de réception nomme une pièce (P-21), pas une opération.".format(plan["code"]))
        line = next((x for x in d["lines"] if x["id"] == plan["line_id"]), None)
        op = next((o for o in (line["operations"] if line else []) if o["op"] == IO.number(v, "OP")), None)
        if op is None:
            raise DIO.Refused("{} absente de la ligne de {}. Correctif : une opération de {}.".format(v.strip(), plan["code"], line["code"] if line else "sa ligne"))
        put("operation_id", op["id"], cur.get("operation_id"), "OP{}".format(cur["op"]) if cur.get("op") else "", "OP{}".format(op["op"]))
    ok, v = IO.get(row, "Pièce", "Part")
    if ok and v.strip():
        n = IO.number(v, "P")
        if n not in parts:
            raise DIO.Refused("pièce « {} » absente de Diamond. Correctif : un code P-n de la liste, ou vide.".format(v.strip()))
        put("part_id", parts[n], cur.get("part_id"), (cur.get("part") or "").split(" ")[0], "P-{}".format(n))
    ok, v = IO.get(row, "Product Characteristic", "Characteristic C-n", "char")
    if ok:
        code = v.split()[0].upper() if v.strip() else ""
        if code and code not in chars:
            raise DIO.Refused("{} n'existe pas (inventée ?). Correctif : une caractéristique C-n de la liste, ou vide.".format(code))
        put("characteristic_id", chars[code]["id"] if code else None, cur.get("characteristic_id"), cur.get("char_code") or "", code)
    ok, v = IO.get(row, "Process Characteristic", "process_char")
    if ok:
        put("char_label", v, cur.get("char_label") or "")
    for field, names in TEXTS.items():
        ok, v = IO.get(row, *names)
        if ok:
            put(field, v, cur.get(field))
    return body, changes


def plan(conn, user, pid, rows):
    d = _data(conn, user, pid)
    plans = {p["number"]: p for p in d["plans"]}
    chars = {c["code"].upper(): c for c in d["characteristics"]}
    parts = {p["number"]: p["id"] for p in d["parts"]}
    out = []
    for n, row in rows:
        ok, raw_plan = IO.get(row, "Plan")
        ok_code, raw = IO.get(row, "Code")
        code = raw.strip().upper() if ok_code else ""
        try:
            p = plans.get(IO.number(raw_plan, "PC")) if ok and raw_plan.strip() else None
            if p is None:
                raise DIO.Refused("plan « {} » introuvable. Correctif : PC-n d'un plan existant (créez le plan sur la page d'abord).".format(raw_plan.strip()))
            cur = next((r for r in p["items"] if r["code"].upper() == code), None) if code else None
            if code and cur is None:
                raise DIO.Refused("{} n'existe pas dans {}. Correctif : réexportez, ou videz « Code » pour créer une ligne.".format(code, p["code"]))
            body, changes = _wanted(row, cur, p, (d, chars, parts))
            values = CPL._item_fields(conn, pid, p, body) if body else {}
            if cur is None and not (values.get("characteristic_id") or str(values.get("char_label") or "").strip()):
                raise DIO.Refused("une nouvelle ligne contrôle une C-n ou nomme la caractéristique de procédé.")
        except DIO.Refused as exc:
            out.append(IO.entry(n, " ".join(x for x in (raw_plan.strip(), code) if x), "refused", reason=str(exc)))
            continue
        except Exception as exc:  # ApiError of control_plans._item_fields
            out.append(IO.entry(n, code, "refused", reason=getattr(exc, "message", str(exc))))
            continue
        label = p["code"] + " · " + ((cur or {}).get("characteristic") or body.get("char_label") or
                                     next((c["code"] + " " + c["label"] for c in chars.values() if c["id"] == values.get("characteristic_id")), ""))
        if cur is None:
            out.append(IO.entry(n, "", "new", label, changes, values=values, plan=p))
        else:
            out.append(IO.entry(n, p["code"] + " " + cur["code"], "update" if values else "same", label, changes, values=values, plan=p,
                                id=cur["id"], op=cur["operation_id"]))
    return out


def apply(ctx, pid, entries):
    conn, uid = ctx.conn, ctx.user["id"]
    for e in entries:
        values = dict(e["_values"])
        if e["kind"] == "update":
            if "operation_id" in values and values["operation_id"] != e["_op"]:
                values["seq"] = CPL.next_seq(conn, e["_plan"]["id"], values["operation_id"])  # its code follows its new operation
            conn.execute("UPDATE diamond_cp_items SET {}, updated_at = ? WHERE id = ?".format(", ".join(k + " = ?" for k in values)),
                         list(values.values()) + [db.utc_now(), e["_id"]])
            audit.log_action(conn, uid, "diamond_cp_item_update", "diamond_cp_items", e["_id"], dict(values, source="import"), ctx.ip)
        else:
            iid = CPL.insert_item(conn, pid, e["_plan"], values)
            audit.log_action(conn, uid, "diamond_cp_item_create", "diamond_cp_items", iid, {"plan": e["_plan"]["number"], "source": "import"}, ctx.ip)


def api_import(ctx):
    """POST …/cplans/import {file, mode: preview | apply, skip: [n…]}."""
    pid = PR.access(ctx, "editor" if ctx.body.get("mode") == "apply" else "reader")
    res = IO.run(ctx, pid, lambda rows: plan(ctx.conn, ctx.user, pid, rows), lambda todo: apply(ctx, pid, todo), "diamond_cplans_import")
    return dict(res, cplans=CPL.payload(ctx.conn, ctx.user, pid)) if res["mode"] == "apply" else res
