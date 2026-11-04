"""Professional profile of an employee or an intern (core lot v0.30, D-B-111).

Shown above every evaluation page so that comments are read in context:
- set by the MANAGER (the approver chosen in Settings): kind (employee / intern), job title, experience level, hire date;
  for an intern: internship dates (4 to 8 months), school, program, tutor;
- written by the EMPLOYEE: his background -- education, experience, certifications, skills, languages.
Who: like « Mes objectifs », the employee and HIS manager only (administrators included out). Every write is journalled
without its text (private content).
"""
import datetime as dt

from . import audit, db, validate
from .errors import ApiError
from .objectives import relation

MIGRATIONS = [
    (14, """
        CREATE TABLE user_profiles (
            user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            kind       TEXT NOT NULL DEFAULT 'employee',
            job_title  TEXT NOT NULL DEFAULT '',
            level      TEXT NOT NULL DEFAULT '',
            hire_date  TEXT,
            start_date TEXT,
            end_date   TEXT,
            school     TEXT NOT NULL DEFAULT '',
            program    TEXT NOT NULL DEFAULT '',
            tutor      TEXT NOT NULL DEFAULT '',
            updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE profile_entries (
            id         INTEGER PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            section    TEXT NOT NULL,
            title      TEXT NOT NULL,
            org        TEXT NOT NULL DEFAULT '',
            period     TEXT NOT NULL DEFAULT '',
            details    TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX idx_profile_entries_user ON profile_entries(user_id, section);
    """),
]

KINDS = {"employee": "Employé", "intern": "Stagiaire"}
LEVELS = {"junior": "Junior (0 à 3 ans)", "intermediate": "Intermédiaire (3 à 7 ans)", "senior": "Senior (7 à 15 ans)",
          "expert": "Expert (15 ans et plus)"}
SECTIONS = {"education": "Formation", "experience": "Expériences", "certification": "Certifications",
            "skill": "Compétences", "language": "Langues"}
MANAGER_TEXT = {"job_title": 120, "school": 160, "program": 160, "tutor": 120}
DATES = ("hire_date", "start_date", "end_date")
ENTRY_TEXT = {"title": 200, "org": 200, "period": 80, "details": 2000}


def _log(ctx, action, target_id, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "profile", target_id, details, ctx.ip)


def _months(start, end):
    a, b = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    return (b.year - a.year) * 12 + (b.month - a.month) + (1 if b.day >= a.day else 0)


def _seniority(hire_date, today=None):
    if not hire_date:
        return ""
    today = today or dt.date.today()
    start = dt.date.fromisoformat(hire_date)
    if start > today:
        return "arrivée le " + hire_date
    months = (today.year - start.year) * 12 + today.month - start.month - (1 if today.day < start.day else 0)
    years, months = divmod(max(months, 0), 12)
    parts = ([str(years) + (" an" if years == 1 else " ans")] if years else []) + ([str(months) + " mois"] if months or not years else [])
    return " et ".join(parts)


def header(conn, user_id):
    """The context line of every evaluation page: name, title, level, seniority, kind, manager."""
    from . import prefs
    person = conn.execute("SELECT id, display_name FROM users WHERE id = ?", (user_id,)).fetchone()
    row = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
    p = dict(row) if row else {"kind": "employee", "job_title": "", "level": "", "hire_date": None, "start_date": None,
                               "end_date": None, "school": "", "program": "", "tutor": ""}
    p.pop("updated_by", None)
    p["name"] = person["display_name"] if person else ""
    p["kind_label"] = KINDS.get(p["kind"], "Employé")
    p["level_label"] = "Stagiaire" if p["kind"] == "intern" else LEVELS.get(p["level"], "")
    p["seniority"] = _seniority(p.get("hire_date"))
    p["months"] = _months(p["start_date"], p["end_date"]) if p.get("start_date") and p.get("end_date") else None
    manager_id = prefs.get(conn, user_id).get("manager_id")
    m = conn.execute("SELECT display_name FROM users WHERE id = ?", (manager_id,)).fetchone() if manager_id else None
    p["manager"] = m["display_name"] if m else None
    return p


def api_get(ctx):
    target = validate.int_param(ctx.params, "uid")
    rel = relation(ctx.conn, ctx.user, target)
    entries = db.rows(ctx.conn.execute("SELECT * FROM profile_entries WHERE user_id = ? ORDER BY section, id", (target,)).fetchall())
    _log(ctx, "profile_viewed", target, {"as": rel})
    return {"relation": rel, "profile": header(ctx.conn, target), "entries": entries, "kinds": KINDS, "levels": LEVELS,
            "sections": SECTIONS}


def _date(body, name):
    value = str(body.get(name) or "").strip()[:10]
    if not value:
        return None
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        raise ApiError(400, "Date « {} » invalide pour {}. Correctif : format AAAA-MM-JJ.".format(value, name))
    return value


