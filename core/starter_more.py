"""The rest of a product in the Project Starter file (0.60.43, D-O-052): with the team, requirements, tests, time codes,
pages and Diamond, the file now also carries the Agile backlog by MVP and the Generator deliverables -- so an AI
assistant prepares a Space with every module filled, from Goldmine to Timesheet.

    "backlog": [{ref, type: epic | story | task | bug, title, description, parent: ref of an epic, mvp: "MVP0".."MVP9",
                 assignee: username of the team, priority: lowest | low | medium | high | highest, points}]
    "deliverables": [{doc_type, title, step, sub}]   (the Generator codes: LCV, CRV, CDCF, PDR, CDR, VVR, MVP, BML…)

Each MVP becomes a Version in Agile (« MVP0 » … ) and every ticket of that MVP points to it; an epic comes before its
children. parse() checks, apply() creates through the modules' own handlers (same checks, same journal).
"""
import re

from .errors import ApiError

LIMITS = {"backlog": 150, "deliverables": 40}
TYPES = ("epic", "story", "task", "bug")
PRIORITIES = ("lowest", "low", "medium", "high", "highest")
MVP_RE = re.compile(r"^MVP[0-9]$")
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,39}$")


def _bad(path, message, fix):
    raise ApiError(400, "Fichier Project Starter refusé ({}) : {} Correctif : {}".format(path, message, fix))


def _text(obj, name, path, max_len, required=False):
    value = obj.get(name)
    if value is None or value == "":
        if required:
            _bad("{}.{}".format(path, name), "valeur manquante.", "donnez-la.")
        return ""
    if not isinstance(value, str):
        _bad("{}.{}".format(path, name), "texte attendu.", "mettez la valeur entre guillemets.")
    value = value.strip()
    if len(value) > max_len:
        _bad("{}.{}".format(path, name), "plus de {} caractères.".format(max_len), "raccourcissez.")
    return value


def _list(raw, name):
    value = raw.get(name)
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > LIMITS[name]:
        _bad(name, "liste attendue, {} éléments au plus.".format(LIMITS[name]), "une liste JSON plus courte.")
    return value


def default_step(code):
    """The PDP step a Generator type belongs to, read from its catalogue line (« PDP — B11 » -> 11, « PDP — A » -> 01)."""
    from modules.codex import catalog
    std = catalog.DOC_TYPES.get(code, {}).get("standard", "")
    found = re.search(r"PDP\s*—\s*([A-D])(\d{1,2})?", std)
    if not found:
        return "01"
    step = found.group(2).zfill(2) if found.group(2) else {"A": "01", "B": "07", "C": "13", "D": "19"}[found.group(1)]
    return step if step in catalog.STEPS else {"A": "01", "B": "07", "C": "13", "D": "19"}[found.group(1)]


