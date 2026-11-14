"""What the summary of the special characteristics reads from the process side (0.60.103, D-O-115): for each characteristic
C-n, the PFMEA rows (PF-30.1) and the control plan rows (PC-2 CP-30.1) that cite it, its Cpk / Ppk from the measurements
(capability.py), the flags of an ECN waiting for a review (impact.py), the Agile ticket of the action that follows it, and the
status that results -- « À compléter » first, then « À revoir » after a change of the dimension, then « Capable »,
« Sous l'exigé », « Étude à faire », « Essai 100 % », « Vérifiée en conception ».
"""
from . import capability as CAP
from . import control_plans as CPL
from . import impact as IM


def _pfmea(conn, pid):
    out = {}
    for r in conn.execute("SELECT p.characteristic_id, p.number, p.issue_id, o.op FROM diamond_pfmea p LEFT JOIN diamond_operations o ON o.id = p.operation_id "
                          "WHERE p.project_id = ? AND p.state = 'accepted' AND p.characteristic_id IS NOT NULL ORDER BY o.op, p.number", (pid,)):
        out.setdefault(r["characteristic_id"], []).append(("PF-{}.{}".format(r["op"] if r["op"] else "?", r["number"]), r["issue_id"]))
    return out


def _tickets(conn, ids):
    ids = [i for i in ids if i]
    if not ids:
        return {}
    return {r["id"]: "{}-{}".format(r["key"], r["number"]) for r in conn.execute(
        "SELECT i.id, i.number, p.key FROM agile_issues i JOIN projects p ON p.id = i.project_id WHERE i.id IN ({})".format(",".join("?" * len(ids))), ids)}


def apply(conn, pid, items, dfmea_rows):
    pf, cp, flags = _pfmea(conn, pid), CPL.refs(conn, pid), IM.open_flags(conn, pid)
    issue_of_row = {r["id"]: r["issue_id"] for r in dfmea_rows}
    tickets = _tickets(conn, [i for v in pf.values() for _c, i in v] + list(issue_of_row.values()))
    for c in items:
        refs = pf.get(c["id"], [])
        text, key, label, st = CAP.summary(conn, c)
        c.update(pfmea_refs=[code for code, _i in refs], cp_refs=cp.get(c["id"], []), flags=flags.get(c["id"], []),
                 cpk=st["cpk"] if st else None, ppk=st["ppk"] if st else None, n=st["n"] if st else 0, short=st["short"] if st else False,
                 cpk_text=text if c["control"] != "design" else "—", ticket="")
        candidates = [i for _c, i in refs if i] + ([issue_of_row.get(c["dfmea_id"])] if c["dfmea_id"] else [])
        c["ticket"] = next((tickets[i] for i in candidates if i in tickets), "")
        if not c["class_code"] or c["status"] == "incomplete":
            continue
        if c["flags"]:
            c["status"], c["status_label"] = "review", "À revoir ({})".format(len(c["flags"]))
        elif c["control"] != "design":
            c["status"], c["status_label"] = key, label
            if key == "below" and c["ticket"]:
                c["status_label"] = "Sous l'exigé · " + c["ticket"]
    return items
