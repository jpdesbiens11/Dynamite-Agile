"""« Idéation » tool (D-B-066, D-B-073): divergent sessions of Tools --
brainstorming, brainwriting 6-3-5 (connected participants in rotating pairs,
ideation_bw.py), storytelling and mind map (cards on a surface with lines,
ideation_map.py).

A session (per Space) has a question and a method; ideas are cards with an
author (3-letter key), a label (theme, story step...), attributes set during
the review (impact, feasibility), a round (brainwriting), an optional parent
idea (« rebondir ») and stars ★ (any member, as many as he likes) that bring
the best ideas out of the log. A closed session is read-only. Journalled.
Sessions created with a method since taken out of the catalogue stay readable.
"""
import csv
import io

from core import audit, db, permissions, prefs, validate
from core.errors import ApiError
from core.files import RawFile

from . import ideation_bw as bw
from . import ideation_map as mindmap

METHODS = {
    "brainstorming": ("Brainstorming", []),
    "brainwriting": ("Brainwriting 6-3-5", []),
    "storytelling": ("Storytelling", ["Il était une fois…", "Chaque jour…", "Jusqu'au jour où…", "À cause de cela…",
                                      "Jusqu'à ce que finalement…", "Depuis ce jour…"]),
    "mindmap": ("Mind Map", []),
    # retired from the catalogue (D-B-073): existing sessions keep their label
    "scamper": ("SCAMPER", []), "crazy8s": ("Crazy 8s", []), "hmw": ("Comment pourrions-nous…", []),
    "empathy": ("Carte d'empathie", []), "morphological": ("Analyse morphologique", []),
}
# 0.60.52 (D-O-061): storytelling left the catalogue -- the use of the product is told in Diamond → Storyline
CREATABLE = ("brainstorming", "brainwriting", "mindmap")
LEVELS = {"": "—", "low": "Faible", "medium": "Moyen", "high": "Fort"}  # impact / feasibility (review)


def access(ctx, minimum="reader"):
    pid = validate.int_param(ctx.params, "pid")
    permissions.require_project_role(ctx.conn, ctx.user, pid, minimum)
    return pid


def _session(ctx, pid):
    row = ctx.conn.execute("SELECT * FROM tools_ideation WHERE id = ? AND project_id = ?",
                           (validate.int_param(ctx.params, "sid"), pid)).fetchone()
    if row is None:
        raise ApiError(404, "Séance d'idéation introuvable dans ce Space.")
    return row


def _open(row):
    if row["status"] == "closed":
        raise ApiError(409, "Séance close : lecture seule. Correctif : « Rouvrir » la séance.")


def _text(body, name, label, limit, required=False):
    value = str(body.get(name) or "").strip()
    if required and not value:
        raise ApiError(400, "{} obligatoire.".format(label))
    if len(value) > limit:
        raise ApiError(400, "{} : {} caractères au maximum.".format(label, limit))
    return value


def _int(body, name, label, low, high, default):
    value = body.get(name, default)
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ApiError(400, "{} : nombre entier attendu.".format(label))
    if not low <= value <= high:
        raise ApiError(400, "{} : entre {} et {}.".format(label, low, high))
    return value


def _level(body, name, label):
    value = str(body.get(name) or "")
    if value not in LEVELS:
        raise ApiError(400, "{} « {} » inconnu. Valeurs : faible, moyen, fort.".format(label, value))
    return value


def _log(ctx, action, sid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "tools_ideation", sid, details, ctx.ip)


def _touch(ctx, sid):
    ctx.conn.execute("UPDATE tools_ideation SET updated_by = ?, updated_at = ? WHERE id = ?", (ctx.user["id"], db.utc_now(), sid))


