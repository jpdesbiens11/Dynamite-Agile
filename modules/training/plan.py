"""Training (D-A-045): topics, individual training plans, workflow with different rights for the employee and his
manager, multiple-choice tests graded here.

Who: like « Mes objectifs », a plan is private to the employee and HIS manager (the approver chosen in Settings);
administrators manage the topics and the workflow, not the plans of others. « Achieved » is set by the manager only
after the employee passed the topic's test (when it has one) and the manager wrote his evaluation.
"""
import datetime as dt

from core import audit, db, permissions, validate
from core.errors import ApiError
from core.objectives import relation

from . import catalog, circle, quiz

TOPIC_FIELDS = {"title": 200, "content": 6000, "reference": 400, "ref_label": 200, "code": 20}


def _log(ctx, action, object_id, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "training", object_id, details, ctx.ip)


def _can_manage_topics(conn, user):
    if user["is_admin"]:
        return True
    pid = catalog.project_id(conn)
    return bool(pid and permissions.is_project_manager(conn, user, pid))


def _year(ctx):
    try:
        year = int(ctx.query.get("year") or dt.date.today().year)
    except ValueError:
        raise ApiError(400, "Année invalide. Correctif : un nombre, ex. 2026.")
    return year


# --------------------------------------------------------------------------
# Topics
# --------------------------------------------------------------------------
def _topic_public(row, full=False):
    t = dict(row)
    parsed, problems = quiz.parse(t.pop("quiz_md") or "") if (row["quiz_md"] or "").strip() else ({"questions": []}, [])
    t["quiz_questions"] = len(parsed["questions"])
    t["has_quiz"] = bool(parsed["questions"]) and not problems
    if full:
        t["quiz_md"] = row["quiz_md"]
    return t


def api_topics(ctx):
    manage = _can_manage_topics(ctx.conn, ctx.user)
    rows = ctx.conn.execute("SELECT * FROM training_topics WHERE project_id = ? {} ORDER BY position, id".format(
        "" if manage else "AND active = 1"), (catalog.project_id(ctx.conn),)).fetchall()
    return {"topics": [_topic_public(r, manage) for r in rows], "can_manage": manage,
            "example_quiz": catalog.EXAMPLE_QUIZ if manage else None}


def _topic_values(conn, body, current=None):
    out = {}
    for key, limit in TOPIC_FIELDS.items():
        if key in body or current is None:
            value = str(body.get(key, "") or "").strip()
            if key == "title" and not value:
                raise ApiError(400, "Titre obligatoire. Correctif : nommez le topic (ex. « Analyse fonctionnelle : arbre des fonctions »).")
            if len(value) > limit:
                raise ApiError(400, "Champ « {} » : {} caractères au maximum (reçu : {}).".format(key, limit, len(value)))
            out[key] = value
    if "parent_id" in body:
        parent = body.get("parent_id")
        if parent in (None, "", 0):
            out["parent_id"] = None
        else:
            prow = conn.execute("SELECT id, parent_id FROM training_topics WHERE id = ?", (parent,)).fetchone()
            if prow is None or (current and prow["id"] == current["id"]) or (prow["parent_id"] is not None):
                raise ApiError(400, "Topic parent invalide. Correctif : choisissez un topic principal (un seul niveau de "
                                    "sous-topics), jamais le topic lui-même.")
            out["parent_id"] = prow["id"]
    if "quiz_md" in body:
        text = str(body.get("quiz_md") or "")
        if text.strip():
            quiz.checked(text)  # every problem at once
        out["quiz_md"] = text
    if "active" in body:
        out["active"] = 1 if body.get("active") else 0
    return out


def api_create_topic(ctx):
    if not _can_manage_topics(ctx.conn, ctx.user):
        raise ApiError(403, "Réservé aux administrateurs et aux Admin du Space TRAINING.")
    values = _topic_values(ctx.conn, ctx.body)
    now = db.utc_now()
    pos = ctx.conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM training_topics").fetchone()[0]
    values.update(project_id=catalog.project_id(ctx.conn), position=pos, created_at=now, updated_at=now)
    tid = ctx.conn.execute("INSERT INTO training_topics ({}) VALUES ({})".format(", ".join(values), ", ".join("?" * len(values))),
                           list(values.values())).lastrowid
    _log(ctx, "training_topic_created", tid, {"title": values["title"]})
    return {"id": tid}


def api_update_topic(ctx):
    if not _can_manage_topics(ctx.conn, ctx.user):
        raise ApiError(403, "Réservé aux administrateurs et aux Admin du Space TRAINING.")
    tid = validate.int_param(ctx.params, "tid")
    row = ctx.conn.execute("SELECT * FROM training_topics WHERE id = ?", (tid,)).fetchone()
    if row is None:
        raise ApiError(404, "Topic introuvable.")
    values = _topic_values(ctx.conn, ctx.body, row)
    if values:
        values["updated_at"] = db.utc_now()
        ctx.conn.execute("UPDATE training_topics SET {} WHERE id = ?".format(", ".join(k + " = ?" for k in values)),
                         list(values.values()) + [tid])
        _log(ctx, "training_topic_updated", tid, {"fields": sorted(k for k in values if k != "updated_at")})
    return {"ok": True}


