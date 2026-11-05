"""A proven Space as a Project Starter file (0.60.43, D-O-052): the team archives, copies or recreates Spaces; the ones
that worked become the example an AI assistant follows to prepare the next product completely.

GET /api/starter/export?space=KEY (administrators, or the Space's managers): the Space read back in the exact format
« Commencer » takes -- project, team, requirements and needs, tests, the Space's own time codes, the first pages, Diamond
(tree, structure, parts, risks, DFMEA), the Agile backlog by MVP and the Generator deliverables. Every value is cut to the
limits of the format and the result passes core/starter.parse, so it can be read by an assistant or applied again as is.
GET /api/starter/prompt?source=KEY gives the interview prompt with this file as the worked example.
"""
import datetime as dt
import json

from . import audit, permissions, starter
from .errors import ApiError
from .files import RawFile

MAX = {"requirements": 300, "tests": 300, "pages": 30, "backlog": 150, "deliverables": 40,
       "functions": 120, "ports": 40, "flows": 200, "parts": 80, "risks": 60, "dfmea": 120}


def _cut(value, n):
    value = str(value or "").strip()
    return value if len(value) <= n else value[:n - 1].rstrip() + "…"


def _pick(value, options, default=""):
    return value if value in options else default


def _space(ctx, param="space"):
    key = str(ctx.query.get(param) or "").strip().upper()
    row = ctx.conn.execute("SELECT id, key, name, description FROM projects WHERE key = ? AND is_archived = 0", (key,)).fetchone()
    if row is None:
        raise ApiError(404, "Space « {} » introuvable. Correctif : choisissez un Space de la liste.".format(key[:20]))
    if not permissions.is_project_manager(ctx.conn, ctx.user, row["id"]):
        raise ApiError(403, "Réservé aux administrateurs et aux Admin du Space {}. Correctif : demandez-le à l'un d'eux.".format(row["key"]))
    return row


def _clean_doc(node):
    """A Dynamite page body without images nor ticket blocks (refused in a starter file)."""
    if isinstance(node, dict):
        if node.get("type") in ("image", "ticket"):
            return None
        out = dict(node)
        if isinstance(node.get("content"), list):
            out["content"] = [c for c in (_clean_doc(x) for x in node["content"]) if c is not None]
        return out
    return node


def _team(conn, pid):
    rows = conn.execute("SELECT u.username, u.display_name, u.study_profile, u.title, m.role FROM memberships m "
                        "JOIN users u ON u.id = m.user_id WHERE m.project_id = ? AND u.is_active = 1 AND u.is_admin = 0 "
                        "ORDER BY u.display_name LIMIT 12", (pid,)).fetchall()
    return [{"username": r["username"], "display_name": _cut(r["display_name"], 80), "study_profile": _cut(r["study_profile"], 80),
             "title": _cut(r["title"], 120), "role": _pick(r["role"], starter.ROLES, "editor")} for r in rows
            if starter.USERNAME_RE.match(r["username"] or "")]


def _requirements(conn, pid, key, v):
    rows = conn.execute("SELECT i.number, r.* FROM agile_requirements r JOIN agile_issues i ON i.id = r.issue_id "
                        "WHERE i.project_id = ? ORDER BY i.number LIMIT ?", (pid, MAX["requirements"])).fetchall()
    out, refs = [], {}
    for r in rows:
        ref = "R{}".format(r["number"])
        refs["{}-{}".format(key, r["number"])] = ref
        parts = [p.strip() for p in (r["source_doc"] or "").split("·")]
        derived = [refs[x.strip()] for x in (r["derived_from"] or "").split(",") if x.strip() in refs]
        out.append({"ref": ref, "kind": _pick(r["kind"], v["kind"], "requirement"), "statement": _cut(r["statement"], 4000) or "—",
                    "rationale": _cut(r["rationale"], 4000), "category": _pick(r["category"], v["category"], "functional"),
                    "lifecycle": _pick(r["lifecycle"], v["lifecycle"]), "stakeholder": _pick(r["stakeholder"], v["stakeholder"]),
                    "source": _pick(r["source"], v["source"], "client"), "standard": _cut(parts[0] if parts else "", 200),
                    "edition": _cut(parts[1] if len(parts) > 1 else "", 40), "clause": _cut(parts[2] if len(parts) > 2 else "", 80),
                    "verification_method": _pick(r["verification_method"], v["verification_method"]),
                    "acceptance_criteria": _cut(r["acceptance_criteria"], 2000),
                    "criticality": _pick(r["criticality"], v["criticality"]), "derived_from": derived,
                    "_tests": [t.strip() for t in (r["test_ref"] or "").replace(";", ",").split(",") if t.strip()]})
    return out


