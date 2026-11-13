"""Verification status of tests and Goldmine requirements, from the results of the test plans (0.60.91, D-O-097).

A test's **verdict** comes from the latest result on each prototype (a later plan replaces an earlier one for the same
prototype): Failed if any prototype failed, else Passed with derogation if any needed one, else Passed if at least one
passed, else Not run (abandoned results do not verify anything). A requirement's verdict combines the verdicts of the
tests it cites in « Test Procedure »: Failed, Verified, Verified with derogation, Partially verified or Not run.
Plans that were cancelled are ignored.
"""
from . import bundles, catalog, tests_api

TEST_LABELS = {"passed": "Passed", "derogation": "Passed with derogation", "failed": "Failed", "not_run": "Not run"}
REQ_LABELS = {"verified": "Verified", "derogation": "Verified with derogation", "failed": "Failed",
              "partial": "Partially verified", "not_run": "Not run"}
SET_ASIDE = ("Rejected", "Obsolete")  # 0.60.99 (D-O-106): a rejected or replaced requirement has nothing left to verify


def executions(conn, pid, test_id=None):
    """Every recorded result of the Space's plans (oldest first), optionally for one test."""
    sql = ("SELECT r.test_id, r.result, r.note, r.updated_at AS at, b.proto, b.serial, p.code AS plan, p.status AS plan_status "
           "FROM testing_results r JOIN testing_bundles b ON b.id = r.bundle_id JOIN testing_plans p ON p.id = b.plan_id "
           "WHERE p.project_id = ? AND p.status != 'cancelled' AND r.result != ''")
    args = [pid]
    if test_id:
        sql += " AND r.test_id = ?"
        args.append(test_id)
    return [dict(r, result_label=bundles.RESULTS[r["result"]]) for r in conn.execute(sql + " ORDER BY r.updated_at, r.id", args)]


def verdicts(rows):
    """{test_id: verdict} from executions(): the latest result per prototype, then the worst of them."""
    latest = {}
    for r in rows:  # oldest first: a later row replaces the earlier one for the same prototype
        latest[(r["test_id"], r["proto"].lower())] = r["result"]
    by_test = {}
    for (test_id, _proto), result in latest.items():
        by_test.setdefault(test_id, set()).add(result)
    out = {}
    for test_id, seen in by_test.items():
        out[test_id] = ("failed" if "failed" in seen else "derogation" if "derogation" in seen
                        else "passed" if "passed" in seen else "not_run")
    return out


def requirement_verdict(tests):
    seen = [v for _t, v in tests]
    if "failed" in seen:
        return "failed"
    if all(v == "not_run" for v in seen):
        return "not_run"
    if "not_run" in seen:
        return "partial"
    return "derogation" if "derogation" in seen else "verified"


def api_verification(ctx):
    """GET /api/testing/verification?space=KEY: one line per requirement that cites tests."""
    pid, key = tests_api.space(ctx)
    by_test = verdicts(executions(ctx.conn, pid))
    linked = tests_api._visible_requirements(ctx.conn, ctx.user, pid)
    reqs = {}
    for test_id, items in linked.items():
        for item in items:
            if item["status"] in SET_ASIDE:
                continue
            reqs.setdefault(item["key"], dict(item, tests=[]))["tests"].append((test_id, by_test.get(test_id, "not_run")))
    rows = []
    for r in sorted(reqs.values(), key=lambda x: (x["key"].split("-")[0], int(x["key"].rsplit("-", 1)[1]))):
        r["tests"].sort()
        verdict = requirement_verdict(r["tests"])
        rows.append(dict(r, tests=[{"test_id": t, "verdict": v} for t, v in r["tests"]], verdict=verdict, verdict_label=REQ_LABELS[verdict]))
    counts = {k: sum(1 for r in rows if r["verdict"] == k) for k in REQ_LABELS}
    return {"space": key, "requirements": rows, "counts": counts, "labels": REQ_LABELS, "test_labels": TEST_LABELS}
