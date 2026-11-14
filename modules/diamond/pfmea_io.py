"""Diamond · PFMEA ↔ spreadsheet and AI assistant (0.60.104, D-O-116).

GET  …/pfmea/export.csv  every row of the PFMEA (validated, drafts, rejected), one per line, with its code PF-30.1.
POST …/pfmea/import      the CSV edited in a spreadsheet, or the answer of an assistant (a ```json block whose keys are the
                         headers of the CSV; the keys of the generation prompt -- op, step, char, process_char, failure_mode,
                         effect, cause, cause_5m, prevention, detection, o, d, s -- are read too).
A row names its PFMEA row by « Code »; « Ligne » (L1) and « Opération » (OP30) place it; « Product Characteristic » names the C-n.
The rules are those of the screen (pfmea.fields): the S of a C-n is inherited from the DFMEA and locked (a lower S is refused;
an S equal to the inherited one changes nothing), the 5M class, ratings 1 to 10. A NEW row arrives as a DRAFT (D-O-114: never
directly in the validated PFMEA); a change of an existing row is applied after the preview, where the person reads it. State,
AP, ticket and the inherited S are read-only. Process access of the Space; every write journalled; nothing deleted.
"""
from core import audit, db

from . import actions as ACT
from . import ai_io as IO
from . import dfmea_io as DIO
from . import pfmea as PF
from . import process as PR

HEADERS = ["Code", "Ligne", "Opération", "Process Step", "Product Characteristic", "Process Characteristic", "Failure Mode", "Failure Effect",
           "Failure Cause", "Cause 5M", "Prevention Controls", "Detection Controls", "S", "S héritée", "O", "D", "AP", "Actions", "Responsable",
           "Échéance", "Status de l'action", "État", "Ticket Agile"]
TEXTS = {"process_step": ("Process Step", "step"), "process_char": ("Process Characteristic", "Process Char.", "process_char"),
         "failure_mode": ("Failure Mode",), "effect": ("Failure Effect", "effect"), "cause": ("Failure Cause", "cause"),
         "prevention": ("Prevention Controls", "prevention"), "detection_ctrl": ("Detection Controls", "detection"), "action": ("Actions", "action")}
RATINGS = {"severity": ("S", "Severity"), "occurrence": ("O", "Occurrence"), "detection": ("D",)}
LABELS = dict({k: v[0] for k, v in TEXTS.items()}, severity="S", occurrence="O", detection="D", cause_5m="Cause 5M", operation_id="Opération",
              characteristic_id="Product Characteristic", action_owner_id="Responsable", action_due="Échéance", action_status="Status de l'action")


def api_export(ctx):
    pid = PR.access(ctx)
    key = ctx.conn.execute("SELECT key FROM projects WHERE id = ?", (pid,)).fetchone()["key"]
    lines = {line["id"]: line["number"] for line in PR.lines(ctx.conn, pid)}
    out = []
    for r in PF.rows(ctx.conn, pid):
        out.append([r["code"], "L{}".format(lines[r["line_id"]]) if r["line_id"] in lines else "", "OP{}".format(r["op"]) if r["op"] else "",
                    r["process_step"], r["char_code"], r["process_char"], r["failure_mode"], r["effect"], r["cause"], PF.CAUSES_5M.get(r["cause_5m"], ""),
                    r["prevention"], r["detection_ctrl"], r["severity"] or "", r["inherited_s"] or "", r["occurrence"] or "", r["detection"] or "",
                    {"H": "High", "M": "Medium", "L": "Low"}.get(r["ap"], ""), r["action"], r["action_owner_name"] or "", r["action_due"],
                    ACT.DFMEA_STATUSES.get(r["action_status"], ""), PF.STATES.get(r["state"], ""), r["ticket"]["key"] if r["ticket"] else ""])
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_pfmea_export", "project", pid, {"rows": len(out)}, ctx.ip)
    return IO.csv_file(HEADERS, out, "pfmea_{}.csv".format(key))


def _context(conn, user, pid):
    from . import characteristics as CH
    lines = PR.payload(conn, user, pid)["lines"]
    ops = {(line["number"], o["op"]): o for line in lines for o in line["operations"]}
    chars = {c["code"].upper(): c for c in CH.payload(conn, pid)["items"]}
    return lines, ops, chars, ACT.members(conn, pid)


