"""Testing API (D-B-079): the test base -- list, record, create, edit, CSV round trip.

D-B-097: one base per Space, chosen by ?space=<KEY> (body « space » for writes; TESTING, the reference catalogue,
when absent). Reading needs to see the Space; writing needs the editor role on it. A Space's base is copied from
the catalogue the first time it is opened. Every refusal says what to change (D-A-031); every write is journalled.
"""
import re

from core import audit, db, permissions
from core.errors import ApiError
from core.files import RawFile

from modules.agile import csv_io

from . import catalog, lists
from .data_tests import CATEGORIES, LEVELS, STATUSES, SUBJECTS

LIMITS = {"title": 200, "standard": 200, "section": 200, "level": 40, "method": 4, "objective": 3000,
          "acceptance": 2000, "means": 2000, "notes": 3000}
EDITABLE = ("title", "subject", "category", "standard", "section", "level", "method", "objective", "acceptance",
            "means", "notes", "status", "location", "equipment", "functions")
LABELS = {"test_id": "identifiant", "title": "titre", "subject": "sujet", "category": "category", "standard": "standard",
          "section": "section", "level": "niveau", "method": "méthode", "objective": "objectif",
          "acceptance": "acceptance criteria", "means": "moyens", "notes": "notes", "status": "status",
          "location": "test location", "equipment": "équipements", "functions": "functions"}
EXPORT = ["test_id", "title", "subject", "category", "standard", "section", "source", "level", "method", "status",
          "location", "equipment", "functions", "objective", "acceptance", "means", "notes", "procedure", "requirements"]
PREFIX = {"func": "FUN", "elec": "ELE", "emc": "EMC", "therm": "THR", "env": "ENV", "ingress": "IP", "mech": "MEC",
          "life": "LIF", "mat": "MAT", "sw": "SW", "usab": "USA", "prod": "PRD", "ver": "VER"}


def _code(value, mapping, label):
    """A code or its French label -> the code."""
    value = str(value or "").strip()
    if value in mapping:
        return value
    for code, text in mapping.items():
        if value.casefold() == text.casefold():
            return code
    raise ApiError(400, "{} « {} » inconnu(e). Valeurs acceptées : {}.".format(label, value[:60], ", ".join(mapping.values())))


def _location_code(conn, value):
    """A location given by its code or its label (CSV: « Laboratoire de l'école ») -> the code."""
    value = str(value or "").strip()
    for code, label in lists.labels(conn, "location").items():
        if value.casefold() in (code.casefold(), label.casefold()):
            return code
    return value


def clean(body, current=None, conn=None):
    out = {}
    for field in EDITABLE:
        if field not in body:
            continue
        value = body[field]
        value = "" if value is None else value
        if not isinstance(value, str):
            raise ApiError(400, "Champ « {} » : texte attendu.".format(LABELS[field]))
        value = value.strip()
        if field in LIMITS and len(value) > LIMITS[field]:
            raise ApiError(400, "Champ « {} » : {} caractères au maximum ({} reçus).".format(LABELS[field], LIMITS[field], len(value)))
        if field == "subject":
            value = _code(value, SUBJECTS, "Subject")
        if field == "category":
            value = _code(value, CATEGORIES, "Category")
        if field == "status" and value not in STATUSES:
            raise ApiError(400, "Status « {} » inconnu. Valeurs acceptées : {}.".format(value[:40], ", ".join(STATUSES)))
        if field == "method":
            letters = re.sub(r"[\s,;+/]", "", value.upper())
            if any(ch not in "IADT" for ch in letters):
                raise ApiError(400, "Method « {} » inconnue : lettres I, A, D, T (ex. « T » ou « AT »).".format(value[:10]))
            value = "".join(ch for ch in "IADT" if ch in letters)
        if field in ("location", "equipment", "functions") and conn is not None:  # D-B-082: central lists only
            kind = {"location": "location", "equipment": "equipment", "functions": "function"}[field]
            if field == "location":
                value = _location_code(conn, value)
            value = lists.check(conn, kind, value, current[field] if current is not None else "", single=field == "location")
        out[field] = value
    if "title" in out and not out["title"]:
        raise ApiError(400, "Le titre du test est obligatoire.")
    return out


