"""Exploration plan (D-B-019): tasks of a multi-month, abstract plan, with
predecessors (finish-to-start), durations in weeks and a computed Gantt.

Not linked to Agile tickets on purpose: same subjects, other granularity.
Rights (same spirit as D-B-017): the plan's structure (tasks, order,
durations, predecessors, owners, import) belongs to administrators; the
owner of a task -- or an administrator -- follows it up (status, progress,
follow-up note). Readers see everything.
"""
import datetime as dt
import re
import unicodedata

from core import audit, db, permissions, validate
from core.errors import ApiError

STATUSES = {"todo": "To Do", "doing": "In Progress", "done": "Done", "blocked": "Blocked"}
STATUS_ALIASES = {"a faire": "todo", "todo": "todo", "to do": "todo", "planifie": "todo", "": "todo",
                  "en cours": "doing", "doing": "doing", "in progress": "doing", "demarre": "doing",
                  "termine": "done", "done": "done", "fait": "done", "complete": "done", "ferme": "done",
                  "bloque": "blocked", "blocked": "blocked", "en attente": "blocked", "on hold": "blocked"}
CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,19}$")
MAX_TASKS = 500
MAX_WEEKS = 520


def norm(text):
    """Lower-case, no accents, single spaces: for matching headers, names, statuses."""
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text).strip().lower()


def status_key(value):
    key = STATUS_ALIASES.get(norm(value))
    if key is None and value in STATUSES:
        key = value
    return key


def parse_date(value):
    value = str(value or "").strip()[:10]
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        m = re.match(r"^(\d{1,2})[/.](\d{1,2})[/.](\d{4})$", value)
        if m:
            try:
                return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                return None
        return None


def split_codes(value):
    return [c.upper() for c in re.split(r"[\s,;]+", str(value or "")) if c]


def pid(ctx):
    return validate.int_param(ctx.params, "pid")


def access(ctx, minimum="reader"):
    project_id = pid(ctx)
    return project_id, permissions.require_project_role(ctx.conn, ctx.user, project_id, minimum)


def log(ctx, action, object_id, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "exploration", object_id, details, ctx.ip)


def members(conn, project_id):
    return db.rows(conn.execute(
        "SELECT u.id, u.display_name, u.username FROM users u "
        "LEFT JOIN memberships m ON m.user_id = u.id AND m.project_id = ? "
        "WHERE u.is_active = 1 AND (m.user_id IS NOT NULL OR u.is_admin = 1) "
        "ORDER BY u.display_name", (project_id,)).fetchall())


def find_member(people, text):
    """Owner cell -> user id: identifier, full name or first name (accents ignored)."""
    wanted = norm(text)
    if not wanted:
        return None
    for person in people:
        if wanted in (norm(person["username"]), norm(person["display_name"])):
            return person["id"]
    first = [p for p in people if norm(p["display_name"]).split(" ")[0] == wanted]
    return first[0]["id"] if len(first) == 1 else False


# --------------------------------------------------------------------------
# Scheduling
# --------------------------------------------------------------------------
class PlanError(ValueError):
    pass


def schedule(tasks, plan_start):
    """tasks: dicts with code, duration_weeks, start_date (ISO or None),
    predecessors (list of codes). Returns {code: (start, end)} as dates.
    Finish-to-start; an imposed start means "not before"."""
    by_code = {t["code"]: t for t in tasks}
    for t in tasks:
        unknown = [p for p in t["predecessors"] if p not in by_code]
        if unknown:
            raise PlanError("{} : prédécesseur(s) inconnu(s) {}.".format(t["code"], ", ".join(unknown)))
    result, state = {}, {}

    def visit(code, trail):
        if state.get(code) == "done":
            return result[code]
        if state.get(code) == "open":
            loop = trail[trail.index(code):] + [code]
            raise PlanError("Boucle de prédécesseurs : {}.".format(" → ".join(loop)))
        state[code] = "open"
        task = by_code[code]
        start = parse_date(task.get("start_date")) or plan_start
        for pred in task["predecessors"]:
            start = max(start, visit(pred, trail + [code])[1])
        end = start + dt.timedelta(days=round(float(task["duration_weeks"]) * 7))
        result[code] = (start, end)
        state[code] = "done"
        return result[code]

    for t in tasks:
        visit(t["code"], [])
    return result


