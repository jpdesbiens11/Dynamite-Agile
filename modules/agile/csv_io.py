"""CSV import/export (H16-H20): round-trip tickets through Excel, and pull
the question/answer threads meant for a client into a separate file.

Design (docs/AGILE_ARCHITECTURE.md, "Import/export CSV"):
- tickets.csv: one row per ticket; `key` blank creates, filled updates.
  Optimistic locking on `updated_at` -- a row edited server-side since the
  export is refused, never silently overwritten (H12).
- questions.csv: one row per comment marked "question" or a reply to one;
  `comment_id` blank creates a new reply, filled rows are ignored on
  import (existing comments are never edited by CSV) (H14).
Both travel over JSON (a `csv` text field), not multipart upload, to keep
the router's plain http.server parsing.
"""
import csv
import io

from core import db, permissions, validate
from core.errors import ApiError
from core.files import RawFile

from . import common as c
from . import issues as issues_mod
from . import csv_rows, summary

TICKET_FIELDS = ["key", "parent_key", "type", "title", "description", "priority",
                 "status", "assignee", "labels", "sprint", "version", "points",
                 "due_date", "updated_at"]
QUESTION_FIELDS = ["issue_key", "comment_id", "parent_comment_id", "requirement_ref",
                   "author", "is_question", "body", "created_at"]

MAX_CSV_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000


def _read_csv_body(ctx, expected_fields):
    """Parse the uploaded CSV text. Accepts what Excel actually produces:
    a UTF-8 BOM, and the ';' delimiter used by French-locale Excel."""
    text = ctx.body.get("csv")
    if not isinstance(text, str) or not text.strip():
        raise ApiError(400, "Fichier vide. Correctif : exportez d'abord un modèle avec "
                            "« Exporter », remplissez-le, puis réimportez-le.")
    if len(text.encode("utf-8")) > MAX_CSV_BYTES:
        raise ApiError(413, "Fichier CSV trop volumineux (5 Mo maximum). Correctif : "
                            "découpez-le en plusieurs imports.")
    text = text.lstrip("\ufeff")
    header = text.splitlines()[0] if text.splitlines() else ""
    delimiter = ";" if header.count(";") > header.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    fieldnames = [f.strip() for f in (reader.fieldnames or [])]
    reader.fieldnames = fieldnames
    missing = [f for f in expected_fields if f not in fieldnames]
    if missing:
        raise ApiError(400, "Colonne(s) manquante(s) : {}. Colonnes lues : {}. Correctif : "
                            "gardez la première ligne exactement comme dans un export "
                            "(noms en anglais, sans les renommer).".format(
                                ", ".join(missing), ", ".join(fieldnames) or "(aucune)"))
    rows = list(reader)
    if len(rows) > MAX_ROWS:
        raise ApiError(413, "{} lignes au maximum par import ({} reçues). Correctif : "
                            "découpez le fichier.".format(MAX_ROWS, len(rows)))
    return rows


def _write_csv(fields, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("" if v is None else v) for k, v in row.items()})
    return buf.getvalue()


# --------------------------------------------------------------------------
# Tickets
# --------------------------------------------------------------------------
def api_export_tickets(ctx):
    project_id, _ = c.access(ctx)
    conn = ctx.conn
    key = c.project_key(conn, project_id)
    rows = conn.execute(
        "SELECT i.*, s.name AS status_name, t.name AS type_name, "
        "u.display_name AS assignee_name, sp.name AS sprint_name, v.name AS version_name, "
        "p.number AS parent_number "
        "FROM agile_issues i JOIN agile_statuses s ON s.id = i.status_id "
        "JOIN agile_issue_types t ON t.id = i.type_id "
        "LEFT JOIN users u ON u.id = i.assignee_id "
        "LEFT JOIN agile_sprints sp ON sp.id = i.sprint_id "
        "LEFT JOIN agile_versions v ON v.id = i.version_id "
        "LEFT JOIN agile_issues p ON p.id = i.parent_id "
        "WHERE i.project_id = ? ORDER BY i.number", (project_id,)).fetchall()
    out = []
    for r in rows:
        labels = conn.execute(
            "SELECT l.name FROM agile_issue_labels il JOIN agile_labels l ON l.id = il.label_id "
            "WHERE il.issue_id = ? ORDER BY l.name", (r["id"],)).fetchall()
        implements = conn.execute(
            "SELECT ti.number AS n, tp.key AS pk FROM agile_links al "
            "JOIN agile_issues ti ON ti.id = al.target_id JOIN projects tp ON tp.id = ti.project_id "
            "WHERE al.source_id = ? AND al.link_type = 'implements'", (r["id"],)).fetchall()
        out.append({
            "key": "{}-{}".format(key, r["number"]),
            "parent_key": "{}-{}".format(key, r["parent_number"]) if r["parent_number"] else "",
            "type": r["type_name"], "title": r["title"], "description": r["description"],
            "priority": r["priority"], "status": r["status_name"],
            "assignee": r["assignee_name"] or "",
            "labels": ";".join(x["name"] for x in labels),
            "sprint": r["sprint_name"] or "", "version": r["version_name"] or "",
            "points": "" if r["story_points"] is None else r["story_points"],
            "due_date": r["due_date"] or "", "updated_at": r["updated_at"],
            "implements": ";".join("{}-{}".format(x["pk"], x["n"]) for x in implements),
            "client_summary": r["client_summary"] or "",
        })
    text = _write_csv(TICKET_FIELDS + ["implements", "client_summary"], out)
    c.log(ctx, "agile_export_tickets", "project", project_id, {"rows": len(out)})
    return RawFile.csv(text, "{}_tickets.csv".format(key))


