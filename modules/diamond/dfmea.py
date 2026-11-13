"""« DFMEA » of Diamond (0.60.15, D-O-027): the Design FMEA of the product, AIAG-VDA structure, on the functions of the
functional tree.

One row = one failure chain. The three levels of the structure (AIAG-VDA, DFMEA):
  Higher-Level Element  the end user / the product / the system -- where the failure effect lands (S);
  Focus Element         the assembly, sub-assembly or component analysed -- its function (from the tree), requirement,
                        failure mode;
  Lower-Level Element   the sub-component, detail part or characteristic -- the failure cause (O), the prevention and
                        detection controls (D): the columns where the team works to avoid the failure.
Scores: RPN = S x O x D and the Action Priority (dfmea_ap.py), side by side. Rows are added, duplicated, moved and
deleted freely (position); « Depuis l'arbre » adds one row per function not analysed yet, « Depuis les risques » one per
project risk marked « À détailler dans le DFMEA ». Every write is journalled; the table exports as CSV.
"""
import csv
import io

from core import audit, db, validate
from core.errors import ApiError
from core.files import RawFile

from . import actions as ACT
from . import classes as CL
from . import dfmea_ap as AP
from . import dfmea_practices as GP
from . import functions as F
from . import structure as S

TEXTS = {"higher": ("Higher-Level Element", 160), "focus": ("Focus Element", 160), "lower": ("Lower-Level Element", 160),
         "requirement": ("Requirement / Characteristic", 400), "failure_mode": ("Failure Mode", 400),
         "effect": ("Failure Effect", 400), "cause": ("Failure Cause", 400), "prevention": ("Prevention Controls", 4000),
         "detection_ctrl": ("Detection Controls", 400), "action": ("Actions", 600)}
RATINGS = {"severity": "Severity (S)", "occurrence": "Occurrence (O)", "detection": "Detection (D)"}
COLUMNS = ["higher", "focus", "lower", "function_id", "requirement", "failure_mode", "effect", "severity", "cause",
           "prevention", "occurrence", "detection_ctrl", "detection", "action"]
MAX_ROWS = 600


def _rows(conn, pid):
    items = [dict(r) for r in conn.execute(
        "SELECT d.*, f.number AS function_number, f.text AS function_text, r.number AS risk_number, ow.display_name AS action_owner_name, "
        "t.test_id AS test_code, t.title AS test_title, tp.key AS test_space FROM diamond_dfmea d "
        "LEFT JOIN diamond_functions f ON f.id = d.function_id AND f.archived = 0 "
        "LEFT JOIN testing_tests t ON t.id = d.test_id LEFT JOIN projects tp ON tp.id = t.project_id "
        "LEFT JOIN diamond_risks r ON r.id = d.risk_id AND r.archived = 0 LEFT JOIN users ow ON ow.id = d.action_owner_id "
        "WHERE d.project_id = ? ORDER BY d.position, d.id", (pid,))]
    for n, row in enumerate(items, start=1):
        row["line"] = n
        row["rpn"] = AP.rpn(row["severity"], row["occurrence"], row["detection"])
        row["ap"] = AP.action_priority(row["severity"], row["occurrence"], row["detection"])
    CL.enrich(conn, pid, items)  # 0.60.101 (D-O-108): the class CC / SC proposed by the rules, decided by a person
    return ACT.enrich(conn, items, "dfmea")  # 0.60.38 (D-O-047): owner, due date, status, Agile ticket


rows = _rows


def _tree_functions(conn, pid):
    items = F.rows(conn, pid)
    lv, tree = F.levels(items), F.in_tree(items)
    # 0.60.28 (D-O-037): the functions outside the tree (estime) too -- every function can fail, none is skipped
    return [{"id": f["id"], "number": f["number"], "text": f["text"], "level": lv[f["id"]], "ftype": f["ftype"], "parent_id": f["parent_id"],
             "in_tree": f["id"] in tree} for f in sorted(items, key=lambda f: (f["id"] not in tree, lv[f["id"]], f["position"], f["number"]))]


CATALOGUE = "TESTING"  # the key of the reference Space on an installation made before 0.60.41 (kept for older data)


