"""The design methods in the Project Starter file (0.60.46, D-O-055): an ideation session with its ideas (Tools), a Pugh
Matrix on the Space's requirements (Goldmine) and a Kepner-Tregoe analysis (Tools), so an example or an AI-prepared
Space shows how the concept was chosen, not only which one.

    "tools": {
      "ideation": [{title, prompt, ideas: [text]}],
      "pugh": [{title, description, concepts: [{name, description}] (the first is the reference),
                criteria: [{requirement: ref of a requirement or need, scores: {concept name: "+" | "S" | "-"}}],
                decision: concept name, note}],
      "kt": [{title, statement, alternatives: [{name, description}],
              criteria: [{kind: must | want, text, weight (want, 1-10), requirement: ref, scores: {alternative name: n}}],
              risks: [{alternative, text, probability: 1-3, seriousness: 1-3}], decision: alternative name, note}]}
A MUST scores 1 (passes) or 0 (fails), a WANT 1 to 10. parse() checks, apply() creates through the modules' handlers.
"""
from .errors import ApiError

LIMITS = {"ideation": 5, "ideas": 80, "pugh": 5, "concepts": 12, "criteria": 40, "kt": 5, "alternatives": 8, "risks": 20}


def _bad(path, message, fix):
    raise ApiError(400, "Fichier Project Starter refusé (tools.{}) : {} Correctif : {}".format(path, message, fix))


def _list(obj, name, path, limit):
    value = obj.get(name) or []
    if not isinstance(value, list) or len(value) > limit:
        _bad(path + name, "liste attendue, {} éléments au plus.".format(limit), "une liste JSON plus courte.")
    return value


def _text(obj, name, path, limit, required=False):
    value = obj.get(name)
    if value in (None, ""):
        if required:
            _bad(path + "." + name, "valeur manquante.", "donnez-la.")
        return ""
    if not isinstance(value, str) or len(value.strip()) > limit or "<" in value:
        _bad(path + "." + name, "texte de {} caractères au plus, sans balise HTML attendu.".format(limit), "raccourcissez.")
    return value.strip()


def _named(items, path, limit):
    out, names = [], set()
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            _bad("{}[{}]".format(path, i), "objet attendu.", "{ \"name\": … }.")
        name = _text(item, "name", "{}[{}]".format(path, i), limit, required=True)
        if name in names:
            _bad("{}[{}].name".format(path, i), "« {} » en double.".format(name[:40]), "un nom unique.")
        names.add(name)
        out.append({"name": name, "description": _text(item, "description", "{}[{}]".format(path, i), 1000)})
    return out, names


def _ideation(raw):
    out = []
    for i, s in enumerate(_list(raw, "ideation", "", LIMITS["ideation"])):
        path = "ideation[{}]".format(i)
        ideas = [_text({"t": x}, "t", path + ".ideas", 1000, required=True) for x in _list(s, "ideas", path + ".", LIMITS["ideas"])]
        out.append({"title": _text(s, "title", path, 200, required=True), "prompt": _text(s, "prompt", path, 1000), "ideas": ideas})
    return out


def _pugh(raw, req_refs):
    out = []
    for i, m in enumerate(_list(raw, "pugh", "", LIMITS["pugh"])):
        path = "pugh[{}]".format(i)
        concepts, names = _named(_list(m, "concepts", path + ".", LIMITS["concepts"]), path + ".concepts", 80)
        if len(concepts) < 2:
            _bad(path + ".concepts", "au moins deux concepts.", "la référence (le premier) et un concept à comparer.")
        criteria = []
        for j, c in enumerate(_list(m, "criteria", path + ".", LIMITS["criteria"])):
            cpath = "{}.criteria[{}]".format(path, j)
            if not isinstance(c, dict) or c.get("requirement") not in req_refs:
                _bad(cpath + ".requirement", "requirement introuvable.", "la ref d'un requirement ou d'un besoin du fichier.")
            scores = c.get("scores") or {}
            if not isinstance(scores, dict) or any(k not in names or k == concepts[0]["name"] or v not in ("+", "S", "-")
                                                   for k, v in scores.items()):
                _bad(cpath + ".scores", "note invalide.", "{ \"nom d'un concept (pas la référence)\": \"+\", \"S\" ou \"-\" }.")
            criteria.append({"requirement": c["requirement"], "scores": dict(scores)})
        decision = m.get("decision") or None
        if decision is not None and decision not in names:
            _bad(path + ".decision", "concept « {} » introuvable.".format(str(decision)[:40]), "le nom d'un des concepts, ou retirez la clé.")
        out.append({"title": _text(m, "title", path, 200, required=True), "description": _text(m, "description", path, 4000),
                    "concepts": concepts, "criteria": criteria, "decision": decision, "note": _text(m, "note", path, 4000)})
    return out


