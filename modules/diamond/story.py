"""« Storyline » of Diamond (0.60.51, D-O-060): the use of the product told scene by scene, before the functional tree.

A free, divergent team exercise: no link to the functions. Each scene has a title, what happens (caption), loose notes
(ideas, irritants, questions) and pictograms placed on it -- people, places, objects, surroundings, feelings -- each at
x / y in percent of the scene, with a size, a mirror flag and a short label. The pictograms are drawn by
tools/story_pictos.py; their keys are listed here so a scene only holds known ones. An AI assistant reads the storyline
to propose the tree and the rest of Diamond (« Copier pour l'IA », 0.60.52). Every write is journalled.
"""
import json

from core import audit, db, validate
from core.errors import ApiError

from . import functions as F

PICTOS = ("adulte", "enfant", "aine", "technicien", "groupe", "main", "maison", "cuisine", "atelier", "bureau", "exterieur",
          "route", "magasin", "produit", "telephone", "ordinateur", "batterie", "prise", "outil", "colis", "voiture", "panier",
          "argent", "horloge", "notice", "soleil", "pluie", "froid", "nuit", "bruit", "eau", "poussiere", "idee", "question",
          "danger", "content", "frustre", "coeur", "mouvement")
MAX_SCENES = 40
MAX_ITEMS = 30
LIMITS = {"title": 80, "caption": 600, "notes": 2000}


def _text(body, name):
    raw = str(body.get(name) or "")
    value = raw.strip() if name == "notes" else " ".join(raw.split())
    if len(value) > LIMITS[name]:
        raise ApiError(400, "{} : {} caractères au maximum (reçu {}). Correctif : raccourcissez.".format(
            {"title": "Titre", "caption": "Ce qui se passe", "notes": "Notes"}[name], LIMITS[name], len(value)))
    return value


def _num(value, low, high, default):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return round(min(high, max(low, number)), 1)


def clean_items(items):
    """The pictograms of a scene, checked: known keys only, positions kept inside the scene."""
    if not isinstance(items, list):
        raise ApiError(400, "Pictogrammes : une liste est attendue. Correctif : rechargez la page.")
    if len(items) > MAX_ITEMS:
        raise ApiError(400, "{} pictogrammes au maximum par scène (reçu {}). Correctif : faites une scène de plus.".format(MAX_ITEMS, len(items)))
    out = []
    for item in items:
        item = item if isinstance(item, dict) else {}
        key = str(item.get("p") or "")
        if key not in PICTOS:
            raise ApiError(400, "Pictogramme « {} » inconnu. Correctif : choisissez-le dans la palette.".format(key[:30]))
        label = " ".join(str(item.get("t") or "").split())
        if len(label) > 40:
            raise ApiError(400, "Étiquette d'un pictogramme : 40 caractères au maximum (reçu {}).".format(len(label)))
        size = int(_num(item.get("s"), 1, 3, 2))
        out.append({"p": key, "x": _num(item.get("x"), 0, 100, 50), "y": _num(item.get("y"), 0, 100, 50), "s": size,
                    "f": 1 if item.get("f") else 0, "t": label})
    return out


def rows(conn, pid):
    out = []
    for r in conn.execute("SELECT * FROM diamond_story_scenes WHERE project_id = ? ORDER BY position, id", (pid,)):
        scene = dict(r)
        scene["position"] = int(scene["position"])
        try:
            scene["items"] = json.loads(scene["items"] or "[]")
        except ValueError:
            scene["items"] = []
        out.append(scene)
    return out


def payload(conn, pid):
    return {"scenes": rows(conn, pid), "pictos": list(PICTOS), "limits": dict(LIMITS, scenes=MAX_SCENES, items=MAX_ITEMS)}


def _scene(ctx, pid):
    row = ctx.conn.execute("SELECT * FROM diamond_story_scenes WHERE id = ? AND project_id = ?",
                           (validate.int_param(ctx.params, "sid"), pid)).fetchone()
    if row is None:
        raise ApiError(404, "Scène introuvable dans ce Space (déjà retirée ?). Correctif : rechargez la page.")
    return dict(row)


def _log(ctx, action, sid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "diamond_story_scenes", sid, details, ctx.ip)


