"""« Commencer » on the server (0.60.06, D-O-019): check a Project Starter file, then create its Space.

POST /api/starter/check  {file, key?, renames?, drop?} -> what would be created, the warnings, and what blocks it
POST /api/starter/apply  same body                     -> the new Space and the temporary passwords (shown once)

`file` is the JSON object, or its text, as the AI assistant gave it (core/starter.py checks it). `key` replaces the
Space key of the file; `renames` {old code: new code} and `drop` [code, ...] adjust the time codes before creation
(the preview of 0.60.07 offers them). Administrators only. Nothing is written by « check »; « apply » writes
everything in the transaction of the request (all or nothing, core/db.connect) and journals each step plus
« starter_applied ». It reuses the code of the screens (admin.create_project_record and its module hooks, Goldmine
and Testing creation, Dynamite pages), so the rules and the journal are the same as by hand.

What the file never decides (D-O-019): requirements « À vérifier » (standard_review), tests « À vérifier » and Draft,
pages « Brouillon IA », members never administrators; an existing account is reused as it is (never modified).
"""
from pathlib import Path

from . import admin, audit, auth, db, starter
from .errors import ApiError

NOTE = "Project Starter"
PLACEHOLDER = {"title": "Essai à définir (Project Starter)", "subject": "func", "category": "custom", "method": "T",
               "objective": "Requis sans essai dans le fichier de démarrage : l'équipe définit l'essai qui le vérifie."}


def _prepare(ctx):
    raw = ctx.body.get("file")
    if not isinstance(raw, (dict, str)):
        raise ApiError(400, "Fichier Project Starter manquant. Correctif : choisissez le fichier .json donné par l'assistant.")
    clean, warnings = starter.parse(raw)
    key = ctx.body.get("key") or clean["project"]["key"]
    if not isinstance(key, str) or not admin.PROJECT_KEY_RE.match(key.strip().upper()):
        raise ApiError(400, "Clé de Space « {} » invalide. Correctif : 2 à 10 majuscules ou chiffres, en commençant par une "
                            "lettre.".format(str(key)[:20]))
    renames, drop = ctx.body.get("renames") or {}, ctx.body.get("drop") or []
    if not isinstance(renames, dict) or not isinstance(drop, list):
        raise ApiError(400, "Ajustements des codes illisibles. Correctif : relancez « Commencer ».")
    code_re, codes, seen = starter._code_re(), [], set()
    for code, label in starter.codes_of(clean):
        if code in drop:
            continue
        new = renames.get(code, code)
        if not isinstance(new, str) or not code_re.match(new) or new in seen:
            raise ApiError(400, "Nouveau code « {} » pour {} invalide ou en double. Correctif : 1 à 5 majuscules, un tiret, "
                                "2 à 4 majuscules ou chiffres, unique (ex. LA-MAR).".format(str(new)[:20], code))
        seen.add(new)
        codes.append({"key": new, "label": label, "from": code})
    return clean, warnings, key.strip().upper(), codes


def _blocking(conn, key, codes):
    out = []
    if conn.execute("SELECT 1 FROM projects WHERE key = ? UNION SELECT 1 FROM retired_project_keys WHERE key = ?",
                    (key, key)).fetchone():
        out.append({"what": "key", "value": key, "message": "La clé de Space {} est déjà prise.".format(key),
                    "fix": "choisissez une autre clé."})
    taken = [c["key"] for c in codes
             if conn.execute("SELECT 1 FROM timesheet_budget_lines WHERE code = ?", (c["key"],)).fetchone()]
    for code in taken:
        out.append({"what": "code", "value": code, "message": "Le code de temps {} existe déjà sur ce site.".format(code),
                    "fix": "renommez-le ou retirez-le."})
    return out


def _team(conn, clean):
    known = {r["username"]: r for r in conn.execute("SELECT id, username, is_admin, is_active FROM users")}
    return [dict(m, exists=m["username"] in known) for m in clean["team"]]


