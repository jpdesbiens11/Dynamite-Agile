"""Diamond · import of an AI answer into a Space that is not empty (0.60.53, D-O-062).

Two ways, chosen in « Importer la réponse de l'IA »:

  add      « Compléter » (default): only what the Space is missing arrives; what is already there stays as it is.
           Section by section: the tree when the Space has none; the structure (inputs, outputs, flows) when the Space has
           neither; the parts, the risks, the Storyline when the Space has none. When the Space already has its tree, the
           file's functions are matched to it by their text (or, in a file without functions, by their F number: F12), and
           the structure, parts, risks and DFMEA of the file hang on the existing functions; what points to a function the
           Space does not have is left out and counted. DFMEA: a row of the file replaces the rows the tool wrote by itself
           for that function (« Ne réalise pas … (à préciser) »), never a row of the team.
  replace  « Tout remplacer » (admins of the Space): a full backup of the Space is written first (data/backups/, ⚙ Admin → Spaces →
           Sauvegardes), then Diamond is emptied and rebuilt from the file; the Storyline stays when the file has none.

plan() reads the file against the Space and returns the clean file to apply, what will be created and what is kept;
wipe() empties Diamond. story_ai.api_import checks, journals and applies.
"""
import re

from core.errors import ApiError

SECTIONS = ("functions", "ports", "flows", "parts", "risks", "dfmea", "story")
AUTO_RE = re.compile(r"^Ne réalise pas « .* » : perte, réalisation partielle, intermittente ou non voulue \(à préciser\)\.$", re.S)
BIG = {k: 10000 for k in ("functions", "ports", "flows", "parts", "risks", "dfmea")}
# children first: the order in which the rows of a Space's Diamond are removed
WIPE = ("diamond_part_functions", "diamond_positions", "diamond_flows", "diamond_ports", "diamond_parts", "diamond_dfmea",
        "diamond_risks", "diamond_functions")


def _norm(text):
    return re.sub(r"[^\w]+", " ", str(text or "").lower()).strip()


def present(conn, pid):
    """How much of each section the Space already holds."""
    one = lambda sql: conn.execute(sql, (pid,)).fetchone()[0]  # noqa: E731
    return {"functions": one("SELECT COUNT(*) FROM diamond_functions WHERE project_id = ? AND archived = 0"),
            "ports": one("SELECT COUNT(*) FROM diamond_ports WHERE project_id = ?"),
            "flows": one("SELECT COUNT(*) FROM diamond_flows WHERE project_id = ?"),
            "parts": one("SELECT COUNT(*) FROM diamond_parts WHERE project_id = ?"),
            "risks": one("SELECT COUNT(*) FROM diamond_risks WHERE project_id = ? AND archived = 0"),
            "dfmea": one("SELECT COUNT(*) FROM diamond_dfmea WHERE project_id = ?"),
            "story": one("SELECT COUNT(*) FROM diamond_story_scenes WHERE project_id = ?")}


def _existing(conn, pid):
    """The Space's tree in the file format (refs F<number>) and {ref: function id}."""
    from core.starter_export_more import diamond as export
    functions = export(conn, pid, {}, set(), BIG)["functions"]
    ids = {"F{}".format(r["number"]): r["id"] for r in
           conn.execute("SELECT id, number FROM diamond_functions WHERE project_id = ? AND archived = 0", (pid,))}
    return functions, ids


def _auto_rows(conn, pid):
    """{function id: (ids of the rows the tool wrote by itself, has a row of the team)}."""
    out = {}
    for r in conn.execute("SELECT id, function_id, failure_mode, severity FROM diamond_dfmea WHERE project_id = ?", (pid,)):
        auto, team = out.get(r["function_id"], ([], False))
        if AUTO_RE.match(r["failure_mode"] or "") and r["severity"] is None:
            auto = auto + [r["id"]]
        else:
            team = True
        out[r["function_id"]] = (auto, team)
    return out


