"""« Kepner-Tregoe » tool (D-B-067): decision analysis of Tools.

A decision (per Space) has a statement, criteria -- DOIT (musts: pass / fail,
an alternative failing one is eliminated) and VEUT (wants: weight 1-10) --,
optionally linked to a Goldmine need or requirement, alternatives scored
1-10 on each want (weighted score = sum of weight x score), and risks
(adverse consequences: probability and seriousness 1-3) of the alternatives.
Deciding records the alternative and the justification (read-only until
reopened). Everything is journalled.
"""
from core import audit, db, permissions, validate
from core.errors import ApiError

from .ideation import _text

KINDS = {"must": "DOIT", "want": "VEUT"}
LEVELS = {1: "Faible", 2: "Moyenne", 3: "Élevée"}


def access(ctx, minimum="reader"):
    pid = validate.int_param(ctx.params, "pid")
    permissions.require_project_role(ctx.conn, ctx.user, pid, minimum)
    return pid


def _kt(ctx, pid):
    row = ctx.conn.execute("SELECT * FROM tools_kt WHERE id = ? AND project_id = ?",
                           (validate.int_param(ctx.params, "kid"), pid)).fetchone()
    if row is None:
        raise ApiError(404, "Analyse Kepner-Tregoe introuvable dans ce Space.")
    return row


def _editable(row):
    if row["status"] == "decided":
        raise ApiError(409, "Décision prise : lecture seule. Correctif : « Rouvrir ».")


def _log(ctx, action, kid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "tools_kt", kid, details, ctx.ip)
    ctx.conn.execute("UPDATE tools_kt SET updated_by = ?, updated_at = ? WHERE id = ?", (ctx.user["id"], db.utc_now(), kid))


def results(criteria, alts, scores, risks):
    """{alt_id: {eliminated, failed_musts, pending_musts, weighted, max, percent, risk, rank}}"""
    out = {}
    wants = [c for c in criteria if c["kind"] == "want"]
    maximum = sum(c["weight"] * 10 for c in wants)
    for a in alts:
        failed = [c["id"] for c in criteria if c["kind"] == "must" and scores.get((c["id"], a["id"]), {}).get("value") == 0]
        pending = [c["id"] for c in criteria if c["kind"] == "must" and (c["id"], a["id"]) not in scores]
        weighted = sum(c["weight"] * (scores.get((c["id"], a["id"]), {}).get("value") or 0) for c in wants)
        risk = sum(r["probability"] * r["seriousness"] for r in risks if r["alt_id"] == a["id"])
        out[a["id"]] = {"eliminated": bool(failed), "failed_musts": failed, "pending_musts": pending,
                        "weighted": weighted, "max": maximum, "percent": round(100 * weighted / maximum) if maximum else 0,
                        "risk": risk}
    alive = sorted({r["weighted"] for r in out.values() if not r["eliminated"]}, reverse=True)
    for r in out.values():
        r["rank"] = None if r["eliminated"] else 1 + sum(1 for v in alive if v > r["weighted"])
    return out


def detail(ctx, row):
    conn = ctx.conn
    key = conn.execute("SELECT key FROM projects WHERE id = ?", (row["project_id"],)).fetchone()["key"]
    criteria = [dict(r) for r in conn.execute(
        "SELECT c.*, i.number AS issue_number, i.title AS issue_title FROM tools_kt_criteria c "
        "LEFT JOIN agile_issues i ON i.id = c.issue_id WHERE c.kt_id = ? ORDER BY c.kind, c.position, c.id", (row["id"],))]
    for c in criteria:
        c["issue_key"] = "{}-{}".format(key, c["issue_number"]) if c["issue_number"] else None
    alts = [dict(r) for r in conn.execute("SELECT * FROM tools_kt_alts WHERE kt_id = ? ORDER BY position, id", (row["id"],))]
    scores = {(r["criterion_id"], r["alt_id"]): {"value": r["value"], "note": r["note"]} for r in conn.execute(
        "SELECT s.* FROM tools_kt_scores s JOIN tools_kt_criteria c ON c.id = s.criterion_id WHERE c.kt_id = ?", (row["id"],))}
    risks = [dict(r) for r in conn.execute("SELECT * FROM tools_kt_risks WHERE kt_id = ? ORDER BY id", (row["id"],))]
    return {"kt": dict(row), "criteria": criteria, "alts": alts, "risks": risks,
            "scores": [{"criterion_id": k[0], "alt_id": k[1], **v} for k, v in scores.items()],
            "results": {str(k): v for k, v in results(criteria, alts, scores, risks).items()},
            "labels": {"kinds": KINDS, "levels": {str(k): v for k, v in LEVELS.items()}}}


def api_list(ctx):
    pid = access(ctx)
    rows = ctx.conn.execute(
        "SELECT k.*, (SELECT COUNT(*) FROM tools_kt_alts WHERE kt_id = k.id) AS n_alts, "
        "(SELECT name FROM tools_kt_alts WHERE id = k.decision_alt_id) AS decision_name, u.display_name AS updated_by_name "
        "FROM tools_kt k LEFT JOIN users u ON u.id = k.updated_by WHERE k.project_id = ? ORDER BY k.updated_at DESC", (pid,)).fetchall()
    return {"analyses": [dict(r) for r in rows]}


