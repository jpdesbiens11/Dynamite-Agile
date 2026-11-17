"""Diamond · the bricks and the concept sheets with an AI assistant (0.60.105, D-O-117), in an external loop like the rest of
the platform (no network from the server): « Copier pour l'IA » gives a prompt built from the Space, the person pastes it in
the assistant of the company, iterates with it, then pastes its answer back in « Importer la réponse de l'IA ».

  GET  /concepts/prompt              the bricks of the tree: which functions share a brick, existing concept or to define
  GET  /concepts/<cid>/prompt        the concept sheets of one brick: several candidate solutions, principle, pros, cons
  POST /concepts/ai {file, dry}      the answer, {"concepts": [...], "sheets": [...]}: dry = what would be created

Nothing is ever removed or overwritten: a brick of the same name already in the Space is kept as it is (its new functions
join it when they have no brick yet), a function already in another brick stays there. What arrives is marked « Brouillon
IA » (source « ai », kind « ai » for a sheet), for the team to review.
"""
import json
import re

from core import audit, terms
from core.errors import ApiError

from . import concept_sheets as S
from . import concepts as C
from . import functions as F

ANSWER = {"concepts": [{"name": "Battery module de cylindrical cells en parallèle", "initial_name": "Honeycomb", "kind": "existing",
                        "reference": "Architecture de battery module du marché (21700 cells, laser-welded busbars)",
                        "description": "Porte les fonctions de stockage de l'énergie.", "functions": ["F12", "F13"]}],
          "sheets": [{"concept": "CB-3", "title": "Cold plate sous les cells",
                      "principle": "Un coolant circule dans une cold plate en aluminium collée sous le module.",
                      "description": "…", "pros": "…", "cons": "…"}]}

GUIDE_BRICKS = """Tu es ingénieur(e) produit dans l'équipe du projet « {name} »{description}. Voici l'arbre fonctionnel du produit (F-n :
fonction ; le retrait montre le niveau : primaire, secondaires, tertiaires ; [Kano] et (type) quand ils sont connus) :

{tree}

{existing}Pour chaque fonction tertiaire (ou secondaire sans tertiaire), propose la **brique technologique** qui la réalise, avec son
**concept initial** : une idée de départ portée par un **nom qui parle** (`initial_name`, deux à quatre mots imagés, ex.
« Cold sandwich », « Radiator head »), que l'équipe retiendra facilement en séance. Ce n'est pas la solution finale : la
divergence (feuilles de concept) et la convergence (Pugh) la feront sans doute pivoter. Plusieurs fonctions partagent souvent
la même brique : regroupe-les dans une seule brique (`name` : ce que la brique est, en termes techniques). Indique pour chaque brique
si elle renvoie à un **concept existant** (`"kind": "existing"`, et `reference` : la technologie, le composant du marché ou le
produit connu) ou si elle est **à définir** (`"kind": "to_define"` : il faudra des feuilles de concept et une matrice de Pugh).
Pose-moi d'abord les questions qui te manquent, puis rends un seul bloc JSON de cette forme (clés en anglais, textes en
français, les fonctions par leur numéro F-n). {terms}

```json
{answer}
```"""

GUIDE_SHEETS = """Tu es ingénieur(e) produit dans l'équipe du projet « {name} ». La brique technologique {code} « {brick} » est à définir.
Elle réalise ces fonctions de l'arbre fonctionnel :
{functions}
{reference}{needs}{sheets}
{initial}Propose {count} feuilles de concept **vraiment différentes** pour cette brique (principes physiques différents, pas des
variantes de détail), en partant du concept initial puis en osant t'en éloigner : un pivot est bienvenu s'il sert mieux les
besoins. Pour chacune : un titre court qui parle, le principe de fonctionnement en une phrase, une description (ce qu'on
dessinerait sur la feuille : architecture, matériaux, ordres de grandeur), les avantages et les inconvénients face aux besoins et
requirements ci-dessus. Nous allons ensuite les comparer en équipe dans une matrice de Pugh. {terms} Rends un seul bloc JSON :

```json
{answer}
```"""


def _project(conn, pid):
    return conn.execute("SELECT name, description FROM projects WHERE id = ?", (pid,)).fetchone()


