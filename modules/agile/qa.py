"""Goldmine question & answer register (D-B-037).

One register per project, one entry per question, tied to a requirement:
- direction "team": question from the team to the client (Qteam-003), answered
  by the client (Acust) -- typed by a team member from an e-mail, or loaded
  from the client package (qa_xlsx.py);
- direction "cust": question or concern from the client (Qcust-004),
  answered by the team (Ateam).
Status: open -> answered -> closed, or cancelled; from any state a question
can be reopened, closed or cancelled, and a reopening can be undone (back to
« answered ») -- D-B-044. Who waits:
team/open and cust/answered wait for the client; cust/open and team/answered
wait for the team. Every step is an event with a stamp « DDMMYYYY-INI »
(06092026-JDE): nothing is deleted, a new answer supersedes the previous
one in the event history (full traceability).
A requirement leaves « Customer Clarification » only when all its questions
are closed (clarification_guard).
"""
import datetime as dt
import unicodedata

from core import db, validate
from core.errors import ApiError

from . import common as c

STAMP_DATE = "%d%m%Y"  # 06092026 = 6 September 2026 (JJMMAAAA); one place to change
DIRECTIONS = {"team": ("Qteam", "Acust"), "cust": ("Qcust", "Ateam")}
STATUSES = {"open": "Open", "answered": "Answered", "closed": "Closed", "cancelled": "Cancelled"}  # D-B-085
DONE = ("closed", "cancelled")
EVENT_KINDS = {"question": "Question", "answer": "Réponse", "close": "Fermeture", "reopen": "Réouverture",
               "cancel": "Annulation", "revert": "Réouverture annulée", "comment": "Commentaire"}
CLIENT_DEFAULT = "Client"
CLARIFICATION = "Customer Clarification"
MAX_TEXT = 4000


# --------------------------------------------------------------------------
# Stamps
# --------------------------------------------------------------------------
def _ascii(text):
    return "".join(ch for ch in unicodedata.normalize("NFKD", text or "") if ch.isascii() and ch.isalpha())


def initials_of(name, fallback="XXX"):
    """JDE for « Jean-Philippe Desbiens » (first letter + two letters of the last word)."""
    words = [w for w in (name or "").replace("-", " ").split() if _ascii(w)]
    if len(words) >= 2:
        value = _ascii(words[0])[:1] + _ascii(words[-1])[:2]
    elif words:
        value = _ascii(words[0])[:3]
    else:
        value = fallback
    return value.upper() or fallback


