"""« À vérifier » on a requirement (0.60.07, D-O-019): the standard an AI assistant named, confirmed by a person.

A requirement created by « Commencer » (core/starter_apply.py) arrives with standard_review = 'to_verify'. A person
checks the edition in force and the clause, then confirms it here; standard_checked keeps « date · who · edition ».
Until then the requirement cannot become « Accepted » (review_guard, called by goldmine.verification_guard).

POST .../issues/<num>/standard-check {edition, clause?}
"""
from core import db, validate
from core.errors import ApiError

from . import common as c

TO_VERIFY, VERIFIED = "to_verify", "verified"
ACCEPTED = "Accepted"


def review_guard(conn, issue_id, target_status_name):
    if target_status_name != ACCEPTED:
        return None
    row = conn.execute("SELECT standard_review, source_doc FROM agile_requirements WHERE issue_id = ?", (issue_id,)).fetchone()
    if row is None or row["standard_review"] != TO_VERIFY:
        return None
    return ("Passage à « Accepted » impossible : la norme « {} » a été proposée par un assistant IA et est encore « À "
            "vérifier ».".format(row["source_doc"] or "?"),
            "Vérifiez l'édition en vigueur et la clause, puis cliquez « Confirmer la norme » dans la fiche du requirement.")


def api_standard_check(ctx):
    from .goldmine import _requirement_issue
    project_id, role = c.access(ctx, "editor")
    row = _requirement_issue(ctx, project_id, c.issue_number(ctx))
    c.require_edit(ctx, role, row)
    current = ctx.conn.execute("SELECT standard_review, source_doc FROM agile_requirements WHERE issue_id = ?",
                               (row["id"],)).fetchone()
    if current is None or current["standard_review"] != TO_VERIFY:
        raise ApiError(409, "Rien à confirmer : la norme de ce requirement n'est pas « À vérifier ».")
    edition = validate.text(ctx.body, "edition", 80)
    clause = validate.text(ctx.body, "clause", 80, required=False)
    checked = " · ".join(x for x in (db.utc_now()[:10], ctx.user["username"], edition, clause) if x)
    ctx.conn.execute("UPDATE agile_requirements SET standard_review = ?, standard_checked = ? WHERE issue_id = ?",
                     (VERIFIED, checked, row["id"]))
    ctx.conn.execute("UPDATE agile_issues SET updated_at = ? WHERE id = ?", (db.utc_now(), row["id"]))
    c.add_history(ctx, row["id"], "req:Standard Review", "À vérifier", "Confirmée : " + checked)
    c.log(ctx, "goldmine_standard_check", "agile_issue", row["id"], {"edition": edition, "clause": clause})
    return {"ok": True, "standard_review": VERIFIED, "standard_checked": checked}
