"""« Copier pour l'IA » and « Importer la réponse de l'IA » of the Storyline (0.60.52, D-O-061).

GET  …/story/prompt  the text a person pastes into an AI assistant: the scenes of the Storyline told in words, the method
                     of the functional tree, the exact « diamond » format of the Project Starter (values read from the
                     tool, a short valid example) -- the assistant answers with a {"diamond": {…}} file.
POST …/import        that file, checked by core/starter_diamond.py (the same rules as « Commencer »), then applied to this
                     Space: the tree, the structure, the parts, the risks, the DFMEA, each item an AI draft to review.
                     {"dry": true} only checks and counts. mode « add » (Compléter, editors) brings only what the Space
                     is missing and hangs it on the existing tree; « replace » (Tout remplacer, admins of the Space) backs the Space
                     up, empties Diamond and rebuilds it from the file (0.60.53, D-O-062, import_merge.py). Journalled.
"""
import json
import re

from core import audit
from core.errors import ApiError

from . import functions as F
from . import story

GUIDE = """# Diamond à partir de la Storyline — {name}

Tu es un ingénieur en conception de produit qui accompagne une équipe. L'équipe a raconté l'usage de son produit, scène par
scène, dans la Storyline de l'outil DynamiteAgile. À partir de ces scènes, prépare l'**analyse fonctionnelle préliminaire**
du module Diamond, que l'équipe relira et corrigera.

**Le produit :** {name}{description}

## La Storyline ({count} scènes)

{scenes}

## La méthode

1. **Fonction primaire** : ce que le produit réalise pour la personne, en un verbe à l'infinitif et son complément.
2. **Fonctions secondaires** : les grandes étapes de l'usage, dans l'ordre des scènes (le « quand ? », de haut en bas) ; la
   dernière branche protège la personne et le produit.
3. **Fonctions tertiaires** : le « comment ? » de chaque secondaire ; une fonction `technique` au niveau 4 seulement si
   elle est nécessaire. Le « pourquoi ? » remonte toujours vers la primaire.
4. Une fonction d'estime ou une contrainte qui ne s'insère pas dans l'arbre reste **hors arbre** (sans parent).
5. Chaque irritant, question ou idée des scènes doit se retrouver quelque part : une fonction, un risque ou une ligne du
   DFMEA.
6. Ensuite : les entrées et sorties du système (`ports`), les flux (`flows` ; vue `general` entre fonctions secondaires,
   `detail` entre fonctions tertiaires sans les techniques), les pièces probables (`parts`, reliées seulement à des fonctions
   secondaires ou tertiaires, jamais à une technique ni à une fonction hors arbre), les risques projet (`risks`,
   P et I de 1 à 5) et une première ligne de DFMEA par fonction importante (`dfmea`, S, O, D de 1 à 10).

## Le format exact

Réponds **uniquement** par un bloc ```json contenant un objet `{{"diamond": {{…}}}}` avec les listes `functions`, `ports`,
`flows`, `parts`, `risks` et `dfmea`. Les `ref` sont de courts identifiants uniques (F1, F2… ; E1, S1… pour les ports) ;
`parent` est la `ref` du parent (null pour la primaire et les fonctions hors arbre). N'écris pas `story`, ni `test`.
{owners}Retire une clé plutôt que de la laisser vide.

{values}

Exemple court et valide (un autre produit) :

```json
{example}
```
"""


def _scene_text(i, scene):
    seen = ", ".join("{}{}".format(story_name(it["p"]), " « {} »".format(it["t"]) if it.get("t") else "") for it in scene["items"])
    lines = ["### Scène {} — {}".format(i + 1, scene["title"])]
    if scene["caption"]:
        lines.append("Ce qui se passe : " + scene["caption"])
    if seen:
        lines.append("On y voit : " + seen + ".")
    if scene["notes"]:
        lines.append("Idées, irritants, questions : " + " ".join(scene["notes"].split()))
    return "\n".join(lines)


NAMES = {"aine": "Aîné", "exterieur": "Extérieur", "telephone": "Téléphone", "horloge": "Temps", "soleil": "Soleil, chaleur",
         "poussiere": "Poussière", "idee": "Idée", "frustre": "Frustré", "coeur": "J'aime", "produit": "Le produit"}


def story_name(key):
    return NAMES.get(key, key.capitalize())


def _members(conn, pid):
    return [r["username"] for r in conn.execute("SELECT u.username FROM memberships m JOIN users u ON u.id = m.user_id "
                                                "WHERE m.project_id = ? AND u.is_active = 1 ORDER BY u.username", (pid,))]


