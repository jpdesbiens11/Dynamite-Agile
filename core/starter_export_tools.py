"""A proven Space read back with its design methods (0.60.46, D-O-055): ideation sessions, Pugh Matrices (last round of
each) and Kepner-Tregoe analyses, in the « tools » shape of core/starter_tools.py. Requirements are named by the refs of the
exported file (« R12 » for issue number 12); criteria on other issues are left out."""
from .starter_tools import LIMITS


def _cut(value, n):
    value = str(value or "").strip()
    return value if len(value) <= n else value[:n - 1].rstrip() + "…"


def _unique(rows, limit):
    out, seen = [], set()
    for r in rows:
        name = _cut(r["name"], limit)
        while name in seen:
            name = _cut(name, limit - 2) + "·"
        seen.add(name)
        out.append((r["id"], name, _cut(r["description"], 1000)))
    return out


def tools(conn, pid, req_numbers):
    """req_numbers: issue id -> ref of the exported requirement."""
    ideation = []
    for s in conn.execute("SELECT id, title, prompt FROM tools_ideation WHERE project_id = ? ORDER BY id LIMIT ?", (pid, LIMITS["ideation"])):
        ideas = [_cut(r["text"], 1000) for r in conn.execute("SELECT text FROM tools_ideas WHERE session_id = ? ORDER BY id LIMIT ?",
                                                             (s["id"], LIMITS["ideas"])) if str(r["text"] or "").strip()]
        ideation.append({"title": _cut(s["title"], 200), "prompt": _cut(s["prompt"], 1000), "ideas": ideas})
    pugh = []
    for m in conn.execute("SELECT * FROM goldmine_pugh p WHERE project_id = ? AND NOT EXISTS (SELECT 1 FROM goldmine_pugh c "
                          "WHERE c.parent_id = p.id) ORDER BY id LIMIT ?", (pid, LIMITS["pugh"])):
        rows = conn.execute("SELECT id, name, description FROM goldmine_pugh_concepts WHERE pugh_id = ? ORDER BY "
                            "(id = ?) DESC, position, id LIMIT ?", (m["id"], m["datum_id"] or 0, LIMITS["concepts"])).fetchall()
        concepts = _unique(rows, 80)
        if len(concepts) < 2:
            continue
        name = {cid: n for cid, n, _d in concepts}
        criteria = []
        for c in conn.execute("SELECT id, issue_id FROM goldmine_pugh_criteria WHERE pugh_id = ? ORDER BY position LIMIT ?",
                              (m["id"], LIMITS["criteria"])):
            if c["issue_id"] not in req_numbers:
                continue
            scores = {name[s["concept_id"]]: s["score"] for s in conn.execute(
                "SELECT concept_id, score FROM goldmine_pugh_scores WHERE criterion_id = ?", (c["id"],))
                if s["concept_id"] in name and s["concept_id"] != concepts[0][0]}
            criteria.append({"requirement": req_numbers[c["issue_id"]], "scores": scores})
        pugh.append({"title": _cut(m["title"], 200), "description": _cut(m["description"], 4000),
                     "concepts": [{"name": n, "description": d} for _i, n, d in concepts], "criteria": criteria,
                     "decision": name.get(m["decision_concept_id"]) if m["status"] == "decided" else None,
                     "note": _cut(m["decision_note"], 4000)})
    kt = []
    for k in conn.execute("SELECT * FROM tools_kt WHERE project_id = ? ORDER BY id LIMIT ?", (pid, LIMITS["kt"])):
        alts = _unique(conn.execute("SELECT id, name, description FROM tools_kt_alts WHERE kt_id = ? ORDER BY position, id LIMIT ?",
                                    (k["id"], LIMITS["alternatives"])).fetchall(), 120)
        name = {aid: n for aid, n, _d in alts}
        criteria = []
        for c in conn.execute("SELECT * FROM tools_kt_criteria WHERE kt_id = ? ORDER BY position LIMIT ?", (k["id"], LIMITS["criteria"])):
            scores = {name[s["alt_id"]]: s["value"] for s in conn.execute(
                "SELECT alt_id, value FROM tools_kt_scores WHERE criterion_id = ?", (c["id"],)) if s["alt_id"] in name}
            item = {"kind": c["kind"], "text": _cut(c["text"], 300), "scores": scores}
            if c["kind"] == "want":
                item["weight"] = max(1, min(10, c["weight"] or 5))
            if c["issue_id"] in req_numbers:
                item["requirement"] = req_numbers[c["issue_id"]]
            criteria.append(item)
        risks = [{"alternative": name[r["alt_id"]], "text": _cut(r["text"], 500), "probability": r["probability"],
                  "seriousness": r["seriousness"]} for r in conn.execute(
                      "SELECT * FROM tools_kt_risks WHERE kt_id = ? ORDER BY id LIMIT ?", (k["id"], LIMITS["risks"])) if r["alt_id"] in name]
        kt.append({"title": _cut(k["title"], 200), "statement": _cut(k["statement"], 1000),
                   "alternatives": [{"name": n, "description": d} for _i, n, d in alts], "criteria": criteria, "risks": risks,
                   "decision": name.get(k["decision_alt_id"]) if k["status"] == "decided" else None, "note": _cut(k["decision_note"], 4000)})
    return {"ideation": ideation, "pugh": pugh, "kt": kt}