def api_check_quiz(ctx):
    return quiz.report(str(ctx.body.get("quiz_md") or ""))


# --------------------------------------------------------------------------
# Workflow
# --------------------------------------------------------------------------
def api_workflow(ctx):
    return {"statuses": catalog.STATUSES, "roles": catalog.ROLES, "rules": catalog.workflow(ctx.conn),
            "can_edit": bool(ctx.user["is_admin"])}


def api_save_workflow(ctx):
    permissions.require_admin(ctx.user)
    rules = ctx.body.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ApiError(400, "Workflow attendu : une liste de transitions [de, vers, libellé, rôles].")
    clean = []
    for i, r in enumerate(rules, start=1):
        if not (isinstance(r, list) and len(r) == 4):
            raise ApiError(400, "Transition {} : 4 éléments attendus (de, vers, libellé, rôles).".format(i))
        frm, to, label, roles = r
        if frm not in catalog.STATUSES or to not in catalog.STATUSES or frm == to:
            raise ApiError(400, "Transition {} : « {} → {} » invalide. Correctif : status parmi {}.".format(
                i, frm, to, ", ".join(catalog.STATUSES)))
        roles = [x for x in (roles or []) if x in catalog.ROLES]
        clean.append([frm, to, str(label or "")[:40] or catalog.STATUSES[to], roles])
    if not any(r[1] == "achieved" and "manager" in r[3] for r in clean):
        raise ApiError(400, "Le gestionnaire doit pouvoir passer un item à « Achieved ». Correctif : cochez « Gestionnaire » "
                            "sur une transition vers Achieved.")
    catalog.save_workflow(ctx.conn, clean)
    _log(ctx, "training_workflow_saved", None, {"rules": len(clean)})
    return {"ok": True, "rules": clean}


# --------------------------------------------------------------------------
# Plans
# --------------------------------------------------------------------------
def api_people(ctx):
    from modules.timesheet import leave
    ids = [ctx.user["id"]] + leave.reports_of(ctx.conn, ctx.user["id"])
    rows = [dict(r) for r in (ctx.conn.execute("SELECT id, display_name FROM users WHERE id = ? AND is_active = 1",
                                                (i,)).fetchone() for i in ids) if r]
    return {"people": rows, "me": ctx.user["id"]}


def _item(conn, item_id):
    row = conn.execute("SELECT i.*, t.title, t.code, t.content, t.reference, t.ref_label, t.quiz_md FROM training_items i "
                       "JOIN training_topics t ON t.id = i.topic_id WHERE i.id = ?", (item_id,)).fetchone()
    if row is None:
        raise ApiError(404, "Item de formation introuvable.")
    return row


def _item_public(row, rel, rules):
    out = {k: row[k] for k in row.keys() if k != "quiz_md"}
    parsed, problems = quiz.parse(row["quiz_md"] or "")
    out["has_quiz"] = bool(parsed["questions"]) and not problems
    out["quiz_questions"] = len(parsed["questions"])
    state = circle.pending(row, parsed) if out["has_quiz"] else None
    out["quiz_remaining"] = len(state["q"]) if state else 0
    out["quiz_first"] = state["first"] if state else None
    out.pop("quiz_pending", None)
    role = "employee" if rel == "self" else "manager"
    out["actions"] = [{"to": to, "label": label} for frm, to, label, roles in rules if frm == row["status"] and role in roles]
    return out


def api_plan(ctx):
    target = validate.int_param(ctx.params, "uid")
    rel = relation(ctx.conn, ctx.user, target)
    year = _year(ctx)
    rules = catalog.workflow(ctx.conn)
    rows = ctx.conn.execute("SELECT i.*, t.title, t.code, t.content, t.reference, t.ref_label, t.quiz_md FROM training_items i "
                            "JOIN training_topics t ON t.id = i.topic_id WHERE i.user_id = ? AND i.year = ? "
                            "ORDER BY t.position, t.id", (target, year)).fetchall()
    person = ctx.conn.execute("SELECT id, display_name FROM users WHERE id = ?", (target,)).fetchone()
    years = sorted({r[0] for r in ctx.conn.execute("SELECT DISTINCT year FROM training_items WHERE user_id = ?", (target,))}
                   | {dt.date.today().year, year})
    return {"person": dict(person), "relation": rel, "year": year, "years": years, "statuses": catalog.STATUSES,
            "items": [_item_public(r, rel, rules) for r in rows]}


