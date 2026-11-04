"""Search hook (core lot v0.7, D-B-022; everywhere, D-B-076): page titles and the text of their current version,
and page comments."""
import json

from .content import plain_text

SCAN = 20000


def search(conn, projects, q):
    marks = ",".join("?" * len(projects))
    hits = []
    if q.wants("page"):
        rows = conn.execute(
            "SELECT p.id, p.project_id, p.title, p.updated_at, v.body, u.display_name FROM dynamite_pages p "
            "JOIN dynamite_versions v ON v.page_id = p.id AND v.version = p.current_version "
            "LEFT JOIN users u ON u.id = p.updated_by "
            "WHERE p.project_id IN ({}) ORDER BY p.updated_at DESC LIMIT ?".format(marks),
            list(projects) + [SCAN]).fetchall()
        for r in rows:
            try:
                text = plain_text(json.loads(r["body"]))
            except (ValueError, TypeError):
                text = ""
            key = projects[r["project_id"]]
            h = q.hit("page", q.score("", r["title"], (text,)), key, r["title"], "#/dynamite/{}/page/{}".format(key, r["id"]),
                      text, r["updated_at"], extra=r["display_name"] or "")
            if h:
                hits.append(h)
    if q.wants("page_comment") and not q.title_only:
        for r in conn.execute(
                "SELECT c.id, c.body, c.created_at, p.id AS page_id, p.project_id, p.title, u.display_name "
                "FROM dynamite_comments c JOIN dynamite_pages p ON p.id = c.page_id LEFT JOIN users u ON u.id = c.author_id "
                "WHERE p.project_id IN ({}) ORDER BY c.id DESC LIMIT ?".format(marks), list(projects) + [SCAN]):
            key = projects[r["project_id"]]
            who = r["display_name"] or ""
            h = q.hit("page_comment", q.score("", "", (r["body"], who)), key, "Commentaire de {} sur « {} »".format(who, r["title"]),
                      "#/dynamite/{}/page/{}".format(key, r["page_id"]), r["body"], r["created_at"])
            if h:
                hits.append(h)
    return hits
