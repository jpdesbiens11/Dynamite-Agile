"""« À vérifier » on a test (0.60.07, D-O-019): the standard an AI assistant named, confirmed by a person.

A test created by « Commencer » (core/starter_apply.py) arrives with review = 'to_verify'. A person checks the edition
in force and the clause, then confirms it here; review_checked keeps « date · who · edition ». Until then the test
cannot become « Approved » (guard, called by tests_api.update -- the screen and the CSV import).

POST /api/testing/tests/<tid>/review {space, edition, clause?}
"""
from core import audit, db, validate
from core.errors import ApiError

TO_VERIFY, VERIFIED, APPROVED = "to_verify", "verified", "Approved"


def guard(row, changes):
    if changes.get("status") == APPROVED and row["review"] == TO_VERIFY:
        raise ApiError(400, "Status « Approved » refusé pour {} : sa norme « {} » a été proposée par un assistant IA et est "
                            "encore « À vérifier ». Correctif : vérifiez l'édition en vigueur et la clause, puis cliquez "
                            "« Confirmer la norme » dans la fiche du test.".format(row["test_id"], row["standard"] or "?"))


def api_review(ctx):
    from . import catalog, tests_api
    catalog.require_space(ctx.conn)
    pid, _key = tests_api.space(ctx, "editor")
    row = tests_api._row(ctx.conn, pid, ctx.params["tid"])
    if row["review"] != TO_VERIFY:
        raise ApiError(409, "Rien à confirmer : la norme de {} n'est pas « À vérifier ».".format(row["test_id"]))
    edition = validate.text(ctx.body, "edition", 80)
    clause = validate.text(ctx.body, "clause", 80, required=False)
    checked = " · ".join(x for x in (db.utc_now()[:10], ctx.user["username"], edition, clause) if x)
    ctx.conn.execute("UPDATE testing_tests SET review = ?, review_checked = ?, updated_by = ?, updated_at = ? WHERE id = ?",
                     (VERIFIED, checked, ctx.user["id"], db.utc_now(), row["id"]))
    tests_api._history(ctx, row["id"], "revue de la norme", "À vérifier", "Confirmée : " + checked)
    audit.log_action(ctx.conn, ctx.user["id"], "testing_review_check", "testing_test", row["id"],
                     {"test_id": row["test_id"], "edition": edition, "clause": clause}, ctx.ip)
    return {"ok": True, "review": VERIFIED, "review_checked": checked}
