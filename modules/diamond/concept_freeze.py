"""Diamond · a frozen brick (0.60.116, D-O-129): the concept of a function line is chosen, the search stops there.

« Figer » takes a text that confirms the concept retained (what it is, in a few sentences: the standard brick and the variant
kept, its key figures). The brick becomes « Selected » and frozen: its name, its description, its status and its other fields
no longer change, no concept sheet is added, changed or archived under it, and it joins no new Pugh matrix; the tree shows
the frozen text as the selected concept. The person who carries the brick and its functions may still change.
« Défiger » takes a reason (journalled) and opens the brick again. Every write is journalled.
"""
from core import audit, db, validate
from core.errors import ApiError

from . import concepts as C
from . import functions as F

LIMITS = {"text": 1000, "reason": 300}
OPEN_FIELDS = {"owner_id", "function_ids"}  # what a frozen brick still accepts


def frozen_error(c, what):
    return ApiError(409, "La brique CB-{} est figée (concept retenu : « {} »). {} est bloqué. Correctif : « Défiger » la brique "
                         "dans son panneau, avec une raison, si le concept doit être revu.".format(c["number"], (c.get("frozen_text") or "")[:80], what))


def guard(conn, pid, cid, what):
    """Raises 409 when the brick is frozen."""
    row = conn.execute("SELECT id, number, frozen, frozen_text FROM diamond_concepts WHERE id = ? AND project_id = ?", (cid, pid)).fetchone()
    if row is not None and row["frozen"]:
        raise frozen_error(dict(row), what)


def guard_fields(c, fields):
    """api_update of a frozen brick: only its owner and its functions may change."""
    if c.get("frozen") and set(fields) - OPEN_FIELDS:
        raise frozen_error(c, "Modifier " + ", ".join(sorted(set(fields) - OPEN_FIELDS)))


def _text(body, name, label):
    value = str(body.get(name) or "").strip()
    if not value:
        raise ApiError(400, "{} obligatoire. Correctif : {}".format(label, "décrivez en quelques phrases le concept retenu (la brique "
                            "standard et la variante gardée, ses chiffres clés)." if name == "text" else "dites pourquoi le concept "
                            "doit être revu."))
    if len(value) > LIMITS[name]:
        raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, LIMITS[name], len(value)))
    return value


def api_freeze(ctx):
    """{text}: the concept retained, confirmed in writing."""
    pid = F.access(ctx, "editor")
    c = C._concept(ctx.conn, pid, validate.int_param(ctx.params, "cid"))
    text = _text(ctx.body, "text", "Concept retenu")
    ctx.conn.execute("UPDATE diamond_concepts SET frozen = 1, frozen_text = ?, frozen_by = ?, frozen_at = ?, status = 'selected', "
                     "updated_by = ?, updated_at = ? WHERE id = ?", (text, ctx.user["id"], db.utc_now(), ctx.user["id"], db.utc_now(), c["id"]))
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_concept_freeze", "diamond_concept", c["id"],
                     {"code": C.code(c["number"]), "text": text[:200]}, ctx.ip)
    return C.payload(ctx.conn, pid)


def api_unfreeze(ctx):
    """{reason}: the brick opens again (its last frozen text stays in the journal)."""
    pid = F.access(ctx, "editor")
    c = C._concept(ctx.conn, pid, validate.int_param(ctx.params, "cid"))
    if not c.get("frozen"):
        raise ApiError(409, "La brique CB-{} n'est pas figée.".format(c["number"]))
    reason = _text(ctx.body, "reason", "Raison")
    ctx.conn.execute("UPDATE diamond_concepts SET frozen = 0, frozen_by = NULL, frozen_at = NULL, updated_by = ?, updated_at = ? "
                     "WHERE id = ?", (ctx.user["id"], db.utc_now(), c["id"]))
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_concept_unfreeze", "diamond_concept", c["id"],
                     {"code": C.code(c["number"]), "reason": reason, "was": (c.get("frozen_text") or "")[:200]}, ctx.ip)
    return C.payload(ctx.conn, pid)
