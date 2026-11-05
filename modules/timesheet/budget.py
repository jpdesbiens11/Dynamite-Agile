"""Timesheet budget structure (D-B-084): Funding Spaces (the set of codes a Space is attached to: the PDP steps, the
internal time, or the Budget Lines of a funding program) and their Budget Lines (the code chosen in a time range,
claimed from the funding organism in the Excel export and the Word report).

Administered in Timesheet → « Spaces et organismes » (administrators only). Codes never change once created
(they go into the Excel exports and the history); labels may be reworded. A line already used by a time range
is never deleted, only deactivated: it stays on its ranges and in the exports, and is no longer offered for new
ranges. « Réclamable » marks the Budget Lines claimed from the funding organisms by default (vacation and health
leave are not).
Tables are attached to the Space TOOLS (catalog.CODES_KEY, D-A-010); until they exist (before the first start-up)
the static catalogue of catalog.TASK_SETS is used.
"""
import re

from core import db, permissions, validate
from core.errors import ApiError

from . import catalog

CODE_RE = re.compile(r"^[A-Z]{1,5}-[A-Z0-9]{2,4}$")  # same pattern as the export filter (?tasks=)
NOT_CLAIMABLE = {"INT-VAC", "INT-SAN"}  # vacation, health leave: never claimed from a funding organism (D-B-036)


def _company_id(conn):
    """The Space that holds the code tables: TOOLS on an installation made before 0.60.41, else DEMO (D-O-050)."""
    from modules.help import reference
    return reference.space(conn, catalog.CODES_KEY)


