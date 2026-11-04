"""Goldmine: engineering requirements inside Agile (D-A-032).

A requirement is an Agile ticket whose type has is_requirement = 1, with
its own workflow (client reception -> verification) and a row of extra
fields in agile_requirements. Traceability to work tickets reuses the
'implements' link (D-A-016). The list endpoint also computes trace gaps,
so the screen can say what is missing rather than just show data
(D-A-031, dynamic feedback).
"""
import re

from core import db, validate
from core.errors import ApiError

from . import common as c
from . import goldmine_need
from . import issues as issues_mod

# D-B-085: technical vocabulary in English (docs/GLOSSARY_EN.md); codes unchanged.
SOURCES = {"client": "Customer", "standard": "Standard", "internal": "Internal", "derived": "Derived"}
# D-B-056: « regulatory » is shown « Standard / Regulatory »; people's safety is its own category.
CATEGORIES = {"functional": "Functional", "performance": "Performance", "interface": "Interface",
              "environmental": "Environmental", "safety": "Safety", "personnel_safety": "Personnel Safety",
              "regulatory": "Standard / Regulatory"}
# D-B-055: phase of the product life cycle (one per requirement, gives the row colour).
LIFECYCLE = {"design": "Design", "cost": "Cost (DTC)", "manufacturing": "Part Manufacturing (DFM)",
             "assembly": "Assembly (DFA)", "test": "Test & Verification (DFT)", "transport": "Transport & Storage",
             "installation": "Installation & Integration", "operation": "Operation (Use)",
             "maintenance": "Maintenance & Repair", "appearance": "Appearance & Appeal",
             "second_life": "Second Life", "end_of_life": "End of Life (Disassembly, Recycling)"}
# D-B-064: a Goldmine item is a requirement or a stakeholder need; requirements derive from needs.
KINDS = {"requirement": "Requirement", "need": "Need"}
STAKEHOLDERS = {"client": "Customer / Buyer", "user": "End User", "authority": "Standards Body / Regulator",
                "integrator": "Integrator / Distributor", "production": "Production / Assemblers", "repair": "Maintenance & Repair",
                "logistics": "Logistics", "recycling": "Recycling / End of Life", "marketing": "Marketing / Sales",
                "management": "Project Management", "safety": "Health & Safety"}
CRITICALITY = ("", "A", "B", "C", "D", "E")
METHODS = {"I": "Inspection", "A": "Analysis", "D": "Demonstration", "T": "Test"}
TEXT_LIMITS = {"derived_from": 400, "external_id": 40, "source_doc": 200, "statement": 4000, "rationale": 4000,
               "acceptance_criteria": 2000, "allocation": 120, "verification_ref": 200, "revision": 10,
               "test_ref": 400, "functions": 200}
FIELDS = ("external_id", "kind", "stakeholder", "derived_from", "source", "source_doc", "statement", "rationale",
          "category", "lifecycle", "criticality",
          "verification_method", "acceptance_criteria", "allocation", "verification_ref", "test_ref",
          "functions", "revision", "received_at") + goldmine_need.FIELDS  # D-B-086: Need Status
FIELD_LABELS = {"external_id": "External ID", "source": "Source", "source_doc": "Source Document",
                "statement": "Statement", "rationale": "Rationale", "category": "Category",
                "lifecycle": "Life-Cycle Phase", "kind": "Kind", "stakeholder": "Stakeholder",
                "derived_from": "Derived From",
                "criticality": "Criticality", "verification_method": "Verification Method",
                "acceptance_criteria": "Acceptance Criteria", "allocation": "Allocation",
                "verification_ref": "Verification Ref.", "test_ref": "Test Procedure", "functions": "Functions",
                "revision": "Revision", "received_at": "Received Date", **goldmine_need.FIELD_LABELS}
from .vocab import LEGACY_LABELS  # noqa: E402,F401  (former French labels, still accepted by the CSV import)

