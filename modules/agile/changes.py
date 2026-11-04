"""Agile "Change Management" (D-B-010, D-B-011): PR, software bugs and ECN.

A PR (problem report) or bug is analysed, then either closed with its root
cause or derived into one or more ECN (link "resolves": the ECN treats the
problem). An ECN goes through the CCB -- draft, submitted, review,
approved, implementation (split into ECN sub-tasks), verification, closed.
Guards refuse a transition whose preconditions are missing and say what to
fill in (D-A-031). These types live in the "change" bucket: they never
appear on the Agile board, backlog or ticket list, only in Change Management.
"""
from core import db
from core.errors import ApiError
from core.files import RawFile

from . import change_fields as cf
from . import common as c
from . import issues as issues_mod

PROBLEM_WF = "PR / Bug Workflow"
PROBLEM_STATUSES = [("Open", "todo", 1), ("In Analysis", "in_progress", 0), ("Derived to ECN", "in_progress", 0),
                    ("Closed", "done", 0), ("Rejected", "done", 0)]
PROBLEM_TRANSITIONS = [("Open", "In Analysis", "Analyze", "editor"),
                       ("In Analysis", "Derived to ECN", "Derive to ECN", "editor"),
                       ("In Analysis", "Closed", "Close without ECN (cause addressed)", "editor"),
                       ("Derived to ECN", "Closed", "Close (ECN closed)", "editor"),
                       ("In Analysis", "Rejected", "Reject", "editor"),
                       ("Rejected", "Open", "Reopen", "editor"),
                       ("Closed", "Open", "Reopen", "editor")]
ECN_WF = "ECN Workflow (Change Management)"
ECN_STATUSES = [("Draft", "todo", 1), ("Submitted", "in_progress", 0), ("CCB Review", "in_progress", 0),
                ("Approved", "in_progress", 0), ("In Implementation", "in_progress", 0),
                ("In Verification", "in_progress", 0), ("Closed", "done", 0), ("Rejected", "done", 0),
                ("Cancelled", "done", 0)]
ECN_TRANSITIONS = [("Draft", "Submitted", "Submit to CCB", "editor"),
                   ("Submitted", "CCB Review", "Start CCB Review", "editor"),
                   ("CCB Review", "Approved", "Approve (CCB)", "admin"),
                   ("CCB Review", "Rejected", "Reject (CCB)", "admin"),
                   ("CCB Review", "Draft", "Return for Correction", "editor"),
                   ("Approved", "In Implementation", "Start Implementation", "editor"),
                   ("In Implementation", "In Verification", "Implementation Done", "editor"),
                   ("In Verification", "Closed", "Close ECN", "editor"),
                   ("In Verification", "In Implementation", "Resume Implementation", "editor"),
                   ("Draft", "Cancelled", "Cancel", "editor"),
                   ("Submitted", "Cancelled", "Cancel", "editor")]
# Existing tickets moved to a new workflow: status category -> new status.
MIGRATE = {"problem": {"todo": "Open", "in_progress": "In Analysis", "done": "Closed"},
           "ecn": {"todo": "Draft", "in_progress": "In Implementation", "done": "Closed"}}
ROLE_NAMES = {"pr": "PR", "bug": "Bug", "ecn": "ECN", "ecn_task": "ECN Task"}


def _role(conn, type_id):
    return conn.execute("SELECT change_role FROM agile_issue_types WHERE id = ?", (type_id,)).fetchone()[0]


def types_by_role(conn, project_id):
    return {r["change_role"]: dict(r) for r in conn.execute(
        "SELECT * FROM agile_issue_types WHERE project_id = ? AND change_role != '' ORDER BY position",
        (project_id,))}


def _linked(conn, issue_id, direction):
    """ECN treating a problem (direction 'in' on the problem) or problems an
    ECN treats ('out' on the ECN), with their status."""
    this, other = ("target_id", "source_id") if direction == "in" else ("source_id", "target_id")
    rows = conn.execute(
        "SELECT o.id, o.number, o.title, p.key AS project_key, s.name AS status_name, s.category AS status_category "
        "FROM agile_links l JOIN agile_issues o ON o.id = l.{other} JOIN projects p ON p.id = o.project_id "
        "JOIN agile_statuses s ON s.id = o.status_id WHERE l.{this} = ? AND l.link_type = 'resolves' "
        "ORDER BY o.number".format(this=this, other=other), (issue_id,)).fetchall()
    return [dict(r, key="{}-{}".format(r["project_key"], r["number"])) for r in rows]


