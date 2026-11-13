"""The Rover's evidence made consistent (0.60.99, D-O-106): what a quality auditor checks first in the demo.

Until 0.60.98 the demo said more than its evidence showed. Its test plans carried a results PDF but no recorded
result, so Testing → Vérification gave « Not run » for requirements that Goldmine called « Verified ». Its closed ECN
had no CCB approvers and no verification reference, and the problem report it treats stayed « Derived to ECN ». Two
example requirements of the former HeadLamp path were still there. Applied once per installation (journal
« demo_evidence_coherent »), right after demo_life: on a new DEMO as on a DEMO loaded by an older version.

  Testing    the plans that are closed or have received their results get one bundle (the prototype tested), a result
             per test and the results PDF as evidence, so the verdicts are computed (testing/verification.py) and the
             closed plan has nothing missing (bundles.close_blockers);
  Goldmine   a requirement is « Verified » when its verdict says so, with its « Verification Ref. » (plan and tests); one
             whose tests are still out keeps « In Verification », with the plan that runs them;
  Change     the CCB approvers and the decision date of the ECNs past « Approved », the verification reference of the
             closed one, and the problem report it treats closed;
  HeadLamp   HL-001 and HL-002 become « Rejected », with a comment: a requirement is never deleted (D-B-061).

A DEMO someone has changed is respected: a plan that already has bundles, a requirement whose reference is filled in,
and an ECN field that is already set are all left as they are.
"""
import json

from core import audit, db

from . import demo_life_data as L
from .demo_life import LIFE_DONE, PREFIX, move
from .headlamp import project_id

DONE = "demo_evidence_coherent"
PROTOS = {"closed": ("Rover MVP 2", "RVR-02"), "results": ("Rover MVP 3", "RVR-03")}
HEADLAMP_IDS = ("HL-001", "HL-002")
REJECT_NOTE = ("Exemple de l'ancien parcours HeadLamp, retiré de la démo (0.60.99). Une exigence ne s'efface jamais : "
               "elle reste ici, « Rejected », avec son historique.")
CCB = "Nina (exemple), Alexis (exemple)"
# closed ECN -> (ECN task that re-ran the test, title of that test in the Test Base)
VERIFIED_BY = {"Rampe moteur de 0,5 s et condensateur de 1 000 µF sur le 5 V": ("Refaire l'essai des arrêts d'urgence",
                                                                               "Arrêts d'urgence")}
TO_VERIFIED = ("Implemented", "In Verification")


def ensure_evidence(ctx):
    """Once, after the Rover in motion (demo_life). Returns the counts, or None (no DEMO, no Rover, already done)."""
    conn = ctx.conn
    pid = project_id(conn)
    if pid is None:
        return None
    logged = lambda action: conn.execute("SELECT 1 FROM audit_log WHERE action = ? AND object_id = ?", (action, str(pid))).fetchone()  # noqa: E731
    if not logged(LIFE_DONE) or logged(DONE):
        return None
    who = _person(conn, "lea") or ctx.user["id"]
    counts = {"rejected": headlamp(ctx, pid)}
    counts["results"] = results(conn, pid, who)
    counts.update(requirements(conn, pid, who))
    counts.update(changes(ctx, pid))
    audit.log_action(conn, ctx.user["id"], DONE, "project", pid, counts, None)
    return counts


def _person(conn, username):
    row = conn.execute("SELECT id FROM users WHERE username = ?", (PREFIX + username,)).fetchone()
    return row["id"] if row else None


def _requirement_rows(conn, pid, where, args=()):
    return [dict(r) for r in conn.execute(
        "SELECT i.*, t.workflow_id, s.name AS status_name, s.category, r.external_id, r.test_ref, r.verification_ref "
        "FROM agile_requirements r JOIN agile_issues i ON i.id = r.issue_id JOIN agile_issue_types t ON t.id = i.type_id "
        "JOIN agile_statuses s ON s.id = i.status_id WHERE i.project_id = ? AND " + where, (pid,) + tuple(args))]