def _apply_implements(ctx, project_id, issue_id, raw_value):
    """Add any 'implements' links named in the CSV's `implements` column
    (keys separated by ';'). Additive only -- a link already on the ticket
    but missing from this row is left alone, so a partial re-import can
    never silently remove a traceability link. Returns a short note for
    the report (empty string if everything applied cleanly)."""
    conn = ctx.conn
    keys = [k.strip() for k in (raw_value or "").split(";") if k.strip()]
    if not keys:
        return ""
    problems = []
    for key in keys:
        try:
            target = c.find_by_key(conn, ctx.user, key)
        except ApiError as exc:
            problems.append("{} : {}".format(key, exc.message))
            continue
        target_type = conn.execute("SELECT is_requirement FROM agile_issue_types WHERE id = ?",
                                   (target["type_id"],)).fetchone()
        if not target_type or not target_type["is_requirement"]:
            problems.append("{} n'est pas un requirement".format(key))
            continue
        try:
            conn.execute("INSERT INTO agile_links (source_id, target_id, link_type, created_by, "
                        "created_at) VALUES (?, ?, 'implements', ?, ?)",
                        (issue_id, target["id"], ctx.user["id"], db.utc_now()))
        except db.sqlite3.IntegrityError:
            pass  # already linked -- fine, additive means idempotent too
    if not problems:
        return ""
    return ("Lien(s) « implements » non créé(s) : {}. Le reste de la ligne est appliqué. "
            "Correctif : chaque clé doit viser un ticket existant d'un type marqué Requirement "
            "(Paramètres → Types), séparées par « ; ».".format("; ".join(problems)))


def _new_number(ctx, project_id, wanted_key):
    """Number for a ticket created by the import. A key typed in the file for
    a number never used yet (EQP-21 while the project is at EQP-15) is
    honoured -- that is what the user meant. Otherwise the next number, kept
    above every key present in the file so a new ticket can never take the
    key of a later row (D-B-008). Returns (number, honoured)."""
    conn = ctx.conn
    next_number = conn.execute("SELECT next_ticket_number FROM projects WHERE id = ?",
                               (project_id,)).fetchone()[0]
    wanted = int(wanted_key.rsplit("-", 1)[1]) if wanted_key else 0
    if wanted >= next_number:
        number, honoured = wanted, True
    else:
        number, honoured = max(next_number, getattr(ctx, "csv_number_floor", 0)), False
    conn.execute("UPDATE projects SET next_ticket_number = ? WHERE id = ?", (number + 1, project_id))
    return number, honoured


