"""« Copier un Space » composed tab by tab (core lot v0.27, D-B-099).

Admin → Spaces → « Copier / composer un Space » always creates a NEW Space (never touches an existing one): for each
tab, the content comes from a Space chosen in a list, or « Vide (comme un Space neuf) » -- e.g. the Goldmine
requirements of Space 1 + the Test Base of Space 3 + an empty Dynamite wiki. A preview lists what will be copied;
creation is one transaction (all or nothing), journalled.

Parts and their tables:
  dynamite     dynamite_* (pages, versions, comments) and their images
  agile        Agile settings (workflows, statuses, types, labels, versions), Sprints, tickets that are not
               requirements, with their comments, history, labels, links, Change Management
  goldmine     requirements and needs (requirement tickets), agile_requirements, Q&A, Pugh matrices
  testing      the Test Base (testing_tests + history) of a Space, or the reference catalogue (copied lazily, D-B-097)
  exploration  the plan (Gantt)
  diamond      the functional tree, structure (inputs, outputs, flows, positions), parts, project risks, DFMEA (0.60.21),
               the Storyline (0.60.51)
  tools        ideation sessions and Kepner-Tregoe (not Generator: its numbers are unique on the whole platform)
  members      the members of a Space and their rights
When Agile and Goldmine come from two Spaces, Agile's settings are kept and the requirements are matched to them by
type and status name; their numbers follow the tickets' (a new key anyway). Links to rows that were not copied are
emptied and counted. Not copied: @mentions (personal), Test Plans (platform-unique codes), Timesheet hours.
"""
import shutil

from . import admin, audit, backup, db, modules, permissions, uploads
from .errors import ApiError

PARTS = ("dynamite", "agile", "goldmine", "diamond", "testing", "exploration", "tools", "members")
LABELS = {"dynamite": "Dynamite (wiki)", "agile": "Agile (tickets, Sprints, réglages)", "goldmine": "Goldmine (Requirements, needs, Q&A, Pugh)",
          "diamond": "Diamond (arbre, structure, pièces, risques, DFMEA)", "testing": "Testing (Test Base)", "exploration": "Exploration (Gantt)", "tools": "Tools (idéation, Kepner-Tregoe)",
          "members": "Membres et droits"}
INFRA = ("agile_settings", "agile_workflows", "agile_statuses", "agile_transitions", "agile_issue_types", "agile_labels",
         "agile_versions")
ISSUE_CHILDREN = ("agile_comments", "agile_history", "agile_issue_labels", "agile_links", "agile_changes", "agile_change_items")
GOLDMINE = ("agile_requirements", "goldmine_qa", "goldmine_qa_events", "goldmine_pugh", "goldmine_pugh_concepts",
            "goldmine_pugh_criteria", "goldmine_pugh_scores")
ATTACHMENT_MODULES = {"dynamite": ("dynamite",), "agile": ("agile",), "goldmine": ("goldmine", "agile_requirement")}
CATALOGUE = "TESTING"  # before 0.60.41; the reference Test Base now lives in DEMO (D-O-050), see _cat()


def _cat(conn):
    """The key of the Space that holds the reference Test Base (DEMO, or TESTING on an older installation)."""
    try:
        from modules.testing import catalog
        pid = catalog.project_id(conn)
    except Exception:
        return CATALOGUE
    row = conn.execute("SELECT key FROM projects WHERE id = ?", (pid,)).fetchone() if pid else None
    return row["key"] if row else CATALOGUE
DIAMOND = ("diamond_functions", "diamond_ports", "diamond_flows", "diamond_positions", "diamond_parts", "diamond_part_functions",
           "diamond_risks", "diamond_dfmea", "diamond_story_scenes", "diamond_cost_settings", "diamond_cost_nre", "diamond_cost_parts",
           "diamond_class_settings", "diamond_class_customers", "diamond_class_decisions",  # 0.60.101 (D-O-108): classes CC / SC
           "diamond_characteristics",  # 0.60.102 (D-O-110): characteristics C-n
           "diamond_company_parts", "diamond_part_pns",  # 0.60.103 (D-O-112): company part numbers
           "diamond_lines", "diamond_operations", "diamond_control_points", "diamond_process_access",  # 0.60.103 (D-O-113)
           "diamond_pfmea",  # 0.60.103 (D-O-114)
           "diamond_control_plans", "diamond_cp_items", "diamond_measurements", "diamond_waves", "diamond_review_flags")  # 0.60.103 (D-O-115)


