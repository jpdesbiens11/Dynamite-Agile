"""Search hook (core lot v0.7, D-B-022; everywhere, D-B-076): tickets, requirements and needs (Goldmine), changes
(PR, bugs, ECN) with their fields, labels, client summary, requirement fields, change fields and affected items;
ticket comments; Goldmine Q&A; Pugh matrices (shown in Tools)."""
from .qa import ref as qa_ref

SCAN = 20000


def _in(projects):
    return ",".join("?" * len(projects)), list(projects)


def _issues(conn, projects, q):
    marks, ids = _in(projects)
    labels = {}
    for r in conn.execute("SELECT il.issue_id, l.name FROM agile_issue_labels il JOIN agile_labels l ON l.id = il.label_id "
                          "WHERE l.project_id IN ({})".format(marks), ids):
        labels.setdefault(r["issue_id"], []).append(r["name"])
    items = {}
    for r in conn.execute("SELECT c.*, i.id AS iid FROM agile_change_items c JOIN agile_issues i ON i.id = c.issue_id "
                          "WHERE i.project_id IN ({})".format(marks), ids):
        items.setdefault(r["iid"], []).append(" ".join(str(r[k] or "") for k in ("item_number", "item_title", "rev_from", "rev_to")))
    rows = conn.execute(
        "SELECT i.id, i.project_id, i.number, i.title, i.description, i.client_summary, i.updated_at, t.name AS type_name, "
        "t.bucket, s.name AS status_name, s.category, u.display_name AS assignee, r.external_id, r.statement, r.rationale, "
        "r.acceptance_criteria, r.source_doc, r.allocation, r.verification_ref, r.derived_from, r.kind, "
        "ch.root_cause, ch.reason, ch.impact_notes, ch.containment, ch.item_ref, ch.effectivity, ch.verification_ref AS ch_ref "
        "FROM agile_issues i JOIN agile_issue_types t ON t.id = i.type_id JOIN agile_statuses s ON s.id = i.status_id "
        "LEFT JOIN users u ON u.id = i.assignee_id LEFT JOIN agile_requirements r ON r.issue_id = i.id "
        "LEFT JOIN agile_changes ch ON ch.issue_id = i.id "
        "WHERE i.project_id IN ({}) ORDER BY i.updated_at DESC LIMIT {}".format(marks, SCAN), ids).fetchall()
    hits = []
    for r in rows:
        type_ = ("need" if r["kind"] == "need" else "requirement") if r["bucket"] == "goldmine" else (
            "change" if r["bucket"] == "change" else "ticket")
        if not q.wants(type_):
            continue
        pkey = projects[r["project_id"]]
        key = "{}-{}".format(pkey, r["number"])
        body = [r["external_id"], r["description"], r["client_summary"], r["statement"], r["rationale"],
                r["acceptance_criteria"], r["source_doc"], r["allocation"], r["verification_ref"], r["derived_from"],
                r["root_cause"], r["reason"], r["impact_notes"], r["containment"], r["item_ref"], r["effectivity"],
                r["ch_ref"], r["type_name"], r["status_name"], r["assignee"], " ".join(labels.get(r["id"], [])),
                " ".join(items.get(r["id"], []))]
        tab = "goldmine" if r["bucket"] == "goldmine" else "agile"
        title = "{} · {}".format(key, r["title"]) + (" ({})".format(r["external_id"]) if r["external_id"] else "")
        text = next((b for b in (r["statement"], r["description"], r["client_summary"], r["root_cause"]) if b), r["type_name"])
        h = q.hit(type_, q.score(key, r["title"] + " " + (r["external_id"] or ""), body), pkey, title,
                  "#/{}/{}/issue/{}".format(tab, pkey, r["number"]), " ".join(str(b or "") for b in body if b) if not q.title_only else text,
                  r["updated_at"], closed=r["category"] == "done", extra=r["status_name"])
        if h:
            h["snippet"] = q.snippet(_best(q, [text] + [b for b in body if b]))
            hits.append(h)
    return hits


def _best(q, texts):
    """The first text that contains a searched word, for the snippet."""
    from core.search import fold
    for t in texts:
        low = fold(t)
        if any(w in low for w in q.required):
            return t
    return texts[0] if texts else ""


def _comments(conn, projects, q):
    if not q.wants("ticket_comment") or q.title_only:
        return []
    marks, ids = _in(projects)
    hits = []
    for r in conn.execute(
            "SELECT c.id, c.body, c.created_at, c.external_author, u.display_name, i.project_id, i.number, i.title, t.bucket "
            "FROM agile_comments c JOIN agile_issues i ON i.id = c.issue_id JOIN agile_issue_types t ON t.id = i.type_id "
            "LEFT JOIN users u ON u.id = c.author_id WHERE i.project_id IN ({}) ORDER BY c.id DESC LIMIT {}".format(marks, SCAN), ids):
        pkey = projects[r["project_id"]]
        key = "{}-{}".format(pkey, r["number"])
        who = r["display_name"] or r["external_author"] or ""
        h = q.hit("ticket_comment", q.score("", "", (r["body"], who)), pkey, "Commentaire de {} sur {} · {}".format(who, key, r["title"]),
                  "#/{}/{}/issue/{}".format("goldmine" if r["bucket"] == "goldmine" else "agile", pkey, r["number"]),
                  r["body"], r["created_at"])
        if h:
            hits.append(h)
    return hits


def _qa(conn, projects, q):
    if not q.wants("qa"):
        return []
    marks, ids = _in(projects)
    hits = []
    for r in conn.execute(
            "SELECT a.*, i.project_id, i.number, i.title FROM goldmine_qa a JOIN agile_issues i ON i.id = a.issue_id "
            "WHERE i.project_id IN ({})".format(marks), ids):
        pkey = projects[r["project_id"]]
        code = qa_ref(r["direction"], r["seq"])
        events = " ".join(e["text"] or "" for e in conn.execute("SELECT text FROM goldmine_qa_events WHERE qa_id = ?", (r["id"],)))
        body = (r["question"], r["answer"], r["asked_name"], r["answered_name"], events, "{}-{}".format(pkey, r["number"]))
        h = q.hit("qa", q.score(code, r["question"], body), pkey, "{} · {}-{} · {}".format(code, pkey, r["number"], r["question"][:90]),
                  "#/goldmine/{}/qa/{}".format(pkey, r["id"]), " ".join(filter(None, (r["question"], r["answer"]))),
                  r["updated_at"], closed=r["status"] in ("closed", "cancelled"))
        if h:
            hits.append(h)
    return hits


def _pugh(conn, projects, q):
    if not q.wants("analysis"):
        return []
    marks, ids = _in(projects)
    hits = []
    for r in conn.execute("SELECT * FROM goldmine_pugh WHERE project_id IN ({})".format(marks), ids):
        concepts = " ".join(c["name"] + " " + (c["description"] or "") for c in
                            conn.execute("SELECT name, description FROM goldmine_pugh_concepts WHERE pugh_id = ?", (r["id"],)))
        pkey = projects[r["project_id"]]
        h = q.hit("analysis", q.score("", r["title"], (r["description"], concepts, r["decision_note"])), pkey,
                  "Pugh Matrix · " + r["title"], "#/tools/{}/pugh/{}".format(pkey, r["id"]),
                  " ".join(filter(None, (r["description"], concepts, r["decision_note"]))), r["updated_at"],
                  closed=r["status"] == "decided")
        if h:
            hits.append(h)
    return hits


def search(conn, projects, q):
    return _issues(conn, projects, q) + _comments(conn, projects, q) + _qa(conn, projects, q) + _pugh(conn, projects, q)