def tests(conn, pid):
    """0.60.24 (D-O-033): the tests a row may name as its key detection test. 0.60.41 (D-O-050): the Space is a closed
    environment -- only its own Test Base (copied once from the reference catalogue when it has none)."""
    try:
        from modules.testing import catalog
        catalog.base(conn, pid)
    except Exception:  # before the Testing migrations (tests of old lots)
        pass
    rows = conn.execute("SELECT t.id, t.test_id AS code, t.title, p.key AS space FROM testing_tests t JOIN projects p ON p.id = t.project_id "
                        "WHERE t.project_id = ? ORDER BY t.test_id", (pid,)).fetchall()
    return [dict(r) for r in rows]


def checks(conn, pid, rows):
    out = []
    if not rows:
        return ["DFMEA vide : « Compléter le DFMEA » crée une ligne par fonction de l'arbre, avec son essai clé et les bonnes "
                "pratiques de prévention ; décrivez ensuite comment chacune peut faillir."]
    nofn = [r for r in rows if not r["function_id"]]
    if nofn:
        out.append("Ligne(s) {} sans fonction de l'arbre : le DFMEA reprend les fonctions de l'arbre fonctionnel.".format(
            ", ".join(str(r["line"]) for r in nofn[:10])))
    unrated = [r for r in rows if r["failure_mode"] and r["failure_mode"] != GP.RAS and not r["ap"]]
    if unrated:
        out.append("Ligne(s) {} : mode de défaillance sans cotation S, O et D complète.".format(", ".join(str(r["line"]) for r in unrated[:10])))
    late = [r for r in rows if r["late"]]  # 0.60.38 (D-O-047)
    if late:
        out.append("Ligne(s) {} : action en retard sur son échéance.".format(", ".join(str(r["line"]) for r in late[:10])))
    orphan = [r for r in rows if r["action"].strip() and not r["action_owner_id"] and r["action_status"] != "done"]
    if orphan:
        out.append("Ligne(s) {} : action sans responsable — choisissez un membre de l'équipe.".format(", ".join(str(r["line"]) for r in orphan[:10])))
    high = [r for r in rows if r["ap"] == "H" and not r["action"].strip()]
    if high:
        out.append("Ligne(s) {} : AP High sans action — une action est attendue (ou la justification des contrôles actuels).".format(
            ", ".join(str(r["line"]) for r in high[:10])))
    severe = [r for r in rows if (r["severity"] or 0) >= 9 and (r["occurrence"] or 0) >= 4]
    if severe:
        out.append("Ligne(s) {} : sévérité 9-10 (sécurité ou norme) avec une occurrence de 4 ou plus — revoir la conception, "
                   "pas seulement la détection.".format(", ".join(str(r["line"]) for r in severe[:10])))
    ras = [r for r in rows if r["failure_mode"] == GP.RAS]  # 0.60.28 (D-O-037): every function can fail, RAS is justified
    if [r for r in ras if not r["effect"].strip()]:
        out.append("Ligne(s) {} : « Rien à signaler » sans justification — écrivez dans Failure Effect pourquoi cette fonction "
                   "ne peut pas faillir.".format(", ".join(str(r["line"]) for r in ras if not r["effect"].strip())))
    elif ras:
        out.append("Ligne(s) {} : « Rien à signaler » — officiellement, toute fonction peut tomber en panne ; relisez ce choix à "
                   "chaque revue.".format(", ".join(str(r["line"]) for r in ras[:10])))
    covered = {r["function_id"] for r in rows}
    missing = [f for f in _tree_functions(conn, pid) if f["id"] not in covered]
    if missing:
        out.append("Fonction(s) de l'arbre sans ligne : {} — « Compléter le DFMEA » en crée une par fonction, avec l'essai clé et "
                   "les bonnes pratiques.".format(", ".join("F{}".format(f["number"]) for f in missing[:10])))
    untested = [r for r in rows if r["failure_mode"] != GP.RAS and not r["test_id"]]
    if untested:
        out.append("Ligne(s) {} sans essai clé de la Test Base.".format(", ".join(str(r["line"]) for r in untested[:10])))
    risks = conn.execute("SELECT number FROM diamond_risks WHERE project_id = ? AND archived = 0 AND to_dfmea = 1 AND id NOT IN "
                         "(SELECT risk_id FROM diamond_dfmea WHERE project_id = ? AND risk_id IS NOT NULL)", (pid, pid)).fetchall()
    if risks:
        out.append("Risque(s) projet à détailler ici : {} — « Depuis les risques ».".format(", ".join("R-{}".format(r["number"]) for r in risks)))
    return out + CL.checks(rows, CL.rules(conn, pid))  # 0.60.101 (D-O-108)