# Reception -> verification (docs/AGILE_ARCHITECTURE.md §8). "Accepted" is
# the requirement *validation* (right requirement, agreed with the
# client); "Verified" is the *verification* (the product meets it).
WORKFLOW_NAME = "Requirement Workflow"
STATUSES = [("Received", "todo", 1), ("In Analysis", "in_progress", 0),
            ("Customer Clarification", "in_progress", 0), ("Accepted", "in_progress", 0),
            ("Allocated", "in_progress", 0), ("Implemented", "in_progress", 0),
            ("In Verification", "in_progress", 0), ("Verified", "done", 0),
            ("Rejected", "done", 0), ("Obsolete", "done", 0)]
TRANSITIONS = [
    ("Received", "In Analysis", "Analyze"),
    ("In Analysis", "Customer Clarification", "Request Clarification"),
    ("Customer Clarification", "In Analysis", "Customer Answer Received"),
    ("In Analysis", "Accepted", "Accept (validated with customer)"),
    ("In Analysis", "Rejected", "Reject"),
    ("Accepted", "Allocated", "Allocate to Subsystem"),
    ("Allocated", "Implemented", "Declare Implemented"),
    ("Implemented", "In Verification", "Start Verification"),
    ("In Verification", "Verified", "Verification Passed"),
    ("In Verification", "Implemented", "Verification Failed"),
    ("Verified", "Obsolete", "Make Obsolete (new revision)"),
]


VERIFIED = "Verified"


def verification_guard(conn, issue_id, target_status_name):
    """A requirement may only become "Verified" once the test (or other
    evidence) that verifies it is named. Returns (message, fix) or None."""
    if target_status_name != VERIFIED:
        return None
    fields = fields_of(conn, issue_id)
    missing = [FIELD_LABELS[f] for f in ("verification_method", "verification_ref") if not fields[f]]
    if not missing:
        return None
    return ("Passage à « Verified » impossible : {} manquant(e)(s).".format(", ".join(missing)),
            "Renseignez la méthode (I/A/D/T) et la référence du test ou du rapport de vérification "
            "dans la fiche requirement, puis refaites la transition.")


def requirement_type(conn, project_id):
    return conn.execute("SELECT * FROM agile_issue_types WHERE project_id = ? AND is_requirement = 1 "
                        "ORDER BY position LIMIT 1", (project_id,)).fetchone()


def api_setup(ctx):
    """Create the Requirement type and its workflow on a project (admin)."""
    project_id, _ = c.access(ctx, "admin")
    return enable(ctx, project_id)


def enable(ctx, project_id):
    """Also run when a project is created (D-B-012)."""
    conn = ctx.conn
    existing = requirement_type(conn, project_id)
    if existing:
        raise ApiError(409, "Goldmine est déjà activé ici (type « {} »). Pour changer son "
                            "workflow : Agile → Paramètres → Types.".format(existing["name"]))
    if conn.execute("SELECT 1 FROM agile_workflows WHERE project_id = ? AND name = ?",
                    (project_id, WORKFLOW_NAME)).fetchone():
        raise ApiError(409, "Un workflow « {} » existe déjà. Correctif : renommez-le dans "
                            "Paramètres, puis réessayez.".format(WORKFLOW_NAME))
    if conn.execute("SELECT 1 FROM agile_issue_types WHERE project_id = ? AND name = 'Requirement'",
                    (project_id,)).fetchone():
        raise ApiError(409, "Un type « Requirement » existe déjà sans être marqué requirement. Correctif : "
                            "cochez « Rôle spécial » sur ce type dans Paramètres → Types, ou renommez-le.")
    wf = conn.execute("INSERT INTO agile_workflows (project_id, name) VALUES (?, ?)",
                      (project_id, WORKFLOW_NAME)).lastrowid
    ids = {}
    for pos, (name, cat, initial) in enumerate(STATUSES):
        ids[name] = conn.execute("INSERT INTO agile_statuses (workflow_id, name, category, position, "
                                 "is_initial) VALUES (?, ?, ?, ?, ?)", (wf, name, cat, pos, initial)).lastrowid
    for src, dst, name in TRANSITIONS:
        conn.execute("INSERT INTO agile_transitions (workflow_id, from_status_id, to_status_id, name) "
                     "VALUES (?, ?, ?, ?)", (wf, ids[src], ids[dst], name))
    position = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM agile_issue_types "
                            "WHERE project_id = ?", (project_id,)).fetchone()[0]
    tid = conn.execute("INSERT INTO agile_issue_types (project_id, name, icon_key, workflow_id, "
                       "is_subtask, is_requirement, bucket, position) VALUES (?, 'Requirement', 'requirement', ?, 0, 1, 'goldmine', ?)",
                       (project_id, wf, position)).lastrowid
    c.log(ctx, "goldmine_enable", "project", project_id, {"type": tid, "workflow": wf})
    return {"type_id": tid, "workflow_id": wf}


