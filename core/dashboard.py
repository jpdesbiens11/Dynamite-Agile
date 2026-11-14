"""Personal dashboard (core lot v0.10, D-B-032): everything that waits for the
signed-in person, across all the projects he can see.

Each module answers through a `dashboard(conn, user, projects)` hook
(core/modules.py) with sections:
    {"key", "module", "title", "items": [{"title", "href", "project", "status",
      "due", "late", "meta"}], "total", "empty", "kpi": {"label", "value", "tone"}}
The core adds the interface observations (Audit) assigned to the person.
Only text is returned; the browser builds the page with textContent.
"""
from . import audit, db, features, modules, permissions, prefs
from .errors import ApiError

MAX_ITEMS = 12


def _audit_section(conn, user):
    rows = conn.execute(
        "SELECT id, description, status, target_release, priority FROM ui_audits "
        "WHERE assignee_id = ? AND status IN ('new', 'planned', 'doing') ORDER BY priority = 'high' DESC, id DESC",
        (user["id"],)).fetchall()
    items = [{"title": "#{} · {}".format(r["id"], r["description"].split("\n")[0][:120]), "href": "#/audit/{}".format(r["id"]),
              "project": "Audit", "status": {"new": "Nouveau", "planned": "Planifié", "doing": "In Progress"}[r["status"]],
              "meta": ("Revision " + r["target_release"]) if r["target_release"] else "", "late": False, "due": None}
             for r in rows]
    return {"key": "audit", "module": "audit", "title": "Observations Audit qui me sont confiées", "items": items[:MAX_ITEMS],
            "total": len(items), "empty": "Aucune observation Audit ne vous est confiée.", "href": "#/audit",
            "kpi": {"label": "Observations Audit", "value": len(items), "tone": "neutral"}}


def api_dashboard(ctx):
    """?user=<id> (administrators, D-B-046): the dashboard of another person, read-only --
    to see a workload from time to time and give feedback. Journalled."""
    target = ctx.user
    viewing = None
    wanted = ctx.query.get("user")
    if wanted and str(wanted) != str(ctx.user["id"]):
        if not ctx.user["is_admin"]:
            raise ApiError(403, "Réservé aux administrateurs.")
        target = ctx.conn.execute("SELECT * FROM users WHERE id = ? AND is_active = 1", (int(wanted),)).fetchone()
        if target is None:
            raise ApiError(404, "Employé introuvable ou inactif.")
        viewing = {"id": target["id"], "display_name": target["display_name"]}
        audit.log_action(ctx.conn, ctx.user["id"], "dashboard_viewed_as", "user", target["id"], None, ctx.ip)
    visible = permissions.visible_projects(ctx.conn, target)
    if prefs.get(ctx.conn, target["id"]).get("hide_sandbox"):  # D-B-052: sandbox hidden by the person
        visible = [p for p in visible if p["key"] != "DEMO"]
    visible = [p for p in visible if p["key"] != "TOOLS"]  # D-B-068: the Tools wiki is not a work space
    # 0.60.42 (D-O-051): the default Space is the whole environment -- the dashboard shows it alone, unless ?all=1
    default = prefs.get(ctx.conn, target["id"]).get("default_space") or ""
    scope = {"space": "", "all": str(ctx.query.get("all", "")) in ("1", "true")}
    if default and not scope["all"] and any(p["key"] == default for p in visible):
        visible = [p for p in visible if p["key"] == default]
        scope["space"] = default
    projects = {p["id"]: p["key"] for p in visible}
    sections = []
    on = features.state(ctx.conn)  # 0.60.103 (D-O-111): a module turned off says nothing
    for key, hook in modules.dashboard_hooks():
        if not on.get(key, True):
            continue
        for section in hook(ctx.conn, target, projects) or []:
            section.setdefault("module", key)
            section["items"] = section.get("items", [])[:MAX_ITEMS]
            sections.append(section)
    sections.append(_audit_section(ctx.conn, target))
    if viewing:  # audit mode: nothing can be changed from here
        for section in sections:
            section["mine"] = False
            for item in section["items"]:
                item.pop("action", None)
    kpis = [dict(s["kpi"], href=s.get("href"), key=s["key"]) for s in sections if s.get("kpi")]
    people = None
    if ctx.user["is_admin"]:
        people = db.rows(ctx.conn.execute("SELECT id, display_name FROM users WHERE is_active = 1 ORDER BY display_name").fetchall())
    return {"user": target["display_name"], "projects": visible, "sections": sections, "kpis": kpis,
            "viewing": viewing, "people": people, "me": ctx.user["id"], "scope": scope, "default_space": default}


ROUTES = [
    ("GET", r"/api/dashboard", api_dashboard, "user"),
]