def seed(conn):
    """Missing sets and lines of the static catalogue (never overwrites what an administrator changed)."""
    pid = _company_id(conn)
    if pid is None:
        return
    now = db.utc_now()
    for pos, (key, (label, items)) in enumerate(catalog.TASK_SETS.items()):
        row = conn.execute("SELECT id FROM timesheet_budget_sets WHERE key = ?", (key,)).fetchone()
        if row is None:
            set_id = conn.execute("INSERT INTO timesheet_budget_sets (project_id, key, label, position, active, created_at, "
                                  "updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)", (pid, key, label, pos, now, now)).lastrowid
        else:
            set_id = row["id"]
        for lpos, (code, name) in enumerate(items):
            old = catalog.OLD_PDP_LABELS.get(code)
            if old and key == catalog.DEFAULT_SET:  # 0.60.09 (D-O-021): the Lean names, only where the label was never reworded
                conn.execute("UPDATE timesheet_budget_lines SET label = ?, updated_at = ? WHERE code = ? AND label = ?",
                             (name, now, code, old))
            if not conn.execute("SELECT 1 FROM timesheet_budget_lines WHERE code = ?", (code,)).fetchone():
                conn.execute("INSERT INTO timesheet_budget_lines (set_id, code, label, claimable, position, active, created_at, "
                             "updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                             (set_id, code, name, 0 if code in NOT_CLAIMABLE else 1, lpos, now, now))


def structure(conn):
    """{set_key: {id, label, active, tasks: [{id, key, label, claimable, active}]}} -- DB, or the static catalogue."""
    try:
        sets = conn.execute("SELECT * FROM timesheet_budget_sets ORDER BY position, id").fetchall()
    except Exception:  # before the migration
        sets = []
    if not sets:
        return {k: {"id": None, "label": label, "active": True,
                    "tasks": [{"id": None, "key": c, "label": n, "claimable": c not in NOT_CLAIMABLE, "active": True}
                              for c, n in items]} for k, (label, items) in catalog.TASK_SETS.items()}
    out = {}
    for s in sets:
        lines = conn.execute("SELECT * FROM timesheet_budget_lines WHERE set_id = ? ORDER BY position, code", (s["id"],))
        out[s["key"]] = {"id": s["id"], "label": s["label"], "active": bool(s["active"]),
                         "tasks": [{"id": r["id"], "key": r["code"], "label": r["label"], "claimable": bool(r["claimable"]),
                                    "active": bool(r["active"])} for r in lines]}
    return out


def labels(conn):
    return {t["key"]: t["label"] for s in structure(conn).values() for t in s["tasks"]}


def leave(conn, struct=None):
    """0.60.41 (D-O-050): the leave codes (INT-VAC, INT-SAN) every Space offers, whatever its set -- vacation and
    health leave are logged in the Space one works in; never claimable."""
    struct = struct or structure(conn)
    return [t for s in struct.values() for t in s["tasks"] if t["key"] in NOT_CLAIMABLE and t["active"]]


def allowed(conn, set_key):
    """Active codes a range of a Space with this set may use (its set, plus the leave codes)."""
    struct = structure(conn)
    s = struct.get(set_key) or struct.get(catalog.DEFAULT_SET) or {"tasks": []}
    codes = [t["key"] for t in s["tasks"] if t["active"]]
    return codes + [t["key"] for t in leave(conn, struct) if t["key"] not in codes]


def meta(conn):
    struct = structure(conn)
    return {"task_sets": {k: {"label": v["label"], "active": v["active"], "tasks": v["tasks"]} for k, v in struct.items()},
            "leave": leave(conn, struct), "statuses": catalog.STATUSES}


# --------------------------------------------------------------------------
# Administration (Timesheet → Spaces et organismes)
# --------------------------------------------------------------------------
def _usage(conn):
    hours = {r["task_key"]: (r["n"], r["h"]) for r in conn.execute(
        "SELECT task_key, COUNT(*) AS n, COALESCE(SUM(hours), 0) AS h FROM timesheet_entries GROUP BY task_key")}
    spaces = {}
    for r in conn.execute("SELECT t.task_set, p.key FROM timesheet_projects t JOIN projects p ON p.id = t.project_id "
                          "WHERE p.is_archived = 0 ORDER BY p.key"):
        spaces.setdefault(r["task_set"], []).append(r["key"])
    return hours, spaces


def api_budget(ctx):
    permissions.require_admin(ctx.user)
    hours, spaces = _usage(ctx.conn)
    sets = structure(ctx.conn)
    for key, s in sets.items():
        s["spaces"] = spaces.get(key, [])
        for t in s["tasks"]:
            t["ranges"], t["hours"] = hours.get(t["key"], (0, 0))
    return {"sets": sets}


def _set_row(conn, set_id):
    row = conn.execute("SELECT * FROM timesheet_budget_sets WHERE id = ?", (set_id,)).fetchone()
    if row is None:
        raise ApiError(404, "Funding Space introuvable.")
    return row


def _label(body, name="label", max_len=120):
    value = validate.text(body, name, max_len)
    if not value.strip():
        raise ApiError(400, "Libellé obligatoire.")
    return value.strip()


def _log(ctx, action, object_id, details):
    from . import weeks
    weeks.log(ctx, action, object_id, details)


def api_create_set(ctx):
    permissions.require_admin(ctx.user)
    pid = _company_id(ctx.conn)
    if pid is None:
        raise ApiError(409, "Le Space TOOLS n'existe pas encore. Correctif : redémarrez le serveur.")
    label = _label(ctx.body)
    if ctx.conn.execute("SELECT 1 FROM timesheet_budget_sets WHERE lower(label) = lower(?)", (label,)).fetchone():
        raise ApiError(409, "Le Funding Space « {} » existe déjà.".format(label))
    n = ctx.conn.execute("SELECT COUNT(*) FROM timesheet_budget_sets").fetchone()[0] + 1
    key = "set{}".format(n)
    while ctx.conn.execute("SELECT 1 FROM timesheet_budget_sets WHERE key = ?", (key,)).fetchone():
        n += 1
        key = "set{}".format(n)
    now = db.utc_now()
    set_id = ctx.conn.execute("INSERT INTO timesheet_budget_sets (project_id, key, label, position, active, created_at, "
                              "updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)", (pid, key, label, n, now, now)).lastrowid
    _log(ctx, "timesheet_budget_set_add", set_id, {"key": key, "label": label})
    return {"id": set_id, "key": key}


def api_update_set(ctx):
    permissions.require_admin(ctx.user)
    row = _set_row(ctx.conn, validate.int_param(ctx.params, "sid"))
    label = _label(ctx.body) if "label" in ctx.body else row["label"]
    active = validate.boolean(ctx.body, "active") if "active" in ctx.body else bool(row["active"])
    if not active and row["active"]:
        used = [r["key"] for r in ctx.conn.execute(
            "SELECT p.key FROM timesheet_projects t JOIN projects p ON p.id = t.project_id "
            "WHERE t.task_set = ? AND p.is_archived = 0", (row["key"],))]
        if used:
            raise ApiError(409, "« {} » est utilisé par {}. Correctif : rattachez d'abord ces Spaces à un autre espace "
                                "financier.".format(row["label"], ", ".join(used)))
    ctx.conn.execute("UPDATE timesheet_budget_sets SET label = ?, active = ?, updated_at = ? WHERE id = ?",
                     (label, int(active), db.utc_now(), row["id"]))
    _log(ctx, "timesheet_budget_set_update", row["id"], {"label": label, "active": active})
    return {"ok": True}


def api_create_line(ctx):
    permissions.require_admin(ctx.user)
    set_row = _set_row(ctx.conn, validate.int_param(ctx.body, "set_id"))
    code = str(ctx.body.get("code") or "").strip().upper()
    if not CODE_RE.match(code):
        raise ApiError(400, "Code « {} » invalide : 1 à 5 lettres, un tiret, 2 à 4 lettres ou chiffres (ex. B-13, "
                            "PARI-03).".format(code[:20]))
    if ctx.conn.execute("SELECT 1 FROM timesheet_budget_lines WHERE code = ?", (code,)).fetchone():
        raise ApiError(409, "Le code {} existe déjà.".format(code))
    label = _label(ctx.body)
    claimable = validate.boolean(ctx.body, "claimable", True)
    now = db.utc_now()
    pos = ctx.conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM timesheet_budget_lines WHERE set_id = ?",
                           (set_row["id"],)).fetchone()[0]
    line_id = ctx.conn.execute("INSERT INTO timesheet_budget_lines (set_id, code, label, claimable, position, active, "
                               "created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                               (set_row["id"], code, label, int(claimable), pos, now, now)).lastrowid
    _log(ctx, "timesheet_budget_line_add", line_id, {"code": code, "set": set_row["key"]})
    return {"id": line_id, "code": code}


def _line_row(conn, line_id):
    row = conn.execute("SELECT * FROM timesheet_budget_lines WHERE id = ?", (line_id,)).fetchone()
    if row is None:
        raise ApiError(404, "Budget Line introuvable.")
    return row


def api_update_line(ctx):
    permissions.require_admin(ctx.user)
    row = _line_row(ctx.conn, validate.int_param(ctx.params, "lid"))
    label = _label(ctx.body) if "label" in ctx.body else row["label"]
    claimable = validate.boolean(ctx.body, "claimable") if "claimable" in ctx.body else bool(row["claimable"])
    active = validate.boolean(ctx.body, "active") if "active" in ctx.body else bool(row["active"])
    ctx.conn.execute("UPDATE timesheet_budget_lines SET label = ?, claimable = ?, active = ?, updated_at = ? WHERE id = ?",
                     (label, int(claimable), int(active), db.utc_now(), row["id"]))
    _log(ctx, "timesheet_budget_line_update", row["id"], {"code": row["code"], "label": label, "claimable": claimable,
                                                          "active": active})
    return {"ok": True}


def api_delete_line(ctx):
    permissions.require_admin(ctx.user)
    row = _line_row(ctx.conn, validate.int_param(ctx.params, "lid"))
    if ctx.conn.execute("SELECT 1 FROM timesheet_entries WHERE task_key = ? LIMIT 1", (row["code"],)).fetchone():
        raise ApiError(409, "Le code {} a déjà des heures saisies : il ne peut pas être supprimé. Correctif : "
                            "désactivez-le (il reste dans les feuilles et les exports).".format(row["code"]))
    ctx.conn.execute("DELETE FROM timesheet_budget_lines WHERE id = ?", (row["id"],))
    _log(ctx, "timesheet_budget_line_delete", row["id"], {"code": row["code"]})
    return {"ok": True}
