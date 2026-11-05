"""Controlled lists of the Testing base (D-B-082): equipment, locations, product functions; acronyms and definitions
of the tool (D-A-037, BDC pages and Word exports: glossary.py).

One central list per kind (testing_lists, rattachée au Space TESTING). Tests pick their location (one), equipment
(several) and product functions (several) from them; Goldmine requirements pick their functions. Only a manager
of TESTING (« Admin du Space ») or an administrator adds, renames or deactivates an entry -- a used entry is never
deleted, only deactivated (it stays on the items that have it, it is no longer offered). The product functions are
also published as a Dynamite page of the « Base de connaissances (BDC) » (DEMO), regenerated from the list.
"""
import json
import re

from core import audit, db, permissions
from core.errors import ApiError

from .data_lists import EQUIPMENT, FUNCTIONS, LOCATIONS

KINDS = {"equipment": "Test Equipment", "location": "Test Location", "function": "Product Function",
         "acronym": "Acronym", "definition": "Definition"}
GLOSSARY = ("acronym", "definition")  # case kept in the code (SoC, DoD, Li-ion), unique whatever the case
CODE_RE = {"equipment": re.compile(r"^EQ-[A-Z0-9]{2,12}$"), "location": re.compile(r"^[A-Z0-9]{2,12}$"),
           "function": re.compile(r"^F\d{1,3}(\.\d{1,2})?$"),
           "acronym": re.compile(r"^[A-Za-z0-9][A-Za-z0-9/&.\-]{0,15}$"),
           "definition": re.compile(r"^[A-Za-z0-9\[][A-Za-z0-9 /&().,'\-\[\]]{1,79}$")}
CODE_HINT = {"equipment": "EQ- suivi de 2 à 12 lettres ou chiffres (ex. EQ-VIB2)", "location": "2 à 12 lettres ou "
             "chiffres majuscules (ex. LAB)", "function": "F suivi de 1 à 3 chiffres, sous-fonction permise (ex. F12, F35.1)",
             "acronym": "1 à 16 lettres, chiffres, / & . - sans espace (ex. RoHS, CdCF, IEC)",
             "definition": "terme anglais de 2 à 80 caractères (ex. Functional Tree)"}
DETAIL_KEYS = ("primary", "supporting", "notes")
GLOSSARY_KEYS = ("fr", "source", "std_term", "std_def")  # French equivalent, source, standard term it replaces
BDC_TITLE = "Product Function Structure (F-XX)"
GENERATED = "Généré — liste des fonctions du produit"  # version note identifying the generated page (kept as is)


def seed(conn, pid):
    """Missing entries of the default lists (never overwrites what a manager changed)."""
    now = db.utc_now()
    have = {(r["kind"], r["code"]) for r in conn.execute("SELECT kind, code FROM testing_lists")}
    rows = [("location", c, l, "", "") for c, l in LOCATIONS] + [("equipment", c, l, cat, "") for c, l, cat in EQUIPMENT]
    rows += [("function", c, n, "", json.dumps(dict(zip(DETAIL_KEYS, (p, s, notes))), ensure_ascii=False))
             for c, n, p, s, notes in FUNCTIONS]
    from .data_acronyms import ACRONYMS
    from .data_definitions import DEFINITIONS
    rows += [("acronym", a, text, dom, json.dumps({"fr": fr}, ensure_ascii=False))
             for dom, items in ACRONYMS.items() for a, text, fr in items]
    rows += [("definition", term, text, dom, json.dumps(dict(zip(GLOSSARY_KEYS, (fr, src, t311, d311))), ensure_ascii=False))
             for dom, items in DEFINITIONS.items() for term, text, fr, src, t311, d311 in items]
    for pos, (kind, code, label, category, details) in enumerate(rows):
        if (kind, code) not in have:
            conn.execute("INSERT INTO testing_lists (project_id, kind, code, label, category, details, position, active, "
                         "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
                         (pid, kind, code, label, category, details, pos, now, now))


def entries(conn, kind=None, active_only=False):
    try:
        sql = "SELECT * FROM testing_lists" + (" WHERE kind = ?" if kind else "") + " ORDER BY kind, code COLLATE NOCASE"
        rows = conn.execute(sql, (kind,) if kind else ()).fetchall()
    except Exception:  # before the migration (tests of old lots)
        return []
    return [r for r in rows if r["active"] or not active_only]


def labels(conn, kind):
    return {r["code"]: r["label"] for r in entries(conn, kind)}


def split(value):
    out = []
    for part in re.split(r"[\s,;]+", str(value or "").upper()):
        if part and part not in out:
            out.append(part)
    return out