# --------------------------------------------------------------------------
# Field validation -- every refusal says what to change (D-A-031)
# --------------------------------------------------------------------------
def _clean(body, current):
    out = {}
    for field in FIELDS:
        if field not in body:
            continue
        value = body[field]
        value = "" if value is None else value
        if not isinstance(value, str):
            raise ApiError(400, "Champ « {} » : texte attendu.".format(FIELD_LABELS[field]))
        value = value.strip()
        limit = TEXT_LIMITS.get(field) or goldmine_need.TEXT_LIMITS.get(field)
        if limit and len(value) > limit:
            raise ApiError(400, "Champ « {} » : {} caractères au maximum ({} reçus).".format(
                FIELD_LABELS[field], limit, len(value)))
        if field == "source" and value not in SOURCES:
            raise ApiError(400, "Source « {} » inconnue. Valeurs acceptées : {}.".format(
                value, ", ".join(SOURCES.values())))
        if field == "category" and value not in CATEGORIES:
            raise ApiError(400, "Category « {} » inconnue. Valeurs acceptées : {}.".format(
                value, ", ".join(CATEGORIES.values())))
        if field == "kind" and value not in KINDS:
            raise ApiError(400, "Nature « {} » inconnue : Requirement (requirement) ou Need (need).".format(value))
        if field == "stakeholder" and value and value not in STAKEHOLDERS:
            raise ApiError(400, "Stakeholder « {} » inconnue. Valeurs acceptées : {}, ou vide.".format(
                value, ", ".join(STAKEHOLDERS.values())))
        if field in ("derived_from", "test_ref", "functions"):
            value = ", ".join(dict.fromkeys(x for x in re.split(r"[\s,;]+", value.upper()) if x))
        if field == "lifecycle" and value and value not in LIFECYCLE:
            raise ApiError(400, "Life-Cycle Phase « {} » inconnue. Valeurs acceptées : {}, ou vide.".format(
                value, ", ".join(LIFECYCLE.values())))
        if field == "criticality" and value.upper() not in CRITICALITY:
            raise ApiError(400, "Criticité « {} » inconnue. Valeurs acceptées : A, B, C, D, E "
                                "(A = la plus haute), ou vide.".format(value))
        if field == "criticality":
            value = value.upper()
        if field == "verification_method":
            letters = re.sub(r"[\s,;+/]", "", value.upper())
            bad = [ch for ch in letters if ch not in METHODS]
            if bad:
                raise ApiError(400, "Verification Method « {} » inconnue. Utilisez une ou "
                                    "plusieurs lettres IADT : I = Inspection, A = Analysis, "
                                    "D = Demonstration, T = Test (ex. « TA »).".format("".join(bad)))
            value = "".join(ch for ch in "IADT" if ch in letters)
        if field == "received_at" and value and not c.is_real_date(value):
            raise ApiError(400, "Date de réception « {} » invalide : format aaaa-mm-jj.".format(value))
        if field == "received_at" and not value:
            value = None
        if field in goldmine_need.FIELDS:
            kind = body.get("kind") or (current or {}).get("kind") or "requirement"
            value = goldmine_need.clean(field, value, kind)
        out[field] = value
    if "statement" in out and not out["statement"] and (current is None or "statement" in body):
        raise ApiError(400, "Le Statement est obligatoire. Correctif : rédigez le requirement sous la "
                            "forme « Le système doit… ».")
    if out.get("kind") == "requirement" and current and current.get("need_status"):
        out["need_status"] = ""  # D-B-086: the maturity belongs to needs only
    return out


