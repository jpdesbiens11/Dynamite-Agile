"""The process side of the Rover in DEMO (0.60.103, D-O-113 to D-O-115): its two line configurations, the PFMEA of the pilot
line (S inherited from the DFMEA), three control plans (reception, pilot line, prototype cell), the measurements of three
characteristics (C-10 capable, C-14 under its required Cpk and followed by a ticket, C-21 capable), the three waves of
« Prioriser » and the accounts that see the process side. Content in demo_process_data.py. Applied once per installation
(journal « demo_process_loaded »), after the company PNs (demo_pn); never on a Space that already describes a line.
"""
import datetime as dt
import types

from core import audit, db

from . import demo_process_data as D
from .demo_life import PREFIX
from .demo_pn import LOADED as PN_LOADED
from .headlamp import project_id

LOADED = "demo_process_loaded"


def ensure_process(ctx):
    conn = ctx.conn
    pid = project_id(conn)
    if pid is None:
        return None
    logged = lambda action: conn.execute("SELECT 1 FROM audit_log WHERE action = ? AND object_id = ?", (action, str(pid))).fetchone()  # noqa: E731
    if not logged(PN_LOADED) or logged(LOADED):
        return None
    counts = {}
    if not conn.execute("SELECT 1 FROM diamond_lines WHERE project_id = ?", (pid,)).fetchone():
        counts = _fill(ctx, conn, pid)
    audit.log_action(conn, ctx.user["id"], LOADED, "project", pid, counts, None)
    return counts


def _fill(ctx, conn, pid):
    people = {r["username"][len(PREFIX):]: r["id"] for r in conn.execute("SELECT id, username FROM users WHERE username LIKE ?", (PREFIX + "%",))}
    uid = people.get("nina", ctx.user["id"])
    chars = {r["number"]: r["id"] for r in conn.execute("SELECT id, number FROM diamond_characteristics WHERE project_id = ?", (pid,))}
    parts = {r["number"]: r["id"] for r in conn.execute("SELECT id, number FROM diamond_parts WHERE project_id = ?", (pid,))}
    now = db.utc_now()
    ops = _lines(conn, pid, uid, chars, now)
    for name in D.ACCESS:
        if name in people:
            conn.execute("INSERT OR IGNORE INTO diamond_process_access (project_id, user_id, granted_by, granted_at) VALUES (?, ?, ?, ?)",
                         (pid, people[name], uid, now))
    rows = _pfmea(conn, pid, uid, ops, chars, people)
    items = _plans(conn, pid, uid, ops, chars, parts, now)
    measures = _measures(conn, pid, chars, people, uid, now)
    ticket = _track(ctx, conn, pid, rows, people)
    waves = _waves(conn, pid, rows)
    return {"lines": len(D.LINES), "operations": len(ops), "pfmea": len(rows), "cp_items": items, "measurements": measures,
            "waves": waves, "ticket": ticket}


