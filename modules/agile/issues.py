"""Tickets: list, create, read, update, transition, labels, comments, links."""
from core import db, permissions, validate
from core.errors import ApiError

from . import common as c

ISSUE_SELECT = (
    "SELECT i.id, i.number, i.title, i.priority, i.story_points, i.due_date, i.rank, "
    "i.type_id, i.status_id, i.parent_id, i.sprint_id, i.version_id, i.assignee_id, "
    "i.reporter_id, i.created_at, i.updated_at, i.resolved_at, "
    "s.name AS status_name, s.category AS status_category, "
    "t.name AS type_name, t.icon_key, t.is_subtask, t.bucket, t.change_role, "
    "ua.display_name AS assignee_name, "
    "(SELECT GROUP_CONCAT(l.name, ',') FROM agile_issue_labels il "
    " JOIN agile_labels l ON l.id = il.label_id WHERE il.issue_id = i.id) AS labels "
    "FROM agile_issues i "
    "JOIN agile_statuses s ON s.id = i.status_id "
    "JOIN agile_issue_types t ON t.id = i.type_id "
    "LEFT JOIN users ua ON ua.id = i.assignee_id ")


def _shape(row, key):
    item = dict(row)
    item["key"] = "{}-{}".format(key, item["number"])
    item["labels"] = sorted(item["labels"].split(","), key=str.lower) if item["labels"] else []
    return item


def list_issues(conn, project_id, where="", params=(), order="i.rank, i.number", limit=500):
    key = c.project_key(conn, project_id)
    sql = ISSUE_SELECT + "WHERE i.project_id = ? " + where + " ORDER BY " + order + " LIMIT ?"
    result = conn.execute(sql, (project_id,) + tuple(params) + (limit,)).fetchall()
    return [_shape(r, key) for r in result]


def api_list(ctx):
    project_id, _ = c.access(ctx)
    q = ctx.query
    where, params = [], []
    # D-B-010/011: Agile lists show Agile work only; requirements (Goldmine tab)
    # and PR / bugs / ECN (Change Management) have their own screens.
    if q.get("bucket") in ("agile", "goldmine", "change"):
        where.append("t.bucket = ?")
        params.append(q["bucket"])
    elif q.get("bucket") != "all":
        where.append("t.bucket = 'agile'")
    for name, column in (("type", "i.type_id"), ("status", "i.status_id"),
                         ("version", "i.version_id")):
        if q.get(name):
            where.append(column + " = ?")
            params.append(c.opt_int(q, name))
    if q.get("assignee") == "none":
        where.append("i.assignee_id IS NULL")
    elif q.get("assignee"):
        where.append("i.assignee_id = ?")
        params.append(c.opt_int(q, "assignee"))
    if q.get("sprint") == "backlog":
        where.append("i.sprint_id IS NULL")
    elif q.get("sprint"):
        where.append("i.sprint_id = ?")
        params.append(c.opt_int(q, "sprint"))
    if q.get("category") == "open":
        where.append("s.category != 'done'")
    elif q.get("category") in c.CATEGORIES:
        where.append("s.category = ?")
        params.append(q["category"])
    if q.get("label"):
        where.append("EXISTS (SELECT 1 FROM agile_issue_labels il JOIN agile_labels l "
                     "ON l.id = il.label_id WHERE il.issue_id = i.id AND l.name = ?)")
        params.append(q["label"][:40])
    if q.get("q"):
        terms = [t.replace('"', "") for t in q["q"][:200].split() if t.replace('"', "")]
        if terms:
            match = " ".join('"{}"*'.format(t) for t in terms)
            where.append("i.id IN (SELECT rowid FROM agile_issues_fts WHERE agile_issues_fts MATCH ?)")
            params.append(match)
    clause = "".join("AND " + w + " " for w in where)
    order = {"updated": "i.updated_at DESC", "priority":
             "CASE i.priority WHEN 'blocker' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 "
             "WHEN 'low' THEN 3 ELSE 4 END, i.number"}.get(q.get("sort"), "i.number DESC")
    return {"issues": list_issues(ctx.conn, project_id, clause, params, order)}


def _check_type(conn, project_id, type_id):
    if type_id is None:
        raise ApiError(400, "Champ requis : type.")
    return c.owned(conn, "agile_issue_types", type_id, project_id, "Type")


