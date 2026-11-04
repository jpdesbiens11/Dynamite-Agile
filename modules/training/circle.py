"""Training tests with circle-back (0.50.10, D-B-128): the employee takes the whole test and gets his mark at the end.
At or above the pass mark (80 % by default) the test is passed. Below it, the missed questions -- and only them -- come
back, round after round, until each one has been answered right: the item is then passed too (learning guaranteed).

- The circle-back state lives on the item (training_items.quiz_pending, JSON): the questions still to redo, the round,
  the mark of the full test and a signature of the quiz text -- a quiz edited by an administrator meanwhile resets it.
- During circle-back the right answers and explanations of a missed question are never sent: only « missed ».
  They are revealed once the question is answered right (and for every question once the test is passed).
- A passed test moves the item to « Completed » (green), whatever the workflow buttons: completing a topic that has a
  test requires the test passed (plan.api_update). « Achieved » stays the manager's (evaluation written).
"""
import hashlib
import json

from core import audit, db, validate
from core.errors import ApiError
from core.objectives import relation

from . import quiz

OPEN = ("todo", "in_progress", "completed")


def _sig(text):
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:12]


def pending(row, parsed=None):
    """Circle-back state of an item ({"q": [indexes], "round", "first", "sig"}) or None when there is none / stale."""
    try:
        state = json.loads(row["quiz_pending"] or "")
    except (ValueError, TypeError, IndexError, KeyError):
        return None
    if not isinstance(state, dict) or not state.get("q") or state.get("sig") != _sig(row["quiz_md"]):
        return None
    if parsed is not None and any(not isinstance(i, int) or not 0 <= i < len(parsed["questions"]) for i in state["q"]):
        return None
    return state


def _quiz_of(row):
    if not (row["quiz_md"] or "").strip():
        raise ApiError(404, "Ce topic n'a pas encore de test. Correctif : un administrateur l'ajoute dans Training → Topics.")
    return quiz.checked(row["quiz_md"])


def _complete(ctx, item_id, status, now):
    """Passed test -> the item is Completed (green); an item already Completed is left as it is."""
    if status == "in_progress":
        ctx.conn.execute("UPDATE training_items SET status = 'completed', completed_at = ?, updated_at = ? WHERE id = ?",
                         (now, now, item_id))
        audit.log_action(ctx.conn, ctx.user["id"], "training_item_updated", "training", item_id,
                         {"as": "employee", "status": "completed", "by": "quiz_passed"}, ctx.ip)
        return "completed"
    return status


def _mask(review, keep_answers):
    """Hide the right answers and the explanation of the questions still missed."""
    return [rv if (rv["ok"] or keep_answers) else {"index": rv["index"], "ok": False, "chosen": rv["chosen"]} for rv in review]


def api_quiz(ctx, item_of):
    row = item_of(ctx.conn, validate.int_param(ctx.params, "iid"))
    relation(ctx.conn, ctx.user, row["user_id"])
    parsed = _quiz_of(row)
    state = pending(row, parsed)
    out = quiz.public(parsed, state["q"] if state else None)
    out["circle_back"] = ({"round": state["round"], "first": state["first"], "remaining": len(state["q"])} if state else None)
    out["passed"] = bool(row["quiz_passed"])
    out["item"] = {k: row[k] for k in ("id", "code", "title", "reference", "ref_label", "status")}
    return out


def api_answer(ctx, item_of):
    row = item_of(ctx.conn, validate.int_param(ctx.params, "iid"))
    if relation(ctx.conn, ctx.user, row["user_id"]) != "self":
        raise ApiError(403, "Le test est passé par l'employé lui-même.")
    if row["status"] not in OPEN:
        raise ApiError(409, "Item déjà « Achieved » : le test n'est plus à passer. Correctif : votre gestionnaire peut le "
                            "rouvrir.")
    parsed = _quiz_of(row)
    answers = ctx.body.get("answers")
    status = row["status"]
    if status == "todo":  # answering the test starts the item
        status = "in_progress"
        ctx.conn.execute("UPDATE training_items SET status = 'in_progress', updated_at = ? WHERE id = ?", (db.utc_now(), row["id"]))
        audit.log_action(ctx.conn, ctx.user["id"], "training_item_updated", "training", row["id"],
                         {"as": "employee", "status": "in_progress", "by": "quiz_started"}, ctx.ip)
    state = pending(row, parsed)
    now = db.utc_now()
    result = quiz.grade(parsed, answers, state["q"] if state else None)
    rnd = state["round"] if state else 0
    ctx.conn.execute("INSERT INTO training_attempts (item_id, score, right_count, total, answers, round, created_at) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)", (row["id"], result["score"], result["right"], result["total"],
                                                     json.dumps(answers), rnd, now))
    missed = [rv["index"] for rv in result["review"] if not rv["ok"]]
    if state:  # circle-back round: only the questions still missed come back
        first, done = state["first"], not missed
    else:
        first, done = result["score"], result["passed"]
    passed = bool(row["quiz_passed"]) or done
    new_state = "" if done else json.dumps({"q": missed, "round": rnd + 1, "first": first, "sig": _sig(row["quiz_md"])})
    best = max(first, row["quiz_score"] or 0) if not state else (row["quiz_score"] or 0)
    ctx.conn.execute("UPDATE training_items SET quiz_score = ?, quiz_passed = ?, quiz_pending = ?, quiz_attempts = "
                     "quiz_attempts + ?, updated_at = ? WHERE id = ?",
                     (best, 1 if passed else 0, new_state, 0 if state else 1, now, row["id"]))
    status = _complete(ctx, row["id"], status, now) if done else status
    audit.log_action(ctx.conn, ctx.user["id"], "training_quiz_taken", "training", row["id"],
                     {"round": rnd, "score": result["score"], "missed": len(missed), "passed": done}, ctx.ip)
    return {"mode": "retry" if state else "full", "round": rnd, "score": result["score"], "right": result["right"],
            "total": result["total"], "first": first, "pass": parsed["pass"], "passed": done, "status": status,
            "remaining": missed, "next_round": None if done else rnd + 1, "review": _mask(result["review"], done)}
