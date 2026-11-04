"""Definitions and acronyms of the platform (D-A-037).

Source of truth: the central lists « definition » and « acronym » (lists.py, Testing → Listes, edited by the TESTING
Space admins and the administrators). From them:
  * three Dynamite pages of the « Base de connaissances (BDC) » (HEADLAMP): Definitions, Acronyms and the French
    translation of the English terms (D-B-085) -- regenerated after every change, left alone once edited by hand;
  * the « Definitions and Conventions » and « Acronyms » sections of the Word exports of Goldmine and Testing.
"""
import json

from . import lists
from .data_definitions import CONVENTIONS

DEF_TITLE = "Definitions"
ACR_TITLE = "Acronyms"
TR_TITLE = "Traduction des termes techniques (EN → FR)"
GENERATED = "Généré — glossaire"  # version note of the generated pages
NOMENCLATURE = "Nomenclature (standard vs. team)"
TEXT = {
    "en": {"conv": "Conventions", "nom": "Nomenclature (standard vs. team)", "attrs": "Document Attributes",
           "terms": "Terms", "acr": "Acronyms", "attr": "Attribute",
           "nom_head": ["Standard Term", "Definition (per the standard)", "Term Used in This Document"],
           "term_head": ["Term", "Definition"], "acr_head": ["Acronym", "Definition"]},
    "fr": {"conv": "Conventions", "nom": "Nomenclature (norme vs. équipe)", "attrs": "Attributs du document",
           "terms": "Termes", "acr": "Acronymes", "attr": "Attribut",
           "nom_head": ["Standard Term", "Definition (per the standard)", "Team Term"],
           "term_head": ["Term", "Definition", "Équivalent FR"], "acr_head": ["Acronym", "Definition", "Équivalent FR"]},
}


def _key(text):
    return text.casefold().lstrip("[")


def items(conn, kind):
    """Active entries of a glossary list, alphabetical whatever the case (SoC between SOP and SRR)."""
    return sorted((lists.public(r) for r in lists.entries(conn, kind, active_only=True)), key=lambda x: _key(x["code"]))


def std_term(d):
    """The term of a cited standard that this team term replaces ("" if none)."""
    return d["details"].get("std_term") or ""


def std_def(d):
    return d["details"].get("std_def") or ""


def nomenclature(defs):
    """Team terms replacing a term of a cited standard, in the order of the list, not alphabetical."""
    return sorted((d for d in defs if std_term(d)), key=lambda d: d["position"])


# --------------------------------------------------------------------------
# Word exports (Goldmine, Testing)
# --------------------------------------------------------------------------
def docx_sections(conn, d, lang, heading, def_rows):
    """Definitions and Conventions (conventions, nomenclature of the standard terms, attributes of the document, terms) and
    Acronyms, from the central lists -- inserted in every Word export."""
    T = TEXT[lang]
    defs, acr = items(conn, "definition"), items(conn, "acronym")
    fr = lang == "fr"
    out = [d.heading(1, heading), d.heading(2, T["conv"])] + [d.para(p) for p in CONVENTIONS]
    nom = nomenclature(defs)
    if nom:
        out += [d.heading(2, T["nom"]), d.table(T["nom_head"], [[std_term(x), std_def(x),
                                                                 x["code"]] for x in nom], [2000, 4400, 3000])]
    out += [d.heading(2, T["attrs"]), d.table([T["attr"], "Description"], [list(r) for r in def_rows], [2200, 7200])]
    rows = [[x["code"], x["label"]] + ([x["details"].get("fr", "")] if fr else []) for x in defs if x not in nom]
    if rows:
        out += [d.heading(2, T["terms"]), d.table(T["term_head"], rows, [2400, 5000, 2000] if fr else [2600, 6800])]
    if acr:
        out += [d.heading(1, T["acr"]), d.table(T["acr_head"], [[x["code"], x["label"]] + (
            [x["details"].get("fr", "")] if fr else []) for x in acr], [1500, 5200, 2700] if fr else [1600, 7800])]
    return out


# --------------------------------------------------------------------------
# « Base de connaissances (BDC) » pages
# --------------------------------------------------------------------------
def _intro(what):
    from modules.help.headlamp import _link, _p, _panel
    return _panel("warning", _p("Page générée depuis la liste centrale « {} » (".format(what),
                                _link("Testing → Listes", "#/testing/lists"), ") : modifiez-la là (Admin du Space TESTING), "
                                "la page et les exports Word suivent. Une modification faite ici arrête la mise à jour."))


def definitions_page(defs):
    from modules.help.gtd import _b
    from modules.help.headlamp import _doc, _h, _p, _panel, _table
    nom = nomenclature(defs)
    blocks = [_panel("info", *[_p(t) for t in CONVENTIONS]), _intro("Definition")]
    if nom:
        blocks += [_h(2, NOMENCLATURE), _table(TEXT["fr"]["nom_head"],
                                               *[[std_term(x), std_def(x), _b(x["code"])] for x in nom])]
    groups = {}
    for x in defs:
        if x not in nom:
            groups.setdefault(x["category"] or "General", []).append(x)
    for cat in sorted(groups):
        blocks += [_h(2, cat), _table(["Term", "Definition", "Source"],
                                      *[[_b(x["code"]), x["label"], x["details"].get("source", "")] for x in groups[cat]])]
    blocks.append(_p("Traduction française des termes : page « {} ».".format(TR_TITLE)))
    return _doc(*blocks)