def plan_start(conn, project_id):
    row = conn.execute("SELECT start_date FROM exploration_plans WHERE project_id = ?", (project_id,)).fetchone()
    return parse_date(row["start_date"]) if row else None


def next_monday(today=None):
    today = today or dt.date.today()
    return today + dt.timedelta(days=(7 - today.weekday()) % 7)


def load(conn, project_id):
    """Tasks in display order with computed dates, late flag and owner name."""
    rows = db.rows(conn.execute(
        "SELECT t.*, u.display_name AS owner_name, u.username AS owner_username FROM exploration_tasks t "
        "LEFT JOIN users u ON u.id = t.owner_id WHERE t.project_id = ? ORDER BY t.position, t.id",
        (project_id,)).fetchall())
    start = plan_start(conn, project_id) or next_monday()
    for r in rows:
        r["predecessors"] = split_codes(r["predecessors"])
    try:
        dates = schedule(rows, start)
    except PlanError:  # never stored (checked on write), kept safe for hand-edited databases
        dates = {r["code"]: (start, start) for r in rows}
    today = dt.date.today()
    for r in rows:
        s, e = dates[r["code"]]
        r["start"], r["end"] = s.isoformat(), e.isoformat()
        r["status_label"] = STATUSES.get(r["status"], r["status"])
        r["late"] = r["status"] != "done" and e < today
    return start, rows


def api_plan(ctx):
    project_id, role = access(ctx)
    start, tasks = load(ctx.conn, project_id)
    return {"start_date": start.isoformat(), "tasks": tasks, "members": members(ctx.conn, project_id),
            "role": role, "can_admin": role == "admin", "me": ctx.user["id"],
            "statuses": [{"key": k, "label": v} for k, v in STATUSES.items()], "today": dt.date.today().isoformat()}


def api_set_start(ctx):
    project_id, _ = access(ctx, "admin")
    start = parse_date(ctx.body.get("start_date"))
    if start is None:
        raise ApiError(400, "Date de début invalide. Correctif : AAAA-MM-JJ.")
    set_start(ctx.conn, project_id, start)
    log(ctx, "exploration_plan_start", project_id, {"start_date": start.isoformat()})
    return {"ok": True}


def set_start(conn, project_id, start):
    conn.execute("INSERT INTO exploration_plans (project_id, start_date, updated_at) VALUES (?, ?, ?) "
                 "ON CONFLICT(project_id) DO UPDATE SET start_date = excluded.start_date, "
                 "updated_at = excluded.updated_at", (project_id, start.isoformat(), db.utc_now()))


# --------------------------------------------------------------------------
# Task writes
# --------------------------------------------------------------------------
STRUCTURE = ("code", "phase", "title", "description", "owner_id", "duration_weeks", "start_date", "predecessors")
FOLLOW_UP = ("status", "progress", "note")


