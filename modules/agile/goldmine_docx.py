"""Goldmine Word export (D-B-083): a requirement specification in the Word template, one Codebeamer-style item per
requirement / need of the filtered list (« REQ-001 - Requirement - … »).

GET /api/agile/p/<pid>/export/requirements.docx?numbers=…&group=category|function|lifecycle&lang=en|fr&title=…
&docno=…&rev=…&subject=…&doctype=…&prepared=…
"""
from core.errors import ApiError
from core.files import RawFile

from modules.testing import word_doc as d
from modules.testing import lists

from . import common as c
from . import goldmine, goldmine_csv, goldmine_need

TEXT = {
    "en": {"intro": "Introduction", "purpose": "Purpose", "scope": "Scope", "refs": "References",
           "defs": "Definitions and Conventions", "reqs": "Requirements", "trace": "Appendix A - Traceability Matrix",
           "purpose_text": "This document lists the requirements of the {space} Space selected in the Goldmine "
                           "base, with their attributes, rationale, source and the tests of the Testing base that verify them.",
           "scope_text": "Selection: {n} item(s){filt}, grouped by {group}.",
           "groups": {"category": "category", "function": "function", "lifecycle": "life-cycle phase"},
           "ref_head": ["Ref.", "Source document / standard", "Items"],
           "def_rows": [("Status", "Requirement Workflow: Received, In Analysis, Customer Clarification, Accepted, "
                         "Allocated, Implemented, In Verification, Verified, Rejected, Obsolete"),
                        ("Criticality", "Criticality of the item (A = highest, E = lowest), from the risk analysis (FMEA)"),
                        ("Method", "I = Inspection, A = Analysis, D = Demonstration, T = Test"),
                        ("Functions", "Product functions (F-XX) of the functional analysis the item belongs to"),
                        ("Test Procedure", "Tests of the Testing base that verify the requirement, with their source"),
                        ("Derived from", "Stakeholder needs the requirement answers"),
                        ("[TBD]", "Value to be defined")],
           "kind": {"requirement": "Requirement", "need": "Need"},
           "a": {"status": "Status", "rev": "Rev.", "key": "Key", "alloc": "Allocation", "cat": "Category",
                 "phase": "Phase", "crit": "Criticality", "method": "Method", "func": "Functions",
                 "acc": "Acceptance criteria", "rat": "Rationale", "src": "Source", "derived": "Derived from",
                 "verified": "Verified by", "impl": "Implemented by", "stake": "Stakeholder",
                 "nstatus": "Need Status"},
           "trace_head": ["Requirement", "Title", "Functions", "Test Procedure (source)"],
           "none": "Not allocated", "reason": "Generated from the Goldmine base of Dynamite | Agile ({n} items)."},
    "fr": {"intro": "Introduction", "purpose": "Objet", "scope": "Portée", "refs": "Références",
           "defs": "Définitions et conventions", "reqs": "Requirements", "trace": "Annexe A - Matrice de traçabilité",
           "purpose_text": "Ce document liste les requirements du Space {space} retenues dans la base Goldmine, "
                           "avec leurs attributs, justification, source et les tests de la base Testing qui les vérifient.",
           "scope_text": "Sélection : {n} élément(s){filt}, groupés par {group}.",
           "groups": {"category": "category", "function": "function", "lifecycle": "life-cycle phase"},
           "ref_head": ["Réf.", "Source Document / standard", "Éléments"],
           "def_rows": [("Status", "Requirement Workflow : Received, In Analysis, Customer Clarification, Accepted, Allocated, "
                         "Implemented, In Verification, Verified, Rejected, Obsolete"),
                        ("Criticality", "Criticité de l'élément (A = la plus haute, E = la plus basse), selon l'analyse de risque (AMDEC)"),
                        ("Method", "I = Inspection, A = Analysis, D = Demonstration, T = Test"),
                        ("Functions", "Fonctions du produit (F-XX) de l'analyse fonctionnelle auxquelles l'élément appartient"),
                        ("Test Procedure", "Tests de la base Testing qui vérifient le requirement, avec leur source"),
                        ("Derived From", "Needs des stakeholders auxquels le requirement répond"),
                        ("[TBD]", "Valeur à définir")],
           "kind": {"requirement": "Requirement", "need": "Need"},
           "a": {"status": "Status", "rev": "Rév.", "key": "Key", "alloc": "Allocation", "cat": "Category",
                 "phase": "Phase", "crit": "Criticality", "method": "Method", "func": "Functions",
                 "acc": "Acceptance Criteria", "rat": "Rationale", "src": "Source", "derived": "Derived From",
                 "verified": "Vérifiée par", "impl": "Implémentée par", "stake": "Stakeholder",
                 "nstatus": "Need Status"},
           "trace_head": ["Requirement", "Titre", "Functions", "Test Procedure (source)"],
           "none": "No Function", "reason": "Généré depuis la base Goldmine de Dynamite | Agile ({n} éléments)."},
}


def _groups(items, group, functions):
    out = {}
    if group == "function":
        for code, label in functions.items():
            members = [r for r in items if code in lists.split(r.get("functions"))]
            if members:
                out["{} - {}".format(code, label)] = members
        rest = [r for r in items if not lists.split(r.get("functions"))]
        if rest:
            out[None] = rest
        return out
    mapping, field = (goldmine.LIFECYCLE, "lifecycle") if group == "lifecycle" else (goldmine.CATEGORIES, "category")
    for code, label in mapping.items():
        members = [r for r in items if r[field] == code]
        if members:
            out[label] = members
    rest = [r for r in items if r[field] not in mapping]
    if rest:
        out[None] = rest
    return out