def detail(ctx, row, pid=None):
    pid = pid or row["project_id"]
    ideas = [dict(r) for r in ctx.conn.execute(
        "SELECT i.*, p.text AS parent_text, "
        "(SELECT COUNT(*) FROM tools_idea_stars s WHERE s.idea_id = i.id) AS stars, "
        "EXISTS(SELECT 1 FROM tools_idea_stars s WHERE s.idea_id = i.id AND s.user_id = ?) AS starred "
        "FROM tools_ideas i LEFT JOIN tools_ideas p ON p.id = i.parent_id WHERE i.session_id = ? ORDER BY i.id",
        (ctx.user["id"], row["id"]))]
    label, tags = METHODS.get(row["method"], (row["method"], []))
    out = {"session": dict(row, method_label=label), "tags": tags, "levels": LEVELS,
           "methods": {k: METHODS[k][0] for k in CREATABLE}, "hidden": 0}
    if row["method"] == "brainwriting":
        out["bw"], visible = bw.state(ctx.conn, ctx.user, row, pid)
        if visible is not None:
            shown = [i for i in ideas if i["author_id"] in visible]
            out["hidden"] = len(ideas) - len(shown)
            ideas = shown
    if row["method"] == "mindmap":
        out["links"] = mindmap.links(ctx.conn, row["id"])
        out["surface"] = {"width": mindmap.WIDTH, "height": mindmap.HEIGHT}
    out["ideas"] = ideas
    return out


def api_list(ctx):
    pid = access(ctx)
    rows = ctx.conn.execute(
        "SELECT s.*, (SELECT COUNT(*) FROM tools_ideas WHERE session_id = s.id) AS n_ideas, u.display_name AS updated_by_name "
        "FROM tools_ideation s LEFT JOIN users u ON u.id = s.updated_by WHERE s.project_id = ? ORDER BY s.updated_at DESC",
        (pid,)).fetchall()
    return {"sessions": [dict(r, method_label=METHODS.get(r["method"], (r["method"],))[0]) for r in rows],
            "methods": {k: METHODS[k][0] for k in CREATABLE}}


def api_create(ctx):
    pid = access(ctx, "editor")
    method = ctx.body.get("method") or "brainstorming"
    if method not in CREATABLE:
        raise ApiError(400, "Method inconnue. Valeurs : {}.".format(", ".join(METHODS[k][0] for k in CREATABLE)))
    now = db.utc_now()
    sid = ctx.conn.execute(
        "INSERT INTO tools_ideation (project_id, title, method, prompt, created_by, created_at, updated_by, updated_at, "
        "round_minutes, rounds, ideas_per_round) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (pid, _text(ctx.body, "title", "Titre", 200, True), method, _text(ctx.body, "prompt", "Question", 1000),
         ctx.user["id"], now, ctx.user["id"], now, _int(ctx.body, "round_minutes", "Durée d'un tour", 1, 60, 5),
         _int(ctx.body, "rounds", "Nombre de tours", 1, 20, 6), _int(ctx.body, "ideas_per_round", "Idées par tour", 1, 10, 3))).lastrowid
    _log(ctx, "ideation_create", sid, {"method": method})
    ctx.params["sid"] = str(sid)
    return detail(ctx, _session(ctx, pid), pid)


def api_get(ctx):
    pid = access(ctx)
    return detail(ctx, _session(ctx, pid), pid)


def api_update(ctx):
    pid = access(ctx, "editor")
    row = _session(ctx, pid)
    changes = {}
    if ctx.body.get("status") in ("open", "closed"):
        changes["status"] = ctx.body["status"]
    else:
        _open(row)
    if "title" in ctx.body:
        changes["title"] = _text(ctx.body, "title", "Titre", 200, True)
    if "prompt" in ctx.body:
        changes["prompt"] = _text(ctx.body, "prompt", "Question", 1000)
    if changes:
        ctx.conn.execute("UPDATE tools_ideation SET {} WHERE id = ?".format(", ".join("{} = ?".format(k) for k in changes)),
                         tuple(changes.values()) + (row["id"],))
        _touch(ctx, row["id"])
        _log(ctx, "ideation_update", row["id"], {"fields": sorted(changes)})
    return detail(ctx, _session(ctx, pid), pid)


