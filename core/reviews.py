"""Annual review cycle of an employee, internship evaluation of an intern (core lot v0.30, D-B-111).

Three phases, each signed by BOTH the employee and his manager before the next one opens:
- start ("Début d'année" / intern: "Accueil"): annual, development and training objectives are agreed;
- mid ("Mi-année" / "Mi-stage"): on EVERY item, a comment from the employee and one from the manager;
- end ("Fin d'année" / "Évaluation finale"): EVERY item receives a verdict from the manager (the employee may give his own
  self-assessment), an overall comment from each side; for an intern, a competency grid scored 1 to 4 and a
  recommendation. The year can be closed (objectives.api_archive) only once the end phase is signed by both.
Items = the objectives of the year (core/objectives.py) + the items modules contribute through a `review_items(conn,
user_id, year)` hook (Training: the training plan). A signed phase is read-only; the manager can reopen it, which also
reopens the phases after it. Private like the objectives: the employee and HIS manager only. Journalled without text.
"""
from . import audit, db, modules, profile, validate
from .errors import ApiError
from .objectives import STATUSES, _archived, _year, relation

MIGRATIONS = [
    (15, """
        CREATE TABLE review_phases (
            user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            year              INTEGER NOT NULL,
            phase             TEXT NOT NULL,
            employee_comment  TEXT NOT NULL DEFAULT '',
            manager_comment   TEXT NOT NULL DEFAULT '',
            recommendation    TEXT NOT NULL DEFAULT '',
            employee_signed_at TEXT,
            manager_signed_at  TEXT,
            PRIMARY KEY (user_id, year, phase)
        );
        CREATE TABLE review_items (
            user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            year             INTEGER NOT NULL,
            item_type        TEXT NOT NULL,
            item_id          INTEGER NOT NULL,
            phase            TEXT NOT NULL,
            employee_comment TEXT NOT NULL DEFAULT '',
            manager_comment  TEXT NOT NULL DEFAULT '',
            employee_verdict TEXT NOT NULL DEFAULT '',
            verdict          TEXT NOT NULL DEFAULT '',
            updated_at       TEXT NOT NULL,
            PRIMARY KEY (item_type, item_id, phase)
        );
        CREATE TABLE review_ratings (
            user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            year      INTEGER NOT NULL,
            criterion TEXT NOT NULL,
            score     INTEGER,
            comment   TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (user_id, year, criterion)
        );
    """),
]

PHASES = ("start", "mid", "end")
LABELS = {"employee": {"start": "Début d'année", "mid": "Mi-année", "end": "Fin d'année"},
          "intern": {"start": "Accueil", "mid": "Mi-stage", "end": "Évaluation finale"}}
VERDICTS = {"exceeded": "Dépassé", "achieved": "Atteint", "partial": "Partiellement atteint", "missed": "Non atteint",
            "dropped": "Abandonné (justifié)"}
CRITERIA = {"technique": "Rigueur technique", "qualite": "Qualité du travail", "autonomie": "Autonomie",
            "communication": "Communication", "equipe": "Esprit d'équipe", "apprentissage": "Capacité d'apprentissage"}
SCORES = {1: "1 · À améliorer", 2: "2 · Satisfaisant", 3: "3 · Très bien", 4: "4 · Excellent"}
RECOMMENDATIONS = {"rehire": "Réembauche recommandée", "extend": "Prolongation recommandée", "discuss": "À discuter",
                   "no": "Non recommandée"}
ITEM_FIELDS = {"self": ("employee_comment", "employee_verdict"), "manager": ("manager_comment", "verdict")}
PHASE_FIELDS = {"self": ("employee_comment",), "manager": ("manager_comment", "recommendation")}


def _log(ctx, action, target_id, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "reviews", target_id, details, ctx.ip)


def items(conn, user_id, year):
    """Every item to review: objectives of the year, then what the modules contribute (training plan)."""
    out = [{"type": "objective", "id": r["id"], "title": r["title"], "group": r["kind"],
            "status": STATUSES.get(r["status"], r["status"])}
           for r in conn.execute("SELECT id, title, kind, status FROM objectives WHERE user_id = ? AND year = ? ORDER BY kind, id",
                                 (user_id, year))]
    for key, hook in modules.review_hooks():
        for item in hook(conn, user_id, year) or []:
            out.append(dict(item, type=key, group=key))
    return out


def _phases(conn, user_id, year):
    rows = {r["phase"]: dict(r) for r in conn.execute("SELECT * FROM review_phases WHERE user_id = ? AND year = ?", (user_id, year))}
    out = {}
    for p in PHASES:
        row = rows.get(p) or {"employee_comment": "", "manager_comment": "", "recommendation": "",
                              "employee_signed_at": None, "manager_signed_at": None}
        row.pop("user_id", None), row.pop("year", None), row.pop("phase", None)
        row["signed"] = bool(row["employee_signed_at"] and row["manager_signed_at"])
        out[p] = row
    return out