def _check_parent(conn, project_id, parent_number, own_id=None):
    if parent_number is None:
        return None
    parent = c.get_issue(conn, project_id, parent_number)
    if own_id is not None and parent["id"] == own_id:
        raise ApiError(400, "Un ticket ne peut pas être son propre parent.")
    return parent["id"]


def _optional_ref(conn, table, value, project_id, label):
    if value is None:
        return None
    c.owned(conn, table, value, project_id, label)
    return value


def _initial_assignee(ctx, conn, project_id, role):
    """An editor's new ticket is assigned to its author unless another member
    is named (D-B-017), so its author keeps the right to complete it."""
    wanted = c.check_member(conn, project_id, c.opt_int(ctx.body, "assignee_id"))
    if wanted is None and role != "admin" and "assignee_id" not in ctx.body:
        return ctx.user["id"]
    return wanted


def api_create(ctx):
    project_id, role = c.access(ctx, "editor")
    conn, body = ctx.conn, ctx.body
    itype = _check_type(conn, project_id, c.opt_int(body, "type_id"))
    title = validate.text(body, "title", 255)
    description = validate.text(body, "description", 20000, required=False)
    priority = body.get("priority") or "medium"
    if priority not in c.PRIORITIES:
        raise ApiError(400, "Priority invalide.")
    initial = conn.execute("SELECT id, category FROM agile_statuses WHERE workflow_id = ? "
                           "ORDER BY is_initial DESC, position LIMIT 1",
                           (itype["workflow_id"],)).fetchone()
    if initial is None:
        raise ApiError(409, "Le workflow de ce type n'a aucun status.")
    values = {
        "parent_id": _check_parent(conn, project_id, c.opt_int(body, "parent_number")),
        "assignee_id": _initial_assignee(ctx, conn, project_id, role),
        "sprint_id": _optional_ref(conn, "agile_sprints", c.opt_int(body, "sprint_id"), project_id, "Sprint"),
        "version_id": _optional_ref(conn, "agile_versions", c.opt_int(body, "version_id"), project_id, "Version"),
        "story_points": c.opt_points(body),
        "due_date": c.opt_date(body, "due_date"),
    }
    number = conn.execute("UPDATE projects SET next_ticket_number = next_ticket_number + 1 "
                          "WHERE id = ? RETURNING next_ticket_number - 1 AS n",
                          (project_id,)).fetchone()["n"]
    rank = conn.execute("SELECT COALESCE(MAX(rank), 0) + 1 FROM agile_issues WHERE project_id = ?",
                        (project_id,)).fetchone()[0]
    now = db.utc_now()
    issue_id = conn.execute(
        "INSERT INTO agile_issues (project_id, number, type_id, status_id, parent_id, title, "
        "description, priority, assignee_id, reporter_id, story_points, due_date, sprint_id, "
        "version_id, rank, created_at, updated_at, resolved_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (project_id, number, itype["id"], initial["id"], values["parent_id"], title, description,
         priority, values["assignee_id"], ctx.user["id"], values["story_points"],
         values["due_date"], values["sprint_id"], values["version_id"], rank, now, now,
         now if initial["category"] == "done" else None)).lastrowid
    if isinstance(body.get("labels"), list):
        _set_labels(ctx, project_id, issue_id, body["labels"], record=False)
    c.add_history(ctx, issue_id, "created", None, title)
    key = "{}-{}".format(c.project_key(conn, project_id), number)
    c.log(ctx, "agile_issue_create", "agile_issue", key, {"title": title})
    return {"key": key, "number": number}