def clean(body, people, current=None):
    """Validate the fields present in `body`; returns a dict of new values."""
    out = {}
    if "code" in body:
        code = str(body.get("code") or "").strip().upper()
        if not CODE_RE.match(code):
            raise ApiError(400, "ID invalide « {} ». Correctif : lettres, chiffres, point ou tiret, 20 car. "
                                "au maximum (ex. T1, 2.3).".format(code))
        out["code"] = code
    for name, limit in (("phase", 80), ("title", 200), ("description", 4000), ("note", 500)):
        if name in body:
            value = str(body.get(name) or "").strip()
            if len(value) > limit:
                raise ApiError(400, "{} : {} caractères au maximum.".format(name, limit))
            out[name] = value
    if "title" in out and not out["title"]:
        raise ApiError(400, "Le nom de la task est obligatoire.")
    if "owner_id" in body:
        owner = body.get("owner_id")
        if owner in (None, ""):
            out["owner_id"] = None
        elif not any(p["id"] == owner for p in people):
            raise ApiError(400, "Le responsable doit être un membre du projet.")
        else:
            out["owner_id"] = owner
    if "duration_weeks" in body:
        try:
            weeks = round(float(str(body.get("duration_weeks")).replace(",", ".")), 2)
        except ValueError:
            raise ApiError(400, "Durée invalide. Correctif : un nombre de semaines (0 = milestone).")
        if not 0 <= weeks <= MAX_WEEKS:
            raise ApiError(400, "Durée hors limites (0 à {} semaines).".format(MAX_WEEKS))
        out["duration_weeks"] = weeks
    if "start_date" in body:
        raw = body.get("start_date")
        start = parse_date(raw)
        if raw not in (None, "") and start is None:
            raise ApiError(400, "Début imposé invalide. Correctif : AAAA-MM-JJ ou vide.")
        out["start_date"] = start.isoformat() if start else None
    if "predecessors" in body:
        raw = body.get("predecessors")
        codes = raw if isinstance(raw, list) else split_codes(raw)
        out["predecessors"] = ", ".join(dict.fromkeys(str(c).strip().upper() for c in codes if str(c).strip()))
    if "status" in body:
        key = status_key(body.get("status"))
        if key is None:
            raise ApiError(400, "Status invalide. Correctif : " + ", ".join(STATUSES.values()) + ".")
        out["status"] = key
    if "progress" in body:
        try:
            progress = int(round(float(str(body.get("progress") or 0).replace("%", "").replace(",", "."))))
        except ValueError:
            raise ApiError(400, "Avancement invalide (0 à 100).")
        out["progress"] = max(0, min(100, progress))
    if out.get("status") == "done" and "progress" not in out:
        out["progress"] = 100
    return out


def check_plan(conn, project_id, changed_id=None, values=None):
    """Re-run the scheduler with a pending change; raises ApiError on a loop,
    an unknown predecessor or a duplicate ID."""
    rows = db.rows(conn.execute("SELECT id, code, duration_weeks, start_date, predecessors FROM exploration_tasks "
                                "WHERE project_id = ?", (project_id,)).fetchall())
    if changed_id is None and values is not None:
        rows.append(dict(values, id=None))
    renamed = {}
    for r in rows:
        if r["id"] is not None and r["id"] == changed_id:
            if "code" in values:
                renamed[r["code"]] = values["code"]
            r.update(values)
    for r in rows:
        r["predecessors"] = [renamed.get(c, c) for c in split_codes(r["predecessors"])]
    codes = [r["code"] for r in rows]
    if len(codes) != len(set(codes)):
        raise ApiError(409, "Cet ID de task existe déjà dans le plan.")
    try:
        schedule(rows, dt.date.today())
    except PlanError as exc:
        raise ApiError(409, "{} Correctif : corrigez la colonne Prédécesseurs.".format(exc))


def _task(ctx, project_id):
    task_id = validate.int_param(ctx.params, "tid")
    row = ctx.conn.execute("SELECT * FROM exploration_tasks WHERE id = ? AND project_id = ?",
                           (task_id, project_id)).fetchone()
    if row is None:
        raise ApiError(404, "Task introuvable.")
    return row


def next_code(conn, project_id):
    """D-B-061: next automatic code, from a counter that never goes back (a deleted T3 stays retired)."""
    import re as _re
    used = {r[0] for r in conn.execute("SELECT code FROM exploration_tasks WHERE project_id = ?", (project_id,))}
    highest = max([int(m.group(1)) for m in (_re.fullmatch(r"T(\d+)", c or "") for c in used) if m] or [0])
    row = conn.execute("SELECT next_task FROM exploration_counters WHERE project_id = ?", (project_id,)).fetchone()
    n = max(highest + 1, row["next_task"] if row else 1)
    while "T{}".format(n) in used:
        n += 1
    conn.execute("INSERT INTO exploration_counters (project_id, next_task) VALUES (?, ?) "
                 "ON CONFLICT(project_id) DO UPDATE SET next_task = excluded.next_task", (project_id, n + 1))
    return "T{}".format(n)