def _kt(raw, req_refs):
    out = []
    for i, k in enumerate(_list(raw, "kt", "", LIMITS["kt"])):
        path = "kt[{}]".format(i)
        alts, names = _named(_list(k, "alternatives", path + ".", LIMITS["alternatives"]), path + ".alternatives", 120)
        criteria = []
        for j, c in enumerate(_list(k, "criteria", path + ".", LIMITS["criteria"])):
            cpath = "{}.criteria[{}]".format(path, j)
            kind = c.get("kind") if isinstance(c, dict) else None
            if kind not in ("must", "want"):
                _bad(cpath + ".kind", "must ou want attendu.", "\"kind\": \"must\" ou \"want\".")
            weight = c.get("weight", 5) if kind == "want" else 0
            if kind == "want" and (not isinstance(weight, int) or not 1 <= weight <= 10):
                _bad(cpath + ".weight", "entier de 1 à 10 attendu.", "le poids du WANT.")
            req = c.get("requirement") or None
            if req is not None and req not in req_refs:
                _bad(cpath + ".requirement", "requirement introuvable.", "la ref d'un requirement du fichier, ou retirez la clé.")
            low, high = (0, 1) if kind == "must" else (1, 10)
            scores = c.get("scores") or {}
            if not isinstance(scores, dict) or any(a not in names or not isinstance(v, int) or not low <= v <= high
                                                   for a, v in scores.items()):
                _bad(cpath + ".scores", "note invalide.", "{ \"nom d'une alternative\": " + ("0 ou 1" if kind == "must" else "1 à 10") + " }.")
            criteria.append({"kind": kind, "text": _text(c, "text", cpath, 300, required=True), "weight": weight,
                             "requirement": req, "scores": dict(scores)})
        risks = []
        for j, r in enumerate(_list(k, "risks", path + ".", LIMITS["risks"])):
            rpath = "{}.risks[{}]".format(path, j)
            if not isinstance(r, dict) or r.get("alternative") not in names:
                _bad(rpath + ".alternative", "alternative introuvable.", "le nom d'une des alternatives.")
            levels = [r.get("probability"), r.get("seriousness")]
            if any(not isinstance(v, int) or not 1 <= v <= 3 for v in levels):
                _bad(rpath, "probability et seriousness de 1 à 3.", "1 (faible), 2 (moyenne) ou 3 (élevée).")
            risks.append({"alternative": r["alternative"], "text": _text(r, "text", rpath, 500, required=True),
                          "probability": levels[0], "seriousness": levels[1]})
        decision = k.get("decision") or None
        if decision is not None and decision not in names:
            _bad(path + ".decision", "alternative « {} » introuvable.".format(str(decision)[:40]), "le nom d'une alternative.")
        out.append({"title": _text(k, "title", path, 200, required=True), "statement": _text(k, "statement", path, 1000),
                    "alternatives": alts, "criteria": criteria, "risks": risks, "decision": decision, "note": _text(k, "note", path, 4000)})
    return out


def parse(raw, req_refs):
    tools = raw.get("tools")
    if tools in (None, {}):
        return {"ideation": [], "pugh": [], "kt": []}
    if not isinstance(tools, dict):
        _bad("", "objet attendu.", "\"tools\": { \"ideation\": […], \"pugh\": […], \"kt\": […] }, ou retirez la clé.")
    return {"ideation": _ideation(tools), "pugh": _pugh(tools, set(req_refs)), "kt": _kt(tools, set(req_refs))}