def _reviews(conn, user_id, year):
    out = {}
    for r in conn.execute("SELECT * FROM review_items WHERE user_id = ? AND year = ?", (user_id, year)):
        out.setdefault("{}:{}".format(r["item_type"], r["item_id"]), {})[r["phase"]] = {
            k: r[k] for k in ("employee_comment", "manager_comment", "employee_verdict", "verdict")}
    return out


def _ratings(conn, user_id, year):
    return {r["criterion"]: {"score": r["score"], "comment": r["comment"]}
            for r in conn.execute("SELECT * FROM review_ratings WHERE user_id = ? AND year = ?", (user_id, year))}


def missing(conn, user_id, year, phase, side):
    """What still blocks `side` ('self' / 'manager') from signing `phase` -- plain sentences, empty when ready."""
    kind = profile.header(conn, user_id)["kind"]
    labels = LABELS[kind]
    phases = _phases(conn, user_id, year)
    out = []
    index = PHASES.index(phase)
    if index and not phases[PHASES[index - 1]]["signed"]:
        out.append("L'étape « {} » doit d'abord être signée par les deux.".format(labels[PHASES[index - 1]]))
    todo = items(conn, user_id, year)
    if phase == "start" and not any(i["type"] == "objective" for i in todo):
        out.append("Aucun objectif : ajoutez au moins un objectif avant de convenir des objectifs.")
    reviews = _reviews(conn, user_id, year)
    own = "employee_comment" if side == "self" else "manager_comment"
    if phase in ("mid", "end"):
        silent = [i["title"] for i in todo if not reviews.get("{}:{}".format(i["type"], i["id"]), {}).get(phase, {}).get(own)]
        if silent:
            out.append("Commentaire {} manquant sur : {}.".format("de l'employé" if side == "self" else "du gestionnaire",
                                                                  ", ".join(silent[:6]) + (" …" if len(silent) > 6 else "")))
    if phase == "end" and side == "manager":
        no_verdict = [i["title"] for i in todo if not reviews.get("{}:{}".format(i["type"], i["id"]), {}).get("end", {}).get("verdict")]
        if no_verdict:
            out.append("Verdict manquant sur : {}.".format(", ".join(no_verdict[:6]) + (" …" if len(no_verdict) > 6 else "")))
        if kind == "intern":
            ratings = _ratings(conn, user_id, year)
            unscored = [CRITERIA[c] for c in CRITERIA if not (ratings.get(c) or {}).get("score")]
            if unscored:
                out.append("Grille de stage incomplète : " + ", ".join(unscored) + ".")
            if not phases["end"]["recommendation"]:
                out.append("Recommandation de fin de stage manquante.")
    if phase == "end" and not phases["end"]["manager_comment" if side == "manager" else "employee_comment"]:
        out.append("Appréciation globale {} manquante.".format("du gestionnaire" if side == "manager" else "de l'employé"))
    return out


def can_close(conn, user_id, year):
    """Sentences blocking the closing of the year (objectives.api_archive)."""
    phases = _phases(conn, user_id, year)
    if phases["end"]["signed"]:
        return []
    labels = LABELS[profile.header(conn, user_id)["kind"]]
    return ["L'étape « {} » n'est pas signée par les deux : chaque item doit avoir été évalué.".format(labels["end"])]


def api_get(ctx):
    target = validate.int_param(ctx.params, "uid")
    rel = relation(ctx.conn, ctx.user, target)
    year = _year(ctx)
    conn = ctx.conn
    head = profile.header(conn, target)
    phases = _phases(conn, target, year)
    current = next((p for p in PHASES if not phases[p]["signed"]), "done")
    side = "self" if rel == "self" else "manager"
    blockers = {p: missing(conn, target, year, p, side) for p in PHASES}
    _log(ctx, "review_viewed", target, {"year": year, "as": rel})
    return {"relation": rel, "year": year, "profile": head, "labels": LABELS[head["kind"]], "phases": phases, "current": current,
            "items": items(conn, target, year), "reviews": _reviews(conn, target, year), "ratings": _ratings(conn, target, year),
            "blockers": blockers, "archived": _archived(conn, target, year), "verdicts": VERDICTS, "criteria": CRITERIA,
            "scores": SCORES, "recommendations": RECOMMENDATIONS}