def api_brainwriting(ctx):
    """{action: join | start | next | finish} -- brainwriting participants and rounds (D-B-073)."""
    pid = access(ctx, "editor")
    row = _session(ctx, pid)
    _open(row)
    if row["method"] != "brainwriting":
        raise ApiError(409, "Cette séance n'est pas un brainwriting.")
    action = ctx.body.get("action")
    if action == "join":
        bw.join(ctx, row)
    else:
        bw.control(ctx, row, pid, action)
    _touch(ctx, row["id"])
    return detail(ctx, _session(ctx, pid), pid)


def api_add_idea(ctx):
    pid = access(ctx, "editor")
    row = _session(ctx, pid)
    _open(row)
    parent = ctx.body.get("parent_id")
    if parent not in (None, ""):
        if not ctx.conn.execute("SELECT 1 FROM tools_ideas WHERE id = ? AND session_id = ?", (int(parent), row["id"])).fetchone():
            raise ApiError(400, "Idée de départ introuvable dans cette séance.")
        parent = int(parent)
    else:
        parent = None
    rnd = ctx.body.get("round")
    rnd = int(rnd) if str(rnd or "").isdigit() else None
    if row["method"] == "brainwriting":
        clock = bw.clock(row)
        if clock["phase"] == "setup":
            raise ApiError(409, "La séance n'a pas démarré. Correctif : « Rejoindre », puis l'animateur clique « Démarrer ».")
        if clock["phase"] == "running":
            if not ctx.conn.execute("SELECT 1 FROM tools_ideation_people WHERE session_id = ? AND user_id = ?",
                                    (row["id"], ctx.user["id"])).fetchone():
                raise ApiError(409, "Rejoignez la séance pour écrire vos idées (bouton « Rejoindre »).")
            rnd = clock["round"]  # the server's clock decides the round
    x = y = None
    if row["method"] == "mindmap":
        if ctx.body.get("x") is not None and ctx.body.get("y") is not None:
            x, y = mindmap.coordinate(ctx.body["x"], mindmap.WIDTH, "x"), mindmap.coordinate(ctx.body["y"], mindmap.HEIGHT, "y")
        else:
            x, y = mindmap.default_position(ctx.conn, row["id"])
    initials = prefs.get(ctx.conn, ctx.user["id"]).get("initials") or ""
    iid = ctx.conn.execute(
        "INSERT INTO tools_ideas (session_id, text, tag, round, parent_id, author_id, author_initials, created_at, pos_x, pos_y) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (row["id"], _text(ctx.body, "text", "Idée", 1000, True),
                                                 _text(ctx.body, "tag", "Étiquette", 60), rnd, parent, ctx.user["id"],
                                                 initials, db.utc_now(), x, y)).lastrowid
    if row["method"] == "mindmap" and ctx.body.get("link_to") not in (None, ""):
        ctx.body.update(a_id=iid, b_id=ctx.body.get("link_to"))
        mindmap.add_link(ctx, row)
    _touch(ctx, row["id"])
    _log(ctx, "ideation_idea_add", row["id"], {"idea_id": iid})
    return detail(ctx, row, pid)


