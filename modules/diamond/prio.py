"""Diamond « Prioriser » (0.60.103, D-O-115): the key rows of the DFMEA and of the PFMEA together, and their actions placed
in time, in waves tied to the milestones of the project (before the prototype, before the pre-series, before production,
each with a date).

GET …/prio: the rows that matter (an action, an AP High, a confirmed class, or a wave) with what the filters read -- AP, CC ·
SC, Cpk under the required one (from the characteristics of the row), S ≥ 9, no detection control, overdue, mine. The PFMEA
rows come only when the « PFMEA » part is on and the account has the process access of the Space.
POST …/prio/waves/init creates the three start waves; PATCH …/prio/waves/<id> renames or dates one; POST …/prio/move
{kind, id, wave_id} puts an action in a wave: its due date becomes the date of the wave, and so does the due date of its
Agile ticket (with a line in the ticket's history). Every write is journalled.
"""
from core import audit, db, features, validate
from core.errors import ApiError

from . import actions as ACT
from . import functions as F

START = [("Vague 1 — avant le prototype", ""), ("Vague 2 — avant la pré-série", ""), ("Vague 3 — avant la production", "")]


def waves(conn, pid):
    return [dict(r) for r in conn.execute("SELECT * FROM diamond_waves WHERE project_id = ? ORDER BY number", (pid,))]


def _cpk_below(conn, pid):
    """{dfmea_id: True} and {characteristic_id: True} where a characteristic is under its required Cpk."""
    from . import capability as CAP
    from . import characteristics as CH
    by_row, by_char = {}, {}
    for c in CH.payload(conn, pid)["items"]:
        if c["control"] == "spc" and c["cpk_req"] is not None:
            _text, key, _label, _st = CAP.summary(conn, c)
            if key == "below":
                by_char[c["id"]] = True
                if c["dfmea_id"]:
                    by_row[c["dfmea_id"]] = True
    return by_row, by_char


def payload(conn, user, pid):
    from . import dfmea as DF
    by_row, by_char = _cpk_below(conn, pid)
    out = []
    for r in DF.rows(conn, pid):
        if r["action"].strip() or r["ap"] == "H" or r["special"] or r["wave_id"]:
            out.append(_item("dfmea", r, "L{}".format(r["line"]), "F{} {}".format(r["function_number"], r["function_text"]) if r["function_number"] else "",
                             r["severity"], r["class_code"] if r["special"] else "", by_row.get(r["id"], False), user))
    pf = features.on(conn, "diamond_pfmea")
    if pf:
        from . import pfmea as PF
        from . import process as PR
        if PR.allowed(conn, user, pid):
            for r in PF.rows(conn, pid):
                if r["state"] == "accepted" and (r["action"].strip() or r["ap"] == "H" or r["class_code"] or r["wave_id"]):
                    out.append(_item("pfmea", r, r["code"], "OP{} {}".format(r["op"], r["op_name"]) if r["op"] else "", r["s"], r["class_code"],
                                     by_char.get(r["characteristic_id"], False), user))
    return {"rows": out, "waves": waves(conn, pid), "pfmea": pf, "today": ACT.today(), "statuses": ACT.DFMEA_STATUSES}


def _item(kind, r, code, where, s, cls, below, user):
    return {"kind": kind, "id": r["id"], "code": code, "where": where, "failure_mode": r["failure_mode"], "s": s, "ap": r["ap"], "class_code": cls,
            "action": r["action"], "owner": r["action_owner_name"] or "", "owner_id": r["action_owner_id"], "due": r["action_due"],
            "status": r["action_status"], "late": r["late"], "ticket": r["ticket"], "wave_id": r["wave_id"], "cpk_below": below,
            "no_detection": not (r["detection_ctrl"] or "").strip(), "mine": r["action_owner_id"] == user["id"]}


def api_get(ctx):
    return payload(ctx.conn, ctx.user, F.access(ctx))