def payload(conn, pid):
    rows = _rows(conn, pid)
    suggest = {k: sorted({r[k] for r in rows if r[k]}) for k in ("higher", "focus", "lower")}
    project = conn.execute("SELECT name FROM projects WHERE id = ?", (pid,)).fetchone()
    if project and project["name"] not in suggest["higher"]:
        suggest["higher"].insert(0, project["name"])
    return {"rows": rows, "functions": _tree_functions(conn, pid), "tests": tests(conn, pid), "suggest": suggest,
            "checks": checks(conn, pid, rows), "members": ACT.members(conn, pid),
            "labels": {"texts": {k: v[0] for k, v in TEXTS.items()}, "ratings": RATINGS, "ap": AP.AP_LABELS, "statuses": ACT.DFMEA_STATUSES},
            "legend": AP.legend(), "classes": CL.info(conn, pid, rows)}


def _log(ctx, action, oid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "diamond_dfmea", oid, details, ctx.ip)


def _row(ctx, pid):
    row = ctx.conn.execute("SELECT * FROM diamond_dfmea WHERE id = ? AND project_id = ?", (validate.int_param(ctx.params, "did"), pid)).fetchone()
    if row is None:
        raise ApiError(404, "Ligne du DFMEA introuvable (déjà effacée ?). Correctif : rechargez la page.")
    return dict(row)


def _fields(conn, pid, body):
    out = {}
    for name, (label, limit) in TEXTS.items():
        if name in body:
            value = str(body.get(name) or "").strip()
            if len(value) > limit:
                raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, limit, len(value)))
            out[name] = GP.ras(value) if name == "failure_mode" else value
    for name, label in RATINGS.items():
        if name in body:
            value = body.get(name)
            if value in (None, "", 0, "0"):
                out[name] = None
                continue
            try:
                value = int(value)
            except (TypeError, ValueError):
                value = -1
            if not 1 <= value <= 10:
                raise ApiError(400, "{} « {} » : de 1 à 10. Correctif : voir la légende (bouton « Légende AP »).".format(label, body.get(name)))
            out[name] = value
    if "function_id" in body:
        fid = body.get("function_id")
        if fid in (None, "", 0):
            out["function_id"] = None
        else:
            if not conn.execute("SELECT 1 FROM diamond_functions WHERE id = ? AND project_id = ? AND archived = 0", (int(fid), pid)).fetchone():
                raise ApiError(400, "Fonction introuvable dans l'arbre de ce Space. Correctif : choisissez une fonction de la liste.")
            out["function_id"] = int(fid)
    if "action_owner_id" in body:  # 0.60.38 (D-O-047): who carries the action, by when, where it stands
        out["action_owner_id"] = ACT.owner(conn, pid, body.get("action_owner_id"))
    if "action_due" in body:
        out["action_due"] = ACT.due(body.get("action_due"))
    if "action_status" in body:
        value = str(body.get("action_status") or "open")
        if value not in ACT.DFMEA_STATUSES:
            raise ApiError(400, "Status de l'action « {} » inconnu. Correctif : {}.".format(value, ", ".join(ACT.DFMEA_STATUSES.values())))
        out["action_status"] = value
    if "test_id" in body:  # 0.60.24: one key test per row (choose, change, remove)
        tid = body.get("test_id")
        if tid in (None, "", 0, "0"):
            out["test_id"] = None
        else:
            try:
                tid = int(tid)
            except (TypeError, ValueError):
                tid = -1
            if tid not in {t["id"] for t in tests(conn, pid)}:
                raise ApiError(400, "Essai introuvable dans la Test Base de ce Space ni dans le catalogue. Correctif : choisissez un "
                                    "essai de la liste.")
            out["test_id"] = tid
    return out


def _renumber(conn, pid, ids):
    for pos, i in enumerate(ids):
        conn.execute("UPDATE diamond_dfmea SET position = ? WHERE id = ?", (pos, i))


def _order(conn, pid):
    return [r["id"] for r in conn.execute("SELECT id FROM diamond_dfmea WHERE project_id = ? ORDER BY position, id", (pid,))]


