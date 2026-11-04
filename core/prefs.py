"""Personal settings and platform policies (core lot v0.10, D-B-027 to D-B-029).

- user_prefs: one JSON document per account -- language, theme, font, text
  size, density, « Mes éléments » filter, landing page, manager (approver of
  the time sheets) and vacation bank. Applied as soon as they change, on
  every device (stored on the server, not in the browser).
- app_settings: platform-wide policies set by administrators; today the
  content-protection controls (watermark, print, copy, blur when the
  window loses the focus) -- deterrence and traceability, since a web page
  cannot prevent an operating-system screenshot.
- privacy events (print / copy / screenshot-key attempts) go to audit_log.
"""
import datetime as dt
import json

from . import permissions, audit, db, validate
from .errors import ApiError

MIGRATIONS = [
    (11, """
        -- D-B-087 (core lot v0.22): « Atlassian » was the default theme; everyone who had it moves to the default theme (key « carnet »)
        -- (the Atlassian base + the hand-drawn layer). Choosing « Atlassian » again in Paramètres keeps it.
        UPDATE user_prefs SET prefs = json_set(prefs, '$.theme', 'carnet') WHERE json_extract(prefs, '$.theme') = 'atlassian';
    """),
    (5, """
        CREATE TABLE user_prefs (
            user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            prefs      TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL
        );
        CREATE TABLE app_settings (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at TEXT NOT NULL
        );
    """),
]

CHOICES = {
    "language": ("fr",),  # D-B-042: French only; other languages through the browser's translation
    "theme": ("carnet", "terminal", "system", "light", "dark", "atlassian", "contrast"),  # D-B-087 default (« Thème par défaut »); D-B-088
    "font": ("system", "atlassian", "readable"),
    "font_size": ("90", "100", "112", "125"),
    "density": ("comfortable", "compact"),
    "landing": ("dashboard", "home", "debuter"),  # 0.60.08: « Débuter »
}
DEFAULTS = {"language": "fr", "theme": "carnet", "font": "system", "font_size": "100", "density": "comfortable",
            "landing": "dashboard", "my_items": False, "manager_id": None, "vacation_bank_hours": None,
            "vacation_bank_date": None, "initials": "", "default_space": "",
            "can_export": False, "hide_sandbox": False,
            "debuter_done": False,  # 0.60.08: « Débuter » closed -- the landing page is the chosen one again
            "baseline_view": ""}  # D-B-129: revision viewed read-only ("" = live)
POLICY_DEFAULTS = {"watermark": False, "block_print": False, "block_copy": False, "blur_unfocused": False}
PRIVACY_EVENTS = {"print": "privacy_print_attempt", "copy": "privacy_copy_attempt",
                  "context": "privacy_context_menu", "printscreen": "privacy_printscreen_key"}


# --------------------------------------------------------------------------
# Personal settings
# --------------------------------------------------------------------------
def get(conn, user_id):
    row = conn.execute("SELECT prefs FROM user_prefs WHERE user_id = ?", (user_id,)).fetchone()
    prefs = dict(DEFAULTS)
    if row:
        try:
            stored = json.loads(row["prefs"])
            prefs.update({k: v for k, v in stored.items() if k in DEFAULTS})
        except ValueError:
            pass
    prefs["language"] = "fr"
    if prefs.get("theme") not in CHOICES["theme"]:  # a theme that no longer exists (restored backup)
        prefs["theme"] = DEFAULTS["theme"]
    return prefs


def _put(conn, user_id, prefs):
    conn.execute("INSERT INTO user_prefs (user_id, prefs, updated_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE "
                 "SET prefs = excluded.prefs, updated_at = excluded.updated_at",
                 (user_id, json.dumps(prefs, ensure_ascii=False), db.utc_now()))


def valid_initials(value):
    """D-B-058: the traceability key is exactly three letters A-Z."""
    return isinstance(value, str) and len(value) == 3 and value.isascii() and value.isalpha() and value.isupper()


def initials_owner(conn, value, user_id):
    """Display name of another active account already using these initials (None when free)."""
    for row in conn.execute("SELECT p.user_id, p.prefs, u.display_name FROM user_prefs p JOIN users u ON u.id = p.user_id "
                            "WHERE u.is_active = 1 AND p.user_id != ?", (user_id,)):
        try:
            if str(json.loads(row["prefs"]).get("initials") or "").upper() == value:
                return row["display_name"]
        except ValueError:
            continue
    return None