def _open_phase(conn, target, year, phase, labels):
    if phase not in PHASES:
        raise ApiError(404, "Étape inconnue. Correctif : start, mid ou end.")
    if _archived(conn, target, year):
        raise ApiError(409, "Année {} archivée : lecture seule.".format(year))
    phases = _phases(conn, target, year)
    if phases[phase]["signed"]:
        raise ApiError(409, "L'étape « {} » est signée par les deux : lecture seule. Correctif : le gestionnaire peut la "
                            "rouvrir.".format(labels[phase]))
    index = PHASES.index(phase)
    if index and not phases[PHASES[index - 1]]["signed"]:
        raise ApiError(409, "L'étape « {} » n'est pas encore ouverte. Correctif : signez d'abord « {} » tous les deux.".format(
            labels[phase], labels[PHASES[index - 1]]))


def _ensure_phase(conn, target, year, phase):
    conn.execute("INSERT INTO review_phases (user_id, year, phase) VALUES (?, ?, ?) ON CONFLICT DO NOTHING", (target, year, phase))


def api_item(ctx):
    target = validate.int_param(ctx.params, "uid")
    rel = relation(ctx.conn, ctx.user, target)
    year = _year(ctx)
    body = ctx.body
    phase = body.get("phase")
    labels = LABELS[profile.header(ctx.conn, target)["kind"]]
    if phase not in ("mid", "end"):
        raise ApiError(400, "Les items se commentent à « {} » et à « {} ».".format(labels["mid"], labels["end"]))
    _open_phase(ctx.conn, target, year, phase, labels)
    key = (str(body.get("item_type") or ""), body.get("item_id"))
    if not any(i["type"] == key[0] and str(i["id"]) == str(key[1]) for i in items(ctx.conn, target, year)):
        raise ApiError(404, "Item introuvable pour cette année.")
    allowed = ITEM_FIELDS["self" if rel == "self" else "manager"]
    asked = [k for k in body if k in ("employee_comment", "manager_comment", "employee_verdict", "verdict")]
    refused = [k for k in asked if k not in allowed]
    if refused:
        raise ApiError(403, "Champ(s) {} réservé(s) à {}.".format(", ".join(refused), "votre gestionnaire" if rel == "self" else "l'employé"))
    changes = {}
    for name in asked:
        if name.endswith("verdict"):
            value = str(body.get(name) or "")
            if value and value not in VERDICTS:
                raise ApiError(400, "Verdict « {} » inconnu. Correctif : {}.".format(value, ", ".join(VERDICTS)))
            if value and phase != "end":
                raise ApiError(400, "Le verdict se donne à « {} ».".format(labels["end"]))
            changes[name] = value
        else:
            changes[name] = validate.text(body, name, 4000, required=False)
    if not changes:
        raise ApiError(400, "Aucune modification demandée.")
    now = db.utc_now()
    ctx.conn.execute("INSERT INTO review_items (user_id, year, item_type, item_id, phase, updated_at) VALUES (?, ?, ?, ?, ?, ?) "
                     "ON CONFLICT DO NOTHING", (target, year, key[0], int(key[1]), phase, now))
    ctx.conn.execute("UPDATE review_items SET {}, updated_at = ? WHERE item_type = ? AND item_id = ? AND phase = ?".format(
        ", ".join(k + " = ?" for k in changes)), list(changes.values()) + [now, key[0], int(key[1]), phase])
    _log(ctx, "review_item_updated", target, {"year": year, "phase": phase, "item": key[0], "fields": sorted(changes)})
    return {"ok": True}


def api_phase(ctx):
    target = validate.int_param(ctx.params, "uid")
    rel = relation(ctx.conn, ctx.user, target)
    year = _year(ctx)
    phase = ctx.params.get("phase")
    head = profile.header(ctx.conn, target)
    _open_phase(ctx.conn, target, year, phase, LABELS[head["kind"]])
    allowed = PHASE_FIELDS["self" if rel == "self" else "manager"]
    refused = [k for k in ctx.body if k not in allowed]
    if refused:
        raise ApiError(403, "Champ(s) {} réservé(s) à {}.".format(", ".join(refused), "votre gestionnaire" if rel == "self" else "l'employé"))
    changes = {}
    for name in ctx.body:
        if name == "recommendation":
            value = str(ctx.body.get(name) or "")
            if value and (value not in RECOMMENDATIONS or head["kind"] != "intern" or phase != "end"):
                raise ApiError(400, "La recommandation se donne à l'évaluation finale d'un stage. Correctif : " + ", ".join(RECOMMENDATIONS) + ".")
            changes[name] = value
        else:
            changes[name] = validate.text(ctx.body, name, 4000, required=False)
    if not changes:
        raise ApiError(400, "Aucune modification demandée.")
    _ensure_phase(ctx.conn, target, year, phase)
    ctx.conn.execute("UPDATE review_phases SET {} WHERE user_id = ? AND year = ? AND phase = ?".format(", ".join(k + " = ?" for k in changes)),
                     list(changes.values()) + [target, year, phase])
    _log(ctx, "review_phase_updated", target, {"year": year, "phase": phase, "fields": sorted(changes)})
    return {"ok": True}