def test_guard(conn, merged, previous="", project_id=None):
    """D-B-079: a requirement always names at least one test of its Space's Test Base (« Test Procedure », D-B-097)."""
    from modules.testing import catalog as testing  # local import: the Testing module reads agile tables too
    refusal = testing.check_refs(conn, merged.get("kind"), merged.get("test_ref"), previous, project_id)
    if refusal:
        raise ApiError(400, "{} Correctif : {}".format(*refusal))


def function_guard(conn, fields, previous=""):
    """D-B-082: the functions of a requirement come from the central list of product functions (Testing → Listes)."""
    if "functions" in fields:
        from modules.testing import lists
        fields["functions"] = lists.check(conn, "function", fields["functions"], previous)


def _requirement_issue(ctx, project_id, number):
    row = c.get_issue(ctx.conn, project_id, number)
    itype = ctx.conn.execute("SELECT is_requirement FROM agile_issue_types WHERE id = ?",
                             (row["type_id"],)).fetchone()
    if not itype["is_requirement"]:
        raise ApiError(400, "Ce ticket n'est pas un requirement. Correctif : changez son type pour un "
                            "type marqué Requirement, ou créez-la depuis Goldmine.")
    return row


def fields_of(conn, issue_id):
    row = conn.execute("SELECT * FROM agile_requirements WHERE issue_id = ?", (issue_id,)).fetchone()
    if row is None:
        return {field: ("A" if field == "revision" else ("client" if field == "source" else
                        ("functional" if field == "category" else ("requirement" if field == "kind" else
                         ("" if field != "received_at" else None)))))
                for field in FIELDS}
    return {field: row[field] for field in FIELDS}


def api_update_fields(ctx):
    project_id, role = c.access(ctx, "editor")
    row = _requirement_issue(ctx, project_id, c.issue_number(ctx))
    c.require_edit(ctx, role, row)
    current = fields_of(ctx.conn, row["id"])
    changes = {k: v for k, v in _clean(ctx.body, current).items() if current.get(k) != v}
    if not changes:
        return {"ok": True, "changed": []}
    function_guard(ctx.conn, changes, current.get("functions"))
    merged = dict(current, **changes)
    test_guard(ctx.conn, merged, current.get("test_ref"), project_id)
    ctx.conn.execute(
        "INSERT INTO agile_requirements (issue_id, {cols}) VALUES (?, {marks}) "
        "ON CONFLICT(issue_id) DO UPDATE SET {sets}".format(
            cols=", ".join(FIELDS), marks=", ".join("?" for _ in FIELDS),
            sets=", ".join("{0} = excluded.{0}".format(f) for f in FIELDS)),
        (row["id"],) + tuple(merged[f] for f in FIELDS))
    ctx.conn.execute("UPDATE agile_issues SET updated_at = ? WHERE id = ?", (db.utc_now(), row["id"]))
    for field, value in changes.items():
        old = current.get(field)
        if field in ("statement", "rationale", "acceptance_criteria"):
            old, value = None, "(modifié)"
        c.add_history(ctx, row["id"], "req:" + FIELD_LABELS[field], old or None, value or None)
    c.log(ctx, "goldmine_fields_update", "agile_issue", row["id"], {"fields": sorted(changes)})
    return {"ok": True, "changed": sorted(changes)}


