"""Core lot v0.37 (0.60.103, D-O-111): « Modules et fonctions » -- an administrator turns optional parts of the platform on
or off, for every Space, in ⚙ Admin → Plateforme. A platform used by bachelor's students may not need timesheets or
annual reviews; a product without an assembly line does not need the process side of Diamond.

What can be turned off:
  module   a whole tab of MODULE_MANIFEST listed in OPTIONAL_MODULES (Timesheet);
  core     a function of the core (« reviews »: objectives, annual review, professional profile, « Mon équipe »);
  module feature  a part of a module, declared by the module in its FEATURES (Diamond: Procédés, PFMEA, Plans de
           contrôle), with the key of the feature it needs (a PFMEA needs the assembly lines).
A part turned off disappears from the menus (session payload « features », nav_manifest filtered) and its routes answer
404 with the way back (router guard) -- its data is kept, never deleted: turned on again, everything is there. Every
part is on by default (an installation before 0.60.103 keeps what it had). Setting app_settings « features » (JSON
{key: bool}); every change is journalled.
"""
import json
import re

from . import audit, db
from .errors import ApiError

OPTIONAL_MODULES = {"timesheet": "Feuilles de temps par étape du PDP, congés, Funding Spaces et réclamations de financement."}
CORE = {
    "reviews": {"label": "Évaluation, objectifs et profil", "group": "Fonctions du compte",
                "help": "Mes objectifs, évaluation annuelle et de stage, profil professionnel et « Mon équipe » du gestionnaire.",
                "routes": [r"/api/objectives(/.*)?", r"/api/reviews(/.*)?", r"/api/profile(/.*)?", r"/api/team"]},
}
SETTING = "features"


def registry():
    """{key: {label, group, help, routes, parent, requires}} -- the modules, the core functions, the module features."""
    from . import modules
    out = {}
    for entry in modules.MODULE_MANIFEST:
        if entry["key"] in OPTIONAL_MODULES and entry["module"] is not None:
            out[entry["key"]] = {"label": entry["label"], "group": "Modules", "help": OPTIONAL_MODULES[entry["key"]], "module": entry["key"],
                                 "routes": [r"/api/{}(/.*)?".format(entry["key"])]}
    out.update(CORE)
    for entry in modules.MODULE_MANIFEST:
        for key, f in (getattr(entry["module"], "FEATURES", None) or {}).items():
            out[key] = dict(f, group=entry["label"], parent=entry["key"])
    return out


def state(conn):
    """{key: on?} for every part of the registry (on unless an administrator turned it off)."""
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (SETTING,)).fetchone()
    saved = {}
    if row:
        try:
            saved = {k: bool(v) for k, v in json.loads(row["value"]).items()}
        except (ValueError, AttributeError):
            saved = {}
    reg = registry()
    out = {k: saved.get(k, True) for k in reg}
    for k, f in reg.items():  # a part that needs another one is off when that one is
        if f.get("requires") and not out.get(f["requires"], True):
            out[k] = False
    return out


def on(conn, key):
    return state(conn).get(key, True)


_compiled = {}


def guard(conn, path):
    """The router calls this before every API route: a part turned off answers 404 (its data is kept)."""
    if not path.startswith("/api/") or path.startswith("/api/admin/"):
        return
    off = [k for k, v in state(conn).items() if not v]
    if not off:
        return
    reg = registry()
    for key in off:
        for pattern in reg[key].get("routes", []):
            rx = _compiled.setdefault(pattern, re.compile(pattern))
            if rx.fullmatch(path):
                raise ApiError(404, "« {} » est désactivé sur cette plateforme. Correctif : un administrateur le réactive dans "
                                    "⚙ Admin → Plateforme → Modules et fonctions (les données sont gardées).".format(reg[key]["label"]))


def visible_modules(conn, manifest):
    """nav_manifest() without the modules turned off."""
    st = state(conn)
    return [m for m in manifest if st.get(m["key"], True)]


def api_get(ctx):
    reg, st = registry(), state(ctx.conn)
    return {"features": [dict({k: v for k, v in f.items() if k != "routes"}, key=k, on=st[k]) for k, f in reg.items()]}


def api_put(ctx):
    """{features: {key: bool}}: what is on and off; an unknown key is refused with the list of the known ones."""
    reg = registry()
    body = ctx.body.get("features")
    if not isinstance(body, dict):
        raise ApiError(400, "« features » attendu : {clé: true | false}.")
    unknown = [k for k in body if k not in reg]
    if unknown:
        raise ApiError(400, "Fonction inconnue : {}. Correctif : {}.".format(", ".join(unknown), ", ".join(reg)))
    row = ctx.conn.execute("SELECT value FROM app_settings WHERE key = ?", (SETTING,)).fetchone()
    try:
        saved = json.loads(row["value"]) if row else {}
    except ValueError:
        saved = {}
    before = {k: saved.get(k, True) for k in reg}
    saved.update({k: bool(v) for k, v in body.items()})
    ctx.conn.execute("INSERT INTO app_settings (key, value, updated_by, updated_at) VALUES (?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET "
                     "value = excluded.value, updated_by = excluded.updated_by, updated_at = excluded.updated_at",
                     (SETTING, json.dumps(saved, sort_keys=True), ctx.user["id"], db.utc_now()))
    changed = {k: bool(v) for k, v in body.items() if before.get(k) != bool(v)}
    if changed:
        audit.log_action(ctx.conn, ctx.user["id"], "features_changed", "app_settings", None, changed, ctx.ip)
    return api_get(ctx)


ROUTES = [
    ("GET", r"/api/admin/features", api_get, "admin"),
    ("PUT", r"/api/admin/features", api_put, "admin"),
]