def space(ctx, minimum="reader"):
    """(project id, key) of the Test Base asked for (D-B-097), its base copied from the catalogue if it has none."""
    key = str(ctx.query.get("space") or (ctx.body or {}).get("space") or catalog.KEY).strip().upper()
    row = ctx.conn.execute("SELECT id, key FROM projects WHERE key = ?", (key,)).fetchone()
    if row is None:
        raise ApiError(404, "Space « {} » introuvable. Correctif : choisissez un Space de la liste de Testing.".format(key[:20]))
    if row["key"] == catalog.KEY:
        _join(ctx, row["id"])
    elif permissions.project_role(ctx.conn, ctx.user, row["id"]) is None:
        raise ApiError(404, "Space « {} » introuvable ou non accessible.".format(key[:20]))
    if minimum == "editor":
        permissions.require_project_role(ctx.conn, ctx.user, row["id"], "editor")
    catalog.base(ctx.conn, row["id"], ctx.user["id"])
    return row["id"], row["key"]


def _row(conn, pid, test_id):
    row = conn.execute("SELECT * FROM testing_tests WHERE project_id = ? AND test_id = ?",
                       (pid, str(test_id or "").upper())).fetchone()
    if row is None:
        raise ApiError(404, "Test « {} » introuvable dans cette Test Base.".format(str(test_id)[:40]))
    return row


def _visible_requirements(conn, user, pid=None):
    """{test_id: [{key, title, status, external_id}]} for the requirements of the Space (D-B-097: its own base), or
    of every Space the user sees for the reference catalogue."""
    projects = {p["id"]: p["key"] for p in permissions.visible_projects(conn, user)}
    if pid is not None and pid != catalog.project_id(conn):
        projects = {k: v for k, v in projects.items() if k == pid}
    out = {}
    if not projects:
        return out
    marks = ",".join("?" * len(projects))
    for r in conn.execute(
            "SELECT i.project_id, i.number, i.title, s.name AS status, r.external_id, r.test_ref FROM agile_requirements r "
            "JOIN agile_issues i ON i.id = r.issue_id JOIN agile_statuses s ON s.id = i.status_id "
            "WHERE r.test_ref != '' AND r.kind = 'requirement' AND i.project_id IN ({})".format(marks), list(projects)):
        item = {"key": "{}-{}".format(projects[r["project_id"]], r["number"]), "title": r["title"], "status": r["status"],
                "external_id": r["external_id"]}
        for ref in catalog.split_refs(r["test_ref"]):
            out.setdefault(ref, []).append(item)
    return out


def _public(row, pages, linked):
    item = {k: row[k] for k in ("test_id", "title", "subject", "category", "standard", "section", "level", "method",
                                "objective", "acceptance", "means", "notes", "status", "origin", "updated_at",
                                "location", "equipment", "functions")}
    item["source"] = catalog.source_of(row)
    item["edited"] = bool(row["edited"])
    item["procedure"] = pages.get(row["subject"])
    item["requirements"] = len(linked.get(row["test_id"], []))
    return item


def _join(ctx, pid):
    """Like TOOLS (D-B-065): an account created after the last start-up becomes an editor of TESTING on first use."""
    if permissions.project_role(ctx.conn, ctx.user, pid) is None:
        ctx.conn.execute("INSERT INTO memberships (user_id, project_id, role) VALUES (?, ?, 'editor')", (ctx.user["id"], pid))
        audit.log_action(ctx.conn, ctx.user["id"], "testing_joined", "project", pid, None, ctx.ip)


def _can_edit(conn, user, pid):
    role = permissions.project_role(conn, user, pid)
    return role in ("editor", "admin")


def api_list(ctx):
    conn = ctx.conn
    ref = catalog.require_space(conn)
    pid, key = space(ctx)
    pages = catalog.procedure_pages(conn, ref)  # procedures: shared wiki TESTING
    linked = _visible_requirements(conn, ctx.user, pid)
    tests = [_public(r, pages, linked) for r in conn.execute("SELECT * FROM testing_tests WHERE project_id = ? ORDER BY test_id",
                                                             (pid,))]
    hub = conn.execute("SELECT id FROM dynamite_pages WHERE project_id = ? AND title = ?", (ref, catalog.HUB)).fetchone()
    return {"space": key, "reference": key == catalog.KEY, "hub_page": hub["id"] if hub else None,
            "can_edit": _can_edit(conn, ctx.user, pid), "tests": tests,
            "can_manage_lists": lists.can_manage(conn, ctx.user),
            "labels": {"subjects": SUBJECTS, "categories": CATEGORIES, "statuses": list(STATUSES), "levels": list(LEVELS),
                       "methods": {"I": "Inspection", "A": "Analysis", "D": "Demonstration", "T": "Test"}},
            "lists": _list_labels(conn)}


