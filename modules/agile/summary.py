"""Client summary ("Synthèse client", D-B-001): one editable field per
ticket holding the current position to send to the client, so the full
comment thread never has to travel with an export.

The comment thread stays the complete record; the summary is the curated
answer. Every change is written to the ticket history with the old and
new text in full (who, when, what), and to the audit log.
"""
from core import db, validate
from core.errors import ApiError

from . import common as c

FIELD = "client_summary"
HISTORY_FIELD = "client_summary"
MAX_LENGTH = 4000
CSV_HEADERS = ["client_summary", "synthese client", "synthèse client", "commentaire principal",
               "summary", "synthese"]


def too_long_message(length):
    return ("Synthèse client de {} caractères.".format(length),
            "{} caractères au maximum : gardez la position à transmettre au client, le détail "
            "reste dans les commentaires.".format(MAX_LENGTH))


def clean(value):
    """Normalize line endings and trailing blanks; returns the text to store."""
    text = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def write(ctx, issue_row, new_value, origin=None):
    """Store `new_value` on the ticket if it changed. Records history with
    full old/new text. `origin` is a short note (e.g. "import CSV",
    "depuis le commentaire #12") added to the history entry. Returns True
    when something changed."""
    old_value = issue_row[FIELD] or ""
    if old_value == new_value:
        return False
    now = db.utc_now()
    ctx.conn.execute(
        "UPDATE agile_issues SET client_summary = ?, client_summary_by = ?, client_summary_at = ?, "
        "updated_at = ? WHERE id = ?", (new_value, ctx.user["id"], now, now, issue_row["id"]))
    # Lightweight trace (D-B-017): who and when, not the full text.
    note = ("(modifiée, {} car.)".format(len(new_value)) if new_value else "(vidée)")
    if origin:
        note += " — " + origin
    c.add_history(ctx, issue_row["id"], HISTORY_FIELD, None, note)
    return True


def api_set(ctx):
    """PUT .../issues/<n>/summary  {client_summary, from_comment_id?}"""
    project_id, role = c.access(ctx, "editor")
    conn, body = ctx.conn, ctx.body
    row = c.get_issue(conn, project_id, c.issue_number(ctx))
    c.require_edit(ctx, role, row)
    raw = validate.text(body, FIELD, MAX_LENGTH * 2, required=False)
    value = clean(raw)
    if len(value) > MAX_LENGTH:
        message, fix = too_long_message(len(value))
        raise ApiError(400, "{} Correctif : {}".format(message, fix))
    origin = None
    comment_id = c.opt_int(body, "from_comment_id")
    if comment_id is not None:
        if not conn.execute("SELECT 1 FROM agile_comments WHERE id = ? AND issue_id = ?",
                            (comment_id, row["id"])).fetchone():
            raise ApiError(404, "Commentaire introuvable sur ce ticket.")
        origin = "reprise du commentaire #{}".format(comment_id)
    changed = write(ctx, row, value, origin)
    if changed:
        c.log(ctx, "agile_summary_update", "agile_issue", row["id"],
              {"length": len(value), "from_comment_id": comment_id})
    return {"ok": True, "changed": changed, **fields_of(conn, row["id"])}


def fields_of(conn, issue_id):
    row = conn.execute(
        "SELECT i.client_summary, i.client_summary_at, u.display_name AS client_summary_by_name "
        "FROM agile_issues i LEFT JOIN users u ON u.id = i.client_summary_by WHERE i.id = ?",
        (issue_id,)).fetchone()
    return {"client_summary": row["client_summary"] or "",
            "client_summary_at": row["client_summary_at"],
            "client_summary_by_name": row["client_summary_by_name"]}


def csv_cell(row):
    """Value of the summary column in an import row, or None when the file
    has no such column (then the stored summary is left untouched)."""
    if FIELD not in row:
        return None
    return clean(row.get(FIELD) or "")