def api_get(ctx):
    project_id, role = c.access(ctx)
    conn = ctx.conn
    row = c.get_issue(conn, project_id, c.issue_number(ctx))
    key = c.project_key(conn, project_id)
    issue = list_issues(conn, project_id, "AND i.id = ? ", (row["id"],))[0]
    issue["description"] = row["description"]
    from . import changes, summary  # local imports keep this module's imports flat
    issue.update(summary.fields_of(conn, row["id"]))
    changes.enrich(conn, project_id, row, issue)
    reporter = conn.execute("SELECT display_name FROM users WHERE id = ?", (row["reporter_id"],)).fetchone()
    issue["reporter_name"] = reporter["display_name"] if reporter else None
    if row["parent_id"]:
        parent = conn.execute("SELECT number, title FROM agile_issues WHERE id = ?",
                              (row["parent_id"],)).fetchone()
        issue["parent"] = {"key": "{}-{}".format(key, parent["number"]),
                           "number": parent["number"], "title": parent["title"]}
    issue["children"] = list_issues(conn, project_id, "AND i.parent_id = ? ", (row["id"],),
                                    "i.number")
    issue["links"] = db.rows(conn.execute(
        "SELECT l.id, l.link_type, 'out' AS direction, o.number, o.title, s.name AS status_name, "
        "s.category AS status_category, p.key AS project_key "
        "FROM agile_links l JOIN agile_issues o ON o.id = l.target_id "
        "JOIN agile_statuses s ON s.id = o.status_id JOIN projects p ON p.id = o.project_id "
        "WHERE l.source_id = ? "
        "UNION ALL SELECT l.id, l.link_type, 'in', o.number, o.title, s.name, s.category, p.key "
        "FROM agile_links l JOIN agile_issues o ON o.id = l.source_id "
        "JOIN agile_statuses s ON s.id = o.status_id JOIN projects p ON p.id = o.project_id "
        "WHERE l.target_id = ?",
        (row["id"], row["id"])).fetchall())
    for link in issue["links"]:
        link["key"] = "{}-{}".format(link["project_key"], link["number"])
    issue["comments"] = db.rows(conn.execute(
        "SELECT cm.id, cm.parent_comment_id, cm.body, cm.created_at, cm.edited_at, cm.author_id, "
        "cm.external_author, cm.is_question, cm.requirement_ref, "
        "COALESCE(u.display_name, cm.external_author) AS author_name "
        "FROM agile_comments cm LEFT JOIN users u ON u.id = cm.author_id "
        "WHERE cm.issue_id = ? ORDER BY cm.id", (row["id"],)).fetchall())
    issue["history"] = db.rows(conn.execute(
        "SELECT h.ts, h.field, h.old_value, h.new_value, u.display_name AS user_name "
        "FROM agile_history h LEFT JOIN users u ON u.id = h.user_id "
        "WHERE h.issue_id = ? ORDER BY h.id DESC LIMIT 200", (row["id"],)).fetchall())
    type_row = conn.execute("SELECT is_requirement FROM agile_issue_types WHERE id = ?",
                            (row["type_id"],)).fetchone()
    issue["is_requirement"] = bool(type_row["is_requirement"])
    if issue["is_requirement"]:
        issue["implemented_by"] = db.rows(conn.execute(
            "SELECT si.number, si.title, p.key AS project_key, s.name AS status_name, "
            "s.category AS status_category FROM agile_links l "
            "JOIN agile_issues si ON si.id = l.source_id JOIN projects p ON p.id = si.project_id "
            "JOIN agile_statuses s ON s.id = si.status_id "
            "WHERE l.target_id = ? AND l.link_type = 'implements' ORDER BY p.key, si.number",
            (row["id"],)).fetchall())
        for imp in issue["implemented_by"]:
            imp["key"] = "{}-{}".format(imp["project_key"], imp["number"])
        from . import goldmine  # local import: goldmine imports this module
        issue["requirement"] = goldmine.fields_of(conn, row["id"])
        review = conn.execute("SELECT standard_review, standard_checked FROM agile_requirements WHERE issue_id = ?",
                              (row["id"],)).fetchone()  # 0.60.07: « À vérifier » (D-O-019)
        issue["requirement"].update(standard_review=review["standard_review"] if review else "",
                                    standard_checked=review["standard_checked"] if review else "")
    issue["can_edit"] = c.can_edit(ctx, role, row)
    issue["can_take"] = c.can_take(ctx, role, row)
    issue["transitions"] = _available_transitions(conn, row, role) if issue["can_edit"] else []
    return {"issue": issue, "role": role}


def _available_transitions(conn, row, role):
    wf = conn.execute("SELECT workflow_id FROM agile_issue_types WHERE id = ?",
                      (row["type_id"],)).fetchone()["workflow_id"]
    result = db.rows(conn.execute(
        "SELECT t.id, t.name, t.to_status_id, t.min_role, s.name AS to_name, s.category AS to_category "
        "FROM agile_transitions t JOIN agile_statuses s ON s.id = t.to_status_id "
        "WHERE t.workflow_id = ? AND (t.from_status_id = ? OR t.from_status_id IS NULL) "
        "AND t.to_status_id != ? ORDER BY s.position, t.id",
        (wf, row["status_id"], row["status_id"])).fetchall())
    level = permissions.ROLE_LEVEL[role]
    return [t for t in result if level >= permissions.ROLE_LEVEL[t["min_role"]]]