def counts(tools):
    return {"ideation": len(tools.get("ideation", [])), "pugh": len(tools.get("pugh", [])), "kt": len(tools.get("kt", []))}


def _call(ctx, func, body, **params):
    saved = ctx.params, ctx.body
    ctx.params, ctx.body = {k: str(v) for k, v in params.items()}, body
    try:
        return func(ctx)
    finally:
        ctx.params, ctx.body = saved


def apply(ctx, pid, tools, req_keys):
    """Create the sessions, matrices and analyses. req_keys: ref -> issue key (« ROVER-12 »)."""
    from modules.agile import pugh
    from modules.toolbox import ideation, kt
    conn, number = ctx.conn, lambda ref: int(req_keys[ref].rsplit("-", 1)[1])  # noqa: E731
    for s in tools["ideation"]:
        _call(ctx, ideation.api_create, {"title": s["title"], "prompt": s["prompt"], "method": "brainstorming"}, pid=pid)
        sid = conn.execute("SELECT MAX(id) FROM tools_ideation WHERE project_id = ?", (pid,)).fetchone()[0]
        for text in s["ideas"]:
            _call(ctx, ideation.api_add_idea, {"text": text}, pid=pid, sid=sid)
    for m in tools["pugh"]:
        _call(ctx, pugh.api_create, {"title": m["title"], "description": m["description"]}, pid=pid)
        mid = conn.execute("SELECT MAX(id) FROM goldmine_pugh WHERE project_id = ?", (pid,)).fetchone()[0]
        for c in m["concepts"]:
            _call(ctx, pugh.api_concept_add, c, pid=pid, mid=mid)
        concept = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM goldmine_pugh_concepts WHERE pugh_id = ?", (mid,))}
        _call(ctx, pugh.api_criteria_add, {"numbers": [number(c["requirement"]) for c in m["criteria"]]}, pid=pid, mid=mid)
        crit = {r["issue_id"]: r["id"] for r in conn.execute("SELECT id, issue_id FROM goldmine_pugh_criteria WHERE pugh_id = ?", (mid,))}
        for c in m["criteria"]:
            issue = conn.execute("SELECT id FROM agile_issues WHERE project_id = ? AND number = ?", (pid, number(c["requirement"]))).fetchone()
            for name, score in c["scores"].items():
                _call(ctx, pugh.api_score, {"criterion_id": crit[issue["id"]], "concept_id": concept[name], "score": score}, pid=pid, mid=mid)
        if m["decision"]:
            _call(ctx, pugh.api_update, {"status": "decided", "decision_concept_id": concept[m["decision"]], "decision_note": m["note"]},
                  pid=pid, mid=mid)
    for k in tools["kt"]:
        _call(ctx, kt.api_create, {"title": k["title"], "statement": k["statement"]}, pid=pid)
        kid = conn.execute("SELECT MAX(id) FROM tools_kt WHERE project_id = ?", (pid,)).fetchone()[0]
        for a in k["alternatives"]:
            _call(ctx, kt.api_alt, a, pid=pid, kid=kid)
        alt = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM tools_kt_alts WHERE kt_id = ?", (kid,))}
        for c in k["criteria"]:
            body = {"kind": c["kind"], "text": c["text"], "weight": c["weight"] or 5}
            if c["requirement"]:
                body["issue_number"] = number(c["requirement"])
            _call(ctx, kt.api_criterion, body, pid=pid, kid=kid)
            cid = conn.execute("SELECT MAX(id) FROM tools_kt_criteria WHERE kt_id = ?", (kid,)).fetchone()[0]
            for name, value in c["scores"].items():
                _call(ctx, kt.api_score, {"criterion_id": cid, "alt_id": alt[name], "value": value}, pid=pid, kid=kid)
        for r in k["risks"]:
            _call(ctx, kt.api_risk, {"alt_id": alt[r["alternative"]], "text": r["text"], "probability": r["probability"],
                                     "seriousness": r["seriousness"]}, pid=pid, kid=kid)
        if k["decision"]:
            _call(ctx, kt.api_update, {"status": "decided", "decision_alt_id": alt[k["decision"]], "decision_note": k["note"]},
                  pid=pid, kid=kid)
    return counts(tools)
