"""« Tools » catalogue (D-B-065, sections D-B-073): the methods, their wiki
pages and FAQ.

Two sections in the Tools tab: Design (divergent and convergent methods) and
Generator (document references). The explanations live in a
Dynamite space « TOOLS » so everybody can improve them like a wiki (versions,
history, comments). At start-up the space and any missing page are created.
A page still in its generated form (every version written by the start-up
account with a generated note) is refreshed when the catalogue changes, and
removed when its method leaves the catalogue; a page edited by someone is
never touched. Every active account is an editor of TOOLS.
"""
from core import audit, permissions
from core.errors import ApiError

from modules.help.gtd import _b, _ol, _ul
from modules.help.headlamp import _doc, _h, _link, _p, _panel

from .methods_convergent import CONVERGENT, REFERENCE
from .methods_divergent import DIVERGENT, RETIRED

KEY = "TOOLS"
NAME = "Tools — Methods et FAQ"
DESCRIPTION = "Boîte à outils de conception : chaque méthode et outil a sa page et sa FAQ, modifiables comme un wiki."
HUB = "Tools — Boîte à outils"
GENERATED = "Généré — catalogue Tools"  # note of every version written by the catalogue
METHODS = DIVERGENT + CONVERGENT + REFERENCE
FAMILY = {"divergent": "Divergent — ouvrir, générer des idées", "convergent": "Convergent — évaluer, choisir",
          "reference": "Référence documentaire"}
# Tools sections (D-B-073): which families each one shows
SECTIONS = {"design": ("Design", ["divergent", "convergent"]), "generator": ("Generator", ["reference"])}
TOOL_LABEL = {"ideation": "Ideation", "pugh": "Pugh Matrix", "kt": "Kepner-Tregoe", "codex": "Reference Generator"}
RENAMED = {"Generator": "Reference Generator",  # old page title -> new (D-B-073)
           # D-B-085: technical names in English
           "Matrice de Pugh": "Pugh Matrix", "Kepner-Tregoe (analyse de décision)": "Kepner-Tregoe (Decision Analysis)",
           "Storytelling (mise en récit)": "Storytelling", "Carte mentale (mind mapping)": "Mind Map"}
OLD_NOTES = ("", "Création", "Modèle de base du projet", "Boîte à outils (D-B-065)")  # notes of generated versions (creation, 0.25 catalogue)


def faq_title(m):
    return "FAQ — " + m["name"]


def method_page(m):
    blocks = [_panel("info", _p(_b(m["tagline"]))), _h(2, "À quoi ça sert"), _p(m["goal"]),
              _h(2, "Quand l'utiliser"), _p(m["when"]), _h(2, "Déroulement"), _ol(*m["steps"]),
              _h(2, "Qui et combien de temps"), _p(m["roles"]), _h(2, "Pièges à éviter"), _ul(*m["pitfalls"]),
              _h(2, "Exemple"), _p(m["example"])]
    if m["tool"]:
        blocks.append(_panel("success", _p("Outil dans la plateforme : ", _link(TOOL_LABEL[m["tool"]], "#/tools"),
                                           " (onglet Tools, choisissez le Space).")))
    blocks.append(_p("Questions fréquentes : voir la sous-page « ", _b(faq_title(m)), " ». Cette page est un wiki : "
                     "« Modifier » pour l'améliorer."))
    return _doc(*blocks)


def faq_page(m):
    blocks = [_p("Questions fréquentes sur ", _b(m["name"]), ". Ajoutez les vôtres (« Modifier ») : la page est "
                 "versionnée.")]
    for q, a in m["faq"]:
        blocks += [_h(2, q), _p(a)]
    return _doc(*blocks)


def hub_page():
    blocks = [_panel("info", _p("Deux sections dans l'onglet Tools : ", _b("Design"), " (diverger : beaucoup d'idées "
                                "sans juger ; puis converger : évaluer et choisir avec les needs et requirements "
                                "Goldmine) et ", _b("Generator"), " (références documentaires du PDP).")), {"type": "toc"}]
    for key, (label, families) in SECTIONS.items():
        blocks.append(_h(2, "Tools → " + label))
        for family in families:
            items = [(_b(m["name"]), " — " + m["tagline"]) for m in METHODS if m["family"] == family]
            if len(families) > 1:
                blocks.append(_p(_b(FAMILY[family])))
            blocks.append(_ul(*items))
    blocks += [_h(2, "Pages"), {"type": "children"}]
    return _doc(*blocks)


def project_id(conn):
    """The Space of the method pages: TOOLS on an installation made before 0.60.41, else DEMO (D-O-050)."""
    from modules.help import reference
    return reference.space(conn, KEY)


def _generated(ctx, page_id):
    """True while every version was written by the start-up account with a generated note."""
    rows = ctx.conn.execute("SELECT author_id, note FROM dynamite_versions WHERE page_id = ?", (page_id,)).fetchall()
    return all(r["author_id"] == ctx.user["id"] and ((r["note"] or "") in OLD_NOTES or (r["note"] or "").startswith(GENERATED))
               for r in rows)