def api_update_idea(ctx):
    """Text by the author (or a Space admin); label, impact, feasibility and position by any editor (review and
    sorting are collective); {delete: true} by the author or a Space admin -- only while the session is open."""
    pid = access(ctx, "editor")
    row = _session(ctx, pid)
    _open(row)
    idea = ctx.conn.execute("SELECT * FROM tools_ideas WHERE id = ? AND session_id = ?",
                            (validate.int_param(ctx.params, "iid"), row["id"])).fetchone()
    if idea is None:
        raise ApiError(404, "Idée introuvable.")
    owner = idea["author_id"] == ctx.user["id"] or permissions.is_project_manager(ctx.conn, ctx.user, pid)
    if ctx.body.get("delete"):
        if not owner:
            raise ApiError(403, "Seul l'auteur (ou un admin du Space) retire une idée.")
        ctx.conn.execute("UPDATE tools_ideas SET parent_id = NULL WHERE parent_id = ?", (idea["id"],))
        ctx.conn.execute("DELETE FROM tools_ideas WHERE id = ?", (idea["id"],))
        _log(ctx, "ideation_idea_delete", row["id"], {"idea_id": idea["id"], "text": idea["text"][:120]})
    else:
        changes = {}
        if "text" in ctx.body:
            text = _text(ctx.body, "text", "Idée", 1000, True)
            if text != idea["text"]:
                if not owner:
                    raise ApiError(403, "Seul l'auteur (ou un admin du Space) modifie le texte d'une idée. Correctif : "
                                        "« Rebondir » pour la compléter.")
                changes["text"] = text
        if "tag" in ctx.body:
            changes["tag"] = _text(ctx.body, "tag", "Étiquette", 60)
        for name, label in (("impact", "Impact"), ("feasibility", "Faisabilité")):
            if name in ctx.body:
                changes[name] = _level(ctx.body, name, label)
        if "x" in ctx.body and "y" in ctx.body:
            changes["pos_x"] = mindmap.coordinate(ctx.body["x"], mindmap.WIDTH, "x")
            changes["pos_y"] = mindmap.coordinate(ctx.body["y"], mindmap.HEIGHT, "y")
        if changes:
            ctx.conn.execute("UPDATE tools_ideas SET {} WHERE id = ?".format(", ".join("{} = ?".format(k) for k in changes)),
                             tuple(changes.values()) + (idea["id"],))
            _log(ctx, "ideation_idea_update", row["id"], {"idea_id": idea["id"], "fields": sorted(changes)})
    _touch(ctx, row["id"])
    return detail(ctx, row, pid)


def api_star(ctx):
    """Toggle my star on an idea (any member, readers too; as many stars as he likes)."""
    pid = access(ctx)
    row = _session(ctx, pid)
    _open(row)
    iid = validate.int_param(ctx.params, "iid")
    if not ctx.conn.execute("SELECT 1 FROM tools_ideas WHERE id = ? AND session_id = ?", (iid, row["id"])).fetchone():
        raise ApiError(404, "Idée introuvable.")
    if ctx.conn.execute("DELETE FROM tools_idea_stars WHERE idea_id = ? AND user_id = ?", (iid, ctx.user["id"])).rowcount == 0:
        ctx.conn.execute("INSERT INTO tools_idea_stars (idea_id, user_id) VALUES (?, ?)", (iid, ctx.user["id"]))
    _log(ctx, "ideation_star", row["id"], {"idea_id": iid})
    return detail(ctx, row, pid)


def api_link(ctx):
    pid = access(ctx, "editor")
    row = _session(ctx, pid)
    _open(row)
    mindmap.add_link(ctx, row)
    _touch(ctx, row["id"])
    return detail(ctx, row, pid)


def api_unlink(ctx):
    pid = access(ctx, "editor")
    row = _session(ctx, pid)
    _open(row)
    mindmap.delete_link(ctx, row)
    _touch(ctx, row["id"])
    return detail(ctx, row, pid)


def api_export(ctx):
    pid = access(ctx)
    data = detail(ctx, _session(ctx, pid), pid)
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow(["N°", "Idée", "Étiquette", "Impact", "Faisabilité", "Étoiles", "Tour", "Rebond sur", "Auteur", "Créée le"])
    for i in data["ideas"]:
        w.writerow([i["id"], i["text"], i["tag"], LEVELS.get(i["impact"] or "", ""), LEVELS.get(i["feasibility"] or "", ""),
                    i["stars"], i["round"] or "", i["parent_id"] or "", i["author_initials"], i["created_at"]])
    _log(ctx, "ideation_export", data["session"]["id"])
    return RawFile(("﻿" + out.getvalue()).encode("utf-8"), "idees_{}.csv".format(data["session"]["id"]), "text/csv")
