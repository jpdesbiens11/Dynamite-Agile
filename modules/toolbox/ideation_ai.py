"""« Idéation » · the AI proposes the groups of the board (0.60.112, D-O-125): a digital brainstorm.

The team writes (or dictates: Win + H, the Mac's dictation, a local Whisper) its post-its on the board of a session -- they show
up for everyone within seconds. Then « IA : proposer des groupes »:

  prompt   the post-its of the session (I<id>, text, current group, stars) and the method: 3 to 8 groups with a short name and a
           reason, every post-it in one group, duplicates flagged, at most a few missing post-its suggested;
  import   the answer ({"groups": [{"name", "why", "ideas": [codes]}], "new": [{"text", "group"}]}) against the board:
             move     a post-it changes group (its label);
             same     already in that group;
             new      a post-it the AI suggests (unticked: the team decides), marked « IA »;
             refused  an unknown code, a post-it in two groups, a name too long;
           the team unticks what it refuses, then applies: the labels change, the new post-its are added, journalled.

The board then goes to Diamond with « ↔ IA » (the session's post-its as source material: rt_prompt, D-O-124).
"""
import json
import re

from core import audit, db, permissions, validate
from core.errors import ApiError
from core.terms import RULE_FR

MAX_TEXT = 300_000
MAX_NEW = 12
KINDS = {"move": "Change de groupe", "same": "Déjà dans ce groupe", "new": "Nouveau post-it (IA)", "refused": "Refusé"}


def _session(ctx, minimum):
    pid = validate.int_param(ctx.params, "pid")
    permissions.require_project_role(ctx.conn, ctx.user, pid, minimum)
    row = ctx.conn.execute("SELECT * FROM tools_ideation WHERE id = ? AND project_id = ?",
                           (validate.int_param(ctx.params, "sid"), pid)).fetchone()
    if row is None:
        raise ApiError(404, "Séance d'idéation introuvable dans ce Space.")
    return pid, row


def _ideas(conn, sid):
    return [dict(r) for r in conn.execute(
        "SELECT i.id, i.text, i.tag, (SELECT COUNT(*) FROM tools_idea_stars s WHERE s.idea_id = i.id) AS stars "
        "FROM tools_ideas i WHERE i.session_id = ? ORDER BY i.id", (sid,))]


def board(conn, pid, sid):
    """{title, text} of a session's post-its, by group -- read by Diamond's « ↔ IA » prompt; None when it is not in this Space."""
    row = conn.execute("SELECT * FROM tools_ideation WHERE id = ? AND project_id = ?", (sid, pid)).fetchone()
    if row is None:
        return None
    groups = {}
    for i in _ideas(conn, sid):
        groups.setdefault(i["tag"] or "Sans groupe", []).append(i)
    lines = []
    for name, items in groups.items():
        lines.append("## " + name)
        lines += ["- I{} {}{}".format(i["id"], i["text"].replace("\n", " "), " ★" * min(i["stars"], 5)) for i in items]
    return {"title": row["title"], "text": "\n".join(lines) or "(aucun post-it)"}


def api_prompt(ctx):
    pid, row = _session(ctx, "reader")
    ideas = _ideas(ctx.conn, row["id"])
    if not ideas:
        raise ApiError(409, "Aucun post-it sur le tableau. Correctif : écrivez ou dictez d'abord les idées de l'équipe.")
    doc = [{"code": "I{}".format(i["id"]), "text": i["text"], "group": i["tag"], "stars": i["stars"]} for i in ideas]
    parts = [
        "Vous animez un brainstorm numérique : l'équipe a écrit ses post-it sur un tableau ; vous proposez des groupes, l'équipe "
        "décide. Séance « {} »{}.".format(row["title"], " — question : " + row["prompt"] if row["prompt"] else ""),
        RULE_FR,
        "CE QUE VOUS FAITES",
        "1. Proposez 3 à 8 groupes : un nom court (60 caractères au plus) qui dit le thème, et une phrase qui dit pourquoi ces "
        "post-it vont ensemble. Gardez un groupe existant (« group ») s'il tient.",
        "2. Chaque post-it va dans un seul groupe ; un post-it qui ne va nulle part va dans « À trier ».",
        "3. Signalez les doublons dans « why » (ex. « I12 et I19 disent la même chose »). Ne réécrivez jamais un post-it.",
        "4. Au plus {} post-it manquants, dans « new », seulement s'ils comblent un vrai trou ; l'équipe les acceptera ou non.".format(MAX_NEW),
        "5. Montrez d'abord le tableau global groupé ; si votre interface sait dessiner (Claude : un artefact HTML « Tableau »), en "
        "post-it de couleur selon leur nature, légende en haut : jaune = idée / solution, bleu = besoin / fonction, rouge = risque "
        "ou problème, violet = question, gris = contrainte, vert = décision ; puis un seul bloc ```json :",
        '{"groups": [{"name": "…", "why": "…", "ideas": ["I12", "I19"]}], "new": [{"text": "…", "group": "…"}]}',
        "L'équipe colle votre réponse dans « IA : proposer des groupes » → « Importer » : elle voit chaque post-it qui change de "
        "groupe, décoche ce qu'elle refuse, puis applique.",
        "POST-IT DU TABLEAU",
        "```json\n" + json.dumps(doc, ensure_ascii=False, indent=1) + "\n```",
    ]
    return {"prompt": "\n\n".join(parts), "count": len(ideas)}