def _refresh(ctx, api, base, page_id, title, body):
    """Rewrite a page still in its generated form when its title or content changed."""
    import json
    from modules.dynamite import content
    page = api.get(base + "/{}".format(page_id))["page"]
    same = page["title"] == title and page.get("body") == json.loads(content.validate(body))
    if same or not _generated(ctx, page_id):
        return
    api.put(base + "/{}".format(page_id), {"title": title, "body": body, "base_version": page["version"], "note": GENERATED})


def _retire(ctx, api, base, pages, title):
    """Remove a retired method page and its FAQ, only if nobody edited them."""
    by_title = {p["title"]: p for p in pages}
    page = by_title.get(title)
    faq = by_title.get("FAQ — " + title)
    for p in (faq, page):
        if p is None:
            continue  # already gone (e.g. the FAQ removed by an earlier start while the page still had children)
        if not _generated(ctx, p["id"]):
            return
        if ctx.conn.execute("SELECT 1 FROM dynamite_pages WHERE parent_id = ?", (p["id"],)).fetchone():
            return
        api.call("DELETE", base + "/{}".format(p["id"]))


def ensure(ctx):
    """Create the TOOLS space, its hub and every missing method / FAQ page; everyone is an editor."""
    from modules.help import reference
    pid = reference.ensure(ctx, KEY)  # 0.60.41 (D-O-050): DEMO, or TOOLS on an older installation
    api = local_api(ctx)
    base = "/api/dynamite/p/{}/pages".format(pid)
    pages = api.get(base)["pages"]
    for title in RETIRED:
        _retire(ctx, api, base, pages, title)
    pages = api.get(base)["pages"]
    titles = {p["title"]: p for p in pages}
    for old, new in RENAMED.items():
        for a, b in ((old, new), (faq_title({"name": old}), faq_title({"name": new}))):
            if a in titles and b not in titles:
                titles[b] = titles.pop(a)
    hub = titles.get(HUB)
    if hub is None:
        home = next((p for p in pages if not p.get("parent_id")), None)
        own = ctx.conn.execute("SELECT key FROM projects WHERE id = ?", (pid,)).fetchone()["key"] == KEY
        if home is not None and own and home["title"] != HUB:  # the TOOLS Space of an older installation: its home is the hub
            page = api.get(base + "/{}".format(home["id"]))["page"]
            api.put(base + "/{}".format(home["id"]), {"title": HUB, "body": hub_page(), "base_version": page["version"],
                                                     "note": GENERATED})
            hub = home
        else:  # 0.60.41 (D-O-050): in DEMO, a page under the home -- never the home itself
            made = api.post(base, {"title": HUB, "parent_id": home["id"] if home and not own else None, "body": hub_page()})
            hub = made.get("page") or made
    _refresh(ctx, api, base, hub["id"], HUB, hub_page())
    for m in METHODS:
        page = titles.get(m["name"])
        if page is None:
            made = api.post(base, {"title": m["name"], "parent_id": hub["id"], "body": method_page(m)})
            page = made.get("page") or made
        else:
            _refresh(ctx, api, base, page["id"], m["name"], method_page(m))
        faq = titles.get(faq_title(m))
        if faq is None:
            api.post(base, {"title": faq_title(m), "parent_id": page["id"], "body": faq_page(m)})
        else:
            _refresh(ctx, api, base, faq["id"], faq_title(m), faq_page(m))
    ctx.conn.execute("INSERT OR IGNORE INTO memberships (user_id, project_id, role) "
                     "SELECT id, ?, 'editor' FROM users WHERE is_active = 1 AND is_admin = 0", (pid,))
    return pid


def local_api(ctx):
    from modules.help.local_api import LocalApi
    return LocalApi(ctx)


def api_catalog(ctx):
    """Sections, methods with their wiki page ids, examples; joins the caller to TOOLS (editor) if needed."""
    pid = project_id(ctx.conn)
    if pid is None:
        raise ApiError(404, "Le Space Tools n'existe pas encore. Correctif : redémarrez le serveur.")
    if permissions.project_role(ctx.conn, ctx.user, pid) is None:
        ctx.conn.execute("INSERT INTO memberships (user_id, project_id, role) VALUES (?, ?, 'editor')", (ctx.user["id"], pid))
        audit.log_action(ctx.conn, ctx.user["id"], "tools_joined", "project", pid, None, ctx.ip)
    ids = {r["title"]: r["id"] for r in ctx.conn.execute("SELECT id, title FROM dynamite_pages WHERE project_id = ?", (pid,))}
    return {"space": KEY, "families": FAMILY, "hub_page": ids.get(HUB),
            "sections": {k: {"label": v[0], "families": v[1]} for k, v in SECTIONS.items()},
            "methods": [{"key": m["key"], "name": m["name"], "family": m["family"], "tagline": m["tagline"],
                         "tool": m["tool"], "page_id": ids.get(m["name"]), "faq_id": ids.get(faq_title(m))}
                        for m in METHODS]}