def has_initials(conn, user_id):
    return valid_initials(get(conn, user_id).get("initials") or "")


def clean(conn, user_id, body):
    """Validated subset of `body`: every refusal names the value and the fix (D-A-031)."""
    out = {}
    for key, options in CHOICES.items():
        if key in body:
            value = str(body[key])
            if value not in options:
                raise ApiError(400, "Valeur « {} » refusée pour {}. Correctif : {}.".format(value, key, ", ".join(options)))
            out[key] = value
    if "my_items" in body:
        out["my_items"] = validate.boolean(body, "my_items")
    if "debuter_done" in body:  # 0.60.08
        out["debuter_done"] = validate.boolean(body, "debuter_done")
    if "hide_sandbox" in body:  # D-B-052: hide the HeadLamp sandbox space (its wiki stays visible)
        out["hide_sandbox"] = validate.boolean(body, "hide_sandbox")
    if "manager_id" in body:
        value = body.get("manager_id")
        if value in (None, "", 0):
            out["manager_id"] = None
        else:
            try:
                value = int(value)
            except (TypeError, ValueError):
                value = -1
            if value == user_id:
                raise ApiError(400, "Vous ne pouvez pas être votre propre gestionnaire. Correctif : choisissez une autre personne.")
            if not conn.execute("SELECT 1 FROM users WHERE id = ? AND is_active = 1", (value,)).fetchone():
                raise ApiError(400, "Gestionnaire introuvable ou inactif. Correctif : choisissez une personne de la liste.")
            out["manager_id"] = value
    if "default_space" in body:  # D-B-098: the Space every tab opens on ("" = the list of Spaces)
        value = str(body.get("default_space") or "").strip().upper()
        if value:
            row = conn.execute("SELECT id FROM projects WHERE key = ?", (value,)).fetchone()
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if row is None or permissions.project_role(conn, user, row["id"]) is None:
                raise ApiError(400, "Space « {} » introuvable ou non accessible. Correctif : cochez un Space de la liste "
                                    "de gauche.".format(value[:20]))
        out["default_space"] = value
    if "initials" in body:  # traceability key: stamps like 06092026-JDE (D-B-037), required to write (D-B-058)
        value = str(body.get("initials") or "").strip().upper()
        if value and not valid_initials(value):
            raise ApiError(400, "Initiales « {} » refusées. Correctif : exactement 3 lettres sans accent, ex. JDE.".format(value))
        if value and initials_owner(conn, value, user_id):
            raise ApiError(409, "Les initiales « {} » sont déjà prises par {}. Correctif : choisissez une autre combinaison "
                                "de 3 lettres (ex. deuxième prénom).".format(value, initials_owner(conn, value, user_id)))
        out["initials"] = value
    if "vacation_bank_hours" in body:
        value = body.get("vacation_bank_hours")
        if value in (None, ""):
            out["vacation_bank_hours"] = None
        else:
            try:
                value = round(float(value), 2)
            except (TypeError, ValueError):
                raise ApiError(400, "Banque de vacances « {} » invalide. Correctif : un nombre d'heures, ex. 112,5.".format(value))
            if not 0 <= value <= 2000:
                raise ApiError(400, "Banque de vacances de {} h refusée. Correctif : de 0 à 2000 heures.".format(value))
            out["vacation_bank_hours"] = value
    if "vacation_bank_date" in body:
        value = str(body.get("vacation_bank_date") or "")[:10]
        if value:
            try:
                dt.date.fromisoformat(value)
            except ValueError:
                raise ApiError(400, "Date « {} » invalide. Correctif : format AAAA-MM-JJ.".format(value))
        out["vacation_bank_date"] = value or None
    if "vacation_bank_hours" in out and out["vacation_bank_hours"] is not None and not (
            out.get("vacation_bank_date") or get(conn, user_id).get("vacation_bank_date")):
        out["vacation_bank_date"] = dt.date.today().isoformat()  # balance « as of today »
    return out