# --------------------------------------------------------------------------
# Setup (admin): workflows, types, migration of existing ECN / bug tickets
# --------------------------------------------------------------------------
def _workflow(conn, project_id, name, statuses, transitions):
    row = conn.execute("SELECT id FROM agile_workflows WHERE project_id = ? AND name = ?", (project_id, name)).fetchone()
    if row:
        ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM agile_statuses WHERE workflow_id = ?",
                                                        (row["id"],))}
        return row["id"], ids
    wf = conn.execute("INSERT INTO agile_workflows (project_id, name) VALUES (?, ?)", (project_id, name)).lastrowid
    ids = {}
    for pos, (sname, cat, initial) in enumerate(statuses):
        ids[sname] = conn.execute("INSERT INTO agile_statuses (workflow_id, name, category, position, is_initial) "
                                  "VALUES (?, ?, ?, ?, ?)", (wf, sname, cat, pos, initial)).lastrowid
    for src, dst, tname, role in transitions:
        conn.execute("INSERT INTO agile_transitions (workflow_id, from_status_id, to_status_id, name, min_role) "
                     "VALUES (?, ?, ?, ?, ?)", (wf, ids[src], ids[dst], tname, role))
    return wf, ids


def _adopt(ctx, project_id, type_row, role, wf_id, status_ids, mapping):
    """Move an existing type (and its tickets) into Goldmine and its new workflow."""
    conn = ctx.conn
    if type_row["workflow_id"] != wf_id:
        for issue in conn.execute("SELECT i.id, s.category, s.name FROM agile_issues i JOIN agile_statuses s "
                                  "ON s.id = i.status_id WHERE i.type_id = ?", (type_row["id"],)).fetchall():
            target = mapping[issue["category"]]
            conn.execute("UPDATE agile_issues SET status_id = ? WHERE id = ?", (status_ids[target], issue["id"]))
            c.add_history(ctx, issue["id"], "status", issue["name"], target + " (passage à la gestion des changements)")
    conn.execute("UPDATE agile_issue_types SET bucket = 'change', change_role = ?, workflow_id = ? WHERE id = ?",
                 (role, wf_id, type_row["id"]))


def api_setup(ctx):
    project_id, _ = c.access(ctx, "admin")
    return enable(ctx, project_id)


def enable(ctx, project_id):
    """Also run when a project is created (D-B-012)."""
    conn = ctx.conn
    if "ecn" in types_by_role(conn, project_id):
        raise ApiError(409, "La gestion des changements est déjà activée sur ce projet.")
    pwf, pids = _workflow(conn, project_id, PROBLEM_WF, PROBLEM_STATUSES, PROBLEM_TRANSITIONS)
    ewf, eids = _workflow(conn, project_id, ECN_WF, ECN_STATUSES, ECN_TRANSITIONS)
    default_wf = conn.execute("SELECT id FROM agile_workflows WHERE project_id = ? AND is_default = 1",
                              (project_id,)).fetchone()["id"]
    wanted = [("pr", "PR", "pr", pwf, pids, MIGRATE["problem"], 0),
              ("bug", "Bug", "bug", pwf, pids, MIGRATE["problem"], 0),
              ("ecn", "ECN", "ecn", ewf, eids, MIGRATE["ecn"], 0),
              ("ecn_task", "ECN Task", "subtask", default_wf, None, None, 1)]
    done = []
    for role, name, icon, wf, sids, mapping, sub in wanted:
        existing = conn.execute("SELECT * FROM agile_issue_types WHERE project_id = ? AND change_role = '' AND "
                                "is_requirement = 0 AND (icon_key = ? AND ? != 'subtask' OR name = ?) ORDER BY position LIMIT 1",
                                (project_id, icon, icon, name)).fetchone()
        if existing is not None:
            if sids:
                _adopt(ctx, project_id, existing, role, wf, sids, mapping)
            else:
                conn.execute("UPDATE agile_issue_types SET bucket = 'change', change_role = ? WHERE id = ?",
                             (role, existing["id"]))
            done.append("{} (existant, déplacé dans Change Management)".format(existing["name"]))
            continue
        position = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM agile_issue_types WHERE project_id = ?",
                                (project_id,)).fetchone()[0]
        conn.execute("INSERT INTO agile_issue_types (project_id, name, icon_key, workflow_id, is_subtask, position, "
                     "bucket, change_role) VALUES (?, ?, ?, ?, ?, ?, 'change', ?)",
                     (project_id, name, icon, wf, sub, position, role))
        done.append(name)
    c.log(ctx, "goldmine_changes_enable", "project", project_id, {"types": done})
    return {"ok": True, "types": done}