def api_update(ctx):
    """Manager only: kind, job title, level, dates, school, program, tutor."""
    target = validate.int_param(ctx.params, "uid")
    rel = relation(ctx.conn, ctx.user, target)
    if rel != "manager":
        raise ApiError(403, "Titre, niveau et dates sont fixés par votre gestionnaire. Correctif : demandez-lui de les mettre "
                            "à jour ; votre parcours, lui, est à vous (section Parcours).")
    body, changes = ctx.body, {}
    if "kind" in body:
        if body["kind"] not in KINDS:
            raise ApiError(400, "Type « {} » inconnu. Correctif : employee ou intern.".format(body["kind"]))
        changes["kind"] = body["kind"]
    if "level" in body:
        if body["level"] not in LEVELS and body["level"] != "":
            raise ApiError(400, "Niveau « {} » inconnu. Correctif : {}.".format(body["level"], ", ".join(LEVELS)))
        changes["level"] = body["level"]
    for name, size in MANAGER_TEXT.items():
        if name in body:
            changes[name] = validate.text(body, name, size, required=False)
    for name in DATES:
        if name in body:
            changes[name] = _date(body, name)
    current = header(ctx.conn, target)
    start, end = changes.get("start_date", current.get("start_date")), changes.get("end_date", current.get("end_date"))
    if start and end and end <= start:
        raise ApiError(400, "Fin du stage ({}) avant son début ({}). Correctif : vérifiez les deux dates.".format(end, start))
    if not changes:
        raise ApiError(400, "Aucune modification demandée.")
    now = db.utc_now()
    ctx.conn.execute("INSERT INTO user_profiles (user_id, updated_by, updated_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO NOTHING",
                     (target, ctx.user["id"], now))
    ctx.conn.execute("UPDATE user_profiles SET {}, updated_by = ?, updated_at = ? WHERE user_id = ?".format(
        ", ".join(k + " = ?" for k in changes)), list(changes.values()) + [ctx.user["id"], now, target])
    _log(ctx, "profile_updated", target, {"fields": sorted(changes)})
    months = header(ctx.conn, target)["months"]
    warning = None
    if months is not None and not 4 <= months <= 8:
        warning = "Stage de {} mois : la grille de stage est prévue pour 4 à 8 mois.".format(months)
    return {"profile": header(ctx.conn, target), "warning": warning}


def _entry_values(body, partial=False):
    out = {}
    if "section" in body or not partial:
        if body.get("section") not in SECTIONS:
            raise ApiError(400, "Section inconnue. Correctif : {}.".format(", ".join(SECTIONS)))
        out["section"] = body["section"]
    for name, size in ENTRY_TEXT.items():
        if name in body or (name == "title" and not partial):
            out[name] = validate.text(body, name, size, required=(name == "title"))
    return out


def _own_entry(ctx):
    eid = validate.int_param(ctx.params, "eid")
    row = ctx.conn.execute("SELECT * FROM profile_entries WHERE id = ?", (eid,)).fetchone()
    if row is None:
        raise ApiError(404, "Élément de parcours introuvable.")
    if relation(ctx.conn, ctx.user, row["user_id"]) != "self":
        raise ApiError(403, "Le parcours est rempli par l'employé lui-même. Correctif : commentez-le dans l'évaluation.")
    return row


def api_add_entry(ctx):
    target = validate.int_param(ctx.params, "uid")
    if relation(ctx.conn, ctx.user, target) != "self":
        raise ApiError(403, "Le parcours est rempli par l'employé lui-même. Correctif : commentez-le dans l'évaluation.")
    values = _entry_values(ctx.body)
    now = db.utc_now()
    eid = ctx.conn.execute("INSERT INTO profile_entries (user_id, section, title, org, period, details, created_at, updated_at) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (target, values["section"], values["title"], values.get("org", ""),
                                                              values.get("period", ""), values.get("details", ""), now, now)).lastrowid
    _log(ctx, "profile_entry_added", target, {"section": values["section"]})
    return {"id": eid}


def api_update_entry(ctx):
    row = _own_entry(ctx)
    values = _entry_values(ctx.body, partial=True)
    if not values:
        raise ApiError(400, "Aucune modification demandée.")
    ctx.conn.execute("UPDATE profile_entries SET {}, updated_at = ? WHERE id = ?".format(", ".join(k + " = ?" for k in values)),
                     list(values.values()) + [db.utc_now(), row["id"]])
    _log(ctx, "profile_entry_updated", row["user_id"], {"fields": sorted(values)})
    return {"ok": True}


def api_delete_entry(ctx):
    row = _own_entry(ctx)
    ctx.conn.execute("DELETE FROM profile_entries WHERE id = ?", (row["id"],))
    _log(ctx, "profile_entry_deleted", row["user_id"], {"section": row["section"]})
    return {"ok": True}


ROUTES = [
    ("GET", r"/api/profile/(?P<uid>\d+)", api_get, "user"),
    ("PATCH", r"/api/profile/(?P<uid>\d+)", api_update, "user"),
    ("POST", r"/api/profile/(?P<uid>\d+)/entries", api_add_entry, "user"),
    ("PATCH", r"/api/profile/entries/(?P<eid>\d+)", api_update_entry, "user"),
    ("DELETE", r"/api/profile/entries/(?P<eid>\d+)", api_delete_entry, "user"),
]