def parse(raw, usernames=()):
    """{backlog, deliverables} cleaned; raises ApiError on the first fault, with the path and the fix."""
    from modules.codex import catalog
    backlog, epics, seen = [], set(), set()
    for i, item in enumerate(_list(raw, "backlog")):
        path = "backlog[{}]".format(i)
        if not isinstance(item, dict):
            _bad(path, "objet attendu.", "{ \"ref\": …, \"type\": …, \"title\": … }.")
        ref = _text(item, "ref", path, 40, required=True)
        if not REF_RE.match(ref) or ref in seen:
            _bad(path + ".ref", "« {} » invalide ou déjà pris.".format(ref[:40]), "une référence courte et unique (E1, S12…).")
        seen.add(ref)
        kind = str(item.get("type") or "story").lower()
        if kind not in TYPES:
            _bad(path + ".type", "« {} » inconnu.".format(kind[:20]), " ou ".join(TYPES) + ".")
        parent = item.get("parent") or None
        if parent is not None and parent not in epics:
            _bad(path + ".parent", "« {} » n'est pas un epic déclaré plus haut.".format(str(parent)[:40]),
                 "la ref d'un epic placé avant dans la liste, ou retirez la clé.")
        if kind == "epic" and parent:
            _bad(path + ".parent", "un epic n'a pas de parent.", "retirez la clé.")
        mvp = str(item.get("mvp") or "").upper()
        if mvp and not MVP_RE.match(mvp):
            _bad(path + ".mvp", "« {} » invalide.".format(mvp[:10]), "MVP0 à MVP9.")
        who = item.get("assignee") or None
        if who is not None and who not in usernames:
            _bad(path + ".assignee", "« {} » n'est pas dans l'équipe.".format(str(who)[:40]), "un username de la liste team.")
        priority = str(item.get("priority") or "medium").lower()
        if priority not in PRIORITIES:
            _bad(path + ".priority", "« {} » inconnue.".format(priority[:20]), ", ".join(PRIORITIES) + ".")
        points = item.get("points")
        if points is not None and (isinstance(points, bool) or not isinstance(points, (int, float)) or not 0 <= points <= 100):
            _bad(path + ".points", "nombre de 0 à 100 attendu.", "un nombre, ou retirez la clé.")
        if kind == "epic":
            epics.add(ref)
        backlog.append({"ref": ref, "type": kind, "title": _text(item, "title", path, 255, required=True),
                        "description": _text(item, "description", path, 4000), "parent": parent, "mvp": mvp,
                        "assignee": who, "priority": priority, "points": points})
    deliverables = []
    for i, item in enumerate(_list(raw, "deliverables")):
        path = "deliverables[{}]".format(i)
        if not isinstance(item, dict):
            _bad(path, "objet attendu.", "{ \"doc_type\": \"PDR\", \"title\": … }.")
        code = str(item.get("doc_type") or "").strip().upper()
        if code not in catalog.DOC_TYPES:
            _bad(path + ".doc_type", "« {} » n'est pas un type du Generator.".format(code[:10]),
                 "un de : " + ", ".join(list(catalog.DOC_TYPES)[:24]) + " …")
        step = str(item.get("step") or "").strip()[:2].zfill(2) if item.get("step") else ""
        if step and step not in catalog.STEPS:
            _bad(path + ".step", "étape du PDP « {} » inconnue.".format(step), ", ".join(catalog.STEPS) + ".")
        sub = str(item.get("sub") or "00").strip()
        if not re.match(r"^\d{1,2}$", sub):
            _bad(path + ".sub", "« {} » invalide.".format(sub[:5]), "1 ou 2 chiffres (00).")
        deliverables.append({"doc_type": code, "title": _text(item, "title", path, 150, required=True),
                             "step": step or default_step(code), "sub": sub})
    return {"backlog": backlog, "deliverables": deliverables}


def counts(clean):
    more = clean.get("more") or {}
    return {"backlog": len(more.get("backlog", [])), "mvps": len({b["mvp"] for b in more.get("backlog", []) if b["mvp"]}),
            "deliverables": len(more.get("deliverables", []))}


def apply(ctx, project_id, key, more, call):
    """Create the MVP versions, the tickets (epics first) and the Generator references. `call(project_id, body, func)`
    runs a module handler for this Space (starter_apply._as). Returns the counts."""
    from modules.agile import issues, planning
    from modules.codex import registry
    conn = ctx.conn
    versions = {}
    for mvp in sorted({b["mvp"] for b in more["backlog"] if b["mvp"]}):
        versions[mvp] = call(project_id, {"name": mvp}, planning.api_create_version)["id"]
    types = {r["icon_key"]: r["id"] for r in conn.execute(
        "SELECT id, icon_key FROM agile_issue_types WHERE project_id = ? AND bucket = 'agile' AND is_subtask = 0 "
        "AND is_requirement = 0 AND change_role = '' ORDER BY position", (project_id,))}
    fallback = types.get("task") or types.get("story") or next(iter(types.values()), None)
    numbers = {}
    for b in more["backlog"]:
        body = {"type_id": types.get(b["type"]) or fallback, "title": b["title"], "description": b["description"],
                "priority": b["priority"], "labels": [b["mvp"]] if b["mvp"] else []}
        if b["parent"]:
            body["parent_number"] = numbers[b["parent"]]
        if b["mvp"]:
            body["version_id"] = versions[b["mvp"]]
        if b["points"] is not None:
            body["story_points"] = b["points"]
        if b["assignee"]:
            row = conn.execute("SELECT id FROM users WHERE username = ?", (b["assignee"],)).fetchone()
            if row:
                body["assignee_id"] = row["id"]
        numbers[b["ref"]] = call(project_id, body, issues.api_create)["number"]
    refs = 0
    for d in more["deliverables"]:
        body = {"doc_type": d["doc_type"], "title": d["title"], "sub": d["sub"], "system_code": key[:20], "revision": 1,
                "step": d["step"]}
        call(project_id, body, registry.api_reserve)
        refs += 1
    return {"backlog": len(numbers), "mvps": len(versions), "deliverables": refs}