def insert(conn, user_id, pid, fields, after_id=None):
    if conn.execute("SELECT COUNT(*) FROM diamond_dfmea WHERE project_id = ?", (pid,)).fetchone()[0] >= MAX_ROWS:
        raise ApiError(409, "{} lignes au maximum par DFMEA. Correctif : regroupez les causes semblables.".format(MAX_ROWS))
    now = db.utc_now()
    values = {k: fields.get(k, "" if k in TEXTS else None) for k in COLUMNS}
    values["risk_id"] = fields.get("risk_id")
    values["test_id"] = fields.get("test_id")
    for name in ("action_owner_id", "action_due", "action_status"):  # 0.60.38
        if fields.get(name) is not None:
            values[name] = fields[name]
    cols = list(values)
    did = conn.execute("INSERT INTO diamond_dfmea (project_id, position, {}, created_by, created_at, updated_by, updated_at) "
                       "VALUES (?, 0, {}, ?, ?, ?, ?)".format(", ".join(cols), ", ".join("?" * len(cols))),
                       [pid] + [values[k] for k in cols] + [user_id, now, user_id, now]).lastrowid
    ids = [i for i in _order(conn, pid) if i != did]
    ids.insert(ids.index(after_id) + 1 if after_id in ids else len(ids), did)
    _renumber(conn, pid, ids)
    return did


def api_list(ctx):
    return payload(ctx.conn, F.access(ctx))


def api_create(ctx):
    pid = F.access(ctx, "editor")
    after = ctx.body.get("after_id")
    did = insert(ctx.conn, ctx.user["id"], pid, _fields(ctx.conn, pid, ctx.body), int(after) if after else None)
    _log(ctx, "diamond_dfmea_create", did)
    return dict(payload(ctx.conn, pid), created=did)


def api_update(ctx):
    pid = F.access(ctx, "editor")
    row = _row(ctx, pid)
    changes = _fields(ctx.conn, pid, ctx.body)
    if changes:
        ctx.conn.execute("UPDATE diamond_dfmea SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(
            ", ".join(k + " = ?" for k in changes)), list(changes.values()) + [ctx.user["id"], db.utc_now(), row["id"]])
        _log(ctx, "diamond_dfmea_update", row["id"], changes)
    return payload(ctx.conn, pid)


def api_duplicate(ctx):
    pid = F.access(ctx, "editor")
    row = _row(ctx, pid)
    did = insert(ctx.conn, ctx.user["id"], pid, {k: row[k] for k in COLUMNS + ["risk_id", "test_id", "action_owner_id", "action_due"]}, row["id"])
    _log(ctx, "diamond_dfmea_duplicate", did, {"from": row["id"]})
    return dict(payload(ctx.conn, pid), created=did)


def api_move(ctx):
    """{direction: "up" | "down"} or {index: n} (0 = first line)."""
    pid = F.access(ctx, "editor")
    row = _row(ctx, pid)
    conn = ctx.conn
    ids = _order(conn, pid)
    i = ids.index(row["id"])
    if "index" in ctx.body:
        target = max(0, min(int(ctx.body["index"]), len(ids) - 1))
    else:
        target = i + (-1 if ctx.body.get("direction") == "up" else 1)
        target = max(0, min(target, len(ids) - 1))
    ids.insert(target, ids.pop(i))
    _renumber(conn, pid, ids)
    _log(ctx, "diamond_dfmea_move", row["id"], {"from": i + 1, "to": target + 1})
    return payload(conn, pid)


def api_delete(ctx):
    pid = F.access(ctx, "editor")
    row = _row(ctx, pid)
    ctx.conn.execute("DELETE FROM diamond_dfmea WHERE id = ?", (row["id"],))
    _renumber(ctx.conn, pid, _order(ctx.conn, pid))
    _log(ctx, "diamond_dfmea_delete", row["id"], {k: row[k] for k in ("focus", "failure_mode", "cause") if row[k]})
    return payload(ctx.conn, pid)