def _changed_fields(conn, existing, v, row):
    """French labels of what this row would change on `existing` (empty:
    the row matches the server, nothing to write)."""
    labels_now = sorted(r["name"].lower() for r in conn.execute(
        "SELECT l.name FROM agile_issue_labels il JOIN agile_labels l ON l.id = il.label_id "
        "WHERE il.issue_id = ?", (existing["id"],)))
    linked = {"{}-{}".format(r["pk"], r["n"]) for r in conn.execute(
        "SELECT tp.key AS pk, ti.number AS n FROM agile_links al JOIN agile_issues ti ON ti.id = al.target_id "
        "JOIN projects tp ON tp.id = ti.project_id WHERE al.source_id = ? AND al.link_type = 'implements'",
        (existing["id"],))}
    wanted_links = {k.strip().upper() for k in (row.get("implements") or "").split(";") if k.strip()}
    points_now = existing["story_points"]
    checks = [
        ("titre", existing["title"] != v["title"]),
        ("description", (existing["description"] or "") != (v["description"] or "")),
        ("type", existing["type_id"] != v["type"]["id"]),
        ("status", v["transition"] is not None or existing["status_id"] != v["status"]["id"]),
        ("priorité", existing["priority"] != v["priority"]),
        ("assigné", existing["assignee_id"] != v["assignee_id"]),
        ("sprint", existing["sprint_id"] != v["sprint_id"]),
        ("version", existing["version_id"] != v["version_id"]),
        ("points", (None if points_now is None else float(points_now)) != v["points"]),
        ("échéance", (existing["due_date"] or None) != (v["due_date"] or None)),
        ("parent", existing["parent_id"] != v["parent_id"]),
        ("labels", labels_now != sorted(x.lower() for x in v["labels"])),
        ("synthèse client", v["client_summary"] is not None and (existing["client_summary"] or "") != v["client_summary"]),
        ("implements", bool(wanted_links - linked)),
    ]
    return [name for name, differs in checks if differs]


def _apply_ticket_row(ctx, project_id, prefix, row, role):
    """Validate (csv_rows) then write one row. Returns the report entry.

    D-B-008: a row identical to the server is reported "inchangée" and
    nothing is written (re-importing the same file is harmless); a stale
    updated_at refuses the row only if it would really change something;
    an unknown key creates the ticket and remembers the file key, so a
    second import of the same file updates it instead of duplicating it."""
    conn = ctx.conn
    v = csv_rows.validate_row(ctx, project_id, prefix, row, role)
    now = db.utc_now()
    existing = v["existing"]
    mapped = ""
    if existing and v["unknown_key"]:
        mapped = ("Clé {} du fichier : ticket créé sous {}-{} lors d'un import précédent, mis à jour ici. "
                  "Remplacez la clé dans votre fichier (ou réexportez).".format(
                      v["unknown_key"], prefix, existing["number"]))
    if existing:
        changed = _changed_fields(conn, existing, v, row)
        key_now = "{}-{}".format(prefix, existing["number"])
        if not changed:
            return {"row": key_now, "status": "inchangée", "reason": "", "fix": "", "warning": mapped}
        if not c.can_edit(ctx, role, existing):
            raise csv_rows.RowError(
                "{} est attribué à quelqu'un d'autre : seul son responsable ou un administrateur peut le "
                "modifier.".format(key_now),
                "Retirez cette ligne du fichier, ou demandez au responsable du ticket de l'importer.")
        if v["stale"]:
            raise csv_rows.RowError(
                "{} a été modifié sur le serveur ({} UTC), après votre export, et votre ligne change : "
                "{}.".format(key_now, existing["updated_at"][:16].replace("T", " "), ", ".join(changed)),
                "Réexportez les tickets et reportez vos changements sur le nouveau fichier, ou videz "
                "« updated_at » sur cette ligne pour imposer vos valeurs.")
    if existing:
        conn.execute(
            "UPDATE agile_issues SET type_id = ?, parent_id = ?, title = ?, description = ?, "
            "priority = ?, status_id = ?, assignee_id = ?, sprint_id = ?, version_id = ?, "
            "story_points = ?, due_date = ?, updated_at = ? WHERE id = ?",
            (v["type"]["id"], v["parent_id"], v["title"], v["description"], v["priority"],
             v["status"]["id"], v["assignee_id"], v["sprint_id"], v["version_id"], v["points"],
             v["due_date"], now, existing["id"]))
        issue_id, key, status = existing["id"], "{}-{}".format(prefix, existing["number"]), "mise à jour"
        old_status = conn.execute("SELECT name FROM agile_statuses WHERE id = ?",
                                  (existing["status_id"],)).fetchone()["name"]
    else:
        number, honoured = _new_number(ctx, project_id, v["unknown_key"])
        rank = conn.execute("SELECT COALESCE(MAX(rank), 0) + 1 FROM agile_issues WHERE project_id = ?",
                            (project_id,)).fetchone()[0]
        issue_id = conn.execute(
            "INSERT INTO agile_issues (project_id, number, type_id, status_id, parent_id, title, "
            "description, priority, assignee_id, reporter_id, story_points, due_date, sprint_id, "
            "version_id, rank, created_at, updated_at, resolved_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
            (project_id, number, v["type"]["id"], v["status"]["id"], v["parent_id"], v["title"],
             v["description"], v["priority"], v["assignee_id"], ctx.user["id"], v["points"],
             v["due_date"], v["sprint_id"], v["version_id"], rank, now, now)).lastrowid
        key, status, old_status = "{}-{}".format(prefix, number), "créée", None
        c.add_history(ctx, issue_id, "created", None, v["title"] + " (import CSV)")
        if honoured:
            mapped = "Clé {} absente du projet : ticket créé avec cette clé.".format(key)
        elif v["unknown_key"]:
            c.add_history(ctx, issue_id, csv_rows.IMPORT_KEY_FIELD, None, v["unknown_key"])
            mapped = ("La clé {} a appartenu à un ticket supprimé (un numéro n'est jamais réutilisé) : "
                      "ticket créé sous {}. Un prochain import de ce même fichier mettra à jour {} "
                      "(pas de doublon) ; pour la suite, réexportez.".format(v["unknown_key"], key, key))
    if v["transition"] is not None:
        conn.execute("UPDATE agile_issues SET resolved_at = ? WHERE id = ?",
                     (now if v["status"]["category"] == "done" else None, issue_id))
        c.add_history(ctx, issue_id, "status", old_status or "(création)",
                      "{} (transition « {} », import CSV)".format(v["status"]["name"], v["transition"]["name"]))
    elif existing is None and v["status"]["category"] == "done":
        conn.execute("UPDATE agile_issues SET resolved_at = ? WHERE id = ?", (now, issue_id))
    issues_mod._set_labels(ctx, project_id, issue_id, v["labels"], record=False)
    if existing:
        c.add_history(ctx, issue_id, "csv_import", None, "ligne mise à jour")
    warning = _apply_implements(ctx, project_id, issue_id, row.get("implements", ""))
    if v["client_summary"] is not None:
        fresh = conn.execute("SELECT * FROM agile_issues WHERE id = ?", (issue_id,)).fetchone()
        summary.write(ctx, fresh, v["client_summary"], "import CSV")
    warning = " ".join(w for w in (mapped, warning) if w)
    return {"row": key, "status": status, "reason": "", "fix": "", "warning": warning}


