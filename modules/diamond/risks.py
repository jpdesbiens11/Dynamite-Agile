"""« Analyse de risque projet » of Diamond (0.60.14, D-O-026): the high-level risk register of the project, before
the DFMEA.

One line per risk, written « Si <cause>, alors <événement>, ce qui <conséquence> », numbered R-1, R-2… for ever (an
archived risk keeps its number). Probability and impact on 1-5; score = P x I; level: 1-4 Faible, 5-9 Moyen, 10-14
Élevé, 15-25 Critique. A response (éviter, réduire, transférer, accepter), an action, an owner (a member of the Space),
a due date, a status, and the residual probability and impact once the action is done. A technical risk may point to
a function of the tree and be marked « À détailler dans le DFMEA ». The checks say what a review would ask. Every write
is journalled; the register exports as CSV (registered by the core).
"""
import csv
import datetime as dt
import io

from core import audit, db, validate
from core.errors import ApiError
from core.files import RawFile

from . import functions as F

CATEGORIES = {"technique": "Technique", "delais": "Délais", "couts": "Coûts", "equipe": "Équipe et ressources",
              "fournisseurs": "Fournisseurs", "normes": "Normes et réglementation", "marche": "Marché et client",
              "securite": "Sécurité"}
PHASES = {"": "—", "A": "A. Discovery", "B": "B. Concept", "C": "C. Design", "D": "D. Validation et lancement"}
RESPONSES = {"": "— à choisir —", "eviter": "Éviter", "reduire": "Réduire", "transferer": "Transférer", "accepter": "Accepter"}
STATUSES = {"open": "Ouvert", "in_progress": "En traitement", "closed": "Fermé"}
LEVELS = [(15, "critique", "Critique"), (10, "eleve", "Élevé"), (5, "moyen", "Moyen"), (1, "faible", "Faible")]
FIELDS = ("title", "cause", "consequence", "category", "phase", "probability", "impact", "response", "action", "owner_id",
          "due_date", "status", "residual_p", "residual_i", "function_id", "to_dfmea", "notes")
MAX_RISKS = 300


def level(score):
    for low, key, label in LEVELS:
        if score and score >= low:
            return {"key": key, "label": label}
    return {"key": "none", "label": "—"}


def _text(body, name, label, limit, required=False):
    value = " ".join(str(body.get(name) or "").split()) if name != "notes" else str(body.get(name) or "").strip()
    if required and not value:
        raise ApiError(400, "{} obligatoire. Correctif : « Si <cause>, alors <événement> » en quelques mots.".format(label))
    if len(value) > limit:
        raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, limit, len(value)))
    return value


def _choice(body, name, options, label):
    value = str(body.get(name) or "").strip()
    if value not in options:
        raise ApiError(400, "{} « {} » inconnu. Correctif : {}.".format(label, value, ", ".join(v for v in options.values() if v != "—")))
    return value


def _scale(body, name, label, optional=False):
    value = body.get(name)
    if optional and value in (None, "", 0, "0"):
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ApiError(400, "{} : un nombre de 1 à 5. Correctif : 1 (rare / faible) à 5 (presque certain / majeur).".format(label))
    if not 1 <= value <= 5:
        raise ApiError(400, "{} {} : de 1 à 5. Correctif : 1 (rare / faible) à 5 (presque certain / majeur).".format(label, value))
    return value


def _members(conn, pid):
    return [dict(r) for r in conn.execute(
        "SELECT u.id, u.display_name FROM users u WHERE u.is_active = 1 AND (u.id IN (SELECT user_id FROM memberships WHERE project_id = ?) "
        "OR u.is_admin = 1) ORDER BY u.display_name", (pid,))]


