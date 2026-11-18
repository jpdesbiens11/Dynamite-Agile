"""Search hook (D-B-076, D-B-079): the tests of the Test Bases. D-B-097: one base per Space -- a test is found in
the Spaces the search covers (the reference catalogue is the Space TESTING)."""


def search(conn, projects, q):
    hits = []
    if not q.wants("test") or not projects:
        return hits
    marks = ",".join("?" * len(projects))
    for r in conn.execute("SELECT * FROM testing_tests WHERE project_id IN ({})".format(marks), list(projects)):
        key = projects[r["project_id"]]
        body = (r["standard"], r["section"], r["objective"], r["acceptance"], r["means"], r["notes"])
        h = q.hit("test", q.score(r["test_id"], r["title"], body), key, "{} · {}".format(r["test_id"], r["title"]),
                  "#/testing/{}/test/{}".format(key, r["test_id"]), " — ".join(filter(None, (r["standard"], r["section"], r["objective"]))),
                  r["updated_at"], closed=r["status"] == "Obsolete", extra=r["status"])
        if h:
            hits.append(h)
    return hits


def change_link(conn, entry, row, key):
    """« Changements » (core lot v0.39, 0.60.120): a test of the Test Base opens on its card."""
    if entry["object_type"] != "testing_test" or not row or not key:
        return None
    return {"tab": "testing", "code": row["test_id"], "title": row["title"], "href": "#/testing/{}/test/{}".format(key, row["test_id"])}
