"""The Rover in DEMO, a project in motion (0.60.54, D-O-063): demo_example.py loads the content of rover.json (wiki,
requirements, tests, Diamond, backlog); this module adds what a real team leaves behind after 15 weeks, so a student sees
every module filled with concrete examples:

  team       four inactive accounts, demo.nina, demo.lea, demo.hugo, demo.alexis (« Nina (exemple) »…): they carry the
             tickets, the hours and the actions; nobody can sign in with them (is_active = 0, unusable password) and the
             « demo. » prefix keeps them apart from real people and from the example team of --exemple (EQP);
  Agile      seven two-week sprints (the last one active), assignees, statuses, dates, history, comments, links between
             tickets and to the requirements, released MVP versions;
  Change     two problem reports derived into ECNs, with their fields, affected items and ECN tasks;
  Goldmine   where each requirement and need stands, and Q&R with the client (the teacher), one still open;
  Testing    the Rover's tests approved, three test plans (closed with its results PDF, results received, sent);
  Exploration the reference plan of the PDP for the Rover, beside the guided tour, done up to the validation;
  Timesheet  the weekly hours of the four students on the PDP codes, approved up to week 13;
  Diamond    owners, due dates and status of the risks and DFMEA actions.

The project starts 14 weeks before the Monday of the day it is loaded: it is always at week 15 of 15. Applied once per
installation (journal « demo_life_loaded »), on a new DEMO as on one loaded by an older version. Content in
demo_life_data.py.
"""
import datetime as dt
import json
import secrets
import types

from core import audit, auth, db

from . import demo_life_data as L
from .demo_example import DONE, FILE
from .headlamp import project_id

LIFE_DONE = "demo_life_loaded"
PREFIX = "demo."


def _stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%S+00:00")


class Clock:
    """Week 1 starts 14 weeks before the Monday of today."""

    def __init__(self, today=None):
        self.today = today or dt.date.today()
        self.start = self.today - dt.timedelta(days=self.today.weekday(), weeks=L.NOW_WEEK - 1)

    def date(self, week, day=0):
        return self.start + dt.timedelta(weeks=week - 1, days=day)

    def at(self, week, day=0, hour=10):
        d = self.date(week, day)
        moment = dt.datetime(d.year, d.month, d.day, hour)
        now = dt.datetime.now()
        return min(moment, now)

    def iso(self, week, day=0, hour=10):
        return _stamp(self.at(week, day, hour))


def ensure_life(ctx, today=None):
    """Once: the Rover's project in motion. Returns the counts, or None (no DEMO, Rover not loaded, already done)."""
    conn = ctx.conn
    pid = project_id(conn)
    if pid is None or not FILE.exists():
        return None
    logged = lambda action: conn.execute("SELECT 1 FROM audit_log WHERE action = ? AND object_id = ?", (action, str(pid))).fetchone()  # noqa: E731
    if not logged(DONE) or logged(LIFE_DONE):
        return None
    raw = json.loads(FILE.read_text("utf-8"))
    clock = Clock(today)
    people = accounts(conn, pid, raw.get("team") or [], clock)
    counts = {"accounts": len(people)}
    from . import demo_life_more as M
    counts.update(agile(ctx, pid, raw, people, clock))
    counts.update(M.changes(ctx, pid, people, clock, _issues(conn, pid, raw)))
    counts.update(M.goldmine(conn, pid, people, clock))
    counts.update(M.testing(ctx, pid, people, clock))
    counts.update(M.plan(ctx, pid, people, clock))
    M.arrange(conn, pid)
    counts.update(M.hours(conn, pid, people, clock, ctx.user["id"]))
    counts.update(M.diamond(conn, pid, raw, people, clock))
    audit.log_action(conn, ctx.user["id"], LIFE_DONE, "project", pid, dict(counts, start=clock.start.isoformat()), None)
    audit.log_action(conn, ctx.user["id"], ARRANGED, "project", pid, {"moved": True}, None)
    return counts


ARRANGED = "demo_plan_arranged"


