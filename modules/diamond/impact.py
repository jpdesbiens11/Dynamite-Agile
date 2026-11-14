"""Impact of a change of a characteristic C-n (0.60.103, D-O-115): when its specification changes (an ECN moves the air
gap from 2,0 to 1,8 mm), everything that cites it is flagged « à revoir » until a person reviews it -- the PFMEA rows, the
control plan rows, its test of the Test Base, its capability study (measurements taken against the old limits). The same
mechanism as the impact analysis of Change Management, taken to the process. A flag is never deleted: « Revu » records who
and when (diamond_review_flags). characteristics.api_update calls raise_for(); POST …/characteristics/<id>/reviewed clears.
"""
from core import audit, db, validate
from core.errors import ApiError

from . import char_spec as SP
from . import functions as F

SPEC_FIELDS = ("nominal", "lsl", "usl", "unit", "prefix", "spec_text", "decimals")
KINDS = {"pfmea": "PFMEA", "cp_item": "Plan de contrôle", "test": "Essai", "capability": "Étude de capabilité"}


def raise_for(conn, user_id, pid, before, after):
    """Flags for everything citing the characteristic when its specification changed. Returns how many were raised."""
    if all(before.get(k) == after.get(k) for k in SPEC_FIELDS):
        return 0
    cid = before["id"]
    reason = "Cote modifiée : {} → {}".format(SP.spec(before) or "—", SP.spec(after) or "—")
    targets = []
    if _has(conn, "diamond_pfmea"):
        targets += [("pfmea", r["id"], "PFMEA ligne {}".format(r["id"])) for r in conn.execute(
            "SELECT id FROM diamond_pfmea WHERE characteristic_id = ? AND state != 'rejected'", (cid,))]
    if _has(conn, "diamond_cp_items"):
        targets += [("cp_item", r["id"], "Plan de contrôle PC-{}".format(r["number"])) for r in conn.execute(
            "SELECT i.id, p.number FROM diamond_cp_items i JOIN diamond_control_plans p ON p.id = i.plan_id WHERE i.characteristic_id = ?", (cid,))]
        if conn.execute("SELECT 1 FROM diamond_measurements WHERE characteristic_id = ? LIMIT 1", (cid,)).fetchone():
            targets.append(("capability", cid, "Étude de capabilité"))
    if after.get("test_id"):
        targets.append(("test", after["test_id"], "Essai de la Test Base"))
    now, made = db.utc_now(), 0
    for kind, oid, label in targets:
        if conn.execute("SELECT 1 FROM diamond_review_flags WHERE characteristic_id = ? AND kind = ? AND object_id IS ? AND reviewed_at = ''",
                        (cid, kind, oid)).fetchone():
            continue
        conn.execute("INSERT INTO diamond_review_flags (project_id, characteristic_id, kind, object_id, label, reason, raised_by, raised_at) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (pid, cid, kind, oid, label, reason, user_id, now))
        made += 1
    return made


def _has(conn, table):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone() is not None


def open_flags(conn, pid):
    """{characteristic_id: [flag]} -- the flags not reviewed yet."""
    out = {}
    for r in conn.execute("SELECT * FROM diamond_review_flags WHERE project_id = ? AND reviewed_at = '' ORDER BY raised_at", (pid,)):
        f = dict(r)
        f["kind_label"] = KINDS.get(f["kind"], f["kind"])
        out.setdefault(f["characteristic_id"], []).append(f)
    return out


def flagged(conn, pid, kind):
    """The ids of the objects of one kind (pfmea, cp_item) that wait for a review."""
    return {r["object_id"] for r in conn.execute("SELECT object_id FROM diamond_review_flags WHERE project_id = ? AND kind = ? AND reviewed_at = ''",
                                                 (pid, kind))}


def api_reviewed(ctx):
    """POST {flag_ids?: [...]}: the flags of the characteristic (all, or the listed ones) are reviewed -- who, when."""
    pid = F.access(ctx, "editor")
    cid = validate.int_param(ctx.params, "cid")
    if not ctx.conn.execute("SELECT 1 FROM diamond_characteristics WHERE id = ? AND project_id = ?", (cid, pid)).fetchone():
        raise ApiError(404, "Caractéristique introuvable.")
    ids = ctx.body.get("flag_ids")
    sql, args = "UPDATE diamond_review_flags SET reviewed_by = ?, reviewed_at = ? WHERE characteristic_id = ? AND reviewed_at = ''", [ctx.user["id"], db.utc_now(), cid]
    if isinstance(ids, list) and ids:
        sql += " AND id IN ({})".format(",".join("?" * len(ids)))
        args += [int(i) for i in ids]
    n = ctx.conn.execute(sql, args).rowcount
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_review_flags_cleared", "diamond_characteristics", cid, {"flags": n}, ctx.ip)
    from . import characteristics as CH
    return dict(CH.payload(ctx.conn, pid), reviewed=n)
