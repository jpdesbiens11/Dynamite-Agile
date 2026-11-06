"""The Rover in DEMO, a project in motion (0.60.54, D-O-063), second part: Change Management, Goldmine, Testing, Exploration,
Timesheet and Diamond. demo_life.ensure_life calls each function once; content in demo_life_data.py."""
import datetime as dt
import json

from core import db

from . import demo_life_data as L
from .demo_life import move, upload


def _as(ctx, pid, body, func):
    from core import starter_apply
    return starter_apply._as(ctx, pid, body, func)


# --------------------------------------------------------------------------
# Change Management
# --------------------------------------------------------------------------
def changes(ctx, pid, people, clock, issues):
    from modules.agile import change_fields as cf, issues as api
    conn = ctx.conn
    kinds = {r["change_role"]: dict(r) for r in conn.execute(
        "SELECT id, change_role, workflow_id FROM agile_issue_types WHERE project_id = ? AND change_role != ''", (pid,))}
    if not {"pr", "ecn", "ecn_task"} <= set(kinds):
        return {"changes": 0}

    def create(role, title, who, week, parent=None, description=""):
        body = {"type_id": kinds[role]["id"], "title": title, "description": description, "priority": "high" if role == "pr" else "medium"}
        if parent:
            body["parent_number"] = parent
        number = _as(ctx, pid, body, api.api_create)["number"]
        row = dict(conn.execute("SELECT * FROM agile_issues WHERE project_id = ? AND number = ?", (pid, number)).fetchone())
        row["workflow_id"] = kinds[role]["workflow_id"]
        conn.execute("UPDATE agile_issues SET assignee_id = ?, reporter_id = ?, created_at = ? WHERE id = ?",
                     (people.get(who), people.get(who), clock.iso(week, 1, 9), row["id"]))
        return row

    made = 0
    for change in L.CHANGES:
        p, e = change["pr"], change["ecn"]
        pr = create("pr", p["title"], p["by"], p["week"], description="Problème trouvé en essai ; voir le ticket relié.")
        cf.save_fields(ctx, pr["id"], cf.clean(p["fields"], cf.PROBLEM_FIELDS))
        move(conn, pr, ["In Analysis", p["status"]], people.get(p["by"]), [clock.iso(p["week"], 1, 14), clock.iso(p["week"], 2, 10)])
        ecn = create("ecn", e["title"], e["by"], e["week"], description="Traite le problème relié (Change Management).")
        fields = {k: bool(v) if k.startswith("impact_") and k != "impact_notes" else v for k, v in e["fields"].items()}
        cf.save_fields(ctx, ecn["id"], cf.clean(fields, cf.ECN_FIELDS))
        cf.save_items(ctx, ecn["id"], cf.clean_items([dict(zip(("item_type", "item_number", "item_title", "rev_from", "rev_to",
                                                                  "disposition"), it)) for it in e["items"]]))
        path = ["Submitted", "CCB Review", "Approved", "In Implementation", "In Verification", "Closed"]
        path = path[:path.index(e["status"]) + 1]
        lead = people.get(L.LEAD)
        move(conn, ecn, path, lead, [clock.iso(e["week"], d, 10 + i) for i, d in enumerate((2, 2, 3, 3, 4, 4))][:len(path)])
        for title, who, status in e["tasks"]:
            task = create("ecn_task", title, who, e["week"], parent=ecn["number"])
            target = {"Done": ["In Progress", "Done"], "In Progress": ["In Progress"]}.get(status, [])
            move(conn, task, target, people.get(who), [clock.iso(e["week"], 3, 9), clock.iso(e["week"], 4, 15)])
        links = [(ecn["id"], pr["id"], "resolves")]
        if issues.get(p.get("relates")):
            links.append((pr["id"], issues[p["relates"]]["id"], "relates"))
        for a, b, kind in links:
            conn.execute("INSERT OR IGNORE INTO agile_links (source_id, target_id, link_type, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
                         (a, b, kind, people.get(e["by"]), clock.iso(e["week"], 2)))
        made += 2
    return {"changes": made}