def _fields(conn, pid, body, partial):
    out = {}
    def want(name):
        return not partial or name in body
    if want("title"):
        out["title"] = _text(body, "title", "Risque", 200, True)
    for name, label, limit in (("cause", "Cause", 400), ("consequence", "Conséquence", 400), ("action", "Action", 600), ("notes", "Notes", 2000)):
        if name in body:
            out[name] = _text(body, name, label, limit)
    if want("category"):
        out["category"] = _choice(dict(body, category=body.get("category") or "technique"), "category", CATEGORIES, "Catégorie")
    for name, options, label in (("phase", PHASES, "Phase"), ("response", RESPONSES, "Stratégie"), ("status", STATUSES, "Status")):
        if name in body:
            out[name] = _choice(body, name, options, label)
    for name, label in (("probability", "Probabilité"), ("impact", "Impact")):
        if want(name):
            out[name] = _scale(dict(body, **{name: body.get(name, 3)}), name, label)
    for name, label in (("residual_p", "Probabilité résiduelle"), ("residual_i", "Impact résiduel")):
        if name in body:
            out[name] = _scale(body, name, label, optional=True)
    if "owner_id" in body:
        owner = body.get("owner_id")
        if owner in (None, "", 0):
            out["owner_id"] = None
        elif int(owner) not in {m["id"] for m in _members(conn, pid)}:
            raise ApiError(400, "Responsable introuvable parmi les membres du Space. Correctif : ajoutez-le au Space, ou choisissez un membre.")
        else:
            out["owner_id"] = int(owner)
    if "due_date" in body:
        value = str(body.get("due_date") or "").strip()
        if value:
            try:
                dt.date.fromisoformat(value)
            except ValueError:
                raise ApiError(400, "Échéance « {} » : date AAAA-MM-JJ. Correctif : choisissez-la dans le calendrier.".format(value))
        out["due_date"] = value
    if "function_id" in body:
        fid = body.get("function_id")
        if fid in (None, "", 0):
            out["function_id"] = None
        else:
            if not conn.execute("SELECT 1 FROM diamond_functions WHERE id = ? AND project_id = ? AND archived = 0", (int(fid), pid)).fetchone():
                raise ApiError(400, "Fonction introuvable dans l'arbre de ce Space. Correctif : choisissez une fonction de la liste.")
            out["function_id"] = int(fid)
    if "to_dfmea" in body:
        out["to_dfmea"] = 1 if body.get("to_dfmea") else 0
    return out


def rows(conn, pid):
    items = [dict(r) for r in conn.execute(
        "SELECT r.*, u.display_name AS owner_name, f.number AS function_number, f.text AS function_text FROM diamond_risks r "
        "LEFT JOIN users u ON u.id = r.owner_id LEFT JOIN diamond_functions f ON f.id = r.function_id AND f.archived = 0 "
        "WHERE r.project_id = ? AND r.archived = 0 ORDER BY r.number", (pid,))]
    for r in items:
        r["score"] = r["probability"] * r["impact"]
        r["level"] = level(r["score"])
        r["residual_score"] = r["residual_p"] * r["residual_i"] if r["residual_p"] and r["residual_i"] else None
        r["residual_level"] = level(r["residual_score"])
    return items


def checks(items, today=None):
    today = today or dt.date.today().isoformat()
    out = []
    live = [r for r in items if r["status"] != "closed"]
    if not items:
        return ["Aucun risque. Demandez à l'équipe : qu'est-ce qui pourrait empêcher le projet d'aboutir (technique, délais, "
                "coûts, équipe, fournisseurs, normes, marché, sécurité) ?"]
    high = [r for r in live if r["score"] >= 10 and (not r["action"] or not r["owner_id"])]
    if high:
        out.append("{} : risque élevé ou critique sans action ou sans responsable.".format(", ".join("R-{}".format(r["number"]) for r in high[:8])))
    late = [r for r in live if r["due_date"] and r["due_date"] < today]
    if late:
        out.append("{} : échéance dépassée.".format(", ".join("R-{}".format(r["number"]) for r in late[:8])))
    accepted = [r for r in live if r["response"] == "accepter" and r["score"] >= 15]
    if accepted:
        out.append("{} : risque critique accepté — à justifier dans les notes (pourquoi on vit avec).".format(
            ", ".join("R-{}".format(r["number"]) for r in accepted[:8])))
    worse = [r for r in items if r["residual_score"] and r["residual_score"] > r["score"]]
    if worse:
        out.append("{} : risque résiduel plus grand que le risque actuel.".format(", ".join("R-{}".format(r["number"]) for r in worse[:8])))
    tech = [r for r in live if r["category"] == "technique" and r["score"] >= 10 and not r["to_dfmea"]]
    if tech:
        out.append("{} : risque technique élevé — cochez « À détailler dans le DFMEA » (fonction, mode de défaillance, causes).".format(
            ", ".join("R-{}".format(r["number"]) for r in tech[:8])))
    if len({r["category"] for r in items}) == 1 and len(items) >= 3:
        out.append("Tous les risques sont de la même catégorie : pensez aussi aux délais, aux coûts, à l'équipe et aux fournisseurs.")
    return out


def payload(conn, pid):
    items = rows(conn, pid)
    view_items = F.rows(conn, pid)
    tree = F.in_tree(view_items)
    return {"risks": items, "checks": checks(items), "members": _members(conn, pid),
            "functions": [{"id": f["id"], "number": f["number"], "text": f["text"]} for f in view_items if f["id"] in tree],
            "labels": {"categories": CATEGORIES, "phases": PHASES, "responses": RESPONSES, "statuses": STATUSES,
                       "levels": [{"min": low, "key": key, "label": label} for low, key, label in LEVELS]}}


def _row(ctx, pid):
    row = ctx.conn.execute("SELECT * FROM diamond_risks WHERE id = ? AND project_id = ? AND archived = 0",
                           (validate.int_param(ctx.params, "rid"), pid)).fetchone()
    if row is None:
        raise ApiError(404, "Risque introuvable dans ce Space (déjà archivé ?). Correctif : rechargez la page.")
    return dict(row)