def _list_labels(conn):
    """{kind: [{code, label, category, active}]} for the pickers and filters."""
    out = {"location": [], "equipment": [], "function": []}
    for r in lists.entries(conn):
        if r["kind"] not in out:  # acronyms and definitions (D-A-037) are not pickers
            continue
        out[r["kind"]].append({"code": r["code"], "label": r["label"], "category": r["category"], "active": bool(r["active"])})
    return out


def api_options(ctx):
    """Light list for the « Test Procedure » field of Goldmine: every test not obsolete, grouped by subject."""
    rows = []
    if catalog.project_id(ctx.conn) is not None:
        pid, _key = space(ctx)
        rows = ctx.conn.execute("SELECT * FROM testing_tests WHERE project_id = ? ORDER BY subject, test_id", (pid,)).fetchall()
    return {"subjects": SUBJECTS, "categories": CATEGORIES,
            "functions": [{"code": r["code"], "label": r["label"], "active": bool(r["active"])}
                          for r in lists.entries(ctx.conn, "function")],
            "tests": [{"test_id": r["test_id"], "title": r["title"], "subject": r["subject"], "category": r["category"],
                       "status": r["status"], "method": r["method"], "functions": r["functions"],
                       "source": catalog.source_of(r)} for r in rows]}


def api_get(ctx):
    conn = ctx.conn
    ref = catalog.require_space(conn)
    pid, key = space(ctx)
    row = _row(conn, pid, ctx.params["tid"])
    pages = catalog.procedure_pages(conn, ref)
    linked = _visible_requirements(conn, ctx.user, pid)
    history = [dict(h) for h in conn.execute(
        "SELECT h.field, h.old_value, h.new_value, h.at, u.display_name AS who FROM testing_history h "
        "LEFT JOIN users u ON u.id = h.user_id WHERE h.test_row_id = ? ORDER BY h.id DESC LIMIT 100", (row["id"],))]
    return {"test": _public(row, pages, linked), "requirements": linked.get(row["test_id"], []), "history": history,
            "can_edit": _can_edit(conn, ctx.user, pid), "space": key}


def _history(ctx, row_id, field, old, new):
    ctx.conn.execute("INSERT INTO testing_history (test_row_id, user_id, field, old_value, new_value, at) "
                     "VALUES (?, ?, ?, ?, ?, ?)", (row_id, ctx.user["id"], field, old, new, db.utc_now()))


def _next_id(conn, pid, subject):
    prefix = "TST-{}-".format(PREFIX[subject])
    numbers = [int(m.group(1)) for (tid,) in conn.execute("SELECT test_id FROM testing_tests WHERE project_id = ? AND test_id LIKE ?",
                                                          (pid, prefix + "%"))
               for m in [re.fullmatch(re.escape(prefix) + r"(\d+)", tid)] if m]
    return "{}{:02d}".format(prefix, max(numbers or [0]) + 1)


def create(ctx, pid, body):
    fields = clean(body, None, ctx.conn)
    for need in ("title", "subject"):
        if not fields.get(need):
            raise ApiError(400, "Champ « {} » obligatoire pour un nouvel test.".format(LABELS[need]))
    fields.setdefault("category", "custom")
    fields.setdefault("status", "Draft")
    test_id = str(body.get("test_id") or "").strip().upper()
    if test_id:
        if not catalog.ID_RE.match(test_id) or len(test_id) > 30:
            raise ApiError(400, "Identifiant « {} » invalide : lettres, chiffres et tirets, ex. TST-CUS-30.".format(test_id[:40]))
        if ctx.conn.execute("SELECT 1 FROM testing_tests WHERE project_id = ? AND test_id = ?", (pid, test_id)).fetchone():
            raise ApiError(409, "Le test {} existe déjà. Correctif : ouvrez sa fiche pour le modifier.".format(test_id))
    else:
        test_id = _next_id(ctx.conn, pid, fields["subject"])
    now = db.utc_now()
    cols = sorted(fields)
    new_id = ctx.conn.execute(
        "INSERT INTO testing_tests (project_id, test_id, {}, origin, edited, created_by, created_at, updated_by, updated_at) "
        "VALUES (?, ?, {}, 'user', 1, ?, ?, ?, ?)".format(", ".join(cols), ", ".join("?" for _ in cols)),
        (pid, test_id) + tuple(fields[c] for c in cols) + (ctx.user["id"], now, ctx.user["id"], now)).lastrowid
    _history(ctx, new_id, "création", None, fields["title"])
    audit.log_action(ctx.conn, ctx.user["id"], "testing_test_create", "testing_test", new_id, {"test_id": test_id}, ctx.ip)
    return test_id