# --------------------------------------------------------------------------
# Goldmine
# --------------------------------------------------------------------------
def goldmine(conn, pid, people, clock):
    from modules.agile import qa
    rows = {r["external_id"]: dict(r) for r in conn.execute(
        "SELECT i.*, t.workflow_id, r.external_id, r.kind FROM agile_requirements r JOIN agile_issues i ON i.id = r.issue_id "
        "JOIN agile_issue_types t ON t.id = i.type_id WHERE i.project_id = ? AND (r.external_id LIKE 'REQ-%' OR r.external_id LIKE 'BES-%')",
        (pid,))}
    lea, lead = people.get("lea"), people.get(L.LEAD)
    checked = "{} · demo.lea · édition en vigueur vérifiée (exemple)".format(clock.date(4, 0).isoformat())
    conn.execute("UPDATE agile_requirements SET standard_review = 'verified', standard_checked = ? WHERE standard_review = 'to_verify' "
                 "AND issue_id IN ({})".format(",".join(str(int(r["id"])) for r in rows.values()) or "NULL"), (checked,))
    moved = 0
    for ref, issue in rows.items():
        conn.execute("UPDATE agile_issues SET assignee_id = COALESCE(assignee_id, ?) WHERE id = ?", (lea, issue["id"]))
        if ref.startswith("BES-"):
            move(conn, issue, ["In Analysis", "Accepted"], lead, [clock.iso(2, 1), clock.iso(3, 2)])
            if ref in L.NEED_STATUS:
                conn.execute("UPDATE agile_requirements SET need_status = ? WHERE issue_id = ?", (L.NEED_STATUS[ref], issue["id"]))
            moved += 1
            continue
        target = L.REQ_STATUS.get(ref, L.REQ_DEFAULT)
        path = ["In Analysis", "Accepted", "Allocated", "Implemented", "In Verification", "Verified"]
        path = path[:path.index(target) + 1]
        weeks = [(4, 1), (5, 2), (7, 1), (12, 3), (13, 2), (14, 3)]
        move(conn, issue, path, lea, [clock.iso(w, d) for w, d in weeks][:len(path)])
        moved += 1
    made = 0
    for ref, who, week, question, answer, answered, status, owner, blocking in L.QA:
        issue = rows.get(ref)
        if issue is None:
            continue
        due = clock.date(L.NOW_WEEK, 4).isoformat() if status == "open" else None
        qid = qa.create(conn, issue, "team", question, people.get(who), owner_id=people.get(owner), due_date=due,
                        blocking=blocking, when=clock.at(week, 1, 10))
        if answer:
            qa.answer(conn, {"id": qid}, answer, None, name="Enseignante (cliente)", when=clock.at(answered, 3, 14))
        if status == "closed":
            qa.set_status(conn, {"id": qid}, "closed", people.get(who), when=clock.at(answered, 3, 16))
        made += 1
    return {"requirements_moved": moved, "qa": made}


# --------------------------------------------------------------------------
# Testing
# --------------------------------------------------------------------------
def _pdf(code, title, tests, clock, week):
    from modules.dynamite import export_pdf
    cell = lambda text: [(text, {})]  # noqa: E731
    rows = [[cell("Essai"), cell("Titre"), cell("Résultat"), cell("Verdict")]]
    rows += [[cell(t["test_id"]), cell(t["title"]), cell(L.RESULTS.get(t["title"], ("—", "—"))[0]),
              cell(L.RESULTS.get(t["title"], ("—", "—"))[1])] for t in tests]
    doc = {"title": "Résultats", "level": 1, "version": 1, "updated": clock.date(week, 4).isoformat(),
           "items": [("p", [("Résultats fictifs de l'exemple Rover, pour montrer la forme d'un rapport d'essais.", {"italic": True})], "panel"),
                     ("table", True, rows)]}
    return export_pdf.build([doc], {"title": "{} — {}".format(code, title), "space": "DEMO", "by": "Léa (exemple)",
                                    "at": clock.date(week, 4).isoformat()})


