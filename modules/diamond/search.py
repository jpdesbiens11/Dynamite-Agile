"""Search hook of Diamond (0.60.36, D-O-044): functions (F-n), project risks (R-n) and DFMEA rows (with their confirmed class
CC / SC and its reason, 0.60.101) -- for the search of the top bar and for Bob le mineur (core/bot.py), who answers with
pointer links to them."""


def search(conn, projects, q):
    if not q.wants("function"):
        return []
    marks = ",".join("?" * len(projects))
    ids = list(projects)
    hits = []
    for r in conn.execute("SELECT * FROM diamond_functions WHERE archived = 0 AND project_id IN ({})".format(marks), ids):
        key, code = projects[r["project_id"]], "F{}".format(r["number"])
        h = q.hit("function", q.score(code, r["text"], (r["notes"], r["ftype"])), key, "{} {}".format(code, r["text"]),
                  "#/diamond/{}/ftree".format(key), r["notes"], r["updated_at"])
        if h:
            hits.append(dict(h, focus=code))  # what the pointer shows on the page (D-O-043)
    for r in conn.execute("SELECT * FROM diamond_risks WHERE archived = 0 AND project_id IN ({})".format(marks), ids):
        key, code = projects[r["project_id"]], "R-{}".format(r["number"])
        h = q.hit("function", q.score(code, r["title"], (r["cause"], r["consequence"], r["action"])), key,
                  "{} {}".format(code, r["title"]), "#/diamond/{}/prisk".format(key), r["cause"], r["updated_at"],
                  closed=r["status"] == "closed", extra="risque")
        if h:
            hits.append(dict(h, focus=code))
    for r in conn.execute("SELECT * FROM diamond_dfmea WHERE project_id IN ({})".format(marks), ids):
        key = projects[r["project_id"]]
        cls = r["class_code"] if r["class_state"] == "confirmed" else ""  # 0.60.101 (D-O-108): « CC », « SC » and the reason are found
        h = q.hit("function", q.score("", r["failure_mode"], (r["effect"], r["cause"], r["focus"], r["requirement"], cls, r["class_reason"])), key,
                  "DFMEA · {}{}".format(cls + " · " if cls else "", r["failure_mode"][:120]), "#/diamond/{}/dfmea".format(key), r["cause"],
                  r["updated_at"], extra="DFMEA")
        if h:
            hits.append(dict(h, focus=r["failure_mode"][:80]))
    return hits
