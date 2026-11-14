"""Diamond · DFMEA ↔ AI assistant (0.60.104, D-O-116): the import of « Exporter (.csv) » edited in a spreadsheet, or of the
answer an assistant gave to « Prompt pour l'IA » (ai_prompts.py).

A row of the file names its DFMEA row by « Ligne » (12 or L12, as exported). To catch a DFMEA changed since the export, a row
whose « Function of Focus Element » names another function than the current row is refused (re-export, or empty « Ligne » to
create a new row). Read-only columns (RPN, AP, Ticket Agile, Risque projet, Class…) are ignored: a class is decided in the
DFMEA, a ticket followed from it. Every value goes through dfmea._fields, the rules of the screen (ratings 1 to 10, the
function in the tree, the key test in the Test Base, the owner a member of the Space). A new row is placed after the last row of
its function. Each write is journalled; nothing is deleted.
"""
from core import audit, db

from . import actions as ACT
from . import ai_io as IO
from . import dfmea as DF
from . import functions as F

# field: (header of the export, other accepted keys)
TEXTS = {"higher": ("Higher-Level Element",), "focus": ("Focus Element",), "lower": ("Lower-Level Element",),
         "requirement": ("Requirement / Characteristic", "Requirement"), "failure_mode": ("Failure Mode",), "effect": ("Failure Effect", "Effect"),
         "cause": ("Failure Cause", "Cause"), "prevention": ("Prevention Controls", "Prevention"),
         "detection_ctrl": ("Detection Controls",), "action": ("Actions", "Action")}
RATINGS = {"severity": ("S", "Severity", "Severity (S)"), "occurrence": ("O", "Occurrence", "Occurrence (O)"), "detection": ("D", "Detection (D)")}
LINE = ("Ligne", "Line", "Code")
FUNCTION = ("Function of Focus Element", "Function", "Fonction")
TEST = ("Essai clé (Test Base)", "Key Test", "Essai clé", "Test")
OWNER = ("Responsable", "Owner")
DUE = ("Échéance", "Due Date", "Due")
STATUS = ("Status de l'action", "Action Status", "Status")
LABELS = dict({k: v[0] for k, v in TEXTS.items()}, severity="S", occurrence="O", detection="D", function_id=FUNCTION[0], test_id=TEST[0],
              action_owner_id=OWNER[0], action_due=DUE[0], action_status=STATUS[0])


class Refused(Exception):
    pass


def _context(conn, pid):
    functions = {f["number"]: f for f in F.rows(conn, pid)}
    tests = {t["code"].upper(): t for t in DF.tests(conn, pid)}
    members = ACT.members(conn, pid)
    return functions, tests, members


def _function(value, functions):
    if not value.strip():
        return None
    n = IO.number(value, "F")
    if n not in functions:
        raise Refused("fonction « {} » absente de l'arbre (F1, F2…). Correctif : une fonction de l'arbre, ou vide.".format(value))
    return functions[n]["id"]


def _test(value, tests):
    if not value.strip():
        return None
    code = value.split()[0].upper()
    if code not in tests:
        raise Refused("essai « {} » absent de la Test Base de ce Space. Correctif : un code TST-… de la liste du prompt, ou vide.".format(code))
    return tests[code]["id"]


def _owner(value, current_name, current_id, members):
    if not value.strip():
        return None
    if current_name and IO.same(value.lower(), current_name.lower()):
        return current_id
    hit = next((m["id"] for m in members if m["display_name"].lower() == value.strip().lower()), None)
    if hit is None:
        raise Refused("responsable « {} » : pas un membre actif du Space. Correctif : son nom affiché, ou vide.".format(value))
    return hit


def _status(value):
    v = value.strip()
    if not v:
        return "open"
    hit = next((k for k, label in ACT.DFMEA_STATUSES.items() if IO.norm(v) in (IO.norm(k), IO.norm(label))), None)
    if hit is None:
        raise Refused("status « {} » inconnu. Correctif : {}.".format(v, ", ".join(ACT.DFMEA_STATUSES.values())))
    return hit


