"""Diamond, the Agile backlog and the Generator deliverables of a proven Space, in the Project Starter format
(0.60.43, D-O-052; see starter_export.py). Functions come parents first (primary, then each level), out-of-tree ones
after; ports, flows, parts, risks and DFMEA rows refer to them by ref."""


def _cut(value, n):
    value = str(value or "").strip()
    return value if len(value) <= n else value[:n - 1].rstrip() + "…"


def _pick(value, options, default=""):
    return value if value in options else default


def diamond(conn, pid, test_refs, usernames, MAX):
    from modules.diamond import functions as F, parts as P, risks as R, structure as S, dfmea as D
    rows = conn.execute("SELECT * FROM diamond_functions WHERE project_id = ? AND archived = 0 ORDER BY position, number", (pid,)).fetchall()
    by_parent = {}
    for r in rows:
        by_parent.setdefault(r["parent_id"], []).append(r)
    primary = next((r for r in rows if r["is_primary"]), None)
    ordered, depth = [], {}
    if primary is not None:
        queue = [(primary, 1)]
        while queue:
            node, d = queue.pop(0)
            ordered.append(node)
            depth[node["id"]] = d
            for child in by_parent.get(node["id"], []):
                if d + 1 <= F.MAX_LEVEL and (d + 1 < F.MAX_LEVEL or child["ftype"] == "technique"):
                    queue.append((child, d + 1))
        ordered += [r for r in rows if r["parent_id"] is None and r["id"] != primary["id"]]
    ordered = ordered[:MAX["functions"]]
    ref = {r["id"]: "F{}".format(r["number"]) for r in ordered}
    functions = [{"ref": ref[r["id"]], "text": _cut(r["text"], 160) or "Fonction", "type": _pick(r["ftype"], F.TYPES, "usage"),
                  "parent": ref.get(r["parent_id"]) if r["id"] in depth and depth[r["id"]] > 1 else None,
                  "kano": _pick(r["kano"], F.KANO), "importance": _pick(r["importance"], F.IMPORTANCE),
                  "critical": bool(r["critical"]), "notes": _cut(r["notes"], 1500)} for r in ordered]
    if functions and functions[0]["type"] != "usage":
        functions[0]["type"] = "usage"
    ports = conn.execute("SELECT * FROM diamond_ports WHERE project_id = ? ORDER BY side, position, id", (pid,)).fetchall()[:MAX["ports"]]
    pref = {p["id"]: "{}{}".format("I" if p["side"] == "in" else "O", i + 1) for i, p in enumerate(ports)}
    out = {"functions": functions,
           "ports": [{"ref": pref[p["id"]], "side": p["side"], "label": _cut(p["label"], 120) or "—", "kind": _pick(p["kind"], S.KINDS, "")}
                     for p in ports]}
    flows = []
    for f in conn.execute("SELECT * FROM diamond_flows WHERE project_id = ? ORDER BY id", (pid,)).fetchall():
        src = ref.get(f["src_function_id"]) or pref.get(f["src_port_id"])
        dst = ref.get(f["dst_function_id"]) or pref.get(f["dst_port_id"])
        if src and dst and f["view"] in S.VIEWS:
            flows.append({"view": f["view"], "kind": _pick(f["kind"], S.KINDS, ""), "label": _cut(f["label"], 120), "src": src, "dst": dst})
    out["flows"] = flows[:MAX["flows"]]
    parts = []
    for p in conn.execute("SELECT * FROM diamond_parts WHERE project_id = ? ORDER BY position, number", (pid,)).fetchall()[:MAX["parts"]]:
        fids = [ref[x["function_id"]] for x in conn.execute("SELECT function_id FROM diamond_part_functions WHERE part_id = ?", (p["id"],))
                if x["function_id"] in ref]
        parts.append({"ref": "P{}".format(p["number"]), "name": _cut(p["name"], 120) or "Pièce", "kind": _pick(p["kind"], P.KINDS, ""),
                      "notes": _cut(p["notes"], 1500), "functions": fids})
    out["parts"] = parts
    user = {r["id"]: r["username"] for r in conn.execute("SELECT id, username FROM users")}
    owner = lambda uid: user.get(uid) if user.get(uid) in usernames else None  # noqa: E731
    out["risks"] = [{"title": _cut(r["title"], 200) or "Risque", "cause": _cut(r["cause"], 1000), "consequence": _cut(r["consequence"], 1000),
                     "category": _pick(r["category"], R.CATEGORIES, ""), "phase": _pick(r["phase"], R.PHASES, ""),
                     "probability": r["probability"], "impact": r["impact"], "response": _pick(r["response"], R.RESPONSES, ""),
                     "action": _cut(r["action"], 1000), "function": ref.get(r["function_id"]),
                     **({"owner": owner(r["owner_id"])} if owner(r["owner_id"]) else {}), **({"due": r["due_date"]} if r["due_date"] else {})}
                    for r in conn.execute("SELECT * FROM diamond_risks WHERE project_id = ? AND archived = 0 ORDER BY number", (pid,)).fetchall()
                    [:MAX["risks"]]]
    test_of = {r["id"]: test_refs.get(r["test_id"]) for r in conn.execute("SELECT id, test_id FROM testing_tests WHERE project_id = ?", (pid,))}
    rows_d = []
    for d in conn.execute("SELECT * FROM diamond_dfmea WHERE project_id = ? ORDER BY position, id", (pid,)).fetchall()[:MAX["dfmea"]]:
        item = {k: _cut(d[k], 1000) for k in D.TEXTS}
        item.update({k: d[k] for k in ("severity", "occurrence", "detection") if d[k]})
        item["function"] = ref.get(d["function_id"])
        if test_of.get(d["test_id"]):
            item["test"] = test_of[d["test_id"]]
        if owner(d["action_owner_id"]):
            item["owner"] = owner(d["action_owner_id"])
        if d["action_due"]:
            item["due"] = d["action_due"]
        if item.get("failure_mode"):
            rows_d.append(item)
    out["dfmea"] = rows_d
    return out