def prompt(conn, pid):
    from core import starter_prompt
    project = conn.execute("SELECT name, description FROM projects WHERE id = ?", (pid,)).fetchone()
    scenes = story.rows(conn, pid)
    values = "\n".join(line for line in starter_prompt.values_table("fr").splitlines()
                       if line.startswith("| Champ") or line.startswith("|---") or line.startswith("| `diamond."))
    example = json.loads(starter_prompt.example())["diamond"]
    for key in ("risks", "dfmea"):
        example[key] = [{k: v for k, v in r.items() if k not in ("owner", "test")} for r in example[key]]
    users = _members(conn, pid)
    owners = ("Un risque ou une ligne du DFMEA peut nommer `owner` (une de ces personnes : {}) et `due` (AAAA-MM-JJ).\n".format(
        ", ".join("`{}`".format(u) for u in users)) if users else "")
    description = " — " + " ".join(project["description"].split()) if project["description"] else ""
    return GUIDE.format(name=project["name"], description=description, count=len(scenes),
                        scenes="\n\n".join(_scene_text(i, s) for i, s in enumerate(scenes)) or "(aucune scène pour l'instant)",
                        owners=owners, values=values, example=json.dumps({"diamond": example}, ensure_ascii=False, indent=1))


def api_prompt(ctx):
    pid = F.access(ctx)
    return {"prompt": prompt(ctx.conn, pid), "scenes": len(story.rows(ctx.conn, pid))}


def _read(body):
    raw = body.get("file")
    if isinstance(raw, str):
        text = raw.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
        if fence:
            text = fence.group(1).strip()
        start, end = text.find("{"), text.rfind("}")
        try:
            raw = json.loads(text[start:end + 1] if start >= 0 else text)
        except ValueError as err:
            raise ApiError(400, "Réponse illisible ({}). Correctif : collez seulement le bloc JSON rendu par l'assistant.".format(
                str(err)[:80]))
    if not isinstance(raw, dict):
        raise ApiError(400, "Objet {\"diamond\": {…}} attendu. Correctif : collez le bloc JSON rendu par l'assistant.")
    if "diamond" not in raw and "functions" in raw:
        raw = {"diamond": raw}
    if not isinstance(raw.get("diamond"), dict):
        raise ApiError(400, "Clé « diamond » absente. Correctif : la réponse doit être {\"diamond\": {\"functions\": […], …}}.")
    return raw


def api_import(ctx):
    """mode « add » (Compléter, default): only what the Space is missing; « replace » (Tout remplacer, admins of the Space): a backup
    of the Space, then Diamond emptied and rebuilt from the file (0.60.53, D-O-062, import_merge.py)."""
    from core import starter_diamond
    from . import import_merge as M
    pid = F.access(ctx, "editor")
    mode = ctx.body.get("mode") or "add"
    if mode not in ("add", "replace"):
        raise ApiError(400, "Mode « {} » inconnu. Correctif : add (Compléter) ou replace (Tout remplacer).".format(str(mode)[:20]))
    if mode == "replace":
        M.require_space_admin(ctx, pid)
    raw = _read(ctx.body)
    removed = M.present(ctx.conn, pid) if mode == "replace" else {}
    plan = M.plan(ctx.conn, pid, raw, set(_members(ctx.conn, pid)), mode)
    clean = plan["clean"]
    counts = starter_diamond.counts({"diamond": clean})
    if mode == "replace" and not clean["story"]:
        removed["story"] = 0
    out = {"mode": mode, "counts": counts, "kept": plan["kept"], "dropped": plan["dropped"],
           "removed": {k: v for k, v in removed.items() if v}}
    if not any(counts.values()):
        raise ApiError(409, "Rien à importer : ce Space a déjà tout ce que contient le fichier. Correctif : choisissez « Tout "
                            "remplacer » pour repartir du fichier, ou importez un fichier avec les parties qui manquent.")
    if ctx.body.get("dry"):
        return out
    if mode == "replace":
        out["backup"] = M.backup(ctx, pid)
        M.wipe(ctx.conn, pid, keep_story=not clean["story"])
    for rid in plan["replace_dfmea"]:
        ctx.conn.execute("DELETE FROM diamond_dfmea WHERE id = ? AND project_id = ?", (rid, pid))
    out["counts"] = starter_diamond.apply(ctx.conn, ctx.user["id"], pid, clean, known=plan["known"])
    out["imported"] = True
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_import", "project", pid,
                     {"mode": mode, "counts": out["counts"], "kept": plan["kept"], "dropped": plan["dropped"],
                      "removed": out["removed"], "backup": out.get("backup", "")}, ctx.ip)
    return out