def api_create(ctx):
    pid = access(ctx, "editor")
    now = db.utc_now()
    kid = ctx.conn.execute(
        "INSERT INTO tools_kt (project_id, title, statement, created_by, created_at, updated_by, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)", (pid, _text(ctx.body, "title", "Titre", 200, True),
                                        _text(ctx.body, "statement", "Statement de la décision", 1000),
                                        ctx.user["id"], now, ctx.user["id"], now)).lastrowid
    for i, name in enumerate(ctx.body.get("alternatives") or []):
        ctx.conn.execute("INSERT INTO tools_kt_alts (kt_id, name, position) VALUES (?, ?, ?)",
                         (kid, _text({"n": name}, "n", "Alternative", 120, True), i))
    _log(ctx, "kt_create", kid)
    ctx.params["kid"] = str(kid)
    return detail(ctx, _kt(ctx, pid))


def api_get(ctx):
    pid = access(ctx)
    return detail(ctx, _kt(ctx, pid))


def api_update(ctx):
    pid = access(ctx, "editor")
    row = _kt(ctx, pid)
    body, changes = ctx.body, {}
    if body.get("status") == "draft":
        changes["status"] = "draft"
    else:
        _editable(row)
    if "title" in body:
        changes["title"] = _text(body, "title", "Titre", 200, True)
    if "statement" in body:
        changes["statement"] = _text(body, "statement", "Statement de la décision", 1000)
    if body.get("status") == "decided":
        alt = int(body.get("decision_alt_id") or 0)
        if not ctx.conn.execute("SELECT 1 FROM tools_kt_alts WHERE id = ? AND kt_id = ?", (alt, row["id"])).fetchone():
            raise ApiError(400, "Choisissez l'alternative retenue.")
        changes.update(status="decided", decision_alt_id=alt, decision_note=_text(body, "decision_note", "Rationale", 4000))
    if changes:
        ctx.conn.execute("UPDATE tools_kt SET {} WHERE id = ?".format(", ".join("{} = ?".format(k) for k in changes)),
                         tuple(changes.values()) + (row["id"],))
        _log(ctx, "kt_update", row["id"], {"fields": sorted(changes)})
    return detail(ctx, _kt(ctx, pid))


def _weight(body):
    try:
        weight = int(body.get("weight") or 5)
    except (TypeError, ValueError):
        weight = 0
    if not 1 <= weight <= 10:
        raise ApiError(400, "Poids d'un VEUT : entier de 1 à 10.")
    return weight


def api_criterion(ctx):
    """POST: add {kind, text, weight, issue_number}; PATCH .../<cid>: {text, weight} or {delete: true}."""
    pid = access(ctx, "editor")
    row = _kt(ctx, pid)
    _editable(row)
    body = ctx.body
    cid = ctx.params.get("cid")
    if cid is None:
        kind = body.get("kind")
        if kind not in KINDS:
            raise ApiError(400, "Type de critère : DOIT (must) ou VEUT (want).")
        issue_id = None
        if body.get("issue_number"):
            found = ctx.conn.execute(
                "SELECT i.id, i.title FROM agile_issues i JOIN agile_issue_types t ON t.id = i.type_id AND t.is_requirement = 1 "
                "WHERE i.project_id = ? AND i.number = ?", (pid, int(body["issue_number"]))).fetchone()
            if found is None:
                raise ApiError(400, "Requirement ou besoin Goldmine introuvable dans ce Space.")
            issue_id = found["id"]
            body = dict(body, text=body.get("text") or found["title"])
        ctx.conn.execute("INSERT INTO tools_kt_criteria (kt_id, kind, text, weight, issue_id, position) VALUES (?, ?, ?, ?, ?, "
                         "(SELECT COALESCE(MAX(position), -1) + 1 FROM tools_kt_criteria WHERE kt_id = ?))",
                         (row["id"], kind, _text(body, "text", "Critère", 300, True), _weight(body) if kind == "want" else 0,
                          issue_id, row["id"]))
        _log(ctx, "kt_criterion_add", row["id"], {"kind": kind})
    else:
        crit = ctx.conn.execute("SELECT * FROM tools_kt_criteria WHERE id = ? AND kt_id = ?", (int(cid), row["id"])).fetchone()
        if crit is None:
            raise ApiError(404, "Critère introuvable.")
        if body.get("delete"):
            ctx.conn.execute("DELETE FROM tools_kt_criteria WHERE id = ?", (crit["id"],))
        else:
            ctx.conn.execute("UPDATE tools_kt_criteria SET text = ?, weight = ? WHERE id = ?",
                             (_text(body, "text", "Critère", 300, True), _weight(body) if crit["kind"] == "want" else 0, crit["id"]))
        _log(ctx, "kt_criterion_" + ("delete" if body.get("delete") else "update"), row["id"], {"criterion_id": crit["id"]})
    return detail(ctx, row)