def ensure_arranged(ctx):
    """0.60.55 (D-O-064): a DEMO filled by 0.60.54 gets the Rover's plan first, once."""
    conn = ctx.conn
    pid = project_id(conn)
    if pid is None:
        return None
    logged = lambda action: conn.execute("SELECT 1 FROM audit_log WHERE action = ? AND object_id = ?", (action, str(pid))).fetchone()  # noqa: E731
    if not logged(LIFE_DONE) or logged(ARRANGED):
        return None
    from . import demo_life_more as M
    moved = M.arrange(conn, pid)
    audit.log_action(conn, ctx.user["id"], ARRANGED, "project", pid, {"moved": moved}, None)
    return moved


def accounts(conn, pid, team, clock):
    """{username of rover.json: id} of the inactive example accounts, created once, editors of DEMO."""
    from core import prefs
    out = {}
    for m in team:
        name = PREFIX + m["username"]
        row = conn.execute("SELECT id FROM users WHERE username = ?", (name,)).fetchone()
        if row is None:
            uid = conn.execute(
                "INSERT INTO users (username, display_name, password_hash, is_admin, is_active, must_change_password, created_at, "
                "title, study_profile) VALUES (?, ?, ?, 0, 0, 1, ?, ?, ?)",
                (name, "{} (exemple)".format(m["display_name"]), auth.hash_password(secrets.token_urlsafe(32)), clock.iso(1),
                 m.get("title", ""), m.get("study_profile", ""))).lastrowid
        else:
            uid = row["id"]
        conn.execute("INSERT OR IGNORE INTO memberships (user_id, project_id, role) VALUES (?, ?, 'editor')", (uid, pid))
        prefs.ensure_initials(conn, uid)
        out[m["username"]] = uid
    return out


def _issues(conn, pid, raw):
    """{ref of the backlog of rover.json: row} of the Rover's tickets in DEMO, found by their title."""
    refs = {b["title"]: b["ref"] for b in raw.get("backlog") or []}
    out = {}
    for r in conn.execute("SELECT i.*, t.workflow_id FROM agile_issues i JOIN agile_issue_types t ON t.id = i.type_id "
                          "WHERE i.project_id = ? AND t.bucket = 'agile' ORDER BY i.number", (pid,)):
        if r["title"] in refs and refs[r["title"]] not in out:
            out[refs[r["title"]]] = dict(r)
    return out


def status_id(conn, workflow_id, name):
    row = conn.execute("SELECT id, category FROM agile_statuses WHERE workflow_id = ? AND name = ?", (workflow_id, name)).fetchone()
    return (row["id"], row["category"]) if row else (None, None)


def move(conn, issue, path, who, moments):
    """Walk a ticket through the statuses of `path`, one history line per step at `moments`."""
    old = conn.execute("SELECT name FROM agile_statuses WHERE id = ?", (issue["status_id"],)).fetchone()
    old = old["name"] if old else None
    for name, moment in zip(path, moments):
        sid, category = status_id(conn, issue["workflow_id"], name)
        if sid is None or name == old:
            continue
        conn.execute("UPDATE agile_issues SET status_id = ?, updated_at = ?, resolved_at = ? WHERE id = ?",
                     (sid, moment, moment if category == "done" else None, issue["id"]))
        conn.execute("INSERT INTO agile_history (issue_id, user_id, ts, field, old_value, new_value) VALUES (?, ?, ?, 'status', ?, ?)",
                     (issue["id"], who, moment, old, name))
        old = name