def api_import_tickets(ctx):
    project_id, role = c.access(ctx, "editor")
    prefix = c.project_key(ctx.conn, project_id)
    rows = _read_csv_body(ctx, TICKET_FIELDS)
    numbers = [int(k.rsplit("-", 1)[1]) for k in ((r.get("key") or "").strip().upper() for r in rows)
               if k.startswith(prefix + "-") and k.rsplit("-", 1)[1].isdigit()]
    ctx.csv_number_floor = max(numbers) + 1 if numbers else 0
    report = []
    for index, row in enumerate(rows):
        line = index + 2  # Excel row number: row 1 is the header
        label = (row.get("key") or "").strip() or (row.get("title") or "").strip()[:60] or "(ligne vide)"
        if not any((value or "").strip() for value in row.values() if isinstance(value, str)):
            continue  # fully blank line (common at the end of an Excel sheet)
        try:
            entry = _apply_ticket_row(ctx, project_id, prefix, row, role)
        except csv_rows.RowError as exc:
            entry = {"row": label, "status": "refusée", "reason": exc.message, "fix": exc.fix,
                     "warning": "", "problems": [{"message": m, "fix": f} for m, f in exc.problems]}
        except ApiError as exc:
            entry = {"row": label, "status": "refusée", "reason": exc.message,
                     "fix": "Corrigez la ligne puis réimportez-la.", "warning": ""}
        entry["line"] = line
        report.append(entry)
    refused = sum(1 for r in report if r["status"] == "refusée")
    c.log(ctx, "agile_import_tickets", "project", project_id, {"rows": len(report), "rejected": refused})
    return {"report": report, "summary": {
        "created": sum(1 for r in report if r["status"] == "créée"),
        "updated": sum(1 for r in report if r["status"] == "mise à jour"),
        "unchanged": sum(1 for r in report if r["status"] == "inchangée"),
        "refused": refused,
        "warnings": sum(1 for r in report if r.get("warning")),
    }}