def api_alt(ctx):
    """POST: add {name, description}; PATCH .../<aid>: {name, description} or {delete: true}."""
    pid = access(ctx, "editor")
    row = _kt(ctx, pid)
    _editable(row)
    aid = ctx.params.get("aid")
    if aid is None:
        ctx.conn.execute("INSERT INTO tools_kt_alts (kt_id, name, description, position) VALUES (?, ?, ?, "
                         "(SELECT COALESCE(MAX(position), -1) + 1 FROM tools_kt_alts WHERE kt_id = ?))",
                         (row["id"], _text(ctx.body, "name", "Alternative", 120, True),
                          _text(ctx.body, "description", "Description", 1000), row["id"]))
        _log(ctx, "kt_alt_add", row["id"])
    elif ctx.body.get("delete"):
        ctx.conn.execute("DELETE FROM tools_kt_alts WHERE id = ? AND kt_id = ?", (int(aid), row["id"]))
        _log(ctx, "kt_alt_delete", row["id"], {"alt_id": int(aid)})
    else:
        ctx.conn.execute("UPDATE tools_kt_alts SET name = ?, description = ? WHERE id = ? AND kt_id = ?",
                         (_text(ctx.body, "name", "Alternative", 120, True), _text(ctx.body, "description", "Description", 1000),
                          int(aid), row["id"]))
        _log(ctx, "kt_alt_update", row["id"], {"alt_id": int(aid)})
    return detail(ctx, row)


def api_score(ctx):
    """{criterion_id, alt_id, value, note}: DOIT 1 (passe) / 0 (échoue), VEUT 1-10; value "" clears."""
    pid = access(ctx, "editor")
    row = _kt(ctx, pid)
    _editable(row)
    crit = ctx.conn.execute("SELECT * FROM tools_kt_criteria WHERE id = ? AND kt_id = ?",
                            (int(ctx.body.get("criterion_id") or 0), row["id"])).fetchone()
    alt = int(ctx.body.get("alt_id") or 0)
    if crit is None or not ctx.conn.execute("SELECT 1 FROM tools_kt_alts WHERE id = ? AND kt_id = ?", (alt, row["id"])).fetchone():
        raise ApiError(400, "Case introuvable dans cette analyse.")
    raw = ctx.body.get("value")
    if raw in (None, ""):
        ctx.conn.execute("DELETE FROM tools_kt_scores WHERE criterion_id = ? AND alt_id = ?", (crit["id"], alt))
    else:
        value = int(raw)
        if crit["kind"] == "must" and value not in (0, 1):
            raise ApiError(400, "Un DOIT se note Passe (1) ou Échoue (0).")
        if crit["kind"] == "want" and not 1 <= value <= 10:
            raise ApiError(400, "Un VEUT se note de 1 à 10 (10 = la meilleure alternative sur ce critère).")
        ctx.conn.execute("INSERT INTO tools_kt_scores (criterion_id, alt_id, value, note) VALUES (?, ?, ?, ?) "
                         "ON CONFLICT(criterion_id, alt_id) DO UPDATE SET value = excluded.value, note = excluded.note",
                         (crit["id"], alt, value, _text(ctx.body, "note", "Note", 1000)))
    _log(ctx, "kt_score", row["id"], {"criterion_id": crit["id"], "alt_id": alt, "value": raw})
    return detail(ctx, row)


def api_risk(ctx):
    """POST: add {alt_id, text, probability, seriousness}; PATCH .../<rid>: {delete: true}."""
    pid = access(ctx, "editor")
    row = _kt(ctx, pid)
    _editable(row)
    rid = ctx.params.get("rid")
    if rid is not None:
        ctx.conn.execute("DELETE FROM tools_kt_risks WHERE id = ? AND kt_id = ?", (int(rid), row["id"]))
        _log(ctx, "kt_risk_delete", row["id"], {"risk_id": int(rid)})
        return detail(ctx, row)
    alt = int(ctx.body.get("alt_id") or 0)
    if not ctx.conn.execute("SELECT 1 FROM tools_kt_alts WHERE id = ? AND kt_id = ?", (alt, row["id"])).fetchone():
        raise ApiError(400, "Alternative introuvable.")
    levels = []
    for name, label in (("probability", "Probabilité"), ("seriousness", "Gravité")):
        value = int(ctx.body.get(name) or 0)
        if value not in LEVELS:
            raise ApiError(400, "{} : Faible (1), Moyenne (2) ou Élevée (3).".format(label))
        levels.append(value)
    ctx.conn.execute("INSERT INTO tools_kt_risks (kt_id, alt_id, text, probability, seriousness) VALUES (?, ?, ?, ?, ?)",
                     (row["id"], alt, _text(ctx.body, "text", "Risque", 500, True), *levels))
    _log(ctx, "kt_risk_add", row["id"], {"alt_id": alt})
    return detail(ctx, row)