def api_check(ctx):
    clean, warnings, key, codes = _prepare(ctx)
    team = _team(ctx.conn, clean)
    reused = [m["username"] for m in team if m["exists"]]
    if reused:
        warnings = warnings + ["Compte(s) existant(s), réutilisé(s) tel(s) quel(s) : {}.".format(", ".join(reused))]
    blocking = _blocking(ctx.conn, key, codes)
    return {"summary": dict(starter.summary(clean), key=key, time_codes=len(codes)), "warnings": warnings,
            "blocking": blocking, "ready": not blocking, "team": team, "codes": codes,
            "requirements": [{k: r[k] for k in ("ref", "kind", "statement", "standard")} for r in clean["requirements"]],
            "tests": [{k: t[k] for k in ("ref", "title", "standard")} for t in clean["tests"]],
            "pages": [{k: p[k] for k in ("ref", "title", "parent")} for p in clean["pages"]]}


def _as(ctx, project_id, body, func):
    """Call a module handler for this Space with this body, as the screens do (same checks, same journal)."""
    saved = ctx.params, ctx.body
    ctx.params, ctx.body = {"pid": str(project_id)}, body
    try:
        return func(ctx)
    finally:
        ctx.params, ctx.body = saved


def _accounts(ctx, project_id, clean):
    created, reused = [], []
    for m in clean["team"]:
        row = ctx.conn.execute("SELECT id FROM users WHERE username = ?", (m["username"],)).fetchone()
        if row is None:
            temp = auth.generate_temp_password()
            user_id = ctx.conn.execute(
                "INSERT INTO users (username, display_name, password_hash, is_admin, is_active, must_change_password, "
                "created_at, study_profile, title) VALUES (?, ?, ?, 0, 1, 1, ?, ?, ?)",
                (m["username"], m["display_name"], auth.hash_password(temp), db.utc_now(), m["study_profile"],
                 m["title"])).lastrowid
            from . import prefs
            prefs.ensure_initials(ctx.conn, user_id)  # 0.60.19 (D-O-030)
            audit.log_action(ctx.conn, ctx.user["id"], "user_created", "user", user_id,
                             {"username": m["username"], "is_admin": False, "via": NOTE}, ctx.ip)
            created.append({"username": m["username"], "display_name": m["display_name"], "temp_password": temp})
        else:
            user_id = row["id"]
            reused.append(m["username"])
        ctx.conn.execute("INSERT OR IGNORE INTO memberships (user_id, project_id, role) VALUES (?, ?, ?)",
                         (user_id, project_id, m["role"]))
        audit.log_action(ctx.conn, ctx.user["id"], "member_set", "project", project_id,
                         {"user_id": user_id, "role": m["role"], "via": NOTE}, ctx.ip)
    return created, reused