def _tables_of(part, infra):
    if part == "dynamite":
        return ("dynamite_pages", "dynamite_versions", "dynamite_comments")
    if part == "agile":
        return (INFRA if infra else ()) + ("agile_sprints", "agile_issues") + ISSUE_CHILDREN
    if part == "goldmine":
        return (INFRA if infra else ()) + ("agile_issues",) + ISSUE_CHILDREN + GOLDMINE
    if part == "testing":
        return ("testing_tests", "testing_history")
    if part == "diamond":
        return DIAMOND
    if part == "exploration":
        return ("exploration_plans", "exploration_tasks", "exploration_counters")
    if part == "tools":
        return tuple(t for t in ("tools_ideation", "tools_ideation_people", "tools_ideas", "tools_idea_votes", "tools_idea_stars",
                                 "tools_idea_links", "tools_kt", "tools_kt_criteria", "tools_kt_alts", "tools_kt_scores", "tools_kt_risks"))
    if part == "members":
        return ("memberships",)
    return ()


def _project(conn, key):
    row = conn.execute("SELECT id, key, name FROM projects WHERE key = ?", (str(key).upper(),)).fetchone()
    if row is None:
        raise ApiError(400, "Space source « {} » introuvable. Correctif : choisissez un Space de la liste.".format(key))
    return dict(row)


def _clean_parts(conn, body):
    parts = {}
    for part in PARTS:
        value = str((body.get("parts") or {}).get(part) or "").strip().upper()
        if value:
            parts[part] = _project(conn, value)
    return parts


def _req_types(conn, pid):
    return {r["id"] for r in conn.execute("SELECT id FROM agile_issue_types WHERE project_id = ? AND is_requirement = 1", (pid,))}


def _plan(conn, parts):
    """{source key: {table: [rows]}} of what will be copied, after the part filters."""
    collected, plan = {}, {}
    infra_src = (parts.get("agile") or parts.get("goldmine") or {}).get("key")
    for part, src in parts.items():
        if part == "testing" and src["key"] == _cat(conn):
            continue  # the catalogue: copied lazily (D-B-097)
        if src["key"] not in collected:
            collected[src["key"]] = backup.collect(conn, src["id"])[1]
        rows = collected[src["key"]]
        req = _req_types(conn, src["id"]) if part in ("agile", "goldmine") else set()
        target = plan.setdefault(src["key"], {})
        for table in _tables_of(part, src["key"] == infra_src):
            items = rows.get(table, [])
            if table == "agile_issues":
                items = [r for r in items if (r["type_id"] in req) == (part == "goldmine")]
            have = {r.get("__rowid") for r in target.get(table, [])}
            target.setdefault(table, []).extend(r for r in items if r.get("__rowid") not in have)
        if part in ATTACHMENT_MODULES:
            have = {r.get("__rowid") for r in target.get("attachments", [])}
            target.setdefault("attachments", []).extend(r for r in rows.get("attachments", [])
                                                        if r["module"] in ATTACHMENT_MODULES[part] and r.get("__rowid") not in have)
    return plan


def _name_maps(conn, src_pid, new_pid):
    """Agile settings of another source matched by name (types, statuses, labels, versions)."""
    maps = {}
    pairs = (("agile_issue_types", "name"), ("agile_labels", "name"), ("agile_versions", "name"))
    for table, col in pairs:
        new = {r[col]: r["id"] for r in conn.execute('SELECT id, "{}" FROM "{}" WHERE project_id = ?'.format(col, table), (new_pid,))}
        maps[table] = {r["id"]: new[r[col]] for r in conn.execute('SELECT id, "{}" FROM "{}" WHERE project_id = ?'.format(col, table),
                                                                 (src_pid,)) if r[col] in new}
    new_status = {}
    for r in conn.execute("SELECT s.id, s.name FROM agile_statuses s JOIN agile_workflows w ON w.id = s.workflow_id "
                          "WHERE w.project_id = ? ORDER BY s.is_initial DESC, s.position", (new_pid,)):
        new_status.setdefault(r["name"], r["id"])
    maps["agile_statuses"] = {r["id"]: new_status[r["name"]] for r in conn.execute(
        "SELECT s.id, s.name FROM agile_statuses s JOIN agile_workflows w ON w.id = s.workflow_id WHERE w.project_id = ?",
        (src_pid,)) if r["name"] in new_status}
    req = conn.execute("SELECT id FROM agile_issue_types WHERE project_id = ? AND is_requirement = 1 ORDER BY id", (new_pid,)).fetchone()
    for old in _req_types(conn, src_pid):  # a requirement type that has another name here
        if old not in maps["agile_issue_types"] and req:
            maps["agile_issue_types"][old] = req["id"]
    return maps


