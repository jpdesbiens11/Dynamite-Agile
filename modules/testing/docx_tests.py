"""Word export of the Testing base (D-B-083): a test specification in the Word template, one Codebeamer-style item
per test of the filtered list (GET /api/testing/export.docx?ids=…&group=subject|function|location&lang=en|fr
&title=…&docno=…&rev=…&subject=…&doctype=…&prepared=…).

Sections: Log of revision, Introduction (purpose, scope), References (standards cited by the tests),
Definitions and Conventions, Acronyms (central lists, D-A-037), Test equipment and locations, Tests (grouped), Appendix: traceability (test →
requirements, function coverage).
"""
from core.errors import ApiError
from core.files import RawFile

from . import catalog, glossary, word_doc as d, lists, tests_api
from .data_tests import CATEGORIES, SUBJECTS

TEXT = {
    "en": {"intro": "Introduction", "purpose": "Purpose", "scope": "Scope", "refs": "References",
           "defs": "Definitions and Conventions", "means": "Test Equipment and Locations", "tests": "Tests",
           "equipment": "Test equipment", "locations": "Test locations", "trace": "Appendix A - Traceability",
           "t2r": "Test to Requirements", "cov": "Function Coverage", "item": "Test",
           "purpose_text": "This document specifies the tests selected in the Testing base to verify the product "
                           "requirements. Each test states its objective, acceptance criteria, level, method, location, "
                           "equipment and the product functions it addresses, with its traceability source.",
           "scope_text": "Selection: {n} test(s) of the Testing base{filt}, grouped by {group}. Standards are cited by "
                         "title and section only; the standard's own text prevails.",
           "ref_head": ["Ref.", "Standard / reference", "Sections cited"],
           "def_rows": [("Category", "Standard (defined by a cited standard), Industry practice (usual practice of the "
                         "consumer-product industry), Custom test (team test to be defined and reviewed)"),
                        ("Status", "Draft, In Review, Approved, Obsolete"),
                        ("Level", "Component, Subsystem, Product, Product in Use"),
                        ("Method", "I = Inspection, A = Analysis, D = Demonstration, T = Test"),
                        ("Location", "Where the test is performed (central list)"),
                        ("Equipment", "Test means from the central equipment list"),
                        ("Functions", "Product functions (F-XX) addressed by the test"),
                        ("Source", "Standard and section the test comes from (traceability)"),
                        ("[TBD]", "Value to be defined, fixed by the linked requirement")],
           "attr": {"status": "Status", "method": "Method", "level": "Level", "location": "Location",
                    "functions": "Functions", "category": "Category", "objective": "Objective",
                    "acceptance": "Acceptance criteria", "equipment": "Equipment", "procedure": "Procedure",
                    "source": "Source", "verifies": "Verifies", "notes": "Notes", "means": "Means"},
           "groups": {"subject": "subject", "function": "function", "location": "location"},
           "none": "(none)", "tbd_loc": "to be planned", "no_function": "Not allocated to a function",
           "cov_head": ["Function ID", "Function Name", "Tests", "Requirements"],
           "t2r_head": ["Test", "Title", "Requirements verified"], "eq_head": ["Code", "Equipment", "Category", "Tests"],
           "loc_head": ["Code", "Location", "Tests"], "reason": "Generated from the Testing base of Dynamite | Agile ({n} tests)."},
    "fr": {"intro": "Introduction", "purpose": "Objet", "scope": "Portée", "refs": "Références",
           "defs": "Définitions et conventions", "means": "Moyens et test locations", "tests": "Tests",
           "equipment": "Test Equipment", "locations": "Test Locations", "trace": "Annexe A - Traçabilité",
           "t2r": "Test vers requirements", "cov": "Couverture des fonctions", "item": "Test",
           "purpose_text": "Ce document spécifie les tests retenus dans la base Testing pour vérifier les "
                           "requirements du produit. Chaque test donne son objectif, son acceptance criteria, son niveau, sa "
                           "méthode, son lieu, ses équipements et les fonctions visées, avec sa source de traçabilité.",
           "scope_text": "Sélection : {n} test(s) de la base Testing{filt}, groupés par {group}. Les standards sont citées "
                         "par titre et section ; le texte de la standard fait foi.",
           "ref_head": ["Réf.", "Standard / référence", "Sections citées"],
           "def_rows": [("Category", "Standard (défini par une standard citée), Industry Practice, Custom Test (propre "
                         "à l'équipe, à définir et revoir)"),
                        ("Status", "Draft, In Review, Approved, Obsolete"),
                        ("Level", "Component, Subsystem, Product, Product in Use"),
                        ("Method", "I = Inspection, A = Analysis, D = Demonstration, T = Test"),
                        ("Test Location", "Où le test est réalisé (liste centrale)"),
                        ("Equipment", "Test Means de la liste centrale"),
                        ("Functions", "Fonctions du produit (F-XX) visées par le test"),
                        ("Source", "Standard et section d'où vient le test (traçabilité)"),
                        ("[TBD]", "Valeur à définir, fixée par le requirement liée")],
           "attr": {"status": "Status", "method": "Method", "level": "Level", "location": "Lieu",
                    "functions": "Functions", "category": "Category", "objective": "Objectif",
                    "acceptance": "Acceptance Criteria", "equipment": "Equipment", "procedure": "Procedure",
                    "source": "Source", "verifies": "Vérifie", "notes": "Notes", "means": "Moyens"},
           "groups": {"subject": "sujet", "function": "fonction", "location": "lieu"},
           "none": "(aucun)", "tbd_loc": "à planifier", "no_function": "No Function",
           "cov_head": ["Fonction", "Nom", "Tests", "Requirements"],
           "t2r_head": ["Test", "Titre", "Requirements vérifiées"], "eq_head": ["Code", "Équipement", "Category", "Tests"],
           "loc_head": ["Code", "Lieu", "Tests"], "reason": "Généré depuis la base Testing de Dynamite | Agile ({n} tests)."},
}
METHODS = {"en": {"I": "Inspection", "A": "Analysis", "D": "Demonstration", "T": "Test"},
           "fr": {"I": "Inspection", "A": "Analysis", "D": "Demonstration", "T": "Test"}}  # D-B-085