# --------------------------------------------------------------------------
# HeadLamp leftovers
# --------------------------------------------------------------------------
def headlamp(ctx, pid):
    conn = ctx.conn
    made = 0
    for r in _requirement_rows(conn, pid, "r.external_id IN (?, ?)", HEADLAMP_IDS):
        if r["category"] == "done":
            continue
        now = db.utc_now()
        path = ["In Analysis", "Rejected"] if r["status_name"] == "Received" else ["Rejected"]
        move(conn, r, path, ctx.user["id"], [now] * len(path))
        conn.execute("INSERT INTO agile_comments (issue_id, author_id, body, created_at) VALUES (?, ?, ?, ?)",
                     (r["id"], ctx.user["id"], REJECT_NOTE, now))
        made += 1
    return made


# --------------------------------------------------------------------------
# Testing: one bundle per plan that has its results, a result per test, the PDF as evidence
# --------------------------------------------------------------------------
def _plans(conn, pid):
    return [dict(p) for p in conn.execute("SELECT * FROM testing_plans WHERE project_id = ? AND code LIKE 'TP-ROVER-%' "
                                          "ORDER BY code", (pid,))]


def results(conn, pid, who):
    titles = {r["test_id"]: r["title"] for r in conn.execute("SELECT test_id, title FROM testing_tests WHERE project_id = ?", (pid,))}
    made = 0
    for p in _plans(conn, pid):
        if p["status"] not in PROTOS or not p["results_id"]:
            continue
        if conn.execute("SELECT 1 FROM testing_bundles WHERE plan_id = ?", (p["id"],)).fetchone():
            continue  # results someone already entered are never touched
        at = p["updated_at"]
        proto, serial = PROTOS[p["status"]]
        bid = conn.execute("INSERT INTO testing_bundles (plan_id, proto, serial, note, created_by, created_at, updated_at) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?)", (p["id"], proto, serial, "Prototype de l'exemple Rover.", who, at, at)).lastrowid
        eid = conn.execute("INSERT INTO testing_evidence (plan_id, attachment_id, name, note, bundle_id, created_by, created_at, kind) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?, 'file')",
                           (p["id"], p["results_id"], p["results_name"], "Rapport d'essais (exemple Rover).", bid, who, at)).lastrowid
        for test_id in json.loads(p["tests"] or "[]"):
            note = L.RESULTS.get(titles.get(test_id), ("",))[0]
            conn.execute("INSERT INTO testing_results (bundle_id, test_id, result, note, evidence, updated_by, updated_at) "
                         "VALUES (?, ?, 'passed', ?, ?, ?, ?)", (bid, test_id, note, json.dumps([eid]), who, at))
            made += 1
    return made


# --------------------------------------------------------------------------
# Goldmine: the status follows the verdict, with its verification reference
# --------------------------------------------------------------------------
def requirements(conn, pid, who):
    from modules.testing import catalog, verification
    by_test = verification.verdicts(verification.executions(conn, pid))
    runs = {}  # test_id -> [(plan code, plan status, results time)]
    for p in _plans(conn, pid):
        for test_id in json.loads(p["tests"] or "[]"):
            runs.setdefault(test_id, []).append((p["code"], p["status"], p["updated_at"]))
    verified = referenced = 0
    for r in _requirement_rows(conn, pid, "r.kind = 'requirement' AND r.external_id LIKE 'REQ-%'"):
        tests = catalog.split_refs(r["test_ref"] or "")
        if not tests:
            continue
        verdict = verification.requirement_verdict([(t, by_test.get(t, "not_run")) for t in tests])
        plans = sorted({run for t in tests for run in runs.get(t, [])})
        status = r["status_name"]
        if verdict in ("verified", "derogation") and status in TO_VERIFIED:
            moment = max(at for _code, state, at in plans if state in PROTOS)
            move(conn, r, ["In Verification", "Verified"], who, [moment, moment])
            status = "Verified"
            verified += 1
        elif status == "Verified" and verdict not in ("verified", "derogation"):
            move(conn, r, ["In Verification"], who, [db.utc_now()])
            status = "In Verification"
        if status in ("In Verification", "Verified") and not (r["verification_ref"] or "").strip():
            ref = _reference(tests, plans, status, by_test)
            conn.execute("UPDATE agile_requirements SET verification_ref = ? WHERE issue_id = ?", (ref, r["id"]))
            conn.execute("INSERT INTO agile_history (issue_id, user_id, ts, field, old_value, new_value) "
                         "VALUES (?, ?, ?, 'verification_ref', '', ?)", (r["id"], who, db.utc_now(), ref))
            referenced += 1
    return {"requirements_verified": verified, "verification_refs": referenced}