def api_create(ctx):
    """Create a requirement (ticket + fields) in one call."""
    project_id, _ = c.access(ctx, "editor")
    rtype = requirement_type(ctx.conn, project_id)
    if rtype is None:
        raise ApiError(409, "Goldmine n'est pas activé sur ce projet. Correctif : un administrateur "
                            "clique sur « Activer Goldmine » dans l'onglet Goldmine.")
    fields = _clean(ctx.body, None)
    if not fields.get("statement"):
        raise ApiError(400, "Le Statement est obligatoire. Correctif : rédigez le requirement sous la "
                            "forme « Le système doit… ».")
    function_guard(ctx.conn, fields)
    test_guard(ctx.conn, dict(fields_of(ctx.conn, -1), **fields), "", project_id)
    title = (ctx.body.get("title") or "").strip() or fields["statement"][:120]
    body = {"type_id": rtype["id"], "title": title, "priority": ctx.body.get("priority") or "medium",
            "parent_number": ctx.body.get("parent_number"), "labels": ctx.body.get("labels") or []}
    if "assignee_id" in ctx.body:
        body["assignee_id"] = ctx.body["assignee_id"]
    original, ctx.body = ctx.body, body
    try:
        created = issues_mod.api_create(ctx)
    finally:
        ctx.body = original
    issue = c.get_issue(ctx.conn, project_id, created["number"])
    merged = dict(fields_of(ctx.conn, issue["id"]), **fields)
    ctx.conn.execute("INSERT INTO agile_requirements (issue_id, {}) VALUES (?, {})".format(
        ", ".join(FIELDS), ", ".join("?" for _ in FIELDS)),
        (issue["id"],) + tuple(merged[f] for f in FIELDS))
    return created


# --------------------------------------------------------------------------
# List with traceability gaps
# --------------------------------------------------------------------------
def api_list(ctx):
    project_id, _ = c.access(ctx)
    conn = ctx.conn
    rtype = requirement_type(conn, project_id)
    if rtype is None:
        return {"enabled": False}
    key = c.project_key(conn, project_id)
    rows = conn.execute(
        "SELECT i.id, i.number, i.title, i.updated_at, i.client_summary, i.assignee_id, s.name AS status_name, s.category AS status_category, "
        "s.position AS status_position, u.display_name AS assignee_name, r.* FROM agile_issues i "
        "JOIN agile_issue_types t ON t.id = i.type_id AND t.is_requirement = 1 "
        "LEFT JOIN users u ON u.id = i.assignee_id "
        "JOIN agile_statuses s ON s.id = i.status_id "
        "LEFT JOIN agile_requirements r ON r.issue_id = i.id "
        "WHERE i.project_id = ? ORDER BY i.number", (project_id,)).fetchall()
    implemented = {}
    for link in conn.execute(
            "SELECT l.target_id, p.key, si.number FROM agile_links l "
            "JOIN agile_issues si ON si.id = l.source_id JOIN projects p ON p.id = si.project_id "
            "JOIN agile_issues ti ON ti.id = l.target_id "
            "WHERE l.link_type = 'implements' AND ti.project_id = ?", (project_id,)):
        implemented.setdefault(link["target_id"], []).append("{}-{}".format(link["key"], link["number"]))
    # Statuses from which a requirement is expected to be traced/verified.
    after_acceptance = {"Accepted", "Allocated", "Implemented", "In Verification", "Verified"}
    needs_ref = {"In Verification", "Verified"}
    items, gaps = [], {"no_implementation": [], "no_verification_ref": [], "no_method": [],
                       "no_acceptance": [], "no_need": [], "unknown_need": [], "no_test": []}
    last = last_changes(conn, project_id)
    from modules.testing import catalog as testing
    known_tests = testing.sources(conn, project_id)
    for r in rows:
        item = {"key": "{}-{}".format(key, r["number"]), "number": r["number"], "title": r["title"],
                "status_name": r["status_name"], "status_category": r["status_category"],
                "updated_at": r["updated_at"], "implemented_by": implemented.get(r["id"], []),
                # « Mes éléments » filters on these (D-B-071); they were missing, so the filter emptied the list
                "assignee_id": r["assignee_id"], "assignee_name": r["assignee_name"] or ""}
        item.update(fields_of(conn, r["id"]))
        item["client_summary"] = r["client_summary"] or ""
        item["test_source"] = testing.source_text(conn, item["test_ref"], known_tests)  # D-B-082: traceability
        item["last_change"] = last.get(r["id"])
        items.append(item)
    resolve_needs(items, gaps)
    for item in items:
        if item["kind"] == "need":
            continue  # a need is traced by the requirements derived from it, not verified itself
        r = {"status_name": item["status_name"], "status_category": item["status_category"]}
        if r["status_name"] in after_acceptance and not item["implemented_by"]:
            gaps["no_implementation"].append(item["key"])
        if r["status_name"] in needs_ref and not item["verification_ref"]:
            gaps["no_verification_ref"].append(item["key"])
        if r["status_category"] != "done" and not item["verification_method"]:
            gaps["no_method"].append(item["key"])
        if r["status_name"] in after_acceptance and not item["acceptance_criteria"]:
            gaps["no_acceptance"].append(item["key"])
        if r["status_category"] != "done" and not item["test_ref"]:
            gaps["no_test"].append(item["key"])  # D-B-079: requirements saved before « Test Procedure »
    return {"enabled": True, "type": dict(rtype), "requirements": items, "gaps": gaps,
            "labels": {"sources": SOURCES, "categories": CATEGORIES, "methods": METHODS, "lifecycle": LIFECYCLE,
                       "kinds": KINDS, "stakeholders": STAKEHOLDERS, **goldmine_need.labels()}}