def _tree_text(conn, pid):
    fns = F.rows(conn, pid)
    lv, tree = F.levels(fns), F.in_tree(fns)
    by_parent = {}
    for f in fns:
        by_parent.setdefault(f["parent_id"], []).append(f)
    lines = []

    def walk(f, depth):
        tag = (" [{}]".format(F.KANO[f["kano"]]) if f["kano"] else "") + (" ({})".format(F.TYPES[f["ftype"]]) if f["ftype"] != "usage" else "")
        lines.append("{}- F{} {}{}".format("  " * depth, f["number"], f["text"], tag))
        for k in sorted(by_parent.get(f["id"], []), key=lambda x: (x["position"], x["number"])):
            if not k["is_primary"]:
                walk(k, depth + 1)
    for f in fns:
        if f["is_primary"]:
            walk(f, 0)
    outside = [f for f in fns if f["id"] not in tree and lv[f["id"]] == 1]
    if outside:
        lines.append("Hors arbre (estime, en attente) :")
        lines += ["- F{} {} ({})".format(f["number"], f["text"], F.TYPES[f["ftype"]]) for f in outside]
    return "\n".join(lines) or "(arbre vide : commencez par l'arbre fonctionnel)"


def _requirements(conn, pid, limit=40):
    rows = conn.execute(
        "SELECT i.number, i.title, COALESCE(r.kind, 'requirement') AS kind, r.criticality FROM agile_issues i "
        "JOIN agile_issue_types t ON t.id = i.type_id AND t.is_requirement = 1 JOIN agile_statuses s ON s.id = i.status_id "
        "LEFT JOIN agile_requirements r ON r.issue_id = i.id WHERE i.project_id = ? AND s.name NOT IN ('Rejected', 'Obsolete') "
        "ORDER BY (COALESCE(r.kind, 'requirement') = 'need') DESC, COALESCE(NULLIF(r.criticality, ''), 'Z'), i.number LIMIT ?",
        (pid, limit)).fetchall()
    key = conn.execute("SELECT key FROM projects WHERE id = ?", (pid,)).fetchone()["key"]
    return ["- {}-{} {}{}".format(key, r["number"], "[Need] " if r["kind"] == "need" else "", r["title"]) for r in rows]


def api_prompt(ctx):
    pid = F.access(ctx)
    p = _project(ctx.conn, pid)
    have = C.rows(ctx.conn, pid)
    existing = ("Briques déjà définies par l'équipe (garde-les, complète seulement) :\n" + "\n".join(
        "- {} {} : {}".format(c["code"], c["name"], ", ".join("F{}".format(n) for n in _numbers(ctx.conn, c["function_ids"])) or "—")
        for c in have) + "\n\n") if have else ""
    text = GUIDE_BRICKS.format(name=p["name"], description=(" — " + " ".join(p["description"].split())) if p["description"] else "",
                               tree=_tree_text(ctx.conn, pid), existing=existing, terms=terms.RULE_FR,
                               answer=json.dumps({"concepts": ANSWER["concepts"]}, ensure_ascii=False, indent=1))
    return {"prompt": text}


def _numbers(conn, fids):
    return [r[0] for r in conn.execute("SELECT number FROM diamond_functions WHERE id IN ({}) ORDER BY number".format(
        ",".join("?" * len(fids))), fids)] if fids else []


def api_sheet_prompt(ctx):
    from modules.agile import common
    pid = F.access(ctx)
    c = C._concept(ctx.conn, pid, int(ctx.params["cid"]))
    fns = {f["id"]: f for f in F.rows(ctx.conn, pid)}
    fids = [r[0] for r in ctx.conn.execute("SELECT function_id FROM diamond_concept_functions WHERE concept_id = ?", (c["id"],))]
    have = S.rows(ctx.conn, pid, c["id"])
    reqs = _requirements(ctx.conn, pid) if common.is_enabled(ctx.conn, pid) else []
    text = GUIDE_SHEETS.format(
        terms=terms.RULE_FR, name=_project(ctx.conn, pid)["name"], code=C.code(c["number"]), brick=c["name"],
        functions="\n".join("- F{} {}".format(fns[i]["number"], fns[i]["text"]) for i in fids if i in fns) or "- (aucune fonction liée)",
        reference=("Description de la brique : {}\n".format(c["description"]) if c["description"] else ""),
        initial=("Concept initial de l'équipe : « {} ».\n".format(c["initial_name"]) if c["initial_name"] else ""),
        needs=("\nBesoins et requirements du projet (les plus importants) :\n" + "\n".join(reqs) + "\n") if reqs else "",
        sheets=("\nFeuilles déjà dessinées (propose autre chose) :\n" + "\n".join("- {} {}".format(s["code"], s["title"]) for s in have) + "\n")
        if have else "", count=3 if have else 4,
        answer=json.dumps({"sheets": [dict(ANSWER["sheets"][0], concept=C.code(c["number"]))]}, ensure_ascii=False, indent=1))
    return {"prompt": text}