def _display(conn, field, value):
    """Readable value for the history tab."""
    if value is None:
        return None
    lookups = {"assignee_id": ("users", "display_name"), "sprint_id": ("agile_sprints", "name"),
               "version_id": ("agile_versions", "name"), "type_id": ("agile_issue_types", "name"),
               "parent_id": ("agile_issues", "title")}
    if field in lookups:
        table, column = lookups[field]
        row = conn.execute("SELECT {} FROM {} WHERE id = ?".format(column, table), (value,)).fetchone()
        return row[0] if row else value
    return value


def api_update(ctx):
    project_id, role = c.access(ctx, "editor")
    conn, body = ctx.conn, ctx.body
    row = c.get_issue(conn, project_id, c.issue_number(ctx))
    taking = set(body) == {"assignee_id"} and c.opt_int(body, "assignee_id") == ctx.user["id"]
    if not (taking and c.can_take(ctx, role, row)):
        c.require_edit(ctx, role, row)
    changes = {}
    if "title" in body:
        changes["title"] = validate.text(body, "title", 255)
    if "description" in body:
        changes["description"] = validate.text(body, "description", 20000, required=False)
    if "priority" in body:
        if body["priority"] not in c.PRIORITIES:
            raise ApiError(400, "Priority invalide.")
        changes["priority"] = body["priority"]
    if "assignee_id" in body:
        changes["assignee_id"] = c.check_member(conn, project_id, c.opt_int(body, "assignee_id"))
    if "parent_number" in body:
        changes["parent_id"] = _check_parent(conn, project_id, c.opt_int(body, "parent_number"), row["id"])
    if "sprint_id" in body:
        changes["sprint_id"] = _optional_ref(conn, "agile_sprints", c.opt_int(body, "sprint_id"),
                                             project_id, "Sprint")
    if "version_id" in body:
        changes["version_id"] = _optional_ref(conn, "agile_versions", c.opt_int(body, "version_id"),
                                              project_id, "Version")
    if "story_points" in body:
        changes["story_points"] = c.opt_points(body)
    if "due_date" in body:
        changes["due_date"] = c.opt_date(body, "due_date")
    if "type_id" in body:
        new_type = _check_type(conn, project_id, c.opt_int(body, "type_id"))
        old_type = conn.execute("SELECT workflow_id FROM agile_issue_types WHERE id = ?",
                                (row["type_id"],)).fetchone()
        if new_type["workflow_id"] != old_type["workflow_id"]:
            raise ApiError(409, "Ce type utilise un autre workflow : changement impossible en V1.")
        changes["type_id"] = new_type["id"]
    changes = {k: v for k, v in changes.items() if row[k] != v}
    if not changes:
        return {"ok": True, "changed": []}
    sets = ", ".join("{} = ?".format(k) for k in changes)
    conn.execute("UPDATE agile_issues SET {}, updated_at = ? WHERE id = ?".format(sets),
                 tuple(changes.values()) + (db.utc_now(), row["id"]))
    for field, value in changes.items():
        old, new = _display(conn, field, row[field]), _display(conn, field, value)
        if field == "description":
            old, new = None, "(modifiée)"
        c.add_history(ctx, row["id"], field, old, new)
    c.log(ctx, "agile_issue_update", "agile_issue", row["id"], {"fields": sorted(changes)})
    return {"ok": True, "changed": sorted(changes)}


def api_delete(ctx):
    project_id, _ = c.access(ctx, "admin")
    row = c.get_issue(ctx.conn, project_id, c.issue_number(ctx))
    if ctx.conn.execute("SELECT is_requirement FROM agile_issue_types WHERE id = ?", (row["type_id"],)).fetchone()[0]:
        raise ApiError(409, "Un requirement ne s'efface jamais (traçabilité, D-B-061). Correctif : passez-la au status "
                            "« Rejected » ou « Obsolete » ; elle reste consultable avec son historique.")
    ctx.conn.execute("DELETE FROM agile_issues WHERE id = ?", (row["id"],))
    c.log(ctx, "agile_issue_delete", "agile_issue", row["id"],
          {"number": row["number"], "title": row["title"]})
    return {"ok": True}


