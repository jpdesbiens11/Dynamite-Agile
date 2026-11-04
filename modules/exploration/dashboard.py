"""Personal dashboard hook (core lot v0.10, D-B-032): the person's open tasks
of the Exploration plans, late ones first."""
from . import plan


def dashboard(conn, user, projects):
    items = []
    for pid, key in projects.items():
        if not conn.execute("SELECT 1 FROM exploration_tasks WHERE project_id = ? AND owner_id = ? AND status != 'done' "
                            "LIMIT 1", (pid, user["id"])).fetchone():
            continue
        try:
            _start, tasks = plan.load(conn, pid)
        except Exception:  # an inconsistent plan must not break the dashboard
            continue
        for t in tasks:
            if t.get("owner_id") == user["id"] and t["status"] != "done":
                items.append({"title": "{} · {}".format(t["code"], t["title"]), "href": "#/exploration/{}/plan".format(key),
                              "project": key, "status": t["status_label"], "due": t["end"], "late": t["late"],
                              "meta": "{} % · fin {}".format(t["progress"], t["end"]),
                              # D-B-038: the owner changes the status right from the dashboard
                              "action": {"method": "PATCH", "url": "/api/exploration/p/{}/tasks/{}".format(pid, t["id"]),
                                         "field": "status", "current": t["status_label"],
                                         "choices": [[k, v] for k, v in plan.STATUSES.items() if k != t["status"]]}})
    items.sort(key=lambda i: (not i["late"], i["due"] or ""))
    late = sum(1 for i in items if i["late"])
    return [{"key": "plan", "title": "Mes tasks du plan (Exploration)", "items": items, "total": len(items),
             "list_href": "#/exploration/{key}/plan", "mine": True,
             "empty": "Aucune task de plan ne vous est confiée.",
             "kpi": {"label": "Tasks du plan", "value": len(items), "tone": "danger" if late else "neutral",
                     "note": "{} en retard".format(late) if late else ""}}]