# --------------------------------------------------------------------------
# Guards (ticket page and CSV import)
# --------------------------------------------------------------------------
def transition_guard(conn, issue_row, target):
    role = _role(conn, issue_row["type_id"])
    if role in ("pr", "bug"):
        ecns = _linked(conn, issue_row["id"], "in")
        if target == "Derived to ECN" and not ecns:
            return ("Aucun ECN ne traite encore ce problème.",
                    "Utilisez le bouton « Derive to ECN » de la fiche : il crée l'ECN, le lie et change le status.")
        if target == "Closed":
            open_ecns = [e["key"] for e in ecns if e["status_category"] != "done"]
            if open_ecns:
                return ("ECN pas encore fermé(s) : {}.".format(", ".join(open_ecns)),
                        "Fermez d'abord l'ECN (implanté et vérifié), puis fermez le problème.")
            if not ecns and not cf.fields_of(conn, issue_row["id"])["root_cause"]:
                return ("Fermeture sans ECN et sans cause racine.",
                        "Renseignez la cause racine (ou « non reproductible », « erreur d'utilisation »…) dans la fiche.")
    elif role == "ecn":
        fields = cf.fields_of(conn, issue_row["id"])
        missing = []
        if target == "Submitted":
            if not fields["change_class"]:
                missing.append("classe (majeur / mineur)")
            if not fields["reason"]:
                missing.append("raison du changement")
            if not (issue_row["description"] or "").strip():
                missing.append("description du changement")
            if not cf.items_of(conn, issue_row["id"]):
                missing.append("au moins un article touché (pièce, assemblage, document…)")
        elif target == "Approved" and not fields["approvers"]:
            missing.append("approbateurs CCB")
        elif target == "In Verification":
            open_tasks = [r[0] for r in conn.execute(
                "SELECT i.number FROM agile_issues i JOIN agile_statuses s ON s.id = i.status_id "
                "WHERE i.parent_id = ? AND s.category != 'done' ORDER BY i.number", (issue_row["id"],))]
            if open_tasks:
                key = c.project_key(conn, issue_row["project_id"])
                return ("Sub-task(s) non terminée(s) : {}.".format(", ".join("{}-{}".format(key, n) for n in open_tasks)),
                        "Terminez-les ou supprimez celles qui ne s'appliquent plus, puis refaites la transition.")
        elif target == "Closed":
            if not fields["effectivity"]:
                missing.append("effectivité")
            if not fields["verification_ref"]:
                missing.append("référence de vérification de l'implantation")
        if missing:
            return ("Passage à « {} » impossible : {} manquant(e)(s).".format(target, ", ".join(missing)),
                    "Complétez la fiche ECN (section Gestion du changement), puis refaites la transition.")
    return None


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------
def _change_issue(ctx, project_id, roles):
    row = c.get_issue(ctx.conn, project_id, c.issue_number(ctx))
    role = _role(ctx.conn, row["type_id"])
    if role not in roles:
        raise ApiError(400, "Ce ticket n'est pas un {}. Correctif : ouvrez-le depuis Agile → Change Management.".format(
            " ou ".join(ROLE_NAMES[r] for r in roles)))
    return row, role


def api_update_fields(ctx):
    project_id, access_role = c.access(ctx, "editor")
    row, role = _change_issue(ctx, project_id, ("pr", "bug", "ecn"))
    c.require_edit(ctx, access_role, row)
    allowed = cf.ECN_FIELDS if role == "ecn" else cf.PROBLEM_FIELDS
    changed = cf.save_fields(ctx, row["id"], cf.clean(ctx.body, allowed))
    if changed:
        c.log(ctx, "goldmine_change_fields", "agile_issue", row["id"], {"fields": changed})
    return {"ok": True, "changed": changed}