def api_transition(ctx):
    project_id, role = c.access(ctx, "editor")
    conn = ctx.conn
    row = c.get_issue(conn, project_id, c.issue_number(ctx))
    c.require_edit(ctx, role, row)
    wanted = c.opt_int(ctx.body, "transition_id")
    allowed = {t["id"]: t for t in _available_transitions(conn, row, role)}
    if wanted not in allowed:
        raise ApiError(409, "Transition non autorisée depuis le status actuel.")
    t = allowed[wanted]
    from . import goldmine  # local import: goldmine imports this module
    blocked = goldmine.verification_guard(conn, row["id"], t["to_name"])
    if not blocked:
        from . import changes  # local import: changes imports this module
        blocked = changes.transition_guard(conn, row, t["to_name"])
    if not blocked:
        from . import qa  # D-B-037: all questions closed before leaving « Customer Clarification »
        blocked = qa.clarification_guard(conn, row, t["to_name"])
    if blocked:
        raise ApiError(409, "{} Correctif : {}".format(*blocked))
    old = conn.execute("SELECT name FROM agile_statuses WHERE id = ?", (row["status_id"],)).fetchone()
    now = db.utc_now()
    conn.execute("UPDATE agile_issues SET status_id = ?, updated_at = ?, resolved_at = ? WHERE id = ?",
                 (t["to_status_id"], now, now if t["to_category"] == "done" else None, row["id"]))
    c.add_history(ctx, row["id"], "status", old["name"], t["to_name"])
    c.log(ctx, "agile_issue_transition", "agile_issue", row["id"],
          {"from": old["name"], "to": t["to_name"]})
    return {"ok": True, "status": t["to_name"]}


# --------------------------------------------------------------------------
# Labels, comments, links
# --------------------------------------------------------------------------
def _set_labels(ctx, project_id, issue_id, names, record=True):
    conn = ctx.conn
    if len(names) > 20:
        raise ApiError(400, "Vingt labels au maximum par ticket.")
    wanted = {}
    for name in names:
        if not isinstance(name, str) or not c.LABEL_RE.match(name.strip()):
            raise ApiError(400, "Label invalide : lettres, chiffres, point, tiret ou soulignement, "
                                "sans espace, 40 caractères au maximum.")
        wanted[name.strip().lower()] = name.strip()
    ids = []
    for name in wanted.values():
        existing = conn.execute("SELECT id FROM agile_labels WHERE project_id = ? AND name = ?",
                                (project_id, name)).fetchone()
        ids.append(existing["id"] if existing else conn.execute(
            "INSERT INTO agile_labels (project_id, name) VALUES (?, ?)", (project_id, name)).lastrowid)
    before = [r["name"] for r in conn.execute(
        "SELECT l.name FROM agile_issue_labels il JOIN agile_labels l ON l.id = il.label_id "
        "WHERE il.issue_id = ? ORDER BY l.name", (issue_id,))]
    conn.execute("DELETE FROM agile_issue_labels WHERE issue_id = ?", (issue_id,))
    conn.executemany("INSERT INTO agile_issue_labels (issue_id, label_id) VALUES (?, ?)",
                     [(issue_id, i) for i in ids])
    after = sorted(wanted.values(), key=str.lower)
    if record and sorted(before, key=str.lower) != after:
        c.add_history(ctx, issue_id, "labels", ", ".join(before) or None, ", ".join(after) or None)
        conn.execute("UPDATE agile_issues SET updated_at = ? WHERE id = ?", (db.utc_now(), issue_id))
    return after


def api_set_labels(ctx):
    project_id, role = c.access(ctx, "editor")
    row = c.get_issue(ctx.conn, project_id, c.issue_number(ctx))
    c.require_edit(ctx, role, row)
    names = ctx.body.get("labels")
    if not isinstance(names, list):
        raise ApiError(400, "Liste de labels attendue.")
    labels = _set_labels(ctx, project_id, row["id"], names)
    c.log(ctx, "agile_issue_labels", "agile_issue", row["id"], {"labels": labels})
    return {"labels": labels}


