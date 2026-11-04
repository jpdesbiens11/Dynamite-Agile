"""Mind map of an ideation session (D-B-073): cards placed freely on a surface
(pos_x, pos_y) and lines between them (tools_idea_links). The session question
is the centre node: a link with b_id NULL goes to the centre. Any editor of
the Space moves cards and draws or removes lines while the session is open;
every change is journalled.
"""
import math

from core import audit, db, validate
from core.errors import ApiError

WIDTH, HEIGHT = 3000, 2000
CENTRE = (WIDTH / 2, HEIGHT / 2)


def default_position(conn, sid):
    """Next free spot on a spiral around the centre, for a card added without coordinates."""
    n = conn.execute("SELECT COUNT(*) FROM tools_ideas WHERE session_id = ?", (sid,)).fetchone()[0]
    angle = n * 0.9
    radius = 230 + 40 * (n // 7)
    return round(CENTRE[0] + radius * math.cos(angle) - 90), round(CENTRE[1] + radius * math.sin(angle) - 30)


def coordinate(value, limit, label):
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ApiError(400, "Position « {} » illisible : nombre attendu.".format(label))
    return max(0.0, min(float(limit - 40), v))


def links(conn, sid):
    return [dict(r) for r in conn.execute("SELECT id, a_id, b_id FROM tools_idea_links WHERE session_id = ? ORDER BY id", (sid,))]


def _idea(conn, sid, iid):
    if iid is None:
        return None
    iid = int(iid)
    if not conn.execute("SELECT 1 FROM tools_ideas WHERE id = ? AND session_id = ?", (iid, sid)).fetchone():
        raise ApiError(400, "Carte {} introuvable dans cette séance.".format(iid))
    return iid


def add_link(ctx, row):
    a = _idea(ctx.conn, row["id"], ctx.body.get("a_id"))
    b = ctx.body.get("b_id")
    b = None if b in (None, "", 0, "0", "centre") else _idea(ctx.conn, row["id"], b)
    if a is None:
        raise ApiError(400, "Carte de départ manquante.")
    if a == b:
        raise ApiError(400, "Une carte ne se relie pas à elle-même.")
    if b is not None and a > b:
        a, b = b, a
    exists = ctx.conn.execute("SELECT 1 FROM tools_idea_links WHERE session_id = ? AND a_id = ? AND b_id IS ?",
                              (row["id"], a, b)).fetchone()
    if not exists:
        ctx.conn.execute("INSERT INTO tools_idea_links (session_id, a_id, b_id, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
                         (row["id"], a, b, ctx.user["id"], db.utc_now()))
        audit.log_action(ctx.conn, ctx.user["id"], "ideation_link_add", "tools_ideation", row["id"], {"a": a, "b": b}, ctx.ip)


def delete_link(ctx, row):
    lid = validate.int_param(ctx.params, "lid")
    if not ctx.conn.execute("DELETE FROM tools_idea_links WHERE id = ? AND session_id = ?", (lid, row["id"])).rowcount:
        raise ApiError(404, "Ligne introuvable.")
    audit.log_action(ctx.conn, ctx.user["id"], "ideation_link_delete", "tools_ideation", row["id"], {"link": lid}, ctx.ip)