def _insert(ctx, src_key, src_pid, tables, info, maps, new_pid, shift=0):
    counts, lost, later = {}, 0, []
    for t in backup._order(info, [t for t in tables if t in info]):
        cols = info[t]["cols"]
        pk_id = "id" in cols and cols["id"]["pk"] == 1 and sum(1 for c in cols.values() if c["pk"]) == 1
        maps.setdefault(t, {})
        for row in tables[t]:
            new = {k: v for k, v in row.items() if k in cols}
            old_id = new.pop("id", None) if pk_id else None
            if old_id is not None and old_id in maps[t]:
                continue  # already given by the name matching (agile settings of another source)
            refs = {}
            for col, parent, _pcol in info[t]["fks"]:
                value = new.get(col)
                if value is None:
                    continue
                if parent == t:
                    refs[col], new[col] = value, None
                    continue
                if parent == "users":
                    continue  # same server: accounts are the same
                new[col] = new_pid if parent == "projects" else maps.get(parent, {}).get(value)
                if new[col] is None:
                    lost += 1
            if t == "agile_issues" and shift:
                new["number"] = new["number"] + shift
            if any(new.get(c) is None and (cols[c]["notnull"] or cols[c]["pk"]) and cols[c]["default"] is None for c in new):
                continue
            names = list(new)
            cur = ctx.conn.execute('INSERT INTO "{}" ({}) VALUES ({})'.format(
                t, ",".join('"{}"'.format(c) for c in names), ",".join("?" * len(names))), [new[c] for c in names])
            if pk_id:
                maps[t][old_id] = cur.lastrowid
            if refs:
                later.append((t, cur.lastrowid, refs))
            counts[t] = counts.get(t, 0) + 1
    for t, new_id, refs in later:
        sets = {c: maps[t].get(v) for c, v in refs.items()}
        ctx.conn.execute('UPDATE "{}" SET {} WHERE rowid = ?'.format(t, ", ".join('"{}" = ?'.format(c) for c in sets)),
                         list(sets.values()) + [new_id])
    for att in tables.get("attachments", []):
        if att.get("id") in maps.get("attachments", {}):
            src = uploads.file_path(ctx.data_dir, src_pid, att["sha256"], att["mime"])
            dst = uploads.file_path(ctx.data_dir, new_pid, att["sha256"], att["mime"])
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
    return counts, lost


def summary(conn, parts):
    plan = _plan(conn, parts)
    out = []
    for part in PARTS:
        src = parts.get(part)
        if src is None:
            out.append({"part": part, "label": LABELS[part], "source": "", "detail": "Vide (comme un Space neuf)"})
            continue
        if part == "testing" and src["key"] == _cat(conn):
            out.append({"part": part, "label": LABELS[part], "source": src["key"], "detail": "copie du catalogue de référence"})
            continue
        rows = plan.get(src["key"], {})
        req = _req_types(conn, src["id"])
        n = {"dynamite": len(rows.get("dynamite_pages", [])), "diamond": len(rows.get("diamond_functions", [])), "testing": len(rows.get("testing_tests", [])),
             "exploration": len(rows.get("exploration_tasks", [])), "tools": len(rows.get("tools_ideation", [])) + len(rows.get("tools_kt", [])),
             "members": len(rows.get("memberships", [])),
             "agile": sum(1 for r in rows.get("agile_issues", []) if r["type_id"] not in req),
             "goldmine": sum(1 for r in rows.get("agile_issues", []) if r["type_id"] in req)}[part]
        unit = {"dynamite": "page(s)", "diamond": "fonction(s)", "testing": "test(s)", "exploration": "tâche(s)", "tools": "session(s)",
                "members": "membre(s)", "agile": "ticket(s)", "goldmine": "Requirement(s) / need(s)"}[part]
        out.append({"part": part, "label": LABELS[part], "source": src["key"], "detail": "{} {}".format(n, unit)})
    return out