def api_add_comment(ctx):
    project_id, _ = c.access(ctx, "editor")
    conn = ctx.conn
    row = c.get_issue(conn, project_id, c.issue_number(ctx))
    body = validate.text(ctx.body, "body", 10000)
    is_question = validate.boolean(ctx.body, "is_question", False)
    requirement_ref = validate.text(ctx.body, "requirement_ref", 40, required=False)
    parent_id = c.opt_int(ctx.body, "parent_comment_id")
    if parent_id is not None:
        parent = conn.execute("SELECT id FROM agile_comments WHERE id = ? AND issue_id = ?",
                              (parent_id, row["id"])).fetchone()
        if parent is None:
            raise ApiError(400, "Commentaire parent introuvable sur ce ticket.")
    cid = conn.execute(
        "INSERT INTO agile_comments (issue_id, parent_comment_id, author_id, is_question, "
        "requirement_ref, body, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (row["id"], parent_id, ctx.user["id"], int(is_question), requirement_ref, body,
         db.utc_now())).lastrowid
    c.log(ctx, "agile_comment_add", "agile_comment", cid, {"issue": row["id"], "question": is_question})
    from core import mentions  # D-A-046: requirement -> Goldmine, other types -> Agile / Change Management
    t = conn.execute("SELECT t.is_requirement, p.key FROM agile_issue_types t JOIN projects p ON p.id = ? "
                     "WHERE t.id = ?", (project_id, row["type_id"])).fetchone()
    href = "#/{}/{}/issue/{}".format("goldmine" if t and t["is_requirement"] else "agile", t["key"] if t else "", row["number"])
    sent = mentions.notify(conn, ctx.user, body, "ticket_comment", href, "{}-{} · {}".format(
        t["key"] if t else "", row["number"], row["title"]), project_id, "agile_comment:{}".format(cid))
    return {"id": cid, "mentions_notice": sent["notice"]}


def api_delete_comment(ctx):
    project_id, role = c.access(ctx, "editor")
    row = c.get_issue(ctx.conn, project_id, c.issue_number(ctx))
    cid = validate.int_param(ctx.params, "cid")
    comment = ctx.conn.execute("SELECT * FROM agile_comments WHERE id = ? AND issue_id = ?",
                               (cid, row["id"])).fetchone()
    if comment is None:
        raise ApiError(404, "Commentaire introuvable.")
    if comment["external_author"] and role != "admin":
        raise ApiError(403, "Seul un administrateur peut supprimer une réponse importée.")
    if comment["author_id"] != ctx.user["id"] and not comment["external_author"] and role != "admin":
        raise ApiError(403, "Seul l'auteur ou un administrateur peut supprimer ce commentaire.")
    ctx.conn.execute("DELETE FROM agile_comments WHERE id = ?", (cid,))
    c.log(ctx, "agile_comment_delete", "agile_comment", cid, {"issue": row["id"]})
    return {"ok": True}


def api_add_link(ctx):
    project_id, role = c.access(ctx, "editor")
    conn = ctx.conn
    row = c.get_issue(conn, project_id, c.issue_number(ctx))
    c.require_edit(ctx, role, row)
    link_type = validate.choice(ctx.body, "link_type", c.LINK_TYPES)
    target_key = (ctx.body.get("target_key") or "").strip()
    if target_key:
        target = c.find_by_key(conn, ctx.user, target_key)
    else:
        # Same-project shorthand, kept for the existing "n° du ticket" field.
        target = c.get_issue(conn, project_id, c.opt_int(ctx.body, "target_number") or 0)
    if target["id"] == row["id"]:
        raise ApiError(400, "Un ticket ne peut pas être lié à lui-même.")
    if link_type == "implements":
        target_type = conn.execute("SELECT is_requirement FROM agile_issue_types WHERE id = ?",
                                   (target["type_id"],)).fetchone()
        if not target_type or not target_type["is_requirement"]:
            raise ApiError(400, "« Implémente » ne peut viser qu'un ticket de type requirement.")
    try:
        lid = conn.execute("INSERT INTO agile_links (source_id, target_id, link_type, created_by, "
                           "created_at) VALUES (?, ?, ?, ?, ?)",
                           (row["id"], target["id"], link_type, ctx.user["id"], db.utc_now())).lastrowid
    except db.sqlite3.IntegrityError:
        raise ApiError(409, "Ce lien existe déjà.")
    c.log(ctx, "agile_link_add", "agile_link", lid, {"from": row["id"], "to": target["id"], "type": link_type})
    return {"id": lid}


def api_delete_link(ctx):
    project_id, role = c.access(ctx, "editor")
    row = c.get_issue(ctx.conn, project_id, c.issue_number(ctx))
    c.require_edit(ctx, role, row)
    lid = validate.int_param(ctx.params, "lid")
    deleted = ctx.conn.execute("DELETE FROM agile_links WHERE id = ? AND (source_id = ? OR target_id = ?)",
                               (lid, row["id"], row["id"])).rowcount
    if not deleted:
        raise ApiError(404, "Lien introuvable.")
    c.log(ctx, "agile_link_delete", "agile_link", lid, {"issue": row["id"]})
    return {"ok": True}