W = 9400  # text width of the template page (twips)


def _groups(tests, group, names):
    if group == "function":
        out = {}
        for code, label in names["function"].items():
            members = [t for t in tests if code in lists.split(t["functions"])]
            if members:
                out["{} - {}".format(code, label)] = members
        rest = [t for t in tests if not lists.split(t["functions"])]
        if rest:
            out[None] = rest
        return out
    if group == "location":
        out = {}
        for t in tests:
            out.setdefault(names["location"].get(t["location"]) if t["location"] else None, []).append(t)
        return dict(sorted(out.items(), key=lambda kv: (kv[0] is None, kv[0] or "")))
    out = {}
    for code, label in SUBJECTS.items():
        members = [t for t in tests if t["subject"] == code]
        if members:
            out[label] = members
    return out


def _item(t, reqs, names, T, lang):
    a = T["attr"]
    method = " + ".join("{} ({})".format(c, METHODS[lang].get(c, c)) for c in (t["method"] or ""))
    loc = names["location"].get(t["location"], t["location"]) if t["location"] else T["tbd_loc"]
    attributes = [["{} : {}".format(a["status"], t["status"]), "{} : {}".format(a["method"], method or "—")],
                  ["{} : {}".format(a["level"], t["level"] or "—"), "{} : {}".format(a["location"], loc)],
                  ["{} : {}".format(a["functions"], t["functions"] or "—"),
                   "{} : {}".format(a["category"], CATEGORIES.get(t["category"], t["category"]))]]
    desc = [d.labelled(a["objective"], t["objective"] or "—"), d.labelled(a["acceptance"], t["acceptance"] or "—")]
    equipment = [names["equipment"].get(c, c) + " ({})".format(c) for c in lists.split(t["equipment"])]
    desc.append(d.para([d.run(a["equipment"] + " :", bold=True)], style="CBdescription"))
    desc.append(d.bullets(equipment) if equipment else d.para(T["none"], style="CBdescription"))
    if t["means"]:
        desc.append(d.labelled(a["means"], t["means"]))
    if t["notes"]:
        desc.append(d.labelled(a["notes"], t["notes"]))
    if t["procedure"]:
        desc.append(d.labelled(a["procedure"], t["procedure"]["title"]))
    upstream = ["{} : {}".format(a["verifies"], ", ".join("{}{} {}".format(r["key"], " ({})".format(r["external_id"])
                                                                          if r["external_id"] else "", r["title"])
                                                         for r in reqs))] if reqs else []
    return d.cb_item(t["test_id"], T["item"], t["title"], attributes, desc,
                     rationale=["{} : {}".format(a["source"], t["source"] or "—")], upstream=upstream)