def api_set_items(ctx):
    project_id, access_role = c.access(ctx, "editor")
    row, _ = _change_issue(ctx, project_id, ("ecn",))
    c.require_edit(ctx, access_role, row)
    changed = cf.save_items(ctx, row["id"], cf.clean_items(ctx.body.get("items")))
    if changed:
        c.log(ctx, "goldmine_change_items", "agile_issue", row["id"], {"count": len(ctx.body.get("items") or [])})
    return {"ok": True, "changed": changed, "items": cf.items_of(ctx.conn, row["id"])}


def api_derive(ctx):
    """PR / bug -> new ECN linked by 'resolves'; the problem moves to
    « Derived to ECN ». Deriving again adds another ECN (several sub-changes)."""
    project_id, access_role = c.access(ctx, "editor")
    conn = ctx.conn
    row, role = _change_issue(ctx, project_id, ("pr", "bug"))
    c.require_edit(ctx, access_role, row)
    status = conn.execute("SELECT name FROM agile_statuses WHERE id = ?", (row["status_id"],)).fetchone()["name"]
    if status not in ("In Analysis", "Derived to ECN"):
        raise ApiError(409, "Le problème est « {} ». Correctif : passez-le d'abord à « In Analysis » "
                            "(transition Analyser).".format(status))
    ecn_type = types_by_role(conn, project_id).get("ecn")
    key = c.project_key(conn, project_id)
    title = (ctx.body.get("title") or "").strip() or "ECN — " + row["title"]
    body = {"type_id": ecn_type["id"], "title": title[:255], "priority": row["priority"],
            "description": "Traite {}-{} : {}\n\n{}".format(key, row["number"], row["title"],
                                                            (row["description"] or "").strip()).strip()[:20000]}
    original, ctx.body = ctx.body, body
    try:
        created = issues_mod.api_create(ctx)
    finally:
        ctx.body = original
    ecn = c.get_issue(conn, project_id, created["number"])
    cf.save_fields(ctx, ecn["id"], {"reason": "correctif"})
    conn.execute("INSERT INTO agile_links (source_id, target_id, link_type, created_by, created_at) "
                 "VALUES (?, ?, 'resolves', ?, ?)", (ecn["id"], row["id"], ctx.user["id"], db.utc_now()))
    if status == "In Analysis":
        target = conn.execute("SELECT s.id FROM agile_statuses s JOIN agile_issue_types t ON t.workflow_id = s.workflow_id "
                              "WHERE t.id = ? AND s.name = 'Derived to ECN'", (row["type_id"],)).fetchone()
        conn.execute("UPDATE agile_issues SET status_id = ?, updated_at = ? WHERE id = ?",
                     (target["id"], db.utc_now(), row["id"]))
        c.add_history(ctx, row["id"], "status", status, "Dérivé en ECN ({})".format(created["key"]))
    c.add_history(ctx, ecn["id"], "created", None, "dérivé de {}-{}".format(key, row["number"]))
    c.log(ctx, "goldmine_derive_ecn", "agile_issue", row["id"], {"ecn": created["key"]})
    return created


def enrich(conn, project_id, row, issue):
    """Add change-management data to the ticket page payload."""
    role = _role(conn, row["type_id"])
    issue["change_role"] = role
    if not role:
        return
    issue["change_labels"] = cf.labels()
    if role in ("pr", "bug", "ecn"):
        issue["change"] = cf.fields_of(conn, row["id"])
    if role == "ecn":
        issue["change_items"] = cf.items_of(conn, row["id"])
        issue["treats"] = _linked(conn, row["id"], "out")
    if role in ("pr", "bug"):
        issue["treated_by"] = _linked(conn, row["id"], "in")
    task_type = types_by_role(conn, project_id).get("ecn_task")
    issue["ecn_task_type_id"] = task_type["id"] if task_type else None