def api_waves_init(ctx):
    pid = F.access(ctx, "editor")
    if waves(ctx.conn, pid):
        raise ApiError(409, "Les vagues existent déjà. Correctif : renommez-les ou datez-les.")
    ctx.conn.executemany("INSERT INTO diamond_waves (project_id, number, name, due_date) VALUES (?, ?, ?, ?)",
                         [(pid, i, name, due) for i, (name, due) in enumerate(START, start=1)])
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_waves_init", "project", pid, {"waves": len(START)}, ctx.ip)
    return payload(ctx.conn, ctx.user, pid)


def api_wave_update(ctx):
    pid = F.access(ctx, "editor")
    w = ctx.conn.execute("SELECT * FROM diamond_waves WHERE id = ? AND project_id = ?", (validate.int_param(ctx.params, "wid"), pid)).fetchone()
    if w is None:
        raise ApiError(404, "Vague introuvable.")
    changes = {}
    if "name" in ctx.body:
        name = " ".join(str(ctx.body.get("name") or "").split())[:80]
        if not name:
            raise ApiError(400, "Nom de la vague obligatoire.")
        changes["name"] = name
    if "due_date" in ctx.body:
        changes["due_date"] = ACT.due(ctx.body.get("due_date"))
    if changes:
        ctx.conn.execute("UPDATE diamond_waves SET {} WHERE id = ?".format(", ".join(k + " = ?" for k in changes)), list(changes.values()) + [w["id"]])
        audit.log_action(ctx.conn, ctx.user["id"], "diamond_wave_update", "diamond_waves", w["id"], changes, ctx.ip)
        if changes.get("due_date"):
            for kind, table in (("dfmea", "diamond_dfmea"), ("pfmea", "diamond_pfmea")):
                for r in ctx.conn.execute("SELECT id FROM {} WHERE wave_id = ?".format(table), (w["id"],)).fetchall():
                    _due(ctx, table, r["id"], changes["due_date"])
    return payload(ctx.conn, ctx.user, pid)


def _due(ctx, table, oid, due):
    """The due date of the action and of its Agile ticket follow the wave."""
    from modules.agile import common
    row = ctx.conn.execute("SELECT action_due, issue_id FROM {} WHERE id = ?".format(table), (oid,)).fetchone()
    ctx.conn.execute("UPDATE {} SET action_due = ? WHERE id = ?".format(table), (due, oid))
    if row["issue_id"]:
        issue = ctx.conn.execute("SELECT id, due_date FROM agile_issues WHERE id = ?", (row["issue_id"],)).fetchone()
        if issue and (issue["due_date"] or "") != due:
            ctx.conn.execute("UPDATE agile_issues SET due_date = ?, updated_at = ? WHERE id = ?", (due, db.utc_now(), issue["id"]))
            common.add_history(ctx, issue["id"], "due_date", issue["due_date"], due)


def api_move(ctx):
    """{kind: dfmea | pfmea, id, wave_id (or null)}: the action goes into a wave (drag and drop of « Prioriser »)."""
    pid = F.access(ctx, "editor")
    kind = ctx.body.get("kind")
    table = {"dfmea": "diamond_dfmea", "pfmea": "diamond_pfmea"}.get(kind)
    if table is None:
        raise ApiError(400, "« kind » : dfmea ou pfmea.")
    if kind == "pfmea":
        from . import process as PR
        PR.access(ctx, "editor")
    try:
        oid = int(ctx.body.get("id"))
    except (TypeError, ValueError):
        oid = -1
    if not ctx.conn.execute("SELECT 1 FROM {} WHERE id = ? AND project_id = ?".format(table), (oid, pid)).fetchone():
        raise ApiError(404, "Ligne introuvable. Correctif : rechargez la page.")
    wid = ctx.body.get("wave_id")
    wave = None
    if wid not in (None, "", 0):
        wave = ctx.conn.execute("SELECT * FROM diamond_waves WHERE id = ? AND project_id = ?", (int(wid), pid)).fetchone()
        if wave is None:
            raise ApiError(400, "Vague introuvable.")
    ctx.conn.execute("UPDATE {} SET wave_id = ? WHERE id = ?".format(table), (wave["id"] if wave else None, oid))
    if wave and wave["due_date"]:
        _due(ctx, table, oid, wave["due_date"])
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_wave_move", table, oid, {"wave": wave["number"] if wave else None}, ctx.ip)
    return payload(ctx.conn, ctx.user, pid)
