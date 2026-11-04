"""Personal dashboard hook (core lot v0.10, D-B-032): the person's open
tickets, changes (PR, bugs, ECN) and requirements, plus the ECN waiting for a
CCB decision when he is an administrator.
0.20.0 (D-B-038): every item carries its possible status changes (the same
transitions as the ticket page) so it can be moved from the dashboard, and
every section names the list to open with « Mes éléments » on."""
import datetime as dt

from core import permissions

BUCKETS = [
    ("agile", "tickets", "Mes tickets Agile ouverts", "Aucun ticket ouvert ne vous est assigné.", "Tickets"),
    ("change", "changes", "Mes changements (PR, bugs, ECN)", "Aucun changement ne vous est assigné.", "Changements"),
    ("goldmine", "requirements", "Mes requirements Goldmine à traiter", "Aucune requirement ne vous est assignée.", "Requirements"),
]
LIST_HREF = {"tickets": "#/agile/{key}/issues", "changes": "#/agile/{key}/changes", "requirements": "#/goldmine/{key}/goldmine",
             "ccb": "#/agile/{key}/changes", "qa": "#/goldmine/{key}/qa"}


def _rows(conn, projects, where, params):
    marks = ",".join("?" * len(projects))
    return conn.execute(
        "SELECT i.id, i.type_id, i.status_id, i.project_id, i.number, i.title, i.priority, i.due_date, i.updated_at, s.name AS status, s.category, "
        "CASE WHEN t.is_requirement = 1 THEN 'goldmine' ELSE t.bucket END AS bucket, t.name AS type_name, t.change_role FROM agile_issues i JOIN agile_statuses s ON s.id = i.status_id "
        "JOIN agile_issue_types t ON t.id = i.type_id WHERE i.project_id IN ({}) AND {} "
        "ORDER BY CASE i.priority WHEN 'blocker' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, "
        "i.due_date IS NULL, i.due_date, i.updated_at DESC".format(marks, where), list(projects) + params).fetchall()


def _action(conn, user, r, roles):
    """Status changes allowed from the dashboard: the ticket's workflow transitions."""
    from .issues import _available_transitions
    role = roles.setdefault(r["project_id"], permissions.project_role(conn, user, r["project_id"]))
    if role not in ("editor", "admin"):
        return None
    choices = [[t["id"], t["to_name"]] for t in _available_transitions(conn, r, role)]
    if not choices:
        return None
    return {"method": "POST", "url": "/api/agile/p/{}/issues/{}/transition".format(r["project_id"], r["number"]),
            "field": "transition_id", "current": r["status"], "choices": choices}


def _item(r, projects, today, conn=None, user=None, roles=None):
    key = projects[r["project_id"]]
    tab = "goldmine" if r["bucket"] == "goldmine" else "agile"
    item = {"title": "{}-{} · {}".format(key, r["number"], r["title"]), "href": "#/{}/{}/issue/{}".format(tab, key, r["number"]),
            "project": key, "status": r["status"], "due": r["due_date"], "meta": r["type_name"],
            "late": bool(r["due_date"] and r["due_date"] < today)}
    if conn is not None:
        item["action"] = _action(conn, user, r, roles)
    return item


def dashboard(conn, user, projects):
    if not projects:
        return []
    today = dt.date.today().isoformat()
    rows = _rows(conn, projects, "i.assignee_id = ? AND s.category != 'done'", [user["id"]])
    sections = []
    roles = {}
    for bucket, key, title, empty, label in BUCKETS:
        items = [_item(r, projects, today, conn, user, roles) for r in rows if (r["bucket"] or "agile") == bucket]
        late = sum(1 for i in items if i["late"])
        sections.append({"key": key, "title": title, "items": items, "total": len(items), "empty": empty,
                         "list_href": LIST_HREF[key], "mine": True,
                         "kpi": {"label": label, "value": len(items), "tone": "danger" if late else "neutral",
                                 "note": "{} en retard".format(late) if late else ""}})
    from . import qa  # D-B-037: client questions waiting for me
    waiting = qa.dashboard_items(conn, user, projects)
    if waiting:
        sections.append({"key": "qa", "title": "Questions client à traiter (Goldmine)", "items": waiting, "total": len(waiting),
                         "list_href": LIST_HREF["qa"], "mine": True,
                         "empty": "", "kpi": {"label": "Questions client", "value": len(waiting),
                                              "tone": "warn" if any(i["late"] for i in waiting) else "neutral"}})
    if user["is_admin"]:
        ccb = _rows(conn, projects, "t.change_role = 'ecn' AND s.name = 'CCB Review'", [])
        if ccb:
            items = [_item(r, projects, today, conn, user, roles) for r in ccb]
            sections.append({"key": "ccb", "title": "ECN en attente de décision CCB", "items": items, "total": len(items),
                             "list_href": LIST_HREF["ccb"], "mine": False,
                             "empty": "", "kpi": {"label": "Décisions CCB", "value": len(items), "tone": "warn"}})
    return sections
