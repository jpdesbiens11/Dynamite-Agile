"""Brainwriting 6-3-5 with connected participants (D-B-073).

A brainwriting session goes setup -> running -> review. Participants join;
the facilitator (creator of the session or an admin of the Space) starts it.
The clock is derived, never stored per round: round = elapsed // minutes + 1
from `started_at`, so no background job is needed; « Tour suivant » moves
`started_at` back so the current round ends now. After the last round the
session is in review (also when the facilitator ends it early).

Pairs change every round with the round-robin « circle » method: with n
participants everybody meets everybody in n - 1 rounds (then it cycles); an
odd participant joins a pair (a trio). While running, a participant sees his
own ideas and those of every partner met so far -- live, by polling; in
review everybody sees everything.
"""
from datetime import datetime, timedelta, timezone

from core import audit, db, permissions
from core.errors import ApiError


def _parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def people(conn, sid):
    return [dict(r) for r in conn.execute(
        "SELECT p.user_id, p.position, u.display_name AS name FROM tools_ideation_people p "
        "JOIN users u ON u.id = p.user_id WHERE p.session_id = ? ORDER BY p.position, p.user_id", (sid,))]


def clock(row, now=None):
    """{phase, round, rounds, minutes, ends_at, server_now} -- phase is the effective one."""
    now = now or datetime.now(timezone.utc)
    out = {"phase": row["phase"] or "setup", "round": 0, "rounds": row["rounds"], "minutes": row["round_minutes"],
           "ends_at": None, "server_now": now.isoformat(timespec="seconds")}
    if out["phase"] == "running":
        started = _parse(row["started_at"])
        length = row["round_minutes"] * 60
        rnd = int((now - started).total_seconds() // length) + 1
        if rnd > row["rounds"]:
            out.update(phase="review", round=row["rounds"])
        else:
            out.update(round=rnd, ends_at=(started + timedelta(seconds=rnd * length)).isoformat(timespec="seconds"))
    elif out["phase"] == "review":
        out["round"] = row["rounds"]
    return out


def pairs(user_ids, rnd):
    """Groups of round `rnd` (1-based), circle method; an odd one out joins the last pair."""
    ids = list(user_ids)
    if len(ids) < 2:
        return [ids] if ids else []
    if len(ids) % 2:
        ids.append(None)
    n = len(ids)
    shift = (rnd - 1) % (n - 1)
    rest = ids[1:]
    rest = rest[-shift:] + rest[:-shift] if shift else rest
    order = [ids[0]] + rest
    groups = [[order[i], order[n - 1 - i]] for i in range(n // 2)]
    out, lonely = [], []
    for g in groups:
        g = [u for u in g if u is not None]
        (out if len(g) == 2 else lonely).append(g)
    for g in lonely:
        (out[-1].extend(g) if out else out.append(g))
    return out


def partners_so_far(user_ids, me, rnd):
    """{round: [partner ids]} for rounds 1..rnd."""
    out = {}
    for r in range(1, rnd + 1):
        for g in pairs(user_ids, r):
            if me in g:
                out[r] = [u for u in g if u != me]
    return out


def is_facilitator(conn, user, row, pid):
    return row["created_by"] == user["id"] or permissions.is_project_manager(conn, user, pid)


def state(conn, user, row, pid):
    """The brainwriting block of the session detail, and the authors this user may see (None = all)."""
    c = clock(row)
    folks = people(conn, row["id"])
    ids = [p["user_id"] for p in folks]
    me = user["id"]
    so_far = partners_so_far(ids, me, c["round"]) if c["phase"] == "running" and me in ids else {}
    current = so_far.get(c["round"], [])
    names = {p["user_id"]: p["name"] for p in folks}
    visible = None
    if c["phase"] == "running":
        visible = {me} | {u for group in so_far.values() for u in group}
    block = dict(c, people=folks, joined=me in ids, facilitator=is_facilitator(conn, user, row, pid),
                 ideas_per_round=row["ideas_per_round"],
                 partners=[{"user_id": u, "name": names.get(u, "?")} for u in current],
                 met=sorted({names.get(u, "?") for group in so_far.values() for u in group}),
                 groups=[[names.get(u, "?") for u in g] for g in pairs(ids, c["round"])] if c["round"] else [])
    return block, visible


def _log(ctx, action, sid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "tools_ideation", sid, details, ctx.ip)


def join(ctx, row):
    if clock(row)["phase"] == "review":
        raise ApiError(409, "La séance est en revue : il n'est plus possible de la rejoindre.")
    pos = ctx.conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM tools_ideation_people WHERE session_id = ?",
                           (row["id"],)).fetchone()[0]
    ctx.conn.execute("INSERT OR IGNORE INTO tools_ideation_people (session_id, user_id, position, joined_at) "
                     "VALUES (?, ?, ?, ?)", (row["id"], ctx.user["id"], pos, db.utc_now()))
    _log(ctx, "ideation_join", row["id"])


def control(ctx, row, pid, action):
    """start / next / finish, by the facilitator."""
    if not is_facilitator(ctx.conn, ctx.user, row, pid):
        raise ApiError(403, "Seul l'animateur (créateur de la séance) ou un admin du Space pilote les tours.")
    c = clock(row)
    now = datetime.now(timezone.utc)
    if action == "start":
        if c["phase"] != "setup":
            raise ApiError(409, "La séance est déjà démarrée.")
        if not ctx.conn.execute("SELECT 1 FROM tools_ideation_people WHERE session_id = ?", (row["id"],)).fetchone():
            raise ApiError(409, "Aucun participant. Correctif : chacun clique « Rejoindre » avant le départ.")
        ctx.conn.execute("UPDATE tools_ideation SET phase = 'running', started_at = ? WHERE id = ?",
                         (now.isoformat(timespec="seconds"), row["id"]))
    elif action == "next":
        if c["phase"] != "running":
            raise ApiError(409, "Aucun tour en cours.")
        ends = _parse(c["ends_at"])
        started = _parse(row["started_at"]) - (ends - now)
        ctx.conn.execute("UPDATE tools_ideation SET started_at = ? WHERE id = ?", (started.isoformat(timespec="seconds"), row["id"]))
    elif action == "finish":
        ctx.conn.execute("UPDATE tools_ideation SET phase = 'review' WHERE id = ?", (row["id"],))
    else:
        raise ApiError(400, "Action inconnue (start, next, finish).")
    _log(ctx, "ideation_" + action, row["id"], {"round": c["round"]})
