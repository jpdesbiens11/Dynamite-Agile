"""Search hook (core lot v0.7, D-B-022; D-B-076): tasks of the plan."""


def search(conn, projects, q):
    if not q.wants("task"):
        return []
    marks = ",".join("?" * len(projects))
    rows = conn.execute(
        "SELECT t.project_id, t.code, t.phase, t.title, t.description, t.note, t.status, t.updated_at, u.display_name "
        "FROM exploration_tasks t LEFT JOIN users u ON u.id = t.owner_id "
        "WHERE t.project_id IN ({}) ORDER BY t.updated_at DESC LIMIT 20000".format(marks), list(projects)).fetchall()
    hits = []
    for r in rows:
        key = projects[r["project_id"]]
        body = (r["phase"], r["description"], r["note"], r["display_name"])
        h = q.hit("task", q.score(r["code"], r["title"], body), key, "{} · {}".format(r["code"], r["title"]),
                  "#/exploration/{}/plan".format(key), " ".join(filter(None, body)), r["updated_at"],
                  closed=r["status"] == "done", extra=r["display_name"] or "")
        if h:
            hits.append(h)
    return hits


def change_link(conn, entry, row, key):
    """« Changements » (core lot v0.39, 0.60.120): a task (its code) or the plan of the Space; both open the plan."""
    if entry["object_type"] != "exploration" or not str(entry["object_id"] or "").isdigit():
        return None
    oid = int(entry["object_id"])
    if "_task_" in entry["action"]:
        task = conn.execute("SELECT project_id, code, title FROM exploration_tasks WHERE id = ?", (oid,)).fetchone()
        pid = task["project_id"] if task else entry["project_id"]
        if pid is None:
            return None
        code, title = (task["code"], task["title"]) if task else (entry["_details"].get("code", ""), entry["_details"].get("title", ""))
    else:
        pid, code, title = oid, "Plan", "Plan d'exploration"
    k = key or (conn.execute("SELECT key FROM projects WHERE id = ?", (pid,)).fetchone() or {"key": ""})["key"]
    href = "#/exploration/{}/plan".format(k)
    return {"project_id": pid, "tab": "exploration", "code": code or "", "title": title or "",
            "href": "/?focus={}{}".format(code, href) if code and code != "Plan" else href}
