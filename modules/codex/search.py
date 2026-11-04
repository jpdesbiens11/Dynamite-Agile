"""Search hook (core lot v0.7, D-B-022; D-B-076): document references -- reference, file name, title, system code,
type, step of the PDP, folder."""
from urllib.parse import quote


def search(conn, projects, q):
    if not q.wants("reference"):
        return []
    marks = ",".join("?" * len(projects))
    rows = conn.execute(
        "SELECT * FROM codex_refs WHERE project_id IN ({}) ORDER BY date_serial DESC, time_serial DESC LIMIT 20000".format(marks),
        list(projects)).fetchall()
    hits = []
    for r in rows:
        key = projects[r["project_id"]]
        body = (r["system_code"], r["doc_type"], "Étape {}".format(r["pdp_step"]), r["folder"], r["svn_path"], r["void_reason"])
        h = q.hit("reference", q.score(r["reference"], "{} {}".format(r["file_name"], r["title"]), body), key, r["file_name"],
                  "#/codex/{}/registre/{}".format(key, quote(r["reference"])), " · ".join(filter(None, map(str, body))),
                  r["updated_at"], closed=r["status"] == "void", extra="annulée" if r["status"] == "void" else "")
        if h:
            hits.append(h)
    return hits