def testing(ctx, pid, people, clock):
    from core import uploads
    conn = ctx.conn
    lea = people.get("lea")
    tests = {r["title"]: dict(r) for r in conn.execute("SELECT * FROM testing_tests WHERE project_id = ? AND origin = 'example'", (pid,))}
    checked = "{} · demo.lea · édition en vigueur vérifiée (exemple)".format(clock.date(5, 2).isoformat())
    for t in tests.values():
        if t["review"] == "to_verify":  # the team confirmed the standards before approving (testing/review.py)
            conn.execute("UPDATE testing_tests SET review = 'verified', review_checked = ? WHERE id = ?", (checked, t["id"]))
            conn.execute("INSERT INTO testing_history (test_row_id, user_id, field, old_value, new_value, at) "
                         "VALUES (?, ?, 'revue de la norme', 'À vérifier', ?, ?)", (t["id"], lea, "Confirmée : " + checked, clock.iso(5, 2)))
        if t["status"] != "Approved":
            conn.execute("UPDATE testing_tests SET status = 'Approved', updated_by = ?, updated_at = ? WHERE id = ?", (lea, clock.iso(12, 2), t["id"]))
            conn.execute("INSERT INTO testing_history (test_row_id, user_id, field, old_value, new_value, at) VALUES (?, ?, 'status', ?, 'Approved', ?)",
                         (t["id"], lea, t["status"], clock.iso(12, 2)))
    locations = {r["code"] for r in conn.execute("SELECT code FROM testing_lists WHERE kind = 'location' AND active = 1")}
    made = 0
    for title, location, names, status, sent, results in L.PLANS:
        chosen = [tests[n] for n in names if n in tests]
        if not chosen or location not in locations:
            continue
        made += 1
        code = "TP-ROVER-{}".format(made)  # never counted by the TP-001, TP-002… of the teams (plans.api_create)
        while conn.execute("SELECT 1 FROM testing_plans WHERE code = ?", (code,)).fetchone():
            code += "B"
        created = clock.iso(sent - 1, 1)
        plan_id = conn.execute(
            "INSERT INTO testing_plans (project_id, code, title, location, tests, purpose, status, created_by, created_at, updated_by, "
            "updated_at, sent_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (pid, code, title, location, json.dumps([t["test_id"] for t in chosen]),
             "Plan d'essais de l'exemple Rover : les essais du Test Plan de validation, regroupés par lieu.", status, lea, created, lea,
             clock.iso(results or sent, 3), clock.iso(sent, 2))).lastrowid
        if results:
            saved = getattr(ctx, "upload", None)
            ctx.upload = upload(_pdf(code, title, chosen, clock, results), "{}_resultats.pdf".format(code))
            try:
                stored = uploads.store_pdf(ctx, pid, "testing_plan", 20 * 1048576)
            finally:
                ctx.upload = saved
            conn.execute("UPDATE testing_plans SET results_id = ?, results_name = ? WHERE id = ?", (stored["id"], stored["original_name"], plan_id))
            if status == "closed":
                conn.execute("UPDATE testing_plans SET closed_at = ?, closed_by = ? WHERE id = ?", (clock.iso(results, 4), people.get(L.LEAD), plan_id))
    return {"tests_approved": len(tests), "test_plans": made}