def _reference(tests, plans, status, by_test):
    codes = ", ".join(code for code, _state, _at in plans) or "plan à venir"
    if status == "Verified":
        return "{} · {} : {} (rapport d'essais joint au plan)".format(
            codes, ", ".join(tests), "Passed with derogation" if "derogation" in {by_test.get(t) for t in tests} else "Passed")
    return "{} · {} : envoyé, résultats attendus".format(codes, ", ".join(tests))


# --------------------------------------------------------------------------
# Change Management: CCB fields, verification reference, the problem report closed with its ECN
# --------------------------------------------------------------------------
def _change(conn, pid, role, title):
    row = conn.execute("SELECT i.*, t.workflow_id, s.name AS status_name FROM agile_issues i JOIN agile_issue_types t ON t.id = i.type_id "
                       "JOIN agile_statuses s ON s.id = i.status_id WHERE i.project_id = ? AND t.change_role = ? AND i.title = ? "
                       "ORDER BY i.number LIMIT 1", (pid, role, title)).fetchone()
    return dict(row) if row else None


def _reached(conn, issue_id, status):
    row = conn.execute("SELECT ts FROM agile_history WHERE issue_id = ? AND field = 'status' AND new_value = ? ORDER BY ts LIMIT 1",
                       (issue_id, status)).fetchone()
    return row["ts"] if row else None


def changes(ctx, pid):
    from modules.agile import change_fields as cf
    conn = ctx.conn
    filled = closed = 0
    for change in L.CHANGES:
        ecn = _change(conn, pid, "ecn", change["ecn"]["title"])
        if ecn is None:
            continue
        current = cf.fields_of(conn, ecn["id"])
        approved = _reached(conn, ecn["id"], "Approved")
        updates = {}
        if approved and not current["approvers"]:
            updates["approvers"] = CCB
        if approved and not current["decision_date"]:
            updates["decision_date"] = approved[:10]
        if ecn["status_name"] == "Closed" and not current["verification_ref"]:
            updates["verification_ref"] = _verified_by(conn, pid, ecn)
        if updates:
            cf.save_fields(ctx, ecn["id"], cf.clean(updates, cf.ECN_FIELDS))
            filled += 1
        pr = _change(conn, pid, "pr", change["pr"]["title"])
        if pr is not None and ecn["status_name"] == "Closed" and pr["status_name"] == "Derived to ECN":
            move(conn, pr, ["Closed"], ecn["assignee_id"] or ctx.user["id"], [ecn["resolved_at"] or db.utc_now()])
            closed += 1
    return {"ecn_filled": filled, "pr_closed": closed}


def _verified_by(conn, pid, ecn):
    task_title, test_title = VERIFIED_BY.get(ecn["title"], ("", ""))
    task = conn.execute("SELECT number FROM agile_issues WHERE parent_id = ? AND title = ?", (ecn["id"], task_title)).fetchone()
    test = conn.execute("SELECT test_id FROM testing_tests WHERE project_id = ? AND title = ?", (pid, test_title)).fetchone()
    key = conn.execute("SELECT key FROM projects WHERE id = ?", (pid,)).fetchone()["key"]
    if task is None or test is None:
        return "Sous-tâches de vérification de l'ECN terminées"
    return "{}-{} · {} refait au banc : {}".format(key, task["number"], test["test_id"], L.RESULTS.get(test_title, ("réussi",))[0])