def plan(conn, pid, raw, members, mode="add"):
    """-> {"clean": parsed file to apply, "known": {ref: id} of existing functions, "replace_dfmea": row ids to remove,
           "counts": what will be created, "kept": {section: count already in the Space}, "dropped": {what: count}}."""
    from core import starter_diamond as SD
    d = dict(raw.get("diamond") or {})
    have = present(conn, pid) if mode == "add" else {k: 0 for k in SECTIONS}
    if mode == "replace" and not d.get("story"):
        have["story"] = present(conn, pid)["story"]  # the Storyline stays when the file has none
    kept, dropped, known, replace_dfmea = {}, {}, {}, []
    file_functions = [f for f in (d.get("functions") or []) if isinstance(f, dict)]
    if have["functions"]:
        SD.parse({"diamond": {"functions": file_functions}})  # the file's own tree must be sound before it is matched
        existing, ids = _existing(conn, pid)
        by_text = {_norm(f["text"]): f["ref"] for f in existing}
        if file_functions:
            remap = {f.get("ref"): by_text.get(_norm(f.get("text"))) for f in file_functions}
            unmatched = sum(1 for v in remap.values() if v is None)
            if unmatched:
                dropped["functions"] = unmatched
        else:
            remap = {ref: ref for ref in ids}
        kept["functions"] = have["functions"]
        d["functions"] = existing
        known = {f["ref"]: ids[f["ref"]] for f in existing if f["ref"] in ids}
        views = SD._views(SD._functions({"functions": existing}, SD._vocab()))
        ports = {p.get("ref") for p in d.get("ports") or [] if isinstance(p, dict)}
        fn = lambda ref: remap.get(ref)  # noqa: E731
        flows = []
        for fl in d.get("flows") or []:
            if not isinstance(fl, dict):
                continue
            ends = [e if e in ports else fn(e) for e in (fl.get("src"), fl.get("dst"))]
            view = fl.get("view") or "general"
            if all(e in ports or e in views.get(view, ()) for e in ends) and ends[0] != ends[1]:
                flows.append(dict(fl, src=ends[0], dst=ends[1]))
            else:
                dropped["flows"] = dropped.get("flows", 0) + 1
        d["flows"] = flows
        taggable = views["general"] | views["detail"]
        parts = []
        for p in d.get("parts") or []:
            if isinstance(p, dict):
                fns = [fn(r) for r in (p.get("functions") or []) if isinstance(r, str)]
                good = [r for r in fns if r in taggable]
                if len(good) < len(fns):
                    dropped["part_links"] = dropped.get("part_links", 0) + len(fns) - len(good)
                p = dict(p, functions=good)
            parts.append(p)
        d["parts"] = parts
        for name in ("risks", "dfmea"):
            rows = []
            for r in d.get(name) or []:
                if isinstance(r, dict) and r.get("function"):
                    target = fn(r["function"])
                    if target is None:
                        dropped[name + "_links"] = dropped.get(name + "_links", 0) + 1
                    r = dict(r, function=target)
                rows.append(r)
            d[name] = rows
    if have["ports"] or have["flows"]:
        if d.get("ports") or d.get("flows"):
            kept["structure"] = have["ports"] + have["flows"]
        d["ports"], d["flows"] = [], []
    for name in ("parts", "risks", "story"):
        if have[name]:
            if d.get(name):
                kept[name] = have[name]
            d[name] = []
    clean = SD.parse({"diamond": d}, "fr", (), members)
    if have["functions"]:
        clean["functions"] = []  # the tree of the Space stays; its refs are in `known`
        auto = _auto_rows(conn, pid)
        rows = []
        for row in clean["dfmea"]:
            fid = known.get(row["function"]) if row["function"] else None
            ids_auto, team = auto.get(fid, ([], False)) if fid else ([], False)
            if team:
                dropped["dfmea_rows"] = dropped.get("dfmea_rows", 0) + 1
                continue
            replace_dfmea += [i for i in ids_auto if i not in replace_dfmea]
            rows.append(row)
        clean["dfmea"] = rows
    created = {k: len(clean.get(k) or []) for k in SECTIONS}
    return {"clean": clean, "known": known, "replace_dfmea": replace_dfmea, "counts": created, "kept": kept, "dropped": dropped}


def wipe(conn, pid, keep_story):
    """Empties the Diamond of the Space (and its Storyline unless keep_story); returns the counts removed."""
    removed = present(conn, pid)
    if keep_story:
        removed["story"] = 0
    conn.execute("UPDATE diamond_functions SET parent_id = NULL, feedback_to = NULL WHERE project_id = ?", (pid,))
    for table in WIPE + (() if keep_story else ("diamond_story_scenes",)):
        conn.execute("DELETE FROM {} WHERE project_id = ?".format(table), (pid,))
    return removed


def backup(ctx, pid):
    """A full backup of the Space, kept on the server (⚙ Admin → Spaces → Sauvegardes); returns its file name."""
    from core import backup as B
    name, data, _manifest = B.build(ctx, pid, reason="avant-import")
    (B._backup_dir(ctx) / name).write_bytes(data)
    return name


def require_space_admin(ctx, pid):
    from core import permissions
    try:
        permissions.require_project_role(ctx.conn, ctx.user, pid, "admin")
    except ApiError:
        raise ApiError(403, "« Tout remplacer » est réservé aux admins du Space. Correctif : choisissez « Compléter », ou "
                            "demandez à un admin du Space.")