def api_create(ctx):
    project_id, _ = access(ctx, "admin")
    conn = ctx.conn
    count = conn.execute("SELECT COUNT(*) FROM exploration_tasks WHERE project_id = ?", (project_id,)).fetchone()[0]
    if count >= MAX_TASKS:
        raise ApiError(409, "{} tasks au maximum par plan.".format(MAX_TASKS))
    body = dict(ctx.body)
    if not str(body.get("code") or "").strip():
        body["code"] = next_code(conn, project_id)
    values = dict({"phase": "", "description": "", "owner_id": None, "duration_weeks": 1, "start_date": None,
                   "predecessors": "", "status": "todo", "progress": 0, "note": ""},
                  **clean(body, members(conn, project_id)))
    if not values.get("title"):
        raise ApiError(400, "Le nom de la task est obligatoire.")
    check_plan(conn, project_id, None, values)
    position = count
    if body.get("position") is not None:  # D-A-041: explicit place in the plan (0 = first)
        position = max(0, min(validate.int_param({"p": body["position"]}, "p"), count))
    elif values.get("phase"):  # D-A-041: a new task joins the end of its phase, not the end of the plan
        last = conn.execute("SELECT MAX(position) FROM exploration_tasks WHERE project_id = ? AND phase = ?",
                            (project_id, values["phase"])).fetchone()[0]
        if last is not None:
            position = last + 1
    conn.execute("UPDATE exploration_tasks SET position = position + 1 WHERE project_id = ? AND position >= ?",
                 (project_id, position))
    task_id = insert(ctx, project_id, values, position)
    log(ctx, "exploration_task_create", task_id, {"code": values["code"], "title": values["title"]})
    return {"id": task_id, "code": values["code"]}


def insert(ctx, project_id, values, position):
    cols = ("code", "phase", "title", "description", "owner_id", "duration_weeks", "start_date", "predecessors",
            "status", "progress", "note")
    return ctx.conn.execute(
        "INSERT INTO exploration_tasks (project_id, position, {}, updated_by, updated_at) VALUES (?, ?, {}, ?, ?)"
        .format(", ".join(cols), ", ".join("?" for _ in cols)),
        (project_id, position) + tuple(values.get(c) for c in cols) + (ctx.user["id"], db.utc_now())).lastrowid


def api_update(ctx):
    project_id, role = access(ctx)
    conn = ctx.conn
    row = _task(ctx, project_id)
    admin = role == "admin"
    owner = role == "editor" and row["owner_id"] == ctx.user["id"]
    wanted = set(ctx.body) - {"position"}
    if not admin and (not owner or wanted - set(FOLLOW_UP) or "position" in ctx.body):
        raise ApiError(403, "Seul le responsable de la task (status, avancement, note) ou un administrateur "
                            "(tout le plan) peut la modifier.")
    changes = {k: v for k, v in clean(ctx.body, members(conn, project_id), row).items() if row[k] != v}
    if set(changes) & {"code", "duration_weeks", "start_date", "predecessors"}:
        check_plan(conn, project_id, row["id"], changes)
        if "code" in changes:  # keep predecessors pointing at the renamed task
            for other in conn.execute("SELECT id, predecessors FROM exploration_tasks WHERE project_id = ? AND id != ?",
                                      (project_id, row["id"])).fetchall():
                codes = split_codes(other["predecessors"])
                if row["code"] in codes:
                    conn.execute("UPDATE exploration_tasks SET predecessors = ? WHERE id = ?", (", ".join(
                        changes["code"] if c == row["code"] else c for c in codes), other["id"]))
    if "position" in ctx.body and admin:
        move(conn, project_id, row, validate.int_param({"p": ctx.body["position"]}, "p"))
    if changes:
        conn.execute("UPDATE exploration_tasks SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(
            ", ".join("{} = ?".format(k) for k in changes)),
            tuple(changes.values()) + (ctx.user["id"], db.utc_now(), row["id"]))
        log(ctx, "exploration_task_update", row["id"], {"code": row["code"], "fields": sorted(changes)})
    return {"ok": True, "changed": sorted(changes)}