def _log(ctx, action, rid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "diamond_risks", rid, details, ctx.ip)


def api_list(ctx):
    return payload(ctx.conn, F.access(ctx))


def create(conn, user_id, pid, fields):
    if conn.execute("SELECT COUNT(*) FROM diamond_risks WHERE project_id = ? AND archived = 0", (pid,)).fetchone()[0] >= MAX_RISKS:
        raise ApiError(409, "{} risques au maximum par Space. Correctif : archivez les risques fermés.".format(MAX_RISKS))
    number = conn.execute("SELECT COALESCE(MAX(number), 0) + 1 FROM diamond_risks WHERE project_id = ?", (pid,)).fetchone()[0]
    now = db.utc_now()
    values = dict({"status": "open", "phase": "", "response": "", "cause": "", "consequence": "", "action": "", "notes": "",
                   "due_date": "", "to_dfmea": 0}, **fields)
    cols = [k for k in FIELDS if k in values]
    return conn.execute("INSERT INTO diamond_risks (project_id, number, {}, created_by, created_at, updated_by, updated_at) "
                        "VALUES (?, ?, {}, ?, ?, ?, ?)".format(", ".join(cols), ", ".join("?" * len(cols))),
                        [pid, number] + [values[k] for k in cols] + [user_id, now, user_id, now]).lastrowid


def api_create(ctx):
    pid = F.access(ctx, "editor")
    fields = _fields(ctx.conn, pid, ctx.body, partial=False)
    rid = create(ctx.conn, ctx.user["id"], pid, fields)
    _log(ctx, "diamond_risk_create", rid, {"title": fields["title"], "score": fields["probability"] * fields["impact"]})
    return dict(payload(ctx.conn, pid), created=rid)


def api_update(ctx):
    pid = F.access(ctx, "editor")
    row = _row(ctx, pid)
    changes = _fields(ctx.conn, pid, ctx.body, partial=True)
    if changes:
        ctx.conn.execute("UPDATE diamond_risks SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(
            ", ".join(k + " = ?" for k in changes)), list(changes.values()) + [ctx.user["id"], db.utc_now(), row["id"]])
        _log(ctx, "diamond_risk_update", row["id"], {k: v for k, v in changes.items() if k != "notes"})
    return payload(ctx.conn, pid)


def api_duplicate(ctx):
    pid = F.access(ctx, "editor")
    row = _row(ctx, pid)
    fields = {k: row[k] for k in FIELDS}
    fields["title"] = (row["title"] + " (copie)")[:200]
    fields["status"] = "open"
    rid = create(ctx.conn, ctx.user["id"], pid, fields)
    _log(ctx, "diamond_risk_duplicate", rid, {"from": row["number"]})
    return dict(payload(ctx.conn, pid), created=rid)


def api_archive(ctx):
    pid = F.access(ctx, "editor")
    row = _row(ctx, pid)
    ctx.conn.execute("UPDATE diamond_risks SET archived = 1, updated_by = ?, updated_at = ? WHERE id = ?", (ctx.user["id"], db.utc_now(), row["id"]))
    _log(ctx, "diamond_risk_archive", row["id"], {"number": row["number"], "title": row["title"]})
    return payload(ctx.conn, pid)


def api_export(ctx):
    pid = F.access(ctx)
    key = ctx.conn.execute("SELECT key FROM projects WHERE id = ?", (pid,)).fetchone()["key"]
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow(["Code", "Risque", "Cause", "Conséquence", "Catégorie", "Phase", "Probabilité", "Impact", "Score", "Niveau",
                "Stratégie", "Action", "Responsable", "Échéance", "Status", "P résiduelle", "I résiduel", "Score résiduel",
                "Fonction", "À détailler dans le DFMEA", "Notes"])
    for r in rows(ctx.conn, pid):
        w.writerow(["R-{}".format(r["number"]), r["title"], r["cause"], r["consequence"], CATEGORIES.get(r["category"], r["category"]),
                    PHASES.get(r["phase"], ""), r["probability"], r["impact"], r["score"], r["level"]["label"],
                    RESPONSES.get(r["response"], "") if r["response"] else "", r["action"], r["owner_name"] or "", r["due_date"],
                    STATUSES.get(r["status"], r["status"]), r["residual_p"] or "", r["residual_i"] or "", r["residual_score"] or "",
                    "F{} {}".format(r["function_number"], r["function_text"]) if r["function_number"] else "",
                    "Oui" if r["to_dfmea"] else "", r["notes"]])
    _log(ctx, "diamond_risk_export", pid)
    return RawFile(("﻿" + out.getvalue()).encode("utf-8"), "risques_projet_{}.csv".format(key), "text/csv")