def resolve_needs(items, gaps):
    """D-B-064: « dérivée de » holds need IDs (external ID or key); give each item the keys of its needs and each
    need the requirements derived from it; list requirements without a need and references to unknown needs."""
    needs = {}
    for it in items:
        if it["kind"] == "need":
            needs[it["key"].upper()] = it
            if it["external_id"]:
                needs[it["external_id"].upper()] = it
            it["derived_requirements"] = []
    for it in items:
        it["needs"] = []
        refs = [x for x in (it.get("derived_from") or "").split(", ") if x]
        for ref in refs:
            need = needs.get(ref)
            if need is None:
                gaps["unknown_need"].append(it["key"])
                continue
            it["needs"].append(need["key"])
            if it["kind"] == "requirement":
                need["derived_requirements"].append(it["key"])
        if it["kind"] == "requirement" and not refs and it["status_category"] != "done":
            gaps["no_need"].append(it["key"])


def last_changes(conn, project_id):
    """D-B-059: last change of each requirement -- when (UTC), who (3-letter key) and the stamp
    JJMMAAAA-INI in local time. From the ticket history; a requirement never changed since its
    creation shows its creation and its author."""
    import datetime as dt
    from .qa import user_initials
    out, names = {}, {}
    rows = conn.execute(
        "SELECT i.id, COALESCE(h.ts, i.created_at) AS ts, COALESCE(h.user_id, i.reporter_id) AS user_id FROM agile_issues i "
        "JOIN agile_issue_types t ON t.id = i.type_id AND t.is_requirement = 1 "
        "LEFT JOIN agile_history h ON h.id = (SELECT MAX(id) FROM agile_history WHERE issue_id = i.id) "
        "WHERE i.project_id = ?", (project_id,)).fetchall()
    for r in rows:
        uid = r["user_id"]
        if uid not in names:
            user = conn.execute("SELECT display_name FROM users WHERE id = ?", (uid,)).fetchone() if uid else None
            names[uid] = (user_initials(conn, uid) if user else "SYS", user["display_name"] if user else "Système")
        initials, name = names[uid]
        try:
            local = dt.datetime.fromisoformat(r["ts"].replace("Z", "+00:00")).astimezone()
        except (ValueError, AttributeError):
            local = None
        out[r["id"]] = {"at": r["ts"], "by": initials, "name": name,
                        "stamp": "{}-{}".format(local.strftime("%d%m%Y"), initials) if local else initials}
    return out