def api_from_tree(ctx):
    """One row per function of the detail view (tertiaries, or a secondary without them) not analysed yet."""
    pid = F.access(ctx, "editor")
    view_nodes, items = S.nodes(ctx.conn, pid)
    by_id = {f["id"]: f for f in items}
    covered = {r["function_id"] for r in ctx.conn.execute("SELECT function_id FROM diamond_dfmea WHERE project_id = ?", (pid,))}
    name = ctx.conn.execute("SELECT name FROM projects WHERE id = ?", (pid,)).fetchone()["name"]
    added = 0
    for f in sorted(view_nodes["detail"].values(), key=lambda f: (by_id[S.sub_of(f, by_id)]["position"], f["position"])):
        if f["id"] in covered:
            continue
        sub = by_id[S.sub_of(f, by_id)]
        insert(ctx.conn, ctx.user["id"], pid, {"higher": name, "focus": "Sous-système F{} · {}".format(sub["number"], sub["text"])[:160],
                                               "function_id": f["id"]})
        added += 1
    _log(ctx, "diamond_dfmea_from_tree", pid, {"rows": added})
    return dict(payload(ctx.conn, pid), added=added)


def api_from_risks(ctx):
    pid = F.access(ctx, "editor")
    name = ctx.conn.execute("SELECT name FROM projects WHERE id = ?", (pid,)).fetchone()["name"]
    todo = ctx.conn.execute("SELECT * FROM diamond_risks WHERE project_id = ? AND archived = 0 AND to_dfmea = 1 AND id NOT IN "
                            "(SELECT risk_id FROM diamond_dfmea WHERE project_id = ? AND risk_id IS NOT NULL) ORDER BY number",
                            (pid, pid)).fetchall()
    for r in todo:
        insert(ctx.conn, ctx.user["id"], pid, {"higher": name, "function_id": r["function_id"], "failure_mode": r["title"],
                                               "effect": r["consequence"], "cause": r["cause"], "risk_id": r["id"]})
    _log(ctx, "diamond_dfmea_from_risks", pid, {"rows": len(todo)})
    return dict(payload(ctx.conn, pid), added=len(todo))


def api_export(ctx):
    pid = F.access(ctx)
    key = ctx.conn.execute("SELECT key FROM projects WHERE id = ?", (pid,)).fetchone()["key"]
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow(["Ligne", "Higher-Level Element", "Focus Element", "Lower-Level Element", "Function of Focus Element",
                "Requirement / Characteristic", "Failure Mode", "Failure Effect", "S", "Failure Cause", "Prevention Controls", "O",
                "Detection Controls", "Essai clé (Test Base)", "D", "RPN", "AP", "Actions", "Responsable", "Échéance", "Status de l'action",
                "Ticket Agile", "Risque projet", "Class", "Class Status", "Décision de classe", "Justification de la classe"])
    cust = CL.customer(ctx.conn, pid)  # 0.60.101 (D-O-108): the symbol of the Space's customer
    for r in _rows(ctx.conn, pid):
        w.writerow([r["line"], r["higher"], r["focus"], r["lower"],
                    "F{} {}".format(r["function_number"], r["function_text"]) if r["function_number"] else "", r["requirement"],
                    r["failure_mode"], r["effect"], r["severity"] or "", r["cause"], r["prevention"], r["occurrence"] or "",
                    r["detection_ctrl"], "{} {}".format(r["test_code"], r["test_title"]) if r["test_code"] else "", r["detection"] or "", r["rpn"] or "", AP.AP_LABELS.get(r["ap"], ""), r["action"],
                    r["action_owner_name"] or "", r["action_due"], ACT.DFMEA_STATUSES.get(r["action_status"], ""),
                    r["ticket"]["key"] if r["ticket"] else "", "R-{}".format(r["risk_number"]) if r["risk_number"] else ""]
                   + class_cells(r, cust))
    _log(ctx, "diamond_dfmea_export", pid)
    return RawFile(("﻿" + out.getvalue()).encode("utf-8"), "dfmea_{}.csv".format(key), "text/csv")


def class_cells(r, cust):
    """0.60.101 (D-O-108): Class (symbol of the customer), Class Status, who and when, why -- for the CSV and Excel exports."""
    st = r["class_status"]
    who = " · ".join(x for x in (r["class_by_initials"] or r["class_by_name"], r["class_at"][:10]) if x) if r["class_state"] else ""
    return [CL.symbol(cust, r["class_shown"]) if st == "confirmed" else CL.symbol(cust, r["class_shown"]) + " ?" if st == "proposed" else "",
            CL.STATES.get(st, "") + (" (" + CL.symbol(cust, r["class_code"]) + ")" if st == "refused" else ""), who,
            r["class_reason"] if r["class_state"] else ""]