def check(conn, kind, value, previous="", single=False):
    """Normalised value ('A, B') or ApiError: every code must be an active entry of the list (a code already on
    the item and since deactivated may stay)."""
    codes = split(value)
    if single and len(codes) > 1:
        raise ApiError(400, "Un seul {} par test.".format(KINDS[kind].lower()))
    known = {r["code"]: r["active"] for r in entries(conn, kind)}
    if not known:
        return ", ".join(codes)
    old = set(split(previous))
    unknown = [c for c in codes if c not in known]
    if unknown:
        raise ApiError(400, "{} inconnu(s) : {}. Correctif : choisissez dans la liste centrale (Testing → Listes) ; "
                            "seul un Admin du Space TESTING peut l'allonger.".format(KINDS[kind], ", ".join(unknown)))
    retired = [c for c in codes if not known[c] and c not in old]
    if retired:
        raise ApiError(400, "{} désactivé(s) : {}. Correctif : choisissez une entrée active.".format(
            KINDS[kind], ", ".join(retired)))
    return ", ".join(codes)


def public(row):
    item = {k: row[k] for k in ("id", "kind", "code", "label", "category", "position", "updated_at")}
    item["active"] = bool(row["active"])
    item["details"] = json.loads(row["details"]) if row["details"] else {}
    return item


def _usage(conn):
    """{(kind, code): count} over the tests (and requirements for the functions)."""
    count = {}
    for r in conn.execute("SELECT location, equipment, functions FROM testing_tests"):
        for kind, value in (("location", r["location"]), ("equipment", r["equipment"]), ("function", r["functions"])):
            for code in split(value):
                count[(kind, code)] = count.get((kind, code), 0) + 1
    try:
        for r in conn.execute("SELECT functions FROM agile_requirements WHERE functions != ''"):
            for code in split(r["functions"]):
                count[("function", code)] = count.get(("function", code), 0) + 1
    except Exception:
        pass
    return count


def can_manage(conn, user):
    from .catalog import project_id
    pid = project_id(conn)
    return pid is not None and permissions.is_project_manager(conn, user, pid)


def api_lists(ctx):
    usage = _usage(ctx.conn)
    items = []
    for r in entries(ctx.conn):
        item = public(r)
        item["used"] = usage.get((r["kind"], r["code"]), 0)
        items.append(item)
    page = ctx.conn.execute("SELECT p.id, pr.key FROM dynamite_pages p JOIN projects pr ON pr.id = p.project_id "
                            "WHERE p.title = ?", (BDC_TITLE,)).fetchone()
    from .glossary import page_links
    return {"kinds": KINDS, "items": items, "can_manage": can_manage(ctx.conn, ctx.user), "bdc_title": BDC_TITLE,
            "bdc_href": "#/dynamite/{}/page/{}".format(page["key"], page["id"]) if page else None,
            "glossary_pages": page_links(ctx.conn)}


def _require_manager(ctx):
    from .catalog import require_space
    pid = require_space(ctx.conn)
    if not permissions.is_project_manager(ctx.conn, ctx.user, pid):
        raise ApiError(403, "Listes centrales : réservé aux Admin du Space TESTING et aux administrateurs.")
    return pid


def _fields(body, kind):
    label = str(body.get("label") or "").strip()
    limit = 600 if kind == "definition" else 160
    if not label or len(label) > limit:
        raise ApiError(400, "{} obligatoire, {} caractères au maximum (reçu : {}).".format(
            "Definition" if kind == "definition" else "Libellé", limit, len(label)))
    category = str(body.get("category") or "").strip()[:80]
    details = ""
    if kind in GLOSSARY:
        raw = body.get("details") or {}
        details = json.dumps({k: str(raw.get(k) or "").strip()[:400] for k in GLOSSARY_KEYS}, ensure_ascii=False)
    if kind == "function":
        raw = body.get("details") or {}
        details = json.dumps({k: str(raw.get(k) or "").strip()[:400] for k in DETAIL_KEYS}, ensure_ascii=False)
    return label, category, details


def api_create(ctx):
    pid = _require_manager(ctx)
    kind = ctx.body.get("kind")
    if kind not in KINDS:
        raise ApiError(400, "Liste « {} » inconnue : {}.".format(str(kind)[:20], ", ".join(KINDS)))
    code = " ".join(str(ctx.body.get("code") or "").split())
    code = code if kind in GLOSSARY else code.upper()
    if not CODE_RE[kind].match(code):
        raise ApiError(400, "Code « {} » invalide : {}.".format(code[:30], CODE_HINT[kind]))
    if ctx.conn.execute("SELECT 1 FROM testing_lists WHERE kind = ? AND code = ? COLLATE NOCASE", (kind, code)).fetchone():
        raise ApiError(409, "Le code {} existe déjà dans cette liste (réactivez-le au besoin).".format(code))
    label, category, details = _fields(ctx.body, kind)
    now = db.utc_now()
    pos = ctx.conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM testing_lists").fetchone()[0]
    new_id = ctx.conn.execute("INSERT INTO testing_lists (project_id, kind, code, label, category, details, position, "
                              "active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
                              (pid, kind, code, label, category, details, pos, now, now)).lastrowid
    audit.log_action(ctx.conn, ctx.user["id"], "testing_list_add", "testing_list", new_id, {"kind": kind, "code": code}, ctx.ip)
    after_change(ctx, kind)
    return {"id": new_id, "code": code}