def update(ctx, row, body):
    changes = {k: v for k, v in clean(body, row, ctx.conn).items() if (row[k] or "") != v}
    if not changes:
        return []
    ctx.conn.execute("UPDATE testing_tests SET {}, edited = 1, updated_by = ?, updated_at = ? WHERE id = ?".format(
        ", ".join(k + " = ?" for k in changes)), tuple(changes.values()) + (ctx.user["id"], db.utc_now(), row["id"]))
    for field, value in changes.items():
        long = field in ("objective", "acceptance", "means", "notes")
        _history(ctx, row["id"], LABELS[field], None if long else row[field] or None, "(modifié)" if long else value or None)
    audit.log_action(ctx.conn, ctx.user["id"], "testing_test_update", "testing_test", row["id"],
                     {"test_id": row["test_id"], "fields": sorted(changes)}, ctx.ip)
    return sorted(changes)


def api_create(ctx):
    catalog.require_space(ctx.conn)
    pid, _key = space(ctx, "editor")
    return {"test_id": create(ctx, pid, ctx.body)}


def api_update(ctx):
    catalog.require_space(ctx.conn)
    pid, _key = space(ctx, "editor")
    return {"ok": True, "changed": update(ctx, _row(ctx.conn, pid, ctx.params["tid"]), ctx.body)}


# --------------------------------------------------------------------------
# CSV
# --------------------------------------------------------------------------
def api_export(ctx):
    listing = api_list(ctx)
    wanted = set(catalog.split_refs(ctx.query.get("ids")))
    linked = _visible_requirements(ctx.conn, ctx.user, space(ctx)[0])
    locations = lists.labels(ctx.conn, "location")
    rows = []
    for t in listing["tests"]:
        if wanted and t["test_id"] not in wanted:
            continue
        row = {f: t.get(f, "") for f in EXPORT}
        row["subject"] = SUBJECTS.get(t["subject"], t["subject"])
        row["category"] = CATEGORIES.get(t["category"], t["category"])
        row["procedure"] = (t["procedure"] or {}).get("title", "")
        row["location"] = locations.get(t["location"], t["location"])
        row["requirements"] = ", ".join(r["key"] for r in linked.get(t["test_id"], []))
        rows.append(row)
    return RawFile.csv(csv_io._write_csv(EXPORT, rows), "testing_essais_{}.csv".format(listing["space"]))


def api_import(ctx):
    """mode preview (nothing written) or apply; lines matched by test_id; an empty test_id creates a test."""
    catalog.require_space(ctx.conn)
    pid, _key = space(ctx, "editor")
    mode = ctx.body.get("mode") or "apply"
    if mode not in ("preview", "apply"):
        raise ApiError(400, "Mode d'import « {} » inconnu (preview ou apply).".format(str(mode)[:20]))
    rows = csv_io._read_csv_body(ctx, ["test_id", "title"])
    report = []
    ctx.conn.execute("SAVEPOINT testing_import")
    try:
        for index, row in enumerate(rows):
            if not any((v or "").strip() for v in row.values() if isinstance(v, str)):
                continue
            body = {k: row[k] for k in EDITABLE if k in row and row[k] is not None}
            tid = (row.get("test_id") or "").strip().upper()
            entry = {"line": index + 2, "test_id": tid or "(nouveau)", "status": "", "reason": "", "changed": []}
            try:
                existing = ctx.conn.execute("SELECT * FROM testing_tests WHERE project_id = ? AND test_id = ?",
                                            (pid, tid)).fetchone() if tid else None
                if existing is None:
                    entry["test_id"] = create(ctx, pid, dict(body, test_id=tid))
                    entry["status"] = "créé"
                else:
                    entry["changed"] = [LABELS[f] for f in update(ctx, existing, body)]
                    entry["status"] = "mis à jour" if entry["changed"] else "inchangé"
            except ApiError as exc:
                entry["status"], entry["reason"] = "refusé", exc.message
            report.append(entry)
    except Exception:
        ctx.conn.execute("ROLLBACK TO testing_import")
        ctx.conn.execute("RELEASE testing_import")
        raise
    if mode == "preview":
        ctx.conn.execute("ROLLBACK TO testing_import")
    ctx.conn.execute("RELEASE testing_import")
    return {"mode": mode, "report": report}