def _listing(conn, project_id):
    key = c.project_key(conn, project_id)
    rows = conn.execute(
        "SELECT i.id, i.number, i.title, i.priority, i.updated_at, i.parent_id, i.assignee_id, t.name AS type_name, t.icon_key, "
        "t.change_role, s.name AS status_name, s.category AS status_category, u.display_name AS assignee_name, "
        "p.number AS parent_number, ch.* FROM agile_issues i JOIN agile_issue_types t ON t.id = i.type_id "
        "JOIN agile_statuses s ON s.id = i.status_id LEFT JOIN users u ON u.id = i.assignee_id "
        "LEFT JOIN agile_issues p ON p.id = i.parent_id LEFT JOIN agile_changes ch ON ch.issue_id = i.id "
        "WHERE i.project_id = ? AND t.change_role != '' ORDER BY i.number DESC", (project_id,)).fetchall()
    out = []
    for r in rows:
        item = {k: r[k] for k in ("number", "title", "priority", "updated_at", "type_name", "icon_key", "change_role",
                                  "status_name", "status_category", "assignee_id", "assignee_name", "severity", "change_class")}
        item["key"] = "{}-{}".format(key, r["number"])
        item["parent_key"] = "{}-{}".format(key, r["parent_number"]) if r["parent_number"] else ""
        item["id"] = r[0]
        if r["change_role"] == "ecn":
            item["treats"] = [x["key"] for x in _linked(conn, r[0], "out")]
            item["items"] = cf.items_of(conn, r[0])
            tasks = conn.execute("SELECT s.category FROM agile_issues i JOIN agile_statuses s ON s.id = i.status_id "
                                 "WHERE i.parent_id = ?", (r[0],)).fetchall()
            item["tasks"] = {"total": len(tasks), "done": sum(1 for t in tasks if t[0] == "done")}
        elif r["change_role"] in ("pr", "bug"):
            item["treated_by"] = [x["key"] for x in _linked(conn, r[0], "in")]
        out.append(item)
    return out


def api_list(ctx):
    project_id, role = c.access(ctx)
    types = types_by_role(ctx.conn, project_id)
    if "ecn" not in types:
        return {"enabled": False, "role": role}
    items = _listing(ctx.conn, project_id)
    for item in items:
        item.pop("id", None)
    return {"enabled": True, "role": role, "types": types, "items": items, "labels": cf.labels()}


EXPORT_FIELDS = ["key", "type", "title", "status", "parent_key", "assignee", "severity", "detected_in", "item_ref",
                 "found_version", "change_class", "reason", "impact_fff", "impact_certification", "impact_safety",
                 "effectivity", "approvers", "decision_date", "verification_ref", "treats", "treated_by",
                 "affected_items", "updated_at"]


def api_export(ctx):
    project_id, _ = c.access(ctx)
    conn = ctx.conn
    if "ecn" not in types_by_role(conn, project_id):
        raise ApiError(409, "Change Management n'est pas activé. Correctif : Agile → Change Management → Activer.")
    from . import csv_io  # local import: csv_io is heavy and imports issues
    rows = []
    for it in _listing(conn, project_id):
        f = cf.fields_of(conn, it["id"])
        rows.append({
            "key": it["key"], "type": it["type_name"], "title": it["title"], "status": it["status_name"],
            "parent_key": it["parent_key"], "assignee": it["assignee_name"] or "",
            "severity": cf.SEVERITIES.get(f["severity"], ""), "detected_in": cf.DETECTED_IN.get(f["detected_in"], ""),
            "item_ref": f["item_ref"], "found_version": f["found_version"],
            "change_class": cf.CLASSES.get(f["change_class"], ""), "reason": cf.REASONS.get(f["reason"], ""),
            "impact_fff": "oui" if f["impact_fff"] else "", "impact_certification": "oui" if f["impact_certification"] else "",
            "impact_safety": "oui" if f["impact_safety"] else "", "effectivity": f["effectivity"],
            "approvers": f["approvers"], "decision_date": f["decision_date"] or "",
            "verification_ref": f["verification_ref"], "treats": ";".join(it.get("treats", [])),
            "treated_by": ";".join(it.get("treated_by", [])),
            "affected_items": " | ".join("{} {} {}→{} ({})".format(cf.ITEM_TYPES.get(x["item_type"], ""), x["item_number"],
                                                                   x["rev_from"] or "—", x["rev_to"] or "—",
                                                                   cf.DISPOSITIONS.get(x["disposition"], ""))
                                         for x in it.get("items", [])),
            "updated_at": it["updated_at"]})
    rows.reverse()
    c.log(ctx, "goldmine_changes_export", "project", project_id, {"rows": len(rows)})
    return RawFile.csv(csv_io._write_csv(EXPORT_FIELDS, rows), "{}_changements.csv".format(c.project_key(conn, project_id)))