def update(ctx, user_id, body):
    changes = clean(ctx.conn, user_id, body)
    prefs = get(ctx.conn, user_id)
    before = dict(prefs)
    prefs.update(changes)
    _put(ctx.conn, user_id, prefs)
    tracked = {k: [before.get(k), v] for k, v in changes.items()
               if k in ("manager_id", "vacation_bank_hours", "vacation_bank_date") and before.get(k) != v}
    if tracked:  # the approver sees these changes: keep who and when
        audit.log_action(ctx.conn, ctx.user["id"], "prefs_hr_changed", "user", user_id, tracked, ctx.ip)
    return prefs


def api_get(ctx):
    users = db.rows(ctx.conn.execute(
        "SELECT id, display_name FROM users WHERE is_active = 1 AND id != ? ORDER BY display_name", (ctx.user["id"],)).fetchall())
    return {"prefs": get(ctx.conn, ctx.user["id"]), "choices": CHOICES, "people": users}


def api_put(ctx):
    return {"prefs": update(ctx, ctx.user["id"], ctx.body)}


def api_admin_get(ctx):
    user_id = validate.int_param(ctx.params, "uid")
    return {"prefs": get(ctx.conn, user_id)}


def api_admin_put(ctx):
    """An administrator corrects a person's approver (manager) or vacation bank, or gives the
    export right (Word / PDF of wiki pages, D-B-050) -- a right the person cannot give himself."""
    user_id = validate.int_param(ctx.params, "uid")
    allowed = {k: v for k, v in ctx.body.items() if k in ("manager_id", "vacation_bank_hours", "vacation_bank_date")}
    result = update(ctx, user_id, allowed) if allowed else get(ctx.conn, user_id)
    if "can_export" in ctx.body:
        value = validate.boolean(ctx.body, "can_export")
        result = get(ctx.conn, user_id)
        result["can_export"] = value
        _put(ctx.conn, user_id, result)
        audit.log_action(ctx.conn, ctx.user["id"], "export_right_" + ("given" if value else "removed"), "user", user_id, None, ctx.ip)
    return {"prefs": result}


# --------------------------------------------------------------------------
# Platform policies (content protection)
# --------------------------------------------------------------------------
def policy(conn):
    row = conn.execute("SELECT value FROM app_settings WHERE key = 'privacy'").fetchone()
    value = dict(POLICY_DEFAULTS)
    if row:
        try:
            value.update({k: bool(v) for k, v in json.loads(row["value"]).items() if k in POLICY_DEFAULTS})
        except ValueError:
            pass
    return value


def api_policy_get(ctx):
    return {"privacy": policy(ctx.conn)}


def api_policy_put(ctx):
    current = policy(ctx.conn)
    for key in POLICY_DEFAULTS:
        if key in ctx.body:
            current[key] = validate.boolean(ctx.body, key)
    ctx.conn.execute("INSERT INTO app_settings (key, value, updated_by, updated_at) VALUES ('privacy', ?, ?, ?) "
                     "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_by = excluded.updated_by, "
                     "updated_at = excluded.updated_at", (json.dumps(current), ctx.user["id"], db.utc_now()))
    audit.log_action(ctx.conn, ctx.user["id"], "privacy_policy_changed", "settings", None, current, ctx.ip)
    return {"privacy": current}


def api_privacy_event(ctx):
    kind = ctx.body.get("kind")
    if kind not in PRIVACY_EVENTS:
        raise ApiError(400, "Événement inconnu.")
    where = validate.text(ctx.body, "page", 300, required=False)
    audit.log_action(ctx.conn, ctx.user["id"], PRIVACY_EVENTS[kind], "privacy", None, {"page": where}, ctx.ip)
    return {"ok": True}


ROUTES = [
    ("GET", r"/api/me/prefs", api_get, "user"),
    ("PUT", r"/api/me/prefs", api_put, "user"),
    ("GET", r"/api/admin/users/(?P<uid>\d+)/prefs", api_admin_get, "admin"),
    ("PUT", r"/api/admin/users/(?P<uid>\d+)/prefs", api_admin_put, "admin"),
    ("GET", r"/api/admin/policy", api_policy_get, "admin"),
    ("PUT", r"/api/admin/policy", api_policy_put, "admin"),
    ("POST", r"/api/privacy/event", api_privacy_event, "user"),
]
