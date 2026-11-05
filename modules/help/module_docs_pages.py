"""The module documentation in the HeadLamp library (0.60.45, D-O-054): a hub page « Documentation des modules » under the
HeadLamp home and one child page per module, in the order of the descent into the mine. Generated at start-up through the
Dynamite handlers (validated, versioned, journalled); a page edited by a person is left alone, the others follow the text
of module_docs.py. The titles stay the same: they are how the pages are found again.
"""
import json

from .headlamp import _doc, _h, _link, _p, _panel, _t, _table, project_id
from .local_api import LocalApi
from .module_docs import MODULES, MVP_X, MVPS
from .module_docs_refs import ACCESS, REFS

HUB = "Documentation des modules"
GENERATED = "Généré — documentation des modules"
ROUTE = {"help": "#/help", "tools": "#/tools"}


def depth(module):
    return "{:,}".format(module["depth"]).replace(",", "\u202f")  # 1 000 m


def title(module):
    return "Module — " + module["name"]


def _ol(items):
    return {"type": "ordered_list", "items": [[_p(*i) if isinstance(i, tuple) else _p(i)] for i in items]}


def _ref_items(ids):
    items = []
    for rid in ids:
        name, source, year, url, lang, access, why = REFS[rid]
        meta = " — {}{} · {} · {}. ".format(source, ", " + year if year else "", lang, ACCESS["fr"][access])
        items.append((_link(name, url), _t(meta), _t(why)))
    return _ol(items)


def page_body(module):
    fr = module["fr"]
    blocks = [
        _panel("info", _p(_t(fr["role"], "bold"), " À {} m dans la mine. Ouvrir : ".format(depth(module)),
                          _link(module["name"], ROUTE.get(module["key"], "#/" + module["key"])), ".")),
        _h(2, "Pourquoi ce module"), _p(fr["why"]),
        _h(2, "Le besoin couvert"), _p(fr["need"]),
        _h(2, "Pas à pas"), _ol([(_t(t + " — ", "bold"), _t(x)) for t, x in fr["steps"]]),
        _h(2, "De MVP 0 à MVP x"),
        _table(["Boucle du PDP", "Ce qu'on fait ici"], *[[label, text] for label, text in zip(MVPS["fr"], fr["mvps"])]),
        _p(_t(MVP_X["fr"], "italic")),
    ]
    if module["parts"]:
        blocks.append(_h(2, "Les facettes"))
        for part in module["parts"]:
            blocks += [_h(3, part["name"]), _p(part["fr"]), _ref_items(part["refs"])]
    blocks += [_h(2, "Références, de la plus à la moins pertinente"), _ref_items(module["refs"]),
               _panel("note", _p("Les normes et les livres sont payants : le lien mène à leur page publique (résumé, sommaire ou "
                                 "aperçu). Les sources gratuites suffisent pour apprendre la méthode."))]
    return _doc(*blocks)


def hub_body():
    rows = [[m["name"], depth(m) + " m", m["fr"]["role"]] for m in MODULES]
    return _doc(
        _panel("info", _p(_t("Pour apprendre en faisant.", "bold"), " Une page par module, dans l'ordre de la descente dans la mine : "
                          "pourquoi le module existe, le besoin qu'il couvre, le pas à pas, ce qu'on y fait de MVP 0 à MVP x, et ses "
                          "références de la plus à la moins pertinente.")),
        _table(["Module", "Profondeur", "À quoi il sert"], *rows),
        _h(2, "Les pages"), {"type": "children"})


def _generated(ctx, page_id):
    versions = ctx.conn.execute("SELECT author_id, note FROM dynamite_versions WHERE page_id = ?", (page_id,)).fetchall()
    return all(v["author_id"] == ctx.user["id"] and ((v["note"] or "").startswith(GENERATED) or (v["note"] or "") in ("", "Création"))
               for v in versions)


def _put(ctx, api, base, pages, name, parent_id, doc):
    from modules.dynamite import content
    page = pages.get(name)
    if page is None:
        return api.post(base, {"title": name, "parent_id": parent_id, "body": doc})["id"]
    if _generated(ctx, page["id"]):
        full = api.get(base + "/{}".format(page["id"]))["page"]
        if full.get("body") != json.loads(content.validate(doc)):
            api.put(base + "/{}".format(page["id"]), {"title": name, "body": doc, "base_version": full["version"], "note": GENERATED})
    return page["id"]


def ensure(ctx):
    """Create or refresh the hub and the module pages in HeadLamp. Returns {hub, pages: {module key: page id}} or None."""
    pid = project_id(ctx.conn)
    if pid is None:
        return None
    api = LocalApi(ctx)
    base = "/api/dynamite/p/{}/pages".format(pid)
    rows = ctx.conn.execute("SELECT p.id, p.parent_id, v.title FROM dynamite_pages p JOIN dynamite_versions v ON v.page_id = p.id "
                            "AND v.version = p.current_version WHERE p.project_id = ? ORDER BY p.id", (pid,)).fetchall()
    home = next((r["id"] for r in rows if r["parent_id"] is None), None)
    pages = {r["title"]: {"id": r["id"]} for r in rows}
    hub = _put(ctx, api, base, pages, HUB, home, hub_body())
    found = {m["key"]: _put(ctx, api, base, pages, title(m), hub, page_body(m)) for m in MODULES}
    return {"hub": hub, "pages": found}


def ids(conn):
    """The page ids, for the Help screen (without writing anything)."""
    pid = project_id(conn)
    if pid is None:
        return None
    rows = conn.execute("SELECT p.id, v.title FROM dynamite_pages p JOIN dynamite_versions v ON v.page_id = p.id "
                        "AND v.version = p.current_version WHERE p.project_id = ?", (pid,)).fetchall()
    by_title = {r["title"]: r["id"] for r in rows}
    if HUB not in by_title:
        return None
    return {"hub": by_title[HUB], "modules": [{"key": m["key"], "name": m["name"], "role": m["fr"]["role"], "page": by_title.get(title(m))}
                                              for m in MODULES]}