def _renumber(conn, pid):
    ids = [r["id"] for r in conn.execute("SELECT id FROM diamond_story_scenes WHERE project_id = ? ORDER BY position, id", (pid,))]
    conn.executemany("UPDATE diamond_story_scenes SET position = ? WHERE id = ?", [(i, sid) for i, sid in enumerate(ids)])
    return ids


def create(conn, user_id, pid, fields, at=None):
    count = conn.execute("SELECT COUNT(*) FROM diamond_story_scenes WHERE project_id = ?", (pid,)).fetchone()[0]
    if count >= MAX_SCENES:
        raise ApiError(409, "{} scènes au maximum par Space. Correctif : regroupez des scènes voisines.".format(MAX_SCENES))
    now = db.utc_now()
    sid = conn.execute("INSERT INTO diamond_story_scenes (project_id, position, title, caption, notes, items, created_by, created_at, "
                       "updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (pid, count if at is None else at - 0.5, fields.get("title") or "Scène {}".format(count + 1),
                        fields.get("caption", ""), fields.get("notes", ""), json.dumps(fields.get("items", []), ensure_ascii=False),
                        user_id, now, user_id, now)).lastrowid
    _renumber(conn, pid)
    return sid


def api_list(ctx):
    return payload(ctx.conn, F.access(ctx))


def api_create(ctx):
    pid = F.access(ctx, "editor")
    fields = {"title": _text(ctx.body, "title"), "caption": _text(ctx.body, "caption")}
    sid = create(ctx.conn, ctx.user["id"], pid, fields)
    _log(ctx, "diamond_story_create", sid, {"title": fields["title"]})
    return dict(payload(ctx.conn, pid), created=sid)


def api_update(ctx):
    pid = F.access(ctx, "editor")
    scene = _scene(ctx, pid)
    changes = {name: _text(ctx.body, name) for name in LIMITS if name in ctx.body}
    if "title" in changes and not changes["title"]:
        changes["title"] = "Scène {}".format(int(scene["position"]) + 1)
    if "items" in ctx.body:
        changes["items"] = json.dumps(clean_items(ctx.body.get("items")), ensure_ascii=False)
    if changes:
        ctx.conn.execute("UPDATE diamond_story_scenes SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(
            ", ".join(k + " = ?" for k in changes)), list(changes.values()) + [ctx.user["id"], db.utc_now(), scene["id"]])
        details = {k: v for k, v in changes.items() if k == "title"}
        if "items" in changes:
            details["pictograms"] = len(json.loads(changes["items"]))
        _log(ctx, "diamond_story_update", scene["id"], details)
    return payload(ctx.conn, pid)


def api_move(ctx):
    pid = F.access(ctx, "editor")
    scene = _scene(ctx, pid)
    ids = [i for i in _renumber(ctx.conn, pid) if i != scene["id"]]
    to = int(_num(ctx.body.get("to"), 0, len(ids), scene["position"]))
    ids.insert(to, scene["id"])
    ctx.conn.executemany("UPDATE diamond_story_scenes SET position = ? WHERE id = ?", [(i, sid) for i, sid in enumerate(ids)])
    _log(ctx, "diamond_story_move", scene["id"], {"to": to + 1})
    return payload(ctx.conn, pid)


def api_duplicate(ctx):
    pid = F.access(ctx, "editor")
    scene = _scene(ctx, pid)
    fields = {"title": (scene["title"] + " (copie)")[:LIMITS["title"]], "caption": scene["caption"], "notes": scene["notes"],
              "items": json.loads(scene["items"] or "[]")}
    sid = create(ctx.conn, ctx.user["id"], pid, fields, at=scene["position"] + 1)
    _log(ctx, "diamond_story_duplicate", sid, {"from": scene["id"]})
    return dict(payload(ctx.conn, pid), created=sid)


def api_delete(ctx):
    pid = F.access(ctx, "editor")
    scene = _scene(ctx, pid)
    ctx.conn.execute("DELETE FROM diamond_story_scenes WHERE id = ?", (scene["id"],))
    _renumber(ctx.conn, pid)
    _log(ctx, "diamond_story_delete", scene["id"], {"title": scene["title"]})
    return payload(ctx.conn, pid)