def _item(r, T):
    a = T["a"]
    item_id = r["external_id"] or r["key"]
    attributes = [["{} : {}".format(a["status"], r["status_name"]), "{} : {}".format(a["rev"], r["revision"] or "—"),
                   "{} : {}".format(a["key"], r["key"])],
                  ["{} : {}".format(a["alloc"], r["allocation"] or "—"),
                   "{} : {}".format(a["cat"], goldmine.CATEGORIES.get(r["category"], r["category"])),
                   "{} : {}".format(a["phase"], goldmine.LIFECYCLE.get(r["lifecycle"], r["lifecycle"] or "—"))],
                  ["{} : {}".format(a["crit"], r["criticality"] or "—"),
                   "{} : {}".format(a["method"], r["verification_method"] or "—"),
                   "{} : {}".format(a["func"], r.get("functions") or "—")]]
    if r["kind"] == "need":
        attributes[0][2] = "{} : {}".format(a["stake"], goldmine.STAKEHOLDERS.get(r["stakeholder"], r["stakeholder"] or "—"))
    if r["kind"] == "need":  # D-B-086: maturity of the need
        attributes[0].append("{} : {}".format(a["nstatus"], goldmine_need.NEED_STATUS.get(r.get("need_status"), "—")))
    desc = [r["statement"] or "—"]
    if r["acceptance_criteria"]:
        desc.append(d.labelled(a["acc"], r["acceptance_criteria"]))
    rationale = []
    if r["rationale"]:
        rationale.append("{} : {}".format(a["rat"], r["rationale"]))
    src = " · ".join(x for x in (goldmine.SOURCES.get(r["source"], r["source"]), r["source_doc"]) if x)
    if src:
        rationale.append("{} : {}".format(a["src"], src))
    upstream = []
    if r["derived_from"]:
        upstream.append("{} : {}".format(a["derived"], r["derived_from"]))
    if r.get("test_source"):
        upstream.append("{} : {}".format(a["verified"], r["test_source"]))
    if r["implemented_by"]:
        upstream.append("{} : {}".format(a["impl"], ", ".join(r["implemented_by"])))
    return d.cb_item(item_id, T["kind"].get(r["kind"], r["kind"]), r["title"], attributes, desc, rationale, upstream)


def api_export(ctx):
    project_id, _ = c.access(ctx)
    listing = goldmine.api_list(ctx)
    if not listing["enabled"]:
        raise ApiError(409, "Goldmine n'est pas activé sur ce projet.")
    selection = goldmine_csv._parse_numbers(ctx.query.get("numbers"))
    items = [r for r in listing["requirements"] if selection is None or r["number"] in selection]
    if not items:
        raise ApiError(400, "Aucune requirement à exporter. Correctif : élargissez les filtres.")
    group = ctx.query.get("group") or "category"
    if group not in ("category", "function", "lifecycle"):
        raise ApiError(400, "Regroupement « {} » inconnu : category, function ou lifecycle.".format(str(group)[:20]))
    key = c.project_key(ctx.conn, project_id)
    meta = d.meta_from_query(ctx.query, {"title": "{} Requirement Specification".format(key), "subject": ctx.conn.execute("SELECT name FROM projects WHERE id = ?", (project_id,)).fetchone()["name"],
                                         "doctype": "System Requirement Specification", "rev": "A",
                                         "prepared": ctx.user["display_name"]})
    T = TEXT[meta["lang"]]
    functions = {r["code"]: r["label"] for r in lists.entries(ctx.conn, "function")}
    filt = " (" + str(ctx.query.get("filters"))[:300] + ")" if ctx.query.get("filters") else ""
    out = [d.heading(1, T["intro"]), d.heading(2, T["purpose"]), d.para(T["purpose_text"].format(space=key)),
           d.heading(2, T["scope"]), d.para(T["scope_text"].format(n=len(items), filt=filt, group=T["groups"][group]))]
    docs = {}
    for r in items:
        if r["source_doc"]:
            docs.setdefault(r["source_doc"], []).append(r["external_id"] or r["key"])
    out += [d.heading(1, T["refs"]), d.table(T["ref_head"], [["REF-[{}]".format(i + 1), doc, ", ".join(ids[:12]) +
                                                              (" …" if len(ids) > 12 else "")]
                                                             for i, (doc, ids) in enumerate(sorted(docs.items()))]
                                              or [["—", "—", "—"]], [1100, 4700, 3600])]
    from modules.testing import glossary
    out += glossary.docx_sections(ctx.conn, d, meta["lang"], T["defs"], T["def_rows"])  # D-A-037
    out.append(d.heading(1, T["reqs"]))
    for label, members in _groups(items, group, functions).items():
        out.append(d.heading(2, label or T["none"]))
        out += [_item(r, T) for r in sorted(members, key=lambda r: (r["kind"] != "need", r["external_id"] or r["key"]))]
    out += [d.heading(1, T["trace"]), d.table(T["trace_head"], [
        [(r["external_id"] + "\n" if r["external_id"] else "") + r["key"], r["title"], r.get("functions") or "—",
         r.get("test_source") or "—"] for r in items if r["kind"] == "requirement"], [1700, 2800, 1400, 3500])]
    from .qa import user_initials
    data = d.build(meta, "".join(out), T["reason"].format(n=len(items)), user_initials(ctx.conn, ctx.user["id"]))
    c.log(ctx, "goldmine_export_docx", "project", project_id, {"rows": len(items), "group": group})
    return RawFile(data, d.filename(meta, key + "_REQ"),
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