def _tests(conn, pid, requirements, v):
    rows = conn.execute("SELECT * FROM testing_tests WHERE project_id = ? ORDER BY test_id LIMIT ?", (pid, MAX["tests"])).fetchall()
    out, seen = [], set()
    for i, t in enumerate(rows):
        ref = "T{}".format(i + 1)
        seen.add(t["test_id"])
        out.append({"ref": ref, "title": _cut(t["title"], 200) or t["test_id"], "subject": _pick(t["subject"], v["subject"], "func"),
                    "category": _pick(t["category"], v["test_category"], "custom"), "standard": _cut(t["standard"], 200),
                    "section": _cut(t["section"], 80), "level": _pick(t["level"], v["level"]), "method": _pick(t["method"], v["method"], "T"),
                    "objective": _cut(t["objective"], 4000), "acceptance": _cut(t["acceptance"], 2000), "means": _cut(t["means"], 2000),
                    "verifies": [r["ref"] for r in requirements if t["test_id"] in r["_tests"]], "_code": t["test_id"]})
    return out


def _time_codes(conn, key):
    row = conn.execute("SELECT id, label FROM timesheet_budget_sets WHERE key = ?", ("starter-" + key.lower(),)).fetchone()
    if row is None:
        return []
    lines = conn.execute("SELECT code, label FROM timesheet_budget_lines WHERE set_id = ? AND active = 1 ORDER BY position",
                         (row["id"],)).fetchall()
    return [{"key": l["code"], "label": _cut(l["label"], 120)} for l in lines[:40]]


def _pages(conn, pid):
    rows = conn.execute("SELECT p.id, p.parent_id, v.title, v.body FROM dynamite_pages p JOIN dynamite_versions v "
                        "ON v.page_id = p.id AND v.version = p.current_version WHERE p.project_id = ? ORDER BY p.position, p.id",
                        (pid,)).fetchall()
    by_id = {r["id"]: r for r in rows}
    depth = {}
    for r in rows:
        d, cur = 1, r
        while cur["parent_id"] in by_id and d < 4:
            d, cur = d + 1, by_id[cur["parent_id"]]
        depth[r["id"]] = d
    out, refs = [], {}
    for r in sorted(rows, key=lambda r: depth[r["id"]]):
        if depth[r["id"]] > 2 or len(out) >= MAX["pages"]:
            continue
        try:
            body = _clean_doc(json.loads(r["body"]))
        except ValueError:
            continue
        refs[r["id"]] = "P{}".format(len(out) + 1)
        out.append({"ref": refs[r["id"]], "title": _cut(r["title"], 200) or "Page",
                    "parent": refs.get(r["parent_id"]) if depth[r["id"]] == 2 else None, "body": body})
    return [p for p in out if p["parent"] is None or p["parent"] in refs.values()]


def build(conn, row):
    from . import starter_export_more as more
    pid, key = row["id"], row["key"]
    v = starter._vocab()
    team = _team(conn, pid)
    requirements = _requirements(conn, pid, key, v)
    tests = _tests(conn, pid, requirements, v)
    codes = _time_codes(conn, key)
    data = {"format": starter.FORMAT, "format_version": starter.FORMAT_VERSION, "language": "fr",
            "generated_by": "DynamiteAgile — export du Space {}".format(key), "generated_at": dt.date.today().isoformat(),
            "project": {"key": key, "name": _cut(row["name"], 120), "description": _cut(row["description"], 4000)},
            "team": team, "requirements": [{k: x for k, x in r.items() if not k.startswith("_")} for r in requirements],
            "tests": [{k: x for k, x in t.items() if not k.startswith("_")} for t in tests],
            "time_codes": [{"key": "CODES", "label": "Codes du Space", "codes": codes}] if codes else [],
            "pages": _pages(conn, pid)}
    usernames = {m["username"] for m in team}
    data["diamond"] = more.diamond(conn, pid, {t["_code"]: t["ref"] for t in tests}, usernames, MAX)
    data["backlog"] = more.backlog(conn, pid, usernames, MAX["backlog"])
    data["deliverables"] = more.deliverables(conn, pid, MAX["deliverables"])
    return data


def api_export(ctx):
    row = _space(ctx)
    data = build(ctx.conn, row)
    starter.parse(json.dumps(data))  # the file must be one « Commencer » takes
    audit.log_action(ctx.conn, ctx.user["id"], "starter_exported", "project", row["id"], {"key": row["key"]}, ctx.ip)
    if ctx.query.get("download"):
        return RawFile(json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8"), "{}_project_starter.json".format(row["key"]),
                       "application/json", export=False)
    return data
