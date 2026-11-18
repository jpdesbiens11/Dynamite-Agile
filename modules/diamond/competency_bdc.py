"""Diamond · the BDC pages of the competencies (0.60.116, D-O-129).

Under « Base de connaissances (BDC) » (DEMO, every installation): a hub « Compétences de l'équipe (Diamond) » and one page
per competency of the catalogue -- the professional background it asks for, the general training, the tools, the
knowledge taken for granted and the artifacts it usually delivers. The summary of « Compétences et équipe » links each
competency to its page. Pages are written through the Dynamite API (validated, versioned, journalled), regenerated after
each change of the catalogue, and left alone once someone edited them by hand (like the glossary, D-A-037). A page is found
by the code at the end of its title, « … (THERM) »: renaming a competency renames its page.
"""
import json
import re

from . import competencies as CP
from . import data_competencies as DC

HUB = "Compétences de l'équipe (Diamond)"
GENERATED = "Généré — catalogue des compétences"
TITLE = "Compétence — {name} ({code})"
CODE_AT_END = re.compile(r"\(([A-Z][A-Z0-9]{1,7})\)$")


def _t(text, *marks):
    node = {"type": "text", "text": text}
    if marks:
        node["marks"] = list(marks)
    return node


def _p(*nodes):
    return {"type": "paragraph", "content": [n if isinstance(n, dict) else _t(n) for n in nodes]}


def _items(text):
    parts = [x.strip() for x in str(text or "").split(";") if x.strip()]
    if not parts:
        return _p(_t("À compléter par l'équipe.", "italic"))
    return {"type": "bullet_list", "items": [[_p(x)] for x in parts]}


def hub_page():
    return {"type": "doc", "content": [
        _p("Les compétences dont une équipe a besoin pour développer les briques technologiques d'un produit. Dans Diamond, "
           "chaque ligne de l'arbre fonctionnel qui aboutit à une brique reçoit une note de 1 à 5 par compétence ; la page "
           "« Compétences et équipe » en fait la somme et aide à décider qui embaucher ou réunir."),
        _p("Chaque page décrit le profil professionnel, la formation, les outils, les connaissances supposées et les livrables "
           "typiques de la compétence. Le catalogue est commun à tous les Spaces ; un administrateur l'allonge dans Diamond → "
           "Compétences et équipe → Catalogue."),
        {"type": "children"}]}


def competency_page(c):
    d = c.get("details") or {}
    blocks = [{"type": "panel", "kind": "info", "content": [_p(_t(c["name"], "bold"), " — " + (c["summary"] or "")),
                                                           _p("Code : {} · icône : {}{}".format(c["code"], c["icon"], "" if c["active"]
                                                              else " · désactivée dans le catalogue"))]}]
    for key in DC.DETAIL_KEYS:
        blocks += [{"type": "heading", "level": 2, "content": [_t(DC.DETAIL_LABELS[key])]}, _items(d.get(key))]
    blocks.append(_p(_t("Page générée depuis le catalogue des compétences de Diamond. Modifiez-la librement : une fois modifiée à "
                        "la main, elle n'est plus régénérée.", "italic")))
    return {"type": "doc", "content": blocks}


def _generated_only(ctx, page_id):
    versions = ctx.conn.execute("SELECT author_id, note FROM dynamite_versions WHERE page_id = ?", (page_id,)).fetchall()
    return all(v["author_id"] == ctx.user["id"] and ((v["note"] or "").startswith(GENERATED) or (v["note"] or "") in ("", "Création"))
               for v in versions)


def _write(ctx, api, base, page, parent, title, body):
    from modules.dynamite import content
    if page is None:
        api.post(base, {"title": title, "parent_id": parent, "body": body})
        return True
    if not _generated_only(ctx, page["id"]):
        return False  # edited by hand: left alone
    full = api.get(base + "/{}".format(page["id"]))["page"]
    if full.get("body") == json.loads(content.validate(body)) and full.get("title") == title:
        return False
    api.put(base + "/{}".format(page["id"]), {"title": title, "body": body, "base_version": full["version"], "note": GENERATED})
    return True


def ensure_pages(ctx):
    """The hub and one page per competency, under « Base de connaissances (BDC) » (DEMO). ctx: a StartupContext."""
    from modules.help import gtd
    from modules.help.local_api import LocalApi
    pid = CP.host_id(ctx.conn)
    if pid is None:
        return False
    api = LocalApi(ctx)
    base = "/api/dynamite/p/{}/pages".format(pid)
    pages = api.get(base)["pages"]
    bdc = next((p for p in pages if p["title"] == gtd.HUB), None) or next((p for p in pages if not p.get("parent_id")), None)
    hub = next((p for p in pages if p["title"] == HUB), None)
    changed = False
    if hub is None:
        made = api.post(base, {"title": HUB, "parent_id": bdc["id"] if bdc else None, "body": hub_page()})
        hub, changed = (made.get("page") or made), True
    mine = {}
    for p in pages:
        m = CODE_AT_END.search(p["title"])
        if m and p.get("parent_id") == hub["id"]:
            mine[m.group(1)] = p
    for c in CP.catalog(ctx.conn):
        changed = _write(ctx, api, base, mine.get(c["code"]), hub["id"], TITLE.format(name=c["name"], code=c["code"]),
                         competency_page(c)) or changed
    return changed


def ensure(ctx):
    """Start-up (help.on_startup, after the BDC hub): the default catalogue, then its pages."""
    CP.seed(ctx.conn)
    return ensure_pages(ctx)


def after_change(ctx):
    """After a change of the catalogue, written as the platform (as at start-up), like the glossary (D-A-037)."""
    from core.startup import StartupContext
    admin = ctx.conn.execute("SELECT * FROM users WHERE is_admin = 1 AND is_active = 1 ORDER BY id LIMIT 1").fetchone()
    if admin is None:
        return False
    return ensure_pages(StartupContext(ctx.conn, admin, getattr(ctx, "data_dir", None), getattr(ctx, "config", {})))


def page_links(conn):
    """{code: href of its BDC page, « _hub »: href of the hub}."""
    pid = CP.host_id(conn)
    if pid is None:
        return {}
    hub = conn.execute("SELECT p.id, pr.key FROM dynamite_pages p JOIN projects pr ON pr.id = p.project_id WHERE p.project_id = ? "
                       "AND p.title = ?", (pid, HUB)).fetchone()
    if hub is None:
        return {}
    href = "#/dynamite/{}/page/{}".format(hub["key"], "{}")
    out = {"_hub": href.format(hub["id"])}
    for r in conn.execute("SELECT id, title FROM dynamite_pages WHERE project_id = ? AND parent_id = ?", (pid, hub["id"])):
        m = CODE_AT_END.search(r["title"])
        if m:
            out[m.group(1)] = href.format(r["id"])
    return out
