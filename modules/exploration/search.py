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
