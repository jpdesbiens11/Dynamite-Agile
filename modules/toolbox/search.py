"""Search hook (D-B-076): Tools -- ideation sessions and their ideas, Kepner-Tregoe analyses. Ideas of a brainwriting
still in its rounds stay private (like on screen): only the author finds them before the review."""
from . import ideation_bw


def search(conn, projects, q):
    marks = ",".join("?" * len(projects))
    hits = []
    if q.wants("idea"):
        sessions = {r["id"]: r for r in conn.execute("SELECT * FROM tools_ideation WHERE project_id IN ({})".format(marks), list(projects))}
        running = {sid for sid, r in sessions.items() if r["method"] == "brainwriting" and ideation_bw.clock(r)["phase"] == "running"}
        for s in sessions.values():
            key = projects[s["project_id"]]
            h = q.hit("idea", q.score("", s["title"], (s["prompt"],)), key, "Séance · " + s["title"],
                      "#/tools/{}/ideation/{}".format(key, s["id"]), s["prompt"], s["updated_at"], closed=s["status"] == "closed")
            if h:
                hits.append(h)
        for r in conn.execute("SELECT i.* FROM tools_ideas i JOIN tools_ideation s ON s.id = i.session_id "
                              "WHERE s.project_id IN ({})".format(marks), list(projects)):
            if r["session_id"] in running and r["author_id"] != q.user_id:
                continue
            s = sessions[r["session_id"]]
            key = projects[s["project_id"]]
            h = q.hit("idea", q.score("", r["text"][:120], (r["tag"], r["author_initials"])), key,
                      "Idée · " + r["text"][:100], "#/tools/{}/ideation/{}".format(key, s["id"]),
                      "{} — séance « {} »".format(r["text"], s["title"]), r["created_at"], closed=s["status"] == "closed")
            if h:
                hits.append(h)
    if q.wants("analysis"):
        for r in conn.execute("SELECT * FROM tools_kt WHERE project_id IN ({})".format(marks), list(projects)):
            parts = [x["text"] for x in conn.execute("SELECT text FROM tools_kt_criteria WHERE kt_id = ?", (r["id"],))]
            parts += [x["name"] + " " + (x["description"] or "") for x in conn.execute("SELECT name, description FROM tools_kt_alts WHERE kt_id = ?", (r["id"],))]
            parts += [x["text"] for x in conn.execute("SELECT text FROM tools_kt_risks WHERE kt_id = ?", (r["id"],))]
            key = projects[r["project_id"]]
            body = [r["statement"], r["decision_note"]] + parts
            h = q.hit("analysis", q.score("", r["title"], body), key, "Kepner-Tregoe · " + r["title"],
                      "#/tools/{}/kt/{}".format(key, r["id"]), " ".join(filter(None, body)), r["updated_at"],
                      closed=r["status"] == "decided")
            if h:
                hits.append(h)
    return hits