def _wanted(row, cur, ctx_data):
    """{field: new value} for the fields the row gives (ids resolved), and the shown [label, old, new] of what differs."""
    functions, tests, members = ctx_data
    cur = cur or {}
    body, changes = {}, []

    def put(field, new, old, shown_old=None, shown_new=None):
        if cur and IO.same(old if old is not None else "", new if new is not None else ""):
            return
        body[field] = new
        changes.append([LABELS[field], IO.cell(shown_old if shown_old is not None else old), IO.cell(shown_new if shown_new is not None else new)])

    for field, names in TEXTS.items():
        ok, v = IO.get(row, *names)
        if ok:
            put(field, v, cur.get(field))
    for field, names in RATINGS.items():
        ok, raw = IO.get(row, *names)
        if ok:
            v = IO.number(raw, "") if raw.strip() else None
            if v is None and raw.strip():
                raise Refused("{} « {} » : un nombre de 1 à 10.".format(LABELS[field], raw))
            put(field, v, cur.get(field))
    ok, v = IO.get(row, *FUNCTION)
    if ok:
        fid = _function(v, functions)
        if cur and cur.get("function_id") and fid and fid != cur["function_id"]:
            raise Refused("la ligne L{} porte la fonction F{}, le fichier F{} : le DFMEA a changé depuis l'export ? Correctif : réexportez, "
                          "ou videz « Ligne » pour créer une nouvelle ligne.".format(cur["line"], cur["function_number"], IO.number(v, "F")))
        put("function_id", fid, cur.get("function_id"), "F{} {}".format(cur["function_number"], cur["function_text"]) if cur.get("function_number") else "", v)
    ok, v = IO.get(row, *TEST)
    if ok:
        put("test_id", _test(v, tests), cur.get("test_id"), cur.get("test_code") or "", v.split()[0] if v.strip() else "")
    ok, v = IO.get(row, *OWNER)
    if ok:
        put("action_owner_id", _owner(v, cur.get("action_owner_name"), cur.get("action_owner_id"), members), cur.get("action_owner_id"),
            cur.get("action_owner_name") or "", v)
    ok, v = IO.get(row, *DUE)
    if ok:
        put("action_due", v.strip()[:10], cur.get("action_due") or "")
    ok, v = IO.get(row, *STATUS)
    if ok:
        new = _status(v)
        put("action_status", new, cur.get("action_status") or "open", ACT.DFMEA_STATUSES.get(cur.get("action_status") or "open", ""),
            ACT.DFMEA_STATUSES[new])
    return body, changes


def plan(conn, pid, rows):
    current = {r["line"]: r for r in DF.rows(conn, pid)}
    data = _context(conn, pid)
    out = []
    for n, row in rows:
        ok, raw = IO.get(row, *LINE)
        line = IO.number(raw, "L") if ok and raw.strip() else None
        try:
            if ok and raw.strip() and line not in current:
                raise Refused("L{} n'existe pas dans ce DFMEA. Correctif : réexportez, ou videz « Ligne » pour créer une nouvelle ligne.".format(raw))
            cur = current.get(line)
            body, changes = _wanted(row, cur, data)
            if cur is None and not str(body.get("failure_mode") or "").strip():
                raise Refused("une nouvelle ligne demande au moins son Failure Mode.")
            values = DF._fields(conn, pid, body) if body else {}
        except Refused as exc:
            out.append(IO.entry(n, "L{}".format(line) if line else "", "refused", reason=str(exc)))
            continue
        except Exception as exc:  # ApiError of dfmea._fields: its message, the rule of the screen
            out.append(IO.entry(n, "L{}".format(line) if line else "", "refused", reason=getattr(exc, "message", str(exc))))
            continue
        label = (body.get("failure_mode") or (cur or {}).get("failure_mode") or "")[:120]
        if cur is None:
            out.append(IO.entry(n, "", "new", label, changes, values=values))
        else:
            out.append(IO.entry(n, "L{}".format(line), "update" if values else "same", label, changes, values=values, id=cur["id"]))
    return out


def apply(ctx, pid, entries):
    conn, uid = ctx.conn, ctx.user["id"]
    for e in entries:
        values = e["_values"]
        if e["kind"] == "update":
            conn.execute("UPDATE diamond_dfmea SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(", ".join(k + " = ?" for k in values)),
                         list(values.values()) + [uid, db.utc_now(), e["_id"]])
            audit.log_action(conn, uid, "diamond_dfmea_update", "diamond_dfmea", e["_id"], dict(values, source="import"), ctx.ip)
        else:
            fid = values.get("function_id")
            last = conn.execute("SELECT id FROM diamond_dfmea WHERE project_id = ? AND function_id IS ? ORDER BY position DESC, id DESC LIMIT 1",
                                (pid, fid)).fetchone() if fid else None
            did = DF.insert(conn, uid, pid, values, last["id"] if last else None)
            audit.log_action(conn, uid, "diamond_dfmea_create", "diamond_dfmea", did, {"source": "import"}, ctx.ip)


def api_import(ctx):
    """POST …/dfmea/import {file, mode: preview | apply, skip: [n…]}: preview by default, the editor role to apply."""
    pid = F.access(ctx, "editor" if ctx.body.get("mode") == "apply" else "reader")
    res = IO.run(ctx, pid, lambda rows: plan(ctx.conn, pid, rows), lambda todo: apply(ctx, pid, todo), "diamond_dfmea_import")
    return dict(res, dfmea=DF.payload(ctx.conn, pid)) if res["mode"] == "apply" else res