def agile(ctx, pid, raw, people, clock):
    conn = ctx.conn
    issues = _issues(conn, pid, raw)
    backlog = {b["ref"]: b for b in raw.get("backlog") or []}
    lead = people.get(L.LEAD)
    sprints = 0
    busy = conn.execute("SELECT 1 FROM agile_sprints WHERE project_id = ? AND state = 'active'", (pid,)).fetchone()
    for i, (name, goal, first, last, refs) in enumerate(L.SPRINTS):
        last_one = i == len(L.SPRINTS) - 1
        state = ("future" if busy else "active") if last_one else "closed"  # one active sprint: a DEMO user's own stays
        sid = conn.execute("INSERT INTO agile_sprints (project_id, name, goal, state, start_date, end_date, created_at) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?)", (pid, "Rover · " + name, goal, state,
                                                             clock.date(first).isoformat(), clock.date(last, 4).isoformat(),
                                                             clock.iso(first, 0, 9))).lastrowid
        sprints += 1
        for ref in refs:
            issue = issues.get(ref)
            if issue is None:
                continue
            who = people.get(backlog[ref].get("assignee")) or lead
            created = clock.iso(first, 0, 9) if ref.startswith("B") else clock.iso(1, 0, 9)
            conn.execute("UPDATE agile_issues SET sprint_id = ?, assignee_id = ?, reporter_id = ?, created_at = ? WHERE id = ?",
                         (sid, who, lead, created, issue["id"]))
            target = L.OPEN.get(ref, "Done")
            path = {"In Progress": ["In Progress"], "In Review": ["In Progress", "In Review"]}.get(target, ["In Progress", "In Review", "Done"])
            moments = [clock.iso(first, 1, 9), clock.iso(last, 2, 15), clock.iso(last, 3, 16)]
            move(conn, issue, path, who, moments)
    for ref, (_name, week, released) in zip(("E0", "E1", "E2", "E3"), L.VERSIONS):
        issue = issues.get(ref)
        if issue is not None:
            conn.execute("UPDATE agile_issues SET assignee_id = ?, reporter_id = ?, created_at = ? WHERE id = ?",
                         (lead, lead, clock.iso(1, 0, 9), issue["id"]))
            first = {"E0": 1, "E1": 3, "E2": 7, "E3": 13}[ref]
            path = ["In Progress"] if ref in L.EPICS_OPEN else ["In Progress", "Done"]
            move(conn, issue, path, lead, [clock.iso(first, 0, 10), clock.iso(week, 4, 16)])
    for name, week, released in L.VERSIONS:
        conn.execute("UPDATE agile_versions SET release_date = ?, is_released = ? WHERE project_id = ? AND name = ?",
                     (clock.date(week, 4).isoformat(), int(released), pid, name))
    comments = _comments(conn, issues, people, clock)
    links = _links(conn, pid, issues, people, clock)
    return {"sprints": sprints, "tickets": len(issues), "comments": comments, "links": links}


def _comments(conn, issues, people, clock):
    last, made = {}, 0
    for ref, who, week, day, text in L.COMMENTS:
        issue = issues.get(ref)
        if issue is None:
            continue
        reply = text.startswith("↳ ")
        cid = conn.execute("INSERT INTO agile_comments (issue_id, author_id, body, created_at, parent_comment_id) VALUES (?, ?, ?, ?, ?)",
                           (issue["id"], people.get(who), text[2:] if reply else text, clock.iso(week, day, 11 + made % 6),
                            last.get(ref) if reply else None)).lastrowid
        last[ref] = cid
        made += 1
    return made


def _links(conn, pid, issues, people, clock):
    reqs = {r["external_id"]: r["issue_id"] for r in conn.execute(
        "SELECT r.external_id, r.issue_id FROM agile_requirements r JOIN agile_issues i ON i.id = r.issue_id WHERE i.project_id = ?", (pid,))}
    made = 0
    for src, dst, kind in L.LINKS:
        a = issues.get(src)
        b = reqs.get(dst) if dst.startswith("REQ-") else (issues.get(dst) or {}).get("id")
        if a is None or b is None:
            continue
        made += conn.execute("INSERT OR IGNORE INTO agile_links (source_id, target_id, link_type, created_by, created_at) "
                             "VALUES (?, ?, ?, ?, ?)", (a["id"], b, kind, a["assignee_id"] or people.get(L.LEAD),
                                                        clock.iso(5, 0))).rowcount
    return made


def upload(data, filename):
    """What a module handler reads as ctx.upload (core/uploads.py)."""
    return types.SimpleNamespace(data=data, filename=filename)


def utc_now():
    return db.utc_now()