def _lines(conn, pid, uid, chars, now):
    """{(line number, op): operation id}"""
    ops = {}
    for number, name, description, operations in D.LINES:
        lid = conn.execute("INSERT INTO diamond_lines (project_id, number, name, description, created_by, created_at, updated_by, updated_at) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (pid, number, name, description, uid, now, uid, now)).lastrowid
        for op, op_name, op_text, equipment, trace, points in operations:
            oid = conn.execute("INSERT INTO diamond_operations (project_id, line_id, op, name, description, equipment, traceability, created_at, "
                               "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (pid, lid, op, op_name, op_text, equipment, trace, now, now)).lastrowid
            ops[(number, op)] = oid
            for position, (char, label, method, frequency) in enumerate(points):
                conn.execute("INSERT INTO diamond_control_points (project_id, operation_id, characteristic_id, label, method, frequency, position, "
                             "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (pid, oid, chars.get(char), label, method, frequency, position, now))
    return ops


def _pfmea(conn, pid, uid, ops, chars, people):
    """The PFMEA of the pilot line; returns [(op, failure mode, row id)]."""
    from modules.diamond import pfmea as PF
    out = []
    for (op, char, step, pchar, mode, effect, cause, m5, prevention, detection_ctrl, s, o, d, action, owner, due, state, source) in D.PFMEA:
        values = {"operation_id": ops[(1, op)], "characteristic_id": chars.get(char), "process_step": step, "process_char": pchar,
                  "failure_mode": mode, "effect": effect, "cause": cause, "cause_5m": m5, "prevention": prevention, "detection_ctrl": detection_ctrl,
                  "severity": s, "occurrence": o, "detection": d, "action": action, "action_owner_id": people.get(owner) if owner else None,
                  "action_due": due, "action_status": "open"}
        out.append((op, mode, PF.insert(conn, uid, pid, values, state=state, source=source)))
    return out


def _plans(conn, pid, uid, ops, chars, parts, now):
    count = 0
    for number, (title, scope, line, phase, revision, rows) in enumerate(D.PLANS, start=1):
        lid = conn.execute("SELECT id FROM diamond_lines WHERE project_id = ? AND number = ?", (pid, line)).fetchone()[0] if line else None
        plid = conn.execute("INSERT INTO diamond_control_plans (project_id, number, title, scope, line_id, phase, revision, created_by, created_at, "
                            "updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (pid, number, title, scope, lid, phase, revision, uid, now, uid, now)).lastrowid
        for position, (where, char, label, equipment, technique, sample, frequency, method, reaction) in enumerate(rows):
            oid = ops[(line, where)] if line else None
            seq = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM diamond_cp_items WHERE plan_id = ? AND operation_id IS ?", (plid, oid)).fetchone()[0]
            conn.execute("INSERT INTO diamond_cp_items (project_id, plan_id, seq, position, operation_id, part_id, characteristic_id, char_label, equipment, "
                         "technique, sample, frequency, control_method, reaction_plan, created_at, updated_at) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (pid, plid, seq, position, oid, None if line else parts.get(where), chars.get(char), label, equipment, technique, sample,
                          frequency, method, reaction, now, now))
            count += 1
    return count


def _measures(conn, pid, chars, people, uid, now):
    count = 0
    for char, (who, source, first, per_day, sample, values) in D.MEASURES.items():
        if char not in chars:
            continue
        start = dt.date.fromisoformat(first)
        for i, value in enumerate(values):
            day = start + dt.timedelta(days=i // per_day)
            taken = "{}T{:02d}:{:02d}:00".format(day.isoformat(), 9 + (i % per_day) // 4, (i % per_day) % 4 * 15)
            conn.execute("INSERT INTO diamond_measurements (project_id, characteristic_id, value, taken_at, sample, source, entered_by, created_at) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (pid, chars[char], value, taken, sample.format(i + 1), source, people.get(who, uid), now))
            count += 1
    return count


def _track(ctx, conn, pid, rows, people):
    """The action of the PFMEA row on the Cpk of C-14 becomes an Agile ticket, as « Suivre dans Agile » does; the demo accounts
    cannot sign in (inactive), so the ticket is made by the start-up account, then given to the owner of the action."""
    from modules.diamond import actions as ACT
    op, start = D.TRACKED
    rid = next((r for o, mode, r in rows if o == op and mode.startswith(start)), None)
    if rid is None:
        return ""
    owner = conn.execute("SELECT action_owner_id FROM diamond_pfmea WHERE id = ?", (rid,)).fetchone()[0]
    conn.execute("UPDATE diamond_pfmea SET action_owner_id = NULL WHERE id = ?", (rid,))
    shim = types.SimpleNamespace(conn=conn, user=ctx.user, params={"pid": pid, "kind": "pfmea", "oid": rid}, body={}, ip=None)
    made = ACT.api_track(shim)["tracked"]
    issue = conn.execute("SELECT issue_id FROM diamond_pfmea WHERE id = ?", (rid,)).fetchone()[0]
    conn.execute("UPDATE diamond_pfmea SET action_owner_id = ? WHERE id = ?", (owner, rid))
    conn.execute("UPDATE agile_issues SET assignee_id = ? WHERE id = ?", (owner, issue))
    return made


def _waves(conn, pid, rows):
    dfmea = {r["number"]: r["dfmea_id"] for r in conn.execute("SELECT number, dfmea_id FROM diamond_characteristics WHERE project_id = ?", (pid,))}
    for number, (name, due, members) in enumerate(D.WAVES, start=1):
        wid = conn.execute("INSERT INTO diamond_waves (project_id, number, name, due_date) VALUES (?, ?, ?, ?)", (pid, number, name, due)).lastrowid
        for m in members:
            if m[0] == "dfmea" and dfmea.get(m[1]):
                conn.execute("UPDATE diamond_dfmea SET wave_id = ? WHERE id = ?", (wid, dfmea[m[1]]))
            elif m[0] == "pfmea":
                rid = next((r for o, mode, r in rows if o == m[1] and mode.startswith(m[2])), None)
                if rid:
                    conn.execute("UPDATE diamond_pfmea SET wave_id = ? WHERE id = ?", (wid, rid))
    return len(D.WAVES)