def api_rating(ctx):
    target = validate.int_param(ctx.params, "uid")
    rel = relation(ctx.conn, ctx.user, target)
    year = _year(ctx)
    head = profile.header(ctx.conn, target)
    if rel != "manager":
        raise ApiError(403, "La grille de stage est remplie par le gestionnaire (tuteur).")
    if head["kind"] != "intern":
        raise ApiError(400, "La grille de compétences est réservée aux stagiaires. Correctif : type « Stagiaire » dans le profil.")
    _open_phase(ctx.conn, target, year, "end", LABELS["intern"])
    criterion = ctx.body.get("criterion")
    if criterion not in CRITERIA:
        raise ApiError(400, "Critère inconnu. Correctif : " + ", ".join(CRITERIA) + ".")
    score = ctx.body.get("score")
    if score not in (None, ""):
        try:
            score = int(score)
        except (TypeError, ValueError):
            score = 0
        if score not in SCORES:
            raise ApiError(400, "Note « {} » refusée. Correctif : 1 à 4.".format(ctx.body.get("score")))
    else:
        score = None
    comment = validate.text(ctx.body, "comment", 2000, required=False) if "comment" in ctx.body else None
    ctx.conn.execute("INSERT INTO review_ratings (user_id, year, criterion) VALUES (?, ?, ?) ON CONFLICT DO NOTHING", (target, year, criterion))
    ctx.conn.execute("UPDATE review_ratings SET score = ?{} WHERE user_id = ? AND year = ? AND criterion = ?".format(
        ", comment = ?" if comment is not None else ""), [score] + ([comment] if comment is not None else []) + [target, year, criterion])
    _log(ctx, "review_rating_updated", target, {"year": year, "criterion": criterion})
    return {"ok": True}


def api_sign(ctx):
    target = validate.int_param(ctx.params, "uid")
    rel = relation(ctx.conn, ctx.user, target)
    year = _year(ctx)
    phase = ctx.params.get("phase")
    labels = LABELS[profile.header(ctx.conn, target)["kind"]]
    _open_phase(ctx.conn, target, year, phase, labels)
    side = "self" if rel == "self" else "manager"
    blockers = missing(ctx.conn, target, year, phase, side)
    if blockers:
        raise ApiError(409, "Signature impossible pour « {} ». Correctif : {}".format(labels[phase], " ".join(blockers)))
    _ensure_phase(ctx.conn, target, year, phase)
    column = "employee_signed_at" if side == "self" else "manager_signed_at"
    ctx.conn.execute("UPDATE review_phases SET {} = ? WHERE user_id = ? AND year = ? AND phase = ?".format(column),
                     (db.utc_now(), target, year, phase))
    _log(ctx, "review_signed", target, {"year": year, "phase": phase, "by": rel})
    from . import team  # core lot v0.31 (D-B-112): the other side is told in Dashboard → Messages
    team.notify_review(ctx.conn, ctx.user, target, year, phase, "signed")
    return {"phases": _phases(ctx.conn, target, year)}


def api_reopen(ctx):
    """Manager only: clears the signatures of this phase and of every phase after it."""
    target = validate.int_param(ctx.params, "uid")
    rel = relation(ctx.conn, ctx.user, target)
    year = _year(ctx)
    phase = ctx.params.get("phase")
    if rel != "manager":
        raise ApiError(403, "Seul le gestionnaire peut rouvrir une étape signée.")
    if phase not in PHASES:
        raise ApiError(404, "Étape inconnue.")
    if _archived(ctx.conn, target, year):
        raise ApiError(409, "Année {} archivée : lecture seule.".format(year))
    later = PHASES[PHASES.index(phase):]
    ctx.conn.execute("UPDATE review_phases SET employee_signed_at = NULL, manager_signed_at = NULL WHERE user_id = ? AND year = ? "
                     "AND phase IN ({})".format(", ".join("?" * len(later))), [target, year] + list(later))
    _log(ctx, "review_reopened", target, {"year": year, "phase": phase})
    from . import team
    team.notify_review(ctx.conn, ctx.user, target, year, phase, "reopened")
    return {"phases": _phases(ctx.conn, target, year)}


R = r"/api/reviews/(?P<uid>\d+)"
ROUTES = [
    ("GET", R, api_get, "user"),
    ("PUT", R + r"/(?P<year>\d{4})/item", api_item, "user"),
    ("PUT", R + r"/(?P<year>\d{4})/phase/(?P<phase>[a-z]+)", api_phase, "user"),
    ("PUT", R + r"/(?P<year>\d{4})/rating", api_rating, "user"),
    ("POST", R + r"/(?P<year>\d{4})/sign/(?P<phase>[a-z]+)", api_sign, "user"),
    ("POST", R + r"/(?P<year>\d{4})/reopen/(?P<phase>[a-z]+)", api_reopen, "user"),
]