def backlog(conn, pid, usernames, limit):
    rows = conn.execute("SELECT i.id, i.number, i.parent_id, i.title, i.description, i.priority, i.story_points, t.icon_key, "
                        "v.name AS version, u.username FROM agile_issues i JOIN agile_issue_types t ON t.id = i.type_id "
                        "LEFT JOIN agile_versions v ON v.id = i.version_id LEFT JOIN users u ON u.id = i.assignee_id "
                        "WHERE i.project_id = ? AND t.bucket = 'agile' AND t.is_requirement = 0 AND t.change_role = '' "
                        "ORDER BY CASE t.icon_key WHEN 'epic' THEN 0 ELSE 1 END, i.number", (pid,)).fetchall()[:limit]
    epics = {r["id"]: "E{}".format(r["number"]) for r in rows if r["icon_key"] == "epic"}
    out = []
    import re
    for r in rows:
        kind = r["icon_key"] if r["icon_key"] in ("epic", "story", "task", "bug") else "task"
        mvp = (r["version"] or "").upper().replace(" ", "")
        item = {"ref": epics.get(r["id"]) or "S{}".format(r["number"]), "type": kind, "title": _cut(r["title"], 255) or "Ticket",
                "description": _cut(r["description"], 4000), "priority": r["priority"] if r["priority"] in
                ("lowest", "low", "medium", "high", "highest") else "medium"}
        if kind != "epic" and r["parent_id"] in epics:
            item["parent"] = epics[r["parent_id"]]
        if re.match(r"^MVP[0-9]$", mvp):
            item["mvp"] = mvp
        if r["username"] in usernames:
            item["assignee"] = r["username"]
        if r["story_points"] is not None and 0 <= r["story_points"] <= 100:
            item["points"] = r["story_points"]
        out.append(item)
    return out


def deliverables(conn, pid, limit):
    from modules.codex import catalog
    rows = conn.execute("SELECT doc_type, title, pdp_step, pdp_sub FROM codex_refs WHERE project_id = ? AND status = 'active' "
                        "ORDER BY id", (pid,)).fetchall()
    return [{"doc_type": r["doc_type"], "title": _cut(r["title"], 150) or catalog.DOC_TYPES[r["doc_type"]]["name"][:150],
             "step": r["pdp_step"] if r["pdp_step"] in catalog.STEPS else "", "sub": (r["pdp_sub"] or "00")[:2]}
            for r in rows if r["doc_type"] in catalog.DOC_TYPES][:limit]