# --------------------------------------------------------------------------
# Exploration
# --------------------------------------------------------------------------
def plan(ctx, pid, people, clock):
    from modules.exploration import plan as P, reference
    conn = ctx.conn
    owners = [people[u] for u in L.TEAM if u in people]
    tasks = reference.build(L.WEEKS, owners, first="ROV0")
    have = {r["code"] for r in conn.execute("SELECT code FROM exploration_tasks WHERE project_id = ?", (pid,))}
    if have & ({t["code"] for t in tasks} | {"ROV0"}):
        return {"plan_tasks": 0}  # codes already taken by a plan the team made: never touched
    pos = (conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM exploration_tasks WHERE project_id = ?", (pid,)).fetchone()[0])
    if not conn.execute("SELECT 1 FROM exploration_plans WHERE project_id = ?", (pid,)).fetchone():
        P.set_start(conn, pid, clock.start)
    P.insert(ctx, pid, {"code": "ROV0", "phase": "Rover", "title": "Rover — lancement du projet (exemple)", "description":
                        "Le plan de référence du PDP appliqué au Rover : 15 semaines, 4 étudiants, deux pistes par phase.",
                        "owner_id": people.get(L.LEAD), "duration_weeks": 0, "start_date": clock.start.isoformat(), "predecessors": "",
                        "status": "done", "progress": 100, "note": ""}, pos)
    for i, t in enumerate(tasks):
        status, progress = L.PLAN_OPEN.get(t["code"], ("done", 100))
        P.insert(ctx, pid, dict(t, phase="Rover · " + t["phase"], start_date=clock.start.isoformat(), status=status, progress=progress,
                                note=""), pos + 1 + i)  # « not before » the Rover's start: the plan of DEMO starts later
    return {"plan_tasks": len(tasks) + 1}


def arrange(conn, pid):
    """0.60.55 (D-O-064): the Rover is the demo -- its plan first and the plan starts with it; the guided tour keeps its own
    dates (its first milestone gets the old start as « not before »). Returns True when something moved."""
    from modules.exploration import plan as P
    rover = conn.execute("SELECT start_date FROM exploration_tasks WHERE project_id = ? AND code = 'ROV0'", (pid,)).fetchone()
    if rover is None or not rover["start_date"]:
        return False
    start = P.plan_start(conn, pid)
    if start is not None:
        conn.execute("UPDATE exploration_tasks SET start_date = ? WHERE project_id = ? AND code = 'J0' AND start_date IS NULL",
                     (start.isoformat(), pid))
    P.set_start(conn, pid, dt.date.fromisoformat(rover["start_date"][:10]))
    rows = conn.execute("SELECT id, phase FROM exploration_tasks WHERE project_id = ? ORDER BY position, id", (pid,)).fetchall()
    ordered = [r for r in rows if r["phase"].startswith("Rover")] + [r for r in rows if not r["phase"].startswith("Rover")]
    conn.executemany("UPDATE exploration_tasks SET position = ? WHERE id = ?", [(i, r["id"]) for i, r in enumerate(ordered)])
    return True


# --------------------------------------------------------------------------
# Timesheet
# --------------------------------------------------------------------------
def hours(conn, pid, people, clock, approver):
    weeks, entries = {}, 0
    now = db.utc_now()
    for who, first, last, items in L.HOURS:
        uid = people.get(who)
        if uid is None:
            continue
        for week in range(first, last + 1):
            monday = clock.date(week)
            key = (uid, monday.isoformat())
            if key not in weeks:
                status = "approved" if week <= L.APPROVED_UNTIL else "submitted" if week < L.NOW_WEEK else "draft"
                row = conn.execute("SELECT id FROM timesheet_weeks WHERE user_id = ? AND week_start = ?", key).fetchone()
                weeks[key] = row["id"] if row else conn.execute(
                    "INSERT INTO timesheet_weeks (user_id, week_start, status, submitted_at, decided_by, decided_at, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (uid, monday.isoformat(), status, clock.iso(week, 4, 17) if status != "draft" else None,
                     approver if status == "approved" else None, clock.iso(week + 1, 0, 9) if status == "approved" else None,
                     clock.iso(week, 0, 9), now)).lastrowid
            for code, h, day, what in items:
                day_date = monday + dt.timedelta(days=day)
                if day_date > clock.today:
                    continue
                conn.execute("INSERT INTO timesheet_entries (week_id, project_id, work_date, task_key, hours, description, created_at, updated_at) "
                             "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (weeks[key], pid, day_date.isoformat(), code, h, what, clock.iso(week, day, 17), now))
                entries += 1
    return {"time_weeks": len(weeks), "time_entries": entries}


# --------------------------------------------------------------------------
# Diamond
# --------------------------------------------------------------------------
def diamond(conn, pid, raw, people, clock):
    d = raw.get("diamond") or {}
    today = clock.today.isoformat()
    done = 0
    for r in d.get("risks") or []:
        if r.get("owner") in people:
            status = "closed" if (r.get("due") or "9") < today else "in_progress"
            done += conn.execute("UPDATE diamond_risks SET owner_id = ?, due_date = ?, status = ? WHERE project_id = ? AND title = ?",
                                 (people[r["owner"]], r.get("due") or "", status, pid, r["title"])).rowcount
    for r in d.get("dfmea") or []:
        if r.get("owner") in people and r.get("failure_mode"):
            status = "done" if (r.get("due") or "9") < today else "in_progress"
            done += conn.execute("UPDATE diamond_dfmea SET action_owner_id = ?, action_due = ?, action_status = ? WHERE project_id = ? "
                                 "AND failure_mode = ? AND action_owner_id IS NULL",
                                 (people[r["owner"]], r.get("due") or None, status, pid, r["failure_mode"])).rowcount
    return {"diamond_owners": done}