def _read(text):
    text = str(text or "")
    if not text.strip():
        raise ApiError(400, "Réponse vide. Correctif : collez la réponse de l'assistant IA (son bloc JSON).")
    if len(text) > MAX_TEXT:
        raise ApiError(413, "Texte trop long ({} caractères au plus).".format(MAX_TEXT))
    for body in reversed(re.findall(r"```(?:json)?[ \t]*\n(.*?)```", text, re.S)) or [text]:
        start, end = body.find("{"), body.rfind("}")
        if 0 <= start < end:
            try:
                data = json.loads(body[start:end + 1])
            except ValueError:
                continue
            if isinstance(data, dict) and isinstance(data.get("groups"), list):
                return data
    raise ApiError(400, "Aucun bloc JSON {\"groups\": [...]} lu. Correctif : collez la réponse complète de l'assistant.")


def plan(conn, sid, data):
    ideas = {"I{}".format(i["id"]): i for i in _ideas(conn, sid)}
    entries, seen, n = [], {}, 0
    for g in data.get("groups") or []:
        if not isinstance(g, dict):
            continue
        name = " ".join(str(g.get("name") or "").split())
        why = " ".join(str(g.get("why") or "").split())[:300]
        for code in g.get("ideas") or []:
            n += 1
            code = str(code).strip()
            idea = ideas.get(code)
            base = {"id": "m{}".format(n), "code": code, "group": name, "why": why, "default": True}
            if not name or len(name) > 60:
                entries.append(dict(base, kind="refused", text=idea["text"] if idea else "", reason="Nom de groupe vide ou de plus de 60 caractères."))
            elif idea is None:
                entries.append(dict(base, kind="refused", text="", reason="Post-it inconnu sur ce tableau."))
            elif code in seen:
                entries.append(dict(base, kind="refused", text=idea["text"], reason="Déjà placé dans « {} ».".format(seen[code])))
            else:
                seen[code] = name
                kind = "same" if idea["tag"] == name else "move"
                entries.append(dict(base, kind=kind, text=idea["text"], before=idea["tag"], _idea=idea["id"]))
    for k, item in enumerate((data.get("new") or [])[:MAX_NEW], start=1):
        item = item if isinstance(item, dict) else {"text": item}
        text, group = " ".join(str(item.get("text") or "").split()), " ".join(str(item.get("group") or "").split())
        base = {"id": "n{}".format(k), "code": "", "group": group, "why": "", "default": False, "text": text}
        if not text or len(text) > 1000 or len(group) > 60:
            entries.append(dict(base, kind="refused", reason="Texte vide ou trop long, ou nom de groupe de plus de 60 caractères."))
        else:
            entries.append(dict(base, kind="new"))
    for e in entries:
        e["kind_label"] = KINDS[e["kind"]]
    left = [c for c in ideas if c not in seen]
    return entries, left


def api_import(ctx):
    pid, row = _session(ctx, "editor")
    if row["status"] == "closed":
        raise ApiError(409, "Séance close : lecture seule. Correctif : « Rouvrir » la séance.")
    entries, left = plan(ctx.conn, row["id"], _read(ctx.body.get("file")))
    public = [{k: v for k, v in e.items() if not k.startswith("_")} for e in entries]
    counts = {k: sum(1 for e in entries if e["kind"] == k) for k in KINDS}
    if ctx.body.get("mode") != "apply":
        return {"mode": "preview", "entries": public, "counts": counts, "left": left}
    skip = {str(x) for x in ctx.body.get("skip") or []}
    take = {str(x) for x in ctx.body.get("take") or []}  # the AI's new post-its the team ticked
    moved = added = 0
    for e in entries:
        if e["kind"] == "move" and e["id"] not in skip:
            ctx.conn.execute("UPDATE tools_ideas SET tag = ? WHERE id = ?", (e["group"], e["_idea"]))
            moved += 1
        elif e["kind"] == "new" and e["id"] in take:
            ctx.conn.execute("INSERT INTO tools_ideas (session_id, text, tag, author_id, author_initials, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                             (row["id"], e["text"], e["group"], ctx.user["id"], "IA", db.utc_now()))
            added += 1
    if not moved and not added:
        raise ApiError(400, "Rien à appliquer : tous les post-it sont déjà dans leur groupe, refusés ou décochés.")
    ctx.conn.execute("UPDATE tools_ideation SET updated_by = ?, updated_at = ? WHERE id = ?", (ctx.user["id"], db.utc_now(), row["id"]))
    audit.log_action(ctx.conn, ctx.user["id"], "ideation_ai_groups", "tools_ideation", row["id"],
                     {"moved": moved, "added": added, "refused": counts["refused"]}, ctx.ip)
    return {"mode": "apply", "moved": moved, "added": added}
