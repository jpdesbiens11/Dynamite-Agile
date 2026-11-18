"""Where an audited Agile / Goldmine object lives, for « Changements » (core lot v0.39, 0.60.120, D-O-133): a ticket, a
requirement or a need, an ECN (« DEMO-12 », its tab and its page), a Pugh Matrix, a Q&A, a version or a sprint."""


def _issue(conn, object_id, row):
    if row is None and object_id and "-" in str(object_id):  # « agile_issue_create » keeps the key, not the id
        key, _, number = str(object_id).rpartition("-")
        if number.isdigit():
            found = conn.execute("SELECT i.* FROM agile_issues i JOIN projects p ON p.id = i.project_id WHERE p.key = ? AND i.number = ?",
                                 (key, int(number))).fetchone()
            row = dict(found) if found else None
    if row is None:
        return None
    t = conn.execute("SELECT bucket, name FROM agile_issue_types WHERE id = ?", (row["type_id"],)).fetchone()
    bucket = t["bucket"] if t else ""
    key = conn.execute("SELECT key FROM projects WHERE id = ?", (row["project_id"],)).fetchone()["key"]
    tab = "goldmine" if bucket == "goldmine" else "agile"
    return {"project_id": row["project_id"], "tab": tab, "code": "{}-{}".format(key, row["number"]), "title": row["title"],
            "href": "#/{}/{}/issue/{}".format(tab, key, row["number"])}


def change_link(conn, entry, row, key):
    object_type, object_id = entry["object_type"], entry["object_id"]
    if object_type == "agile_issue":
        return _issue(conn, object_id, row)
    if not key:
        return None
    if object_type == "goldmine_pugh" and row:
        return {"tab": "tools", "code": "Pugh", "href": "#/tools/{}/pugh/{}".format(key, row["id"])}
    if object_type in ("goldmine_qa", "agile_qa") and row:
        return {"tab": "goldmine", "code": "Q&R", "href": "#/goldmine/{}/qa/{}".format(key, row["id"])}
    if object_type in ("agile_version", "agile_versions"):
        return {"tab": "agile", "code": "Version", "href": "#/agile/{}/versions".format(key)}
    if object_type in ("agile_sprint", "agile_sprints"):
        return {"tab": "agile", "code": "Sprint", "href": "#/agile/{}/backlog".format(key)}
    return None