def api_add(ctx):
    target = validate.int_param(ctx.params, "uid")
    relation(ctx.conn, ctx.user, target)
    year = _year(ctx)
    topic = ctx.conn.execute("SELECT id, title FROM training_topics WHERE id = ? AND active = 1",
                             (ctx.body.get("topic_id"),)).fetchone()
    if topic is None:
        raise ApiError(400, "Topic introuvable ou inactif. Correctif : choisissez un topic de la liste.")
    due = str(ctx.body.get("due_date") or "").strip()[:10]
    if due:
        try:
            dt.date.fromisoformat(due)
        except ValueError:
            raise ApiError(400, "Échéance « {} » invalide. Correctif : format AAAA-MM-JJ.".format(due))
    if ctx.conn.execute("SELECT 1 FROM training_items WHERE topic_id = ? AND user_id = ? AND year = ?",
                        (topic["id"], target, year)).fetchone():
        raise ApiError(409, "« {} » est déjà dans le plan {}. Correctif : ouvrez l'item existant.".format(topic["title"], year))
    now = db.utc_now()
    iid = ctx.conn.execute("INSERT INTO training_items (topic_id, user_id, year, status, due_date, created_by, created_at, "
                           "updated_at) VALUES (?, ?, ?, 'todo', ?, ?, ?, ?)",
                           (topic["id"], target, year, due or None, ctx.user["id"], now, now)).lastrowid
    _log(ctx, "training_item_added", iid, {"user": target, "year": year, "topic": topic["id"]})
    return {"id": iid}


def api_update(ctx):
    row = _item(ctx.conn, validate.int_param(ctx.params, "iid"))
    rel = relation(ctx.conn, ctx.user, row["user_id"])
    role = "employee" if rel == "self" else "manager"
    changes = {}
    if "note" in ctx.body:
        changes["note"] = validate.text(ctx.body, "note", 2000, required=False)
    if "due_date" in ctx.body:
        changes["due_date"] = str(ctx.body.get("due_date") or "").strip()[:10] or None
    if "manager_eval" in ctx.body:
        if role != "manager":
            raise ApiError(403, "L'évaluation est écrite par le gestionnaire seulement.")
        changes["manager_eval"] = validate.text(ctx.body, "manager_eval", 3000, required=False)
    to = ctx.body.get("status")
    if to is not None and to != row["status"]:
        rules = [r for r in catalog.workflow(ctx.conn) if r[0] == row["status"] and r[1] == to]
        if not rules:
            raise ApiError(400, "Passage « {} → {} » absent du workflow Training. Correctif : utilisez un bouton proposé, "
                                "ou demandez à un administrateur d'ajouter la transition.".format(
                                    catalog.STATUSES[row["status"]], catalog.STATUSES.get(to, to)))
        if role not in rules[0][3]:
            raise ApiError(403, "« {} » est réservé au {}.".format(rules[0][2], " ou à l'".join(
                catalog.ROLES[r].lower() for r in rules[0][3]) or "personne"))
        if to == "achieved":
            parsed, problems = quiz.parse(row["quiz_md"] or "")
            if parsed["questions"] and not problems and not row["quiz_passed"]:
                raise ApiError(409, "Test du topic pas encore réussi ({} %, seuil {} %). Correctif : l'employé passe le test, "
                                    "puis vous cochez « Achieved ».".format(row["quiz_score"] or 0, parsed["pass"]))
            if not (changes.get("manager_eval") or row["manager_eval"] or "").strip():
                raise ApiError(409, "Évaluation du gestionnaire manquante. Correctif : écrivez votre évaluation, puis cochez "
                                    "« Achieved ».")
            changes.update(achieved_at=db.utc_now(), achieved_by=ctx.user["id"])
        if to == "completed":
            parsed, problems = quiz.parse(row["quiz_md"] or "")
            if parsed["questions"] and not problems and not row["quiz_passed"]:
                raise ApiError(409, "Ce topic a un test : il passe à « Completed » tout seul quand le test est réussi. "
                                    "Correctif : « Passer le test ».")
            changes["completed_at"] = db.utc_now()
        changes["status"] = to
    if changes:
        changes["updated_at"] = db.utc_now()
        ctx.conn.execute("UPDATE training_items SET {} WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                         list(changes.values()) + [row["id"]])
        _log(ctx, "training_item_updated", row["id"], {"as": role, "status": changes.get("status"),
                                                       "fields": sorted(k for k in changes if k not in ("updated_at",))})
    return {"ok": True}


def api_delete(ctx):
    row = _item(ctx.conn, validate.int_param(ctx.params, "iid"))
    rel = relation(ctx.conn, ctx.user, row["user_id"])
    if rel == "self" and row["status"] != "todo":
        raise ApiError(409, "Seul un item « To Do » se retire du plan par l'employé. Correctif : demandez à votre gestionnaire.")
    ctx.conn.execute("DELETE FROM training_attempts WHERE item_id = ?", (row["id"],))
    ctx.conn.execute("DELETE FROM training_items WHERE id = ?", (row["id"],))
    _log(ctx, "training_item_removed", row["id"], {"user": row["user_id"]})
    return {"ok": True}


# --------------------------------------------------------------------------
# Tests (circle-back: circle.py, 0.50.10)
# --------------------------------------------------------------------------
def api_quiz(ctx):
    return circle.api_quiz(ctx, _item)


def api_answer(ctx):
    return circle.api_answer(ctx, _item)