def body(conn, tests, linked, names, meta, group, filt):
    T = TEXT[meta["lang"]]
    out = [d.heading(1, T["intro"]), d.heading(2, T["purpose"]), d.para(T["purpose_text"]),
           d.heading(2, T["scope"]),
           d.para(T["scope_text"].format(n=len(tests), filt=filt, group=T["groups"][group]))]
    standards = {}
    for t in tests:
        standards.setdefault(t["standard"], set()).add(t["section"])
    out += [d.heading(1, T["refs"]), d.table(T["ref_head"], [
        ["REF-[{}]".format(i + 1), std, "\n".join(sorted(s for s in secs if s))]
        for i, (std, secs) in enumerate(sorted(standards.items()))], [1100, 3600, 4700])]
    out += glossary.docx_sections(conn, d, meta["lang"], T["defs"], T["def_rows"])  # D-A-037
    used_eq, used_loc = {}, {}
    for t in tests:
        for c in lists.split(t["equipment"]):
            used_eq.setdefault(c, []).append(t["test_id"])
        if t["location"]:
            used_loc.setdefault(t["location"], []).append(t["test_id"])
    out += [d.heading(1, T["means"]), d.heading(2, T["equipment"]),
            d.table(T["eq_head"], [[c, names["equipment"].get(c, c), names["equipment_cat"].get(c, ""), ", ".join(ids)]
                                   for c, ids in sorted(used_eq.items())] or [[T["none"], "", "", ""]], [1300, 3700, 1500, 2900]),
            d.heading(2, T["locations"]),
            d.table(T["loc_head"], [[c, names["location"].get(c, c), ", ".join(ids)] for c, ids in sorted(used_loc.items())]
                    or [[T["none"], "", ""]], [1300, 2600, 5500])]
    out.append(d.heading(1, T["tests"]))
    for label, members in _groups(tests, group, names).items():
        out.append(d.heading(2, label or T["no_function" if group == "function" else "tbd_loc"]))
        out += [_item(t, linked.get(t["test_id"], []), names, T, meta["lang"]) for t in members]
    out += [d.heading(1, T["trace"]), d.heading(2, T["t2r"]),
            d.table(T["t2r_head"], [[t["test_id"], t["title"], "\n".join("{} {}".format(r["key"], r["external_id"]).strip()
                                                                          for r in linked.get(t["test_id"], [])) or "—"]
                                    for t in tests], [1600, 3800, 4000]),
            d.heading(2, T["cov"])]
    cov = []
    for code, label in names["function"].items():
        ids = [t["test_id"] for t in tests if code in lists.split(t["functions"])]
        reqs = sorted({r["key"] for t in tests if t["test_id"] in ids for r in linked.get(t["test_id"], [])})
        cov.append([code, label, ", ".join(ids) or "—", str(len(reqs))])
    out.append(d.table(T["cov_head"], cov, [1200, 3400, 3900, 900]))
    return "".join(out)


def api_export(ctx):
    listing = tests_api.api_list(ctx)
    wanted = set(catalog.split_refs(ctx.query.get("ids")))
    tests = [t for t in listing["tests"] if not wanted or t["test_id"] in wanted]
    if not tests:
        raise ApiError(400, "Aucun test à exporter. Correctif : élargissez les filtres.")
    group = ctx.query.get("group") or "subject"
    if group not in ("subject", "function", "location"):
        raise ApiError(400, "Regroupement « {} » inconnu : subject, function ou location.".format(str(group)[:20]))
    meta = d.meta_from_query(ctx.query, {"title": "Test Specification", "doctype": "Test Specification",
                                         "subject": tests_api.space(ctx)[1], "rev": "A", "prepared": ctx.user["display_name"]})
    linked = tests_api._visible_requirements(ctx.conn, ctx.user, tests_api.space(ctx)[0])
    entries = lists.entries(ctx.conn)
    names = {k: {r["code"]: r["label"] for r in entries if r["kind"] == k} for k in ("location", "equipment", "function")}
    names["equipment_cat"] = {r["code"]: r["category"] for r in entries if r["kind"] == "equipment"}
    filt = " (" + str(ctx.query.get("filters"))[:300] + ")" if ctx.query.get("filters") else ""
    from modules.agile.qa import user_initials
    data = d.build(meta, body(ctx.conn, tests, linked, names, meta, group, filt), TEXT[meta["lang"]]["reason"].format(n=len(tests)),
                   user_initials(ctx.conn, ctx.user["id"]))
    from core import audit
    audit.log_action(ctx.conn, ctx.user["id"], "testing_export_docx", "project", tests_api.space(ctx)[0],
                     {"tests": len(tests), "group": group}, ctx.ip)
    return RawFile(data, d.filename(meta, "TST"),
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