def compose(ctx, key, name, description, parts):
    project = admin.create_project_record(ctx, key, name, description, provision=False)
    pid = project["id"]
    plan, info = _plan(ctx.conn, parts), backup._tables(ctx.conn)
    hooks = dict(modules.project_hooks())
    agile, gold = parts.get("agile"), parts.get("goldmine")
    for part in ("dynamite", "exploration"):
        if part not in parts and part in hooks:
            hooks[part](ctx, pid)  # « Vide » = like a new Space
    if not agile and not gold:
        hooks["agile"](ctx, pid)
        hooks["goldmine"](ctx, pid)
    report, lost = {}, 0
    order = [s for s in (agile, gold) if s] + [s for p, s in parts.items() if p not in ("agile", "goldmine")]
    done = set()
    for src in order:
        if src["key"] in done or src["key"] not in plan:
            continue
        done.add(src["key"])
        maps = {"projects": {src["id"]: pid}}
        shift = 0
        if gold and agile and gold["key"] != agile["key"] and src["key"] == gold["key"]:
            maps.update(_name_maps(ctx.conn, src["id"], pid))  # Agile settings come from the Agile source
            shift = ctx.conn.execute("SELECT COALESCE(MAX(number), 0) FROM agile_issues WHERE project_id = ?", (pid,)).fetchone()[0]
        counts, n_lost = _insert(ctx, src["key"], src["id"], plan[src["key"]], info, maps, pid, shift)
        for _k, hook in modules.restore_hooks():
            hook(ctx.conn, maps, src["key"], key)
        report[src["key"]] = counts
        lost += n_lost
    if agile and not gold:
        hooks["goldmine"](ctx, pid)  # the requirement type exists
    if "timesheet" in hooks:
        hooks["timesheet"](ctx, pid)
    testing = parts.get("testing")
    if testing and testing["key"] != _cat(ctx.conn):
        pass  # copied with its rows above
    top = ctx.conn.execute("SELECT COALESCE(MAX(number), 0) FROM agile_issues WHERE project_id = ?", (pid,)).fetchone()[0]
    ctx.conn.execute("UPDATE projects SET next_ticket_number = ? WHERE id = ?", (top + 1, pid))
    if "members" not in parts:
        ctx.conn.execute("INSERT OR IGNORE INTO memberships (user_id, project_id, role) VALUES (?, ?, 'manager')", (ctx.user["id"], pid))
    audit.log_action(ctx.conn, ctx.user["id"], "space_composed", "project", pid,
                     {"key": key, "parts": {p: s["key"] for p, s in parts.items()}, "rows": report, "lost_links": lost}, ctx.ip)
    return {"project": {"id": pid, "key": key}, "rows": report, "lost_links": lost}


def api_sources(ctx):
    permissions.require_admin(ctx.user)
    rows = ctx.conn.execute("SELECT id, key, name FROM projects WHERE is_archived = 0 ORDER BY key").fetchall()
    return {"parts": [{"part": p, "label": LABELS[p]} for p in PARTS], "spaces": [dict(r) for r in rows], "catalogue": _cat(ctx.conn)}


def api_compose(ctx):
    permissions.require_admin(ctx.user)
    key = str(ctx.body.get("key") or "").strip().upper()
    name = str(ctx.body.get("name") or "").strip()[:100]
    parts = _clean_parts(ctx.conn, ctx.body)
    if ctx.body.get("mode") == "preview":
        if not admin.PROJECT_KEY_RE.match(key):
            raise ApiError(400, "Clé « {} » invalide. Correctif : 2 à 10 lettres majuscules ou chiffres, une lettre d'abord.".format(key))
        if ctx.conn.execute("SELECT 1 FROM projects WHERE key = ?", (key,)).fetchone():
            raise ApiError(409, "La clé {} existe déjà : la copie crée toujours un nouveau Space. Correctif : une autre clé.".format(key))
        return {"key": key, "name": name or key, "summary": summary(ctx.conn, parts)}
    if not name:
        raise ApiError(400, "Nom du nouveau Space manquant. Correctif : écrivez un nom.")
    return compose(ctx, key, name, str(ctx.body.get("description") or "")[:500], parts)


ROUTES = [
    ("GET", r"/api/admin/spacecopy", api_sources, "admin"),
    ("POST", r"/api/admin/spacecopy", api_compose, "admin"),
]