def _time_codes(ctx, project_id, key, codes):
    if not codes:
        return None
    from modules.timesheet import budget, manage
    tools = budget._company_id(ctx.conn)
    if tools is None:
        raise ApiError(409, "Les tables des codes de temps n'existent pas encore. Correctif : redémarrez l'outil, puis "
                            "relancez « Commencer ».")
    set_key, now = "starter-" + key.lower(), db.utc_now()
    position = ctx.conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM timesheet_budget_sets").fetchone()[0]
    set_id = ctx.conn.execute("INSERT INTO timesheet_budget_sets (project_id, key, label, position, active, created_at, "
                              "updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                              (tools, set_key, "Codes du projet {}".format(key), position, now, now)).lastrowid
    for pos, c in enumerate(codes):
        ctx.conn.execute("INSERT INTO timesheet_budget_lines (set_id, code, label, claimable, position, active, created_at, "
                         "updated_at) VALUES (?, ?, ?, 1, ?, 1, ?, ?)", (set_id, c["key"], c["label"][:120], pos, now, now))
    manage.save_settings(ctx.conn, project_id, task_set=set_key)
    audit.log_action(ctx.conn, ctx.user["id"], "timesheet_budget_set_add", "project", project_id,
                     {"key": set_key, "codes": len(codes), "via": NOTE}, ctx.ip)
    return set_key


def _tests(ctx, project_id, clean):
    from modules.testing import tests_api
    ids = {}
    untested = [r for r in clean["requirements"] if r["kind"] == "requirement"
                and not any(r["ref"] in t["verifies"] for t in clean["tests"])]
    items = list(clean["tests"]) + ([dict(PLACEHOLDER, ref="", standard="", section="", level="", acceptance="", means="")]
                                    if clean["tests"] and untested else [])
    for t in items:
        body = {f: t[f] for f in ("title", "subject", "category", "standard", "section", "level", "method", "objective",
                                  "acceptance", "means")}
        body["status"] = "Draft"
        test_id = tests_api.create(ctx, project_id, body)
        ctx.conn.execute("UPDATE testing_tests SET review = ? WHERE project_id = ? AND test_id = ?",
                         (starter.REVIEW, project_id, test_id))
        ids[t["ref"]] = test_id
    return ids, [r["ref"] for r in untested] if "" in ids else []


def _requirements(ctx, project_id, key, clean, test_ids):
    from modules.agile import goldmine
    keys = {}
    for r in clean["requirements"]:
        tests = [test_ids[t["ref"]] for t in clean["tests"] if r["ref"] in t["verifies"]]
        if not tests and r["kind"] == "requirement" and "" in test_ids:
            tests = [test_ids[""]]
        source_doc = " · ".join(x for x in (r["standard"], r["edition"], r["clause"]) if x)[:200]
        body = {"statement": r["statement"], "kind": r["kind"], "rationale": r["rationale"], "category": r["category"],
                "lifecycle": r["lifecycle"], "stakeholder": r["stakeholder"], "source": r["source"],
                "source_doc": source_doc, "verification_method": r["verification_method"],
                "acceptance_criteria": r["acceptance_criteria"], "criticality": r["criticality"],
                "external_id": r["ref"][:40], "derived_from": ", ".join(keys[x] for x in r["derived_from"]),
                "test_ref": ", ".join(tests)}
        number = _as(ctx, project_id, body, goldmine.api_create)["number"]
        keys[r["ref"]] = "{}-{}".format(key, number)
        ctx.conn.execute("UPDATE agile_requirements SET standard_review = ? WHERE issue_id = (SELECT id FROM agile_issues "
                         "WHERE project_id = ? AND number = ?)", (starter.REVIEW, project_id, number))
    return keys


def _pages(ctx, project_id, clean):
    from modules.dynamite import content, pages
    home = ctx.conn.execute("SELECT id, current_version FROM dynamite_pages WHERE project_id = ? AND parent_id IS NULL "
                            "ORDER BY position, id LIMIT 1", (project_id,)).fetchone()
    ids = {}
    for p in clean["pages"]:
        if p["parent"] is None and home is not None and not ids:  # the first top page becomes the home page
            version, now = home["current_version"] + 1, db.utc_now()
            ctx.conn.execute("INSERT INTO dynamite_versions (page_id, version, title, body, author_id, created_at, note) "
                             "VALUES (?, ?, ?, ?, ?, ?, ?)", (home["id"], version, p["title"], content.validate(p["body"]),
                                                              ctx.user["id"], now, NOTE))
            ctx.conn.execute("UPDATE dynamite_pages SET title = ?, current_version = ?, updated_by = ?, updated_at = ? "
                             "WHERE id = ?", (p["title"], version, ctx.user["id"], now, home["id"]))
            pages._log(ctx, "dynamite_page_save", home["id"], {"version": version, "via": NOTE})
            ids[p["ref"]] = home["id"]
            continue
        parent = ids[p["parent"]] if p["parent"] else (home["id"] if home is not None else None)
        ids[p["ref"]] = _as(ctx, project_id, {"title": p["title"], "parent_id": parent, "body": p["body"]},
                            pages.api_create)["id"]
    return ids


def api_apply(ctx):
    clean, warnings, key, codes = _prepare(ctx)
    blocking = _blocking(ctx.conn, key, codes)
    if blocking:
        raise ApiError(409, "Rien n'a été créé : {} Correctif : {}".format(blocking[0]["message"], blocking[0]["fix"]))
    project = clean["project"]
    description = project["description"] if len(project["description"]) <= 500 else project["description"][:497] + "…"
    space = admin.create_project_record(ctx, key, project["name"][:100], description)
    pid = space["id"]
    created, reused = _accounts(ctx, pid, clean)
    set_key = _time_codes(ctx, pid, key, codes)
    test_ids, placeholder_for = _tests(ctx, pid, clean)
    req_keys = _requirements(ctx, pid, key, clean, test_ids)
    page_ids = _pages(ctx, pid, clean)
    from . import starter_diamond  # 0.60.22 (D-O-032)
    rows = {r["test_id"]: r["id"] for r in ctx.conn.execute("SELECT id, test_id FROM testing_tests WHERE project_id = ?", (pid,))}
    made = starter_diamond.apply(ctx.conn, ctx.user["id"], pid, clean["diamond"],
                                 {ref: rows.get(code) for ref, code in test_ids.items()})  # ref -> row id of the test
    from . import starter_more  # 0.60.43 (D-O-052): the Agile backlog by MVP, the Generator deliverables
    more = starter_more.apply(ctx, pid, key, clean["more"], lambda p, body, func: _as(ctx, p, body, func))
    from modules.exploration import reference  # 0.60.22: the reference Gantt of the PDP, sized for the team
    owners = [r["id"] for m in clean["team"] for r in ctx.conn.execute("SELECT id FROM users WHERE username = ?", (m["username"],))]
    plan_tasks = reference.apply(ctx, pid, reference.parse_start(project["start_date"]), project["weeks"], owners or [ctx.user["id"]])
    counts = {"accounts_created": len(created), "accounts_reused": len(reused), "requirements": len(req_keys),
              "tests": len(test_ids), "time_codes": len(codes), "pages": len(page_ids),
              **{"diamond_" + k: n for k, n in made.items()}, "plan_tasks": plan_tasks, **{"agile_" + k: n for k, n in more.items()}}
    # 0.60.42 (D-O-051): the new product becomes the default Space of whoever has none yet -- the whole platform opens on it
    from core import prefs as P
    for uid in set(owners + [ctx.user["id"]]):
        if not P.get(ctx.conn, uid).get("default_space"):
            P._put(ctx.conn, uid, {"default_space": key})
    audit.log_action(ctx.conn, ctx.user["id"], "starter_applied", "project", pid,
                     dict(counts, key=key, generated_by=clean["generated_by"][:120], task_set=set_key or ""), ctx.ip)
    return {"project": {"id": pid, "key": key, "name": space["name"]}, "accounts": created, "reused": reused,
            "counts": counts, "requirements": req_keys, "tests": {k: v for k, v in test_ids.items() if k},
            "placeholder_for": placeholder_for, "warnings": warnings}


EXAMPLES = Path(__file__).resolve().parent.parent / "deploy" / "starter_exemples"


def api_examples(ctx):
    """0.60.07: the example files of deploy/starter_exemples/, to try « Commencer » before asking an AI assistant."""
    out = []
    for f in sorted(EXAMPLES.glob("*.json")):
        text = f.read_text("utf-8")
        try:
            name = starter.parse(text)[0]["project"]["name"]
        except ApiError:
            continue
        out.append({"id": f.stem, "name": name, "text": text})
    return {"examples": out}


def api_status(ctx):
    """0.60.07: the Dashboard puts « Commencer » forward until a first project has been started this way."""
    started = ctx.conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'starter_applied'").fetchone()[0]
    return {"show": started == 0, "started": started}


def api_prompt(ctx):
    """0.60.18: the prompt to paste into an AI assistant (FR / EN), served by the tool itself so it works offline too."""
    from . import starter_prompt
    from .files import RawFile
    lang = "en" if str((ctx.query or {}).get("lang") or "fr")[:2] == "en" else "fr"
    proven = None
    if (ctx.query or {}).get("source"):  # 0.60.43 (D-O-052): a proven Space of the team as the worked example
        from . import starter_export
        proven = starter_export.build(ctx.conn, starter_export._space(ctx, "source"))
    text = starter_prompt.render(lang, proven=proven)
    if str((ctx.query or {}).get("download") or "") == "1":
        return RawFile(text.encode("utf-8"), "starter.md" if lang == "fr" else "starter_en.md", "text/markdown; charset=utf-8",
                       export=False)
    return {"lang": lang, "text": text}


def _export(ctx):
    from . import starter_export
    return starter_export.api_export(ctx)


ROUTES = [
    ("GET", r"/api/starter/status", api_status, "admin"),
    ("GET", r"/api/starter/examples", api_examples, "admin"),
    ("GET", r"/api/starter/prompt", api_prompt, "user"),
    ("GET", r"/api/starter/export", _export, "user"),  # 0.60.43 (D-O-052): administrators or the Space's managers
    ("POST", r"/api/starter/check", api_check, "admin"),
    ("POST", r"/api/starter/apply", api_apply, "admin"),
]