# --------------------------------------------------------------------------
# Questions / answers (H14)
# --------------------------------------------------------------------------
def api_export_questions(ctx):
    """Only comments marked as a question, or a reply to one -- not the
    whole internal thread -- so the file can go to a client as-is."""
    project_id, _ = c.access(ctx)
    conn = ctx.conn
    key = c.project_key(conn, project_id)
    rows = conn.execute(
        "SELECT cm.id, cm.parent_comment_id, cm.is_question, cm.requirement_ref, cm.body, "
        "cm.created_at, COALESCE(u.display_name, cm.external_author) AS author, i.number "
        "FROM agile_comments cm JOIN agile_issues i ON i.id = cm.issue_id "
        "LEFT JOIN users u ON u.id = cm.author_id "
        "WHERE i.project_id = ? AND (cm.is_question = 1 OR cm.parent_comment_id IN "
        "(SELECT id FROM agile_comments WHERE is_question = 1)) ORDER BY i.number, cm.id",
        (project_id,)).fetchall()
    out = [{
        "issue_key": "{}-{}".format(key, r["number"]), "comment_id": r["id"],
        "parent_comment_id": r["parent_comment_id"] or "", "requirement_ref": r["requirement_ref"],
        "author": r["author"] or "", "is_question": "oui" if r["is_question"] else "non",
        "body": r["body"], "created_at": r["created_at"],
    } for r in rows]
    text = _write_csv(QUESTION_FIELDS, out)
    c.log(ctx, "agile_export_questions", "project", project_id, {"rows": len(out)})
    return RawFile.csv(text, "{}_questions.csv".format(key))


def api_import_questions(ctx):
    """New replies only (H14): a row with `comment_id` already filled is a
    row Agile itself produced on export, and is skipped -- comments are
    never edited by CSV, only added to."""
    project_id, _ = c.access(ctx, "editor")
    conn = ctx.conn
    rows = _read_csv_body(ctx, QUESTION_FIELDS)
    report = []
    for row in rows:
        issue_key = (row.get("issue_key") or "").strip()
        if (row.get("comment_id") or "").strip():
            report.append({"row": issue_key, "status": "ignorée",
                           "reason": "Commentaire déjà présent (comment_id rempli).",
                           "fix": "Normal : seules les lignes à comment_id vide sont ajoutées."})
            continue
        body = (row.get("body") or "").strip()
        if not issue_key or not body:
            report.append({"row": issue_key or "(vide)", "status": "refusée",
                           "reason": "Clé de ticket ou texte de réponse manquant.",
                           "fix": "Remplissez issue_key (ex. EQP-4) et body."})
            continue
        try:
            issue = c.find_by_key(conn, ctx.user, issue_key)
            permissions.require_project_role(conn, ctx.user, issue["project_id"], "editor")
        except ApiError as exc:
            report.append({"row": issue_key, "status": "refusée", "reason": exc.message,
                           "fix": "Vérifiez la clé du ticket et vos droits d'éditeur sur son projet."})
            continue
        parent_id = None
        parent_raw = (row.get("parent_comment_id") or "").strip()
        if parent_raw:
            parent = conn.execute("SELECT id FROM agile_comments WHERE id = ? AND issue_id = ?",
                                  (parent_raw, issue["id"])).fetchone()
            if parent is None:
                report.append({"row": issue_key, "status": "refusée",
                               "reason": "Commentaire parent {} introuvable sur ce ticket.".format(parent_raw),
                               "fix": "Reprenez le comment_id de la question dans un export récent, "
                                      "ou videz parent_comment_id."})
                continue
            parent_id = parent["id"]
        author = (row.get("author") or "").strip()
        is_question = (row.get("is_question") or "").strip().lower() in ("oui", "yes", "true", "1")
        conn.execute(
            "INSERT INTO agile_comments (issue_id, parent_comment_id, author_id, external_author, "
            "is_question, requirement_ref, body, created_at) VALUES (?, ?, NULL, ?, ?, ?, ?, ?)",
            (issue["id"], parent_id, author or "Externe", int(is_question),
             (row.get("requirement_ref") or "").strip(), body, db.utc_now()))
        report.append({"row": issue_key, "status": "ajoutée", "reason": "", "fix": ""})
    c.log(ctx, "agile_import_questions", "project", project_id,
          {"rows": len(rows), "added": sum(1 for r in report if r["status"] == "ajoutée")})
    return {"report": report}