def _read(body):
    raw = body.get("file")
    if isinstance(raw, str):
        text = raw.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
        text = fence.group(1).strip() if fence else text
        start, end = text.find("{"), text.rfind("}")
        try:
            raw = json.loads(text[start:end + 1] if start >= 0 else text)
        except ValueError as err:
            raise ApiError(400, "Réponse illisible ({}). Correctif : collez seulement le bloc JSON rendu par l'assistant.".format(str(err)[:80]))
    if not isinstance(raw, dict) or not isinstance(raw.get("concepts", []), list) or not isinstance(raw.get("sheets", []), list):
        raise ApiError(400, "Objet {\"concepts\": […], \"sheets\": […]} attendu. Correctif : collez le bloc JSON rendu par l'assistant.")
    return raw


def _norm(text):
    return re.sub(r"[^\w]+", " ", str(text or "").lower()).strip()


def api_import(ctx):
    pid = F.access(ctx, "editor")
    raw = _read(ctx.body)
    numbers = {"F{}".format(f["number"]): f["id"] for f in F.rows(ctx.conn, pid)}
    linked = {r[0] for r in ctx.conn.execute("SELECT function_id FROM diamond_concept_functions WHERE project_id = ?", (pid,))}
    have = {_norm(c["name"]): c for c in C.rows(ctx.conn, pid)}
    codes = {c["code"]: c["id"] for c in have.values()}
    out = {"concepts": 0, "kept": 0, "links": 0, "sheets": 0, "dropped": 0}
    plan_c, plan_s = [], []
    for i, item in enumerate(raw.get("concepts") or []):
        if not isinstance(item, dict):
            raise ApiError(400, "concepts[{}] : objet attendu.".format(i))
        fields = C._fields(item)
        refs = [str(r).strip().upper().replace("F-", "F") for r in (item.get("functions") or []) if isinstance(r, (str, int))]
        fids = [numbers[r] for r in refs if r in numbers and numbers[r] not in linked]
        out["dropped"] += len(refs) - len(fids)
        linked |= set(fids)
        known = have.get(_norm(fields["name"]))
        out["kept" if known else "concepts"] += 1
        out["links"] += len(fids)
        plan_c.append((known, fields, fids))
    names = {_norm(f["name"]) for _k, f, _x in plan_c}
    for i, item in enumerate(raw.get("sheets") or []):
        if not isinstance(item, dict):
            raise ApiError(400, "sheets[{}] : objet attendu.".format(i))
        target = str(item.get("concept") or "").strip().upper()
        if target not in codes and _norm(item.get("concept")) not in names | set(have):
            raise ApiError(400, "sheets[{}].concept « {} » introuvable. Correctif : le code d'une brique du Space (CB-3) ou le nom "
                                "d'une brique du fichier.".format(i, str(item.get("concept"))[:40]))
        plan_s.append((target, _norm(item.get("concept")), dict(S._fields(dict(item, kind="ai")))))
        out["sheets"] += 1
    if ctx.body.get("dry"):
        return out
    if not (out["concepts"] or out["links"] or out["sheets"]):
        raise ApiError(409, "Rien à importer : ce Space a déjà tout ce que contient la réponse.")
    for known, fields, fids in plan_c:
        if known:
            C.link(ctx.conn, pid, known["id"], fids)
        else:
            cid = C.add(ctx.conn, ctx.user["id"], pid, fields, fids, source="ai")
            have[_norm(fields["name"])] = {"id": cid}
    for target, name, fields in plan_s:
        cid = codes.get(target) or have[name]["id"]
        S.add(ctx.conn, ctx.user["id"], pid, cid, fields)
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_concepts_ai_import", "project", pid, out, ctx.ip)
    out["imported"] = True
    return out