def api_update(ctx):
    _require_manager(ctx)
    row = ctx.conn.execute("SELECT * FROM testing_lists WHERE id = ?", (int(ctx.params["lid"]),)).fetchone()
    if row is None:
        raise ApiError(404, "Entrée de liste introuvable.")
    label, category, details = _fields(dict({"label": row["label"], "category": row["category"],
                                             "details": json.loads(row["details"] or "{}")}, **ctx.body), row["kind"])
    active = 1 if ctx.body.get("active", bool(row["active"])) else 0
    ctx.conn.execute("UPDATE testing_lists SET label = ?, category = ?, details = ?, active = ?, updated_at = ? WHERE id = ?",
                     (label, category, details, active, db.utc_now(), row["id"]))
    audit.log_action(ctx.conn, ctx.user["id"], "testing_list_update", "testing_list", row["id"],
                     {"kind": row["kind"], "code": row["code"], "active": bool(active)}, ctx.ip)
    after_change(ctx, row["kind"])
    return {"ok": True}


# --------------------------------------------------------------------------
# « Base de connaissances (BDC) » page of the product functions
# --------------------------------------------------------------------------
def after_change(ctx, kind):
    if kind == "function" or kind in GLOSSARY:
        from core.startup import StartupContext
        admin = ctx.conn.execute("SELECT * FROM users WHERE is_admin = 1 AND is_active = 1 ORDER BY id LIMIT 1").fetchone()
        if admin is None:
            return
        sctx = StartupContext(ctx.conn, admin, getattr(ctx, "data_dir", None), getattr(ctx, "config", {}))
        if kind == "function":  # written as the platform, like at start-up (the manager may not edit DEMO)
            ensure_bdc_page(sctx)
        else:
            from . import glossary
            glossary.ensure_pages(sctx)


def bdc_page(rows):
    from modules.help.gtd import _b, _ul
    from modules.help.headlamp import _doc, _h, _link, _p, _panel, _table
    active = [public(r) for r in rows if r["active"]]
    return _doc(
        _panel("info", _p(_b("Product function structure"), " — the functions of the functional analysis (F-XX). Every "
                          "Goldmine requirement and every Testing test belongs to one or more functions; two different "
                          "tests can thus verify the same requirement on two different functions.")),
        _panel("warning", _p("Page generated from the central list (", _link("Testing → Listes", "#/testing/lists"),
                             "): edit it there (TESTING Space admins), the page follows. A manual edit here stops the "
                             "automatic update.")),
        _h(2, "Function Allocation to Subsystems"),
        _table(["Function ID", "Function Name", "Primary Component(s)", "Supporting Components", "Implementation Notes"],
               *[[_b(f["code"]), f["label"], f["details"].get("primary", ""), f["details"].get("supporting", ""),
                  f["details"].get("notes", "")] for f in active]),
        _h(2, "Key"),
        _ul("Primary Component(s): the subsystem or part mainly responsible for the function.",
            "Supporting Components: other elements that enable or support the function."),
        _h(2, "Use"),
        _ul("Goldmine: « Functions » field of the requirement record (filter and Word export).",
            "Testing: « Functions » field of each test; tests of the same function come first in « Test Procedure »."))


def ensure_bdc_page(ctx):
    """Create / refresh the product functions page under « Base de connaissances (BDC) » (DEMO)."""
    import json as _json
    from modules.dynamite import content
    from modules.help import gtd
    from modules.help.local_api import LocalApi
    pid = gtd.project_id(ctx.conn)
    rows = entries(ctx.conn, "function")
    if pid is None or not rows:
        return False
    api = LocalApi(ctx)
    base = "/api/dynamite/p/{}/pages".format(pid)
    pages = api.get(base)["pages"]
    hub = next((p for p in pages if p["title"] == gtd.HUB), None)
    page = next((p for p in pages if p["title"] == BDC_TITLE), None)
    body = bdc_page(rows)
    if page is None:
        root = hub or next((p for p in pages if not p.get("parent_id")), None)
        api.post(base, {"title": BDC_TITLE, "parent_id": root["id"] if root else None, "body": body})
        return True
    versions = ctx.conn.execute("SELECT author_id, note FROM dynamite_versions WHERE page_id = ?", (page["id"],)).fetchall()
    if not all(v["author_id"] == ctx.user["id"] and ((v["note"] or "").startswith(GENERATED) or (v["note"] or "") in ("", "Création"))
               for v in versions):
        return False  # edited by hand: left alone
    full = api.get(base + "/{}".format(page["id"]))["page"]
    if full["title"] == BDC_TITLE and full.get("body") == _json.loads(content.validate(body)):
        return False
    api.put(base + "/{}".format(page["id"]), {"title": BDC_TITLE, "body": body, "base_version": full["version"],
                                             "note": GENERATED})
    return True