def move(conn, project_id, row, position):
    ids = [r[0] for r in conn.execute("SELECT id FROM exploration_tasks WHERE project_id = ? ORDER BY position, id",
                                      (project_id,))]
    ids.remove(row["id"])
    ids.insert(max(0, min(position, len(ids))), row["id"])
    conn.executemany("UPDATE exploration_tasks SET position = ? WHERE id = ?", [(i, t) for i, t in enumerate(ids)])


def api_reorder(ctx):
    """D-A-041 (edit mode): the whole plan order at once, each task with its phase -- move a task up / down, drag it
    anywhere, into another phase, or move a whole phase. The order is the display order of the plan and of the Gantt;
    dates still come from durations and predecessors. Administrators only; journalled once."""
    project_id, _ = access(ctx, "admin")
    conn = ctx.conn
    order = ctx.body.get("order")
    rows = {r["id"]: r for r in conn.execute("SELECT id, code, phase FROM exploration_tasks WHERE project_id = ?",
                                              (project_id,)).fetchall()}
    if not isinstance(order, list) or not all(isinstance(x, dict) for x in order):
        raise ApiError(400, "Ordre attendu : une liste {id, phase} de toutes les tasks du plan.")
    try:
        ids = [int(x.get("id")) for x in order]
    except (TypeError, ValueError):
        raise ApiError(400, "Ordre : chaque élément doit porter l'id numérique d'une task.")
    missing, unknown = sorted(set(rows) - set(ids)), sorted(set(ids) - set(rows))
    if missing or unknown or len(ids) != len(set(ids)):
        raise ApiError(409, "Le plan a changé pendant l'édition ({} task(s) absente(s), {} inconnue(s) ou en double). "
                            "Correctif : rechargez la page et refaites le déplacement.".format(
                                len(missing), len(unknown) + len(ids) - len(set(ids))))
    phases_changed = []
    for pos, (tid, item) in enumerate(zip(ids, order)):
        phase = " ".join(str(item.get("phase", rows[tid]["phase"]) or "").split())
        if len(phase) > 80:
            raise ApiError(400, "Phase « {}… » trop longue : 80 caractères au maximum.".format(phase[:30]))
        if phase != rows[tid]["phase"]:
            phases_changed.append(rows[tid]["code"])
            conn.execute("UPDATE exploration_tasks SET position = ?, phase = ?, updated_by = ?, updated_at = ? WHERE id = ?",
                         (pos, phase, ctx.user["id"], db.utc_now(), tid))
        else:
            conn.execute("UPDATE exploration_tasks SET position = ? WHERE id = ?", (pos, tid))
    log(ctx, "exploration_plan_reorder", project_id, {"tasks": len(ids), "phase_changed": phases_changed})
    return {"ok": True, "phase_changed": phases_changed}


def api_delete(ctx):
    project_id, _ = access(ctx, "admin")
    row = _task(ctx, project_id)
    users = [r["code"] for r in ctx.conn.execute("SELECT code, predecessors FROM exploration_tasks WHERE "
                                                  "project_id = ?", (project_id,)).fetchall()
             if row["code"] in split_codes(r["predecessors"])]
    if users:
        raise ApiError(409, "{} est le prédécesseur de {}. Correctif : retirez-le d'abord de leurs "
                            "prédécesseurs.".format(row["code"], ", ".join(users)))
    ctx.conn.execute("DELETE FROM exploration_tasks WHERE id = ?", (row["id"],))
    log(ctx, "exploration_task_delete", row["id"], {"code": row["code"], "title": row["title"]})
    return {"ok": True}