def acronyms_page(acr):
    from modules.help.gtd import _b
    from modules.help.headlamp import _doc, _h, _p, _table
    blocks = [_p(_b("{} acronymes".format(len(acr))), " de l'outil et du domaine du produit. Un acronyme à plusieurs sens les sépare par « ; »."), _intro("Acronym"),
              _h(2, "A – Z"), _table(["Acronym", "Definition", "Domain"],
                                     *[[_b(x["code"]), x["label"], x["category"]] for x in acr])]
    return _doc(*blocks)


def translation_page(defs, acr):
    from modules.agile import vocab
    from modules.help.gtd import _b
    from modules.help.headlamp import _doc, _h, _p, _panel, _table
    from .data_lists import EQUIPMENT
    from .legacy import EQUIPMENT_FR
    blocks = [_panel("info", _p(_b("Les termes techniques restent en anglais"), " dans toute la plateforme (D-B-085) : "
                                "champs, statuts, types, workflows, catalogues. Cette page donne leur équivalent français "
                                "pour qui ne les connaît pas ; leur sens exact est dans les pages « {} » et « {} »."
                                .format(DEF_TITLE, ACR_TITLE))), _intro("Definition / Acronym"),
              _h(2, "Termes (Definitions)"),
              _table(["English", "Français"], *[[_b(x["code"]), x["details"].get("fr", "")] for x in defs
                                                if x["details"].get("fr")]),
              _h(2, "Acronymes"),
              _table(["Acronym", "English", "Français"], *[[_b(x["code"]), x["label"], x["details"]["fr"]] for x in acr
                                                            if x["details"].get("fr")]),
              _h(2, "Statuts, types et workflows de la plateforme")]
    platform = {}
    for table in (vocab.STATUS_EN, vocab.TYPE_EN, vocab.WORKFLOW_EN):
        for french, english in table.items():
            platform.setdefault(english, french)
    blocks.append(_table(["English", "Français"], *[[_b(en), fr] for en, fr in sorted(platform.items(), key=lambda kv: kv[0].casefold())]))
    labels = {code: label for code, label, _cat in EQUIPMENT}
    blocks += [_h(2, "Test Equipment"), _table(["Code", "English", "Français"], *[
        [code, labels[code], fr] for code, fr in sorted(EQUIPMENT_FR.items()) if code in labels])]
    return _doc(*blocks)


def _ensure(ctx, api, base, pages, parent, title, body):
    from modules.dynamite import content
    page = next((p for p in pages if p["title"] == title), None)
    if page is None:
        api.post(base, {"title": title, "parent_id": parent, "body": body})
        return True
    versions = ctx.conn.execute("SELECT author_id, note FROM dynamite_versions WHERE page_id = ?", (page["id"],)).fetchall()
    if not all(v["author_id"] == ctx.user["id"] and ((v["note"] or "").startswith(GENERATED) or (v["note"] or "") in ("", "Création"))
               for v in versions):
        return False  # edited by hand: left alone
    full = api.get(base + "/{}".format(page["id"]))["page"]
    if full.get("body") == json.loads(content.validate(body)):
        return False
    api.put(base + "/{}".format(page["id"]), {"title": title, "body": body, "base_version": full["version"],
                                             "note": GENERATED})
    return True


def ensure_pages(ctx):
    """Create / refresh the three glossary pages under « Base de connaissances (BDC) » (HEADLAMP)."""
    from modules.help import gtd
    from modules.help.local_api import LocalApi
    pid = gtd.project_id(ctx.conn)
    defs, acr = items(ctx.conn, "definition"), items(ctx.conn, "acronym")
    if pid is None or not (defs or acr):
        return False
    api = LocalApi(ctx)
    base = "/api/dynamite/p/{}/pages".format(pid)
    pages = api.get(base)["pages"]
    hub = next((p for p in pages if p["title"] == gtd.HUB), None) or next((p for p in pages if not p.get("parent_id")), None)
    parent = hub["id"] if hub else None
    changed = False
    for title, body in ((DEF_TITLE, definitions_page(defs)), (ACR_TITLE, acronyms_page(acr)),
                        (TR_TITLE, translation_page(defs, acr))):
        changed = _ensure(ctx, api, base, pages, parent, title, body) or changed
    return changed


def page_links(conn):
    from modules.help import gtd
    rows = conn.execute("SELECT p.id, p.title, pr.key FROM dynamite_pages p JOIN projects pr ON pr.id = p.project_id "
                        "WHERE p.project_id = ? AND p.title IN (?, ?, ?)",
                        (gtd.project_id(conn), DEF_TITLE, ACR_TITLE, TR_TITLE)).fetchall()
    return {r["title"]: "#/dynamite/{}/page/{}".format(r["key"], r["id"]) for r in rows}