def user_initials(conn, user_id):
    row = conn.execute("SELECT display_name, username FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        return "XXX"
    from core import prefs
    chosen = prefs.get(conn, user_id).get("initials")
    return chosen or initials_of(row["display_name"] or row["username"])


def stamp(initials, when=None):
    return "{}-{}".format((when or dt.datetime.now()).strftime(STAMP_DATE), initials)


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------
def ref(direction, seq):
    return "{}-{:03d}".format(DIRECTIONS[direction][0], seq)


def waiting_on(row):
    if row["status"] in DONE:
        return ""
    if (row["direction"] == "team") == (row["status"] == "open"):
        return "client"
    return "team"


SELECT = (
    "SELECT q.*, i.project_id, i.number, i.title AS req_title, i.assignee_id AS req_assignee, s.name AS req_status, "
    "r.statement AS req_statement, r.external_id AS req_external, r.revision AS req_current_revision, "
    "o.display_name AS owner_name, ua.display_name AS asked_user, ub.display_name AS answered_user "
    "FROM goldmine_qa q JOIN agile_issues i ON i.id = q.issue_id JOIN agile_statuses s ON s.id = i.status_id "
    "LEFT JOIN agile_requirements r ON r.issue_id = i.id LEFT JOIN users o ON o.id = q.owner_id "
    "LEFT JOIN users ua ON ua.id = q.asked_by LEFT JOIN users ub ON ub.id = q.answered_by ")


def decorate(row, key):
    item = dict(row)
    item["ref"] = ref(item["direction"], item["seq"])
    item["req_key"] = "{}-{}".format(key, item["number"])
    item["full_ref"] = "{} · {}".format(item["req_key"], item["ref"])
    item["ask_label"], item["answer_label"] = DIRECTIONS[item["direction"]]
    item["status_label"] = STATUSES[item["status"]]
    item["waiting_on"] = waiting_on(item)
    item["asked_who"] = item["asked_name"] or item["asked_user"] or ""
    item["answered_who"] = item["answered_name"] or item["answered_user"] or ""
    return item


def list_project(conn, project_id, issue_id=None):
    key = c.project_key(conn, project_id)
    sql = SELECT + "WHERE i.project_id = ?"
    params = [project_id]
    if issue_id is not None:
        sql += " AND q.issue_id = ?"
        params.append(issue_id)
    rows = conn.execute(sql + " ORDER BY q.status IN ('closed', 'cancelled'), q.blocking DESC, q.asked_at, q.id", params).fetchall()
    return [decorate(r, key) for r in rows]


def events(conn, qa_ids):
    if not qa_ids:
        return {}
    out = {}
    rows = conn.execute("SELECT e.*, u.display_name AS user_name FROM goldmine_qa_events e LEFT JOIN users u ON u.id = e.user_id "
                        "WHERE e.qa_id IN ({}) ORDER BY e.id".format(",".join("?" * len(qa_ids))), qa_ids).fetchall()
    for r in db.rows(rows):
        out.setdefault(r["qa_id"], []).append(r)
    return out


def counts(items, user_id):
    return {"team": sum(1 for q in items if q["waiting_on"] == "team"),
            "client": sum(1 for q in items if q["waiting_on"] == "client"),
            "mine": sum(1 for q in items if q["waiting_on"] == "team" and (q["owner_id"] or q["req_assignee"]) == user_id),
            "blocking": sum(1 for q in items if q["blocking"] and q["status"] not in DONE),
            "closed": sum(1 for q in items if q["status"] == "closed"),
            "cancelled": sum(1 for q in items if q["status"] == "cancelled"), "all": len(items)}


# --------------------------------------------------------------------------
# Writing (shared with the Excel import)
# --------------------------------------------------------------------------
def _event(conn, qa_id, kind, text, user_id, name, when, stamp_text):
    conn.execute("INSERT INTO goldmine_qa_events (qa_id, kind, text, user_id, name, at, stamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (qa_id, kind, text, user_id, name, when, stamp_text))


def create(conn, issue, direction, question, user_id, name="", owner_id=None, due_date=None, blocking=False, when=None):
    project_id = issue["project_id"]
    seq = conn.execute("SELECT COALESCE(MAX(q.seq), 0) + 1 FROM goldmine_qa q JOIN agile_issues i ON i.id = q.issue_id "
                       "WHERE i.project_id = ? AND q.direction = ?", (project_id, direction)).fetchone()[0]
    moment = when or dt.datetime.now()
    at = moment.strftime("%Y-%m-%dT%H:%M:%S")
    who = initials_of(name) if name else user_initials(conn, user_id)
    st = stamp(who, moment)
    rev = conn.execute("SELECT revision FROM agile_requirements WHERE issue_id = ?", (issue["id"],)).fetchone()
    qa_id = conn.execute(
        "INSERT INTO goldmine_qa (issue_id, seq, direction, question, asked_by, asked_name, asked_at, asked_stamp, status, "
        "owner_id, due_date, blocking, req_revision, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?)",
        (issue["id"], seq, direction, question, user_id, name, at, st, owner_id, due_date, int(bool(blocking)),
         rev["revision"] if rev else "", db.utc_now())).lastrowid
    _event(conn, qa_id, "question", question, user_id, name, at, st)
    return qa_id


def answer(conn, qa, text, user_id, name="", when=None):
    moment = when or dt.datetime.now()
    at = moment.strftime("%Y-%m-%dT%H:%M:%S")
    st = stamp(initials_of(name) if name else user_initials(conn, user_id), moment)
    conn.execute("UPDATE goldmine_qa SET answer = ?, answered_by = ?, answered_name = ?, answered_at = ?, answered_stamp = ?, "
                 "status = 'answered', closed_stamp = '', updated_at = ? WHERE id = ?",
                 (text, user_id, name, at, st, db.utc_now(), qa["id"]))
    _event(conn, qa["id"], "answer", text, user_id, name, at, st)
    return st


def set_status(conn, qa, status, user_id, name="", note="", when=None):
    moment = when or dt.datetime.now()
    at = moment.strftime("%Y-%m-%dT%H:%M:%S")
    st = stamp(initials_of(name) if name else user_initials(conn, user_id), moment)
    conn.execute("UPDATE goldmine_qa SET status = ?, closed_stamp = ?, updated_at = ? WHERE id = ?",
                 (status, st if status in DONE else "", db.utc_now(), qa["id"]))
    kind = {"closed": "close", "open": "reopen", "cancelled": "cancel", "answered": "revert"}[status]
    _event(conn, qa["id"], kind, note, user_id, name, at, st)
    return st


def comment(conn, qa, text, user_id, name="", when=None):
    """A follow-up remark (client or team) kept in the signed history, without changing the answer."""
    moment = when or dt.datetime.now()
    at = moment.strftime("%Y-%m-%dT%H:%M:%S")
    st = stamp(initials_of(name) if name else user_initials(conn, user_id), moment)
    conn.execute("UPDATE goldmine_qa SET updated_at = ? WHERE id = ?", (db.utc_now(), qa["id"]))
    _event(conn, qa["id"], "comment", text, user_id, name, at, st)
    return st


def clarification_guard(conn, issue_row, target_name):
    """Leaving « Customer Clarification » needs every question of the requirement closed."""
    current = conn.execute("SELECT name FROM agile_statuses WHERE id = ?", (issue_row["status_id"],)).fetchone()
    if not current or current["name"] != CLARIFICATION or target_name == CLARIFICATION:
        return None
    left = conn.execute("SELECT COUNT(*) FROM goldmine_qa WHERE issue_id = ? AND status NOT IN ('closed', 'cancelled')",
                        (issue_row["id"],)).fetchone()[0]
    if not left:
        return None
    return ("Sortie de « Customer Clarification » impossible : {} question(s) encore ouverte(s) ou à fermer.".format(left),
            "Répondez puis fermez chaque question (Goldmine → Q&A), puis refaites la transition.")


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
def _text(body, name, required=True):
    value = str(body.get(name) or "").strip()
    if required and not value:
        raise ApiError(400, "Texte vide. Correctif : écrivez la {}.".format({"question": "question", "answer": "réponse"}.get(name, name)))
    if len(value) > MAX_TEXT:
        raise ApiError(400, "Texte de {} caractères. Correctif : {} au maximum.".format(len(value), MAX_TEXT))
    return value


def _get(ctx, project_id):
    qa_id = validate.int_param(ctx.params, "qid")
    row = ctx.conn.execute("SELECT q.*, i.project_id FROM goldmine_qa q JOIN agile_issues i ON i.id = q.issue_id "
                           "WHERE q.id = ? AND i.project_id = ?", (qa_id, project_id)).fetchone()
    if row is None:
        raise ApiError(404, "Question introuvable dans ce projet.")
    return row


def _one(ctx, project_id, qa_id):
    items = [q for q in list_project(ctx.conn, project_id) if q["id"] == qa_id]
    item = items[0]
    item["events"] = events(ctx.conn, [qa_id]).get(qa_id, [])
    return item


def api_list(ctx):
    project_id, role = c.access(ctx, "reader")
    issue_id = None
    if ctx.query.get("issue"):
        issue_id = c.get_issue(ctx.conn, project_id, int(ctx.query["issue"]))["id"]
    items = list_project(ctx.conn, project_id, issue_id)
    history = events(ctx.conn, [q["id"] for q in items])
    for q in items:
        q["events"] = history.get(q["id"], [])
    return {"items": items, "counts": counts(items, ctx.user["id"]), "members": c.members(ctx.conn, project_id),
            "can_edit": role in ("editor", "admin"), "statuses": STATUSES, "me": ctx.user["id"]}


def api_create(ctx):
    project_id, _role = c.access(ctx, "editor")
    issue = c.get_issue(ctx.conn, project_id, c.issue_number(ctx))
    direction = ctx.body.get("direction", "team")
    if direction not in DIRECTIONS:
        raise ApiError(400, "Sens « {} » inconnu. Correctif : team (question au client) ou cust (question du client).".format(direction))
    question = _text(ctx.body, "question")
    name = str(ctx.body.get("external_name") or "").strip()[:80] if direction == "cust" else ""
    if direction == "cust" and not name:
        name = CLIENT_DEFAULT
    owner = c.check_member(ctx.conn, project_id, c.opt_int(ctx.body, "owner_id")) or issue["assignee_id"]
    due = c.opt_date(ctx.body, "due_date")
    qa_id = create(ctx.conn, issue, direction, question, ctx.user["id"], name, owner, due, validate.boolean(ctx.body, "blocking", False))
    c.log(ctx, "goldmine_qa_create", "goldmine_qa", qa_id, {"issue": issue["id"], "direction": direction})
    return dict(_one(ctx, project_id, qa_id), mentions_notice=_mentions(ctx, project_id, issue, question, qa_id))


def api_answer(ctx):
    project_id, _role = c.access(ctx, "editor")
    qa = _get(ctx, project_id)
    if qa["status"] in DONE:
        raise ApiError(409, "Question {}. Correctif : rouvrez-la d'abord.".format(STATUSES[qa["status"]].lower()))
    text = _text(ctx.body, "answer")
    name = ""
    if qa["direction"] == "team":  # the client's answer, typed by a team member
        name = str(ctx.body.get("external_name") or "").strip()[:80] or CLIENT_DEFAULT
    answer(ctx.conn, qa, text, ctx.user["id"], name)
    c.log(ctx, "goldmine_qa_answer", "goldmine_qa", qa["id"], {"by_client": bool(name)})
    issue = ctx.conn.execute("SELECT * FROM agile_issues WHERE id = ?", (qa["issue_id"],)).fetchone()
    return dict(_one(ctx, project_id, qa["id"]), mentions_notice=_mentions(ctx, project_id, issue, text, qa["id"]))


def _mentions(ctx, project_id, issue, text, qa_id):
    """D-A-046: « @username » in a question or an answer opens the requirement's Q&A in Goldmine."""
    from core import mentions
    key = ctx.conn.execute("SELECT key FROM projects WHERE id = ?", (project_id,)).fetchone()["key"]
    return mentions.notify(ctx.conn, ctx.user, text, "qa", "#/goldmine/{}/issue/{}".format(key, issue["number"]),
                           "Q&A {}-{} · {}".format(key, issue["number"], issue["title"]), project_id,
                           "goldmine_qa:{}".format(qa_id))["notice"]


def api_status(ctx):
    project_id, _role = c.access(ctx, "editor")
    qa = _get(ctx, project_id)
    action = ctx.params.get("action")
    target = {"close": "closed", "reopen": "open", "cancel": "cancelled", "revert": "answered"}[action]
    if qa["status"] == target:
        raise ApiError(409, "Question déjà {}.".format(STATUSES[target].lower()))
    if action == "revert" and (qa["status"] != "open" or not qa["answer"]):
        raise ApiError(409, "Rien à annuler : seule une question rouverte qui a déjà une réponse revient à « Answered ».")
    note = str(ctx.body.get("note") or "").strip()[:MAX_TEXT]
    set_status(ctx.conn, qa, target, ctx.user["id"], note=note)
    c.log(ctx, "goldmine_qa_" + action, "goldmine_qa", qa["id"], None)
    return _one(ctx, project_id, qa["id"])


def api_update(ctx):
    project_id, _role = c.access(ctx, "editor")
    qa = _get(ctx, project_id)
    changes = {}
    if "owner_id" in ctx.body:
        changes["owner_id"] = c.check_member(ctx.conn, project_id, c.opt_int(ctx.body, "owner_id"))
    if "due_date" in ctx.body:
        changes["due_date"] = c.opt_date(ctx.body, "due_date")
    if "blocking" in ctx.body:
        changes["blocking"] = int(validate.boolean(ctx.body, "blocking"))
    if not changes:
        raise ApiError(400, "Aucune modification demandée.")
    ctx.conn.execute("UPDATE goldmine_qa SET {}, updated_at = ? WHERE id = ?".format(", ".join("{} = ?".format(k) for k in changes)),
                     list(changes.values()) + [db.utc_now(), qa["id"]])
    c.log(ctx, "goldmine_qa_update", "goldmine_qa", qa["id"], changes)
    return _one(ctx, project_id, qa["id"])


def dashboard_items(conn, user, projects):
    """Questions waiting for the team that are mine (owner, or the requirement's assignee)."""
    if not projects:
        return []
    rows = conn.execute(
        SELECT + "WHERE i.project_id IN ({}) AND ((q.direction = 'cust' AND q.status = 'open') OR "
        "(q.direction = 'team' AND q.status = 'answered')) AND COALESCE(q.owner_id, i.assignee_id) = ? "
        "ORDER BY q.blocking DESC, q.asked_at".format(",".join("?" * len(projects))), list(projects) + [user["id"]]).fetchall()
    out = []
    for r in rows:
        key = projects[r["project_id"]]
        q = decorate(r, key)
        out.append({"title": "{} · {}".format(q["full_ref"], q["question"][:100]),
                    "href": "#/goldmine/{}/qa/{}".format(key, q["id"]), "project": key,
                    "status": "Réponse client à fermer" if q["direction"] == "team" else "Question du client",
                    "late": bool(q["due_date"] and q["due_date"] < dt.date.today().isoformat()) or bool(q["blocking"]),
                    "due": q["due_date"], "meta": q["asked_stamp"]})
    return out