def _wanted(row, cur, data):
    lines, ops, chars, members = data
    cur = cur or {}
    body, changes = {}, []

    def put(field, new, old, shown_old=None, shown_new=None):
        if cur and IO.same(old if old is not None else "", new if new is not None else ""):
            return
        body[field] = new
        changes.append([LABELS[field], IO.cell(shown_old if shown_old is not None else old), IO.cell(shown_new if shown_new is not None else new)])

    ok_op, op_raw = IO.get(row, "Opération", "Operation", "op")
    ok_line, line_raw = IO.get(row, "Ligne", "Line")
    if ok_op and op_raw.strip():
        number = IO.number(line_raw, "L") if ok_line and line_raw.strip() else cur.get("line_number") or (lines[0]["number"] if lines else None)
        op = ops.get((number, IO.number(op_raw, "OP")))
        if op is None:
            raise DIO.Refused("{} absente de L{}. Correctif : une opération de Diamond → Procédés.".format(op_raw.strip(), number))
        put("operation_id", op["id"], cur.get("operation_id"), "OP{}".format(cur["op"]) if cur.get("op") else "", "OP{}".format(op["op"]))
    ok, v = IO.get(row, "Product Characteristic", "Product Char.", "char", "Characteristic")
    if ok:
        code = v.split()[0].upper() if v.strip() else ""
        if code and code not in chars:
            raise DIO.Refused("{} n'existe pas (inventée ?). Correctif : une caractéristique C-n de la liste, ou vide.".format(code))
        put("characteristic_id", chars[code]["id"] if code else None, cur.get("characteristic_id"), cur.get("char_code") or "", code)
    for field, names in TEXTS.items():
        ok, v = IO.get(row, *names)
        if ok:
            put(field, v, cur.get(field))
    ok, v = IO.get(row, "Cause 5M", "cause_5m", "5M")
    if ok:
        key = next((k for k, label in PF.CAUSES_5M.items() if IO.norm(v) in (IO.norm(k), IO.norm(label))), v.strip())
        put("cause_5m", key, cur.get("cause_5m") or "", PF.CAUSES_5M.get(cur.get("cause_5m"), ""), PF.CAUSES_5M.get(key, v))
    for field, names in RATINGS.items():
        ok, raw = IO.get(row, *names)
        if not ok:
            continue
        v = IO.number(raw, "") if raw.strip() else None
        if v is None and raw.strip():
            raise DIO.Refused("{} « {} » : un nombre de 1 à 10.".format(LABELS[field], raw))
        if field == "severity" and cur and not cur.get("severity") and v == cur.get("inherited_s"):
            continue  # the inherited S copied back: nothing changes
        put(field, v, cur.get(field))
    ok, v = IO.get(row, "Responsable", "Owner")
    if ok:
        put("action_owner_id", DIO._owner(v, cur.get("action_owner_name"), cur.get("action_owner_id"), members), cur.get("action_owner_id"),
            cur.get("action_owner_name") or "", v)
    ok, v = IO.get(row, "Échéance", "Due")
    if ok:
        put("action_due", v.strip()[:10], cur.get("action_due") or "")
    ok, v = IO.get(row, "Status de l'action", "Action Status")
    if ok:
        new = DIO._status(v)
        put("action_status", new, cur.get("action_status") or "open", ACT.DFMEA_STATUSES.get(cur.get("action_status") or "open", ""),
            ACT.DFMEA_STATUSES[new])
    return body, changes


def plan(conn, user, pid, rows):
    current = {r["code"].upper(): r for r in PF.rows(conn, pid)}
    data = _context(conn, user, pid)
    out = []
    for n, row in rows:
        ok, raw = IO.get(row, "Code")
        code = raw.strip().upper() if ok else ""
        try:
            if code and code not in current:
                raise DIO.Refused("{} n'existe pas dans ce PFMEA. Correctif : réexportez, ou videz « Code » pour créer une ligne.".format(raw))
            cur = current.get(code)
            body, changes = _wanted(row, cur, data)
            if cur is None and not (body.get("operation_id") and str(body.get("failure_mode") or "").strip()):
                raise DIO.Refused("une nouvelle ligne demande son Opération (OP30) et son Failure Mode.")
            values = PF.fields(conn, pid, body, {k: (cur or {}).get(k) for k in ("severity", "characteristic_id")}) if body else {}
        except DIO.Refused as exc:
            out.append(IO.entry(n, code, "refused", reason=str(exc)))
            continue
        except Exception as exc:  # ApiError of pfmea.fields (the locked S, the 5M class, a rating out of range)
            out.append(IO.entry(n, code, "refused", reason=getattr(exc, "message", str(exc))))
            continue
        label = (body.get("failure_mode") or (cur or {}).get("failure_mode") or "")[:120]
        if cur is None:
            out.append(IO.entry(n, "", "new", label + " (brouillon)", changes, values=values))
        else:
            out.append(IO.entry(n, cur["code"], "update" if values else "same", label, changes, values=values, id=cur["id"], op=cur["operation_id"]))
    return out


def apply(ctx, pid, entries, source):
    conn, uid = ctx.conn, ctx.user["id"]
    for e in entries:
        values = dict(e["_values"])
        if e["kind"] == "update":
            if "operation_id" in values and values["operation_id"] != e["_op"]:
                values["number"] = conn.execute("SELECT COALESCE(MAX(number), 0) + 1 FROM diamond_pfmea WHERE project_id = ? AND operation_id IS ?",
                                                (pid, values["operation_id"])).fetchone()[0]
            conn.execute("UPDATE diamond_pfmea SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(", ".join(k + " = ?" for k in values)),
                         list(values.values()) + [uid, db.utc_now(), e["_id"]])
            audit.log_action(conn, uid, "diamond_pfmea_update", "diamond_pfmea", e["_id"], dict(values, source="import"), ctx.ip)
        else:
            rid = PF.insert(conn, uid, pid, values, state="draft", source=source)
            audit.log_action(conn, uid, "diamond_pfmea_create", "diamond_pfmea", rid, {"source": source, "state": "draft"}, ctx.ip)


def api_import(ctx):
    """POST …/pfmea/import {file, mode: preview | apply, skip: [n…]}."""
    pid = PR.access(ctx, "editor" if ctx.body.get("mode") == "apply" else "reader")
    fmt = IO.read_rows(ctx.body.get("file"))[0]
    res = IO.run(ctx, pid, lambda rows: plan(ctx.conn, ctx.user, pid, rows),
                 lambda todo: apply(ctx, pid, todo, "ai" if fmt == "json" else "import"), "diamond_pfmea_import")
    return dict(res, pfmea=PF.payload(ctx.conn, ctx.user, pid)) if res["mode"] == "apply" else res
