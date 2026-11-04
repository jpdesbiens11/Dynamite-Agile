"""Timesheet Word report (D-A-042): an extract of the time sheets for the selected Budget Lines, in the Word
template of the tool (modules/testing/word_doc.py, the one of Goldmine and Testing), addressed to an
organism or a client entered when the report is created (name, reference of the programme / contract, contact).

Same selection as the Excel export (period, organism, week status, Budget Lines and Spaces ticked « x »), same
data (export.load). Content: recipient and scope, summary per Budget Line, hours per employee and Budget Line,
detail of each range with its justification, attestation block, then the Definitions and Acronyms of the platform
when the Testing lists exist. Administrators only, journalled.
"""
import datetime as dt
import re

from core import permissions
from core.errors import ApiError
from core.files import RawFile
from modules.testing import word_doc as d

from . import budget, export, weeks

KINDS = {"grant": ("Organisme de subvention", "Funding Organism"), "client": ("Client", "Customer"),
         "other": ("Destinataire", "Recipient")}
LIMIT = 160
TEXT = {
    "fr": {"scope": "Objet et périmètre", "recipient": "Destinataire", "ref": "Référence (programme / contrat)",
           "contact": "Contact", "period": "Période", "status": "Status des semaines", "lines": "Budget Lines",
           "spaces": "Spaces", "all": "Tous", "rows": "Plages de temps", "hours": "Heures",
           "summary": "Sommaire par Budget Line", "people": "Heures par employé et Budget Line",
           "detail": "Détail des heures et justifications", "attest": "Attestation", "employee": "Employé",
           "date": "Date", "just": "Justification", "total": "Total", "label": "Budget Line Label", "share": "Part",
           "none": "Aucune heure pour cette sélection.",
           "intro": "Ce document présente l'extrait des feuilles de temps des Budget Lines sélectionnés, préparé pour {}. "
                    "Chaque heure est rattachée à une semaine {} et porte la justification saisie par l'employé.",
           "attest_text": "Je certifie que les heures ci-dessus proviennent des feuilles de temps des employés, telles "
                          "qu'approuvées par leur gestionnaire.",
           "prepared": "Préparé par", "approved": "Approuvé par", "sign": "Signature et date", "item": "Élément",
           "value": "Valeur", "role": "Rôle", "name": "Nom"},
    "en": {"scope": "Purpose and Scope", "recipient": "Recipient", "ref": "Reference (programme / contract)",
           "contact": "Contact", "period": "Period", "status": "Week status", "lines": "Budget Lines",
           "spaces": "Spaces", "all": "All", "rows": "Time ranges", "hours": "Hours",
           "summary": "Summary per Budget Line", "people": "Hours per Employee and Budget Line",
           "detail": "Detail of Hours and Justifications", "attest": "Attestation", "employee": "Employee",
           "date": "Date", "just": "Justification", "total": "Total", "label": "Budget Line Label", "share": "Share",
           "none": "No hours for this selection.",
           "intro": "This document presents the extract of the time sheets for the selected Budget Lines, prepared "
                    "for {}. Every hour belongs to a {} week and carries the justification entered by the employee.",
           "attest_text": "I certify that the hours above come from the employees' time sheets, as approved by their "
                          "manager.",
           "prepared": "Prepared by", "approved": "Approved by", "sign": "Signature and date", "item": "Item",
           "value": "Value", "role": "Role", "name": "Name"},
}
STATUS_WORD = {"fr": {"approved": "approuvée", "submitted": "soumise ou approuvée", "all": "(tout status)"},
               "en": {"approved": "approved", "submitted": "submitted or approved", "all": "(any status)"}}


def _text(ctx, name, required=False):
    value = " ".join(str(ctx.query.get(name) or "").split())
    if required and not value:
        raise ApiError(400, "Destinataire obligatoire. Correctif : entrez le nom de l'organisme de subvention ou du "
                            "client à qui le rapport est adressé.")
    if len(value) > LIMIT:
        raise ApiError(400, "Champ « {} » : {} caractères au maximum (reçu : {}).".format(name, LIMIT, len(value)))
    return value


def _hours(value):
    return "{:.2f}".format(value).rstrip("0").rstrip(".")


def _glossary(conn, lang, heading):
    """Definitions and Acronyms of the platform (D-A-037) when the Testing lists exist."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'testing_lists'").fetchone():
        return []
    from modules.testing import glossary
    return glossary.docx_sections(conn, d, lang, heading, [("Budget Line", "Code of the funding structure (Timesheet)"),
                                                          ("Week status", "Draft, Submitted, Approved, Returned")])


def body(conn, rows, names, sel, lang):
    T = TEXT[lang]
    kind_label = KINDS[sel["kind"]][0 if lang == "fr" else 1]
    total = round(sum(r["hours"] for r in rows), 2)
    out = [d.heading(1, T["scope"]), d.para(T["intro"].format(sel["recipient"], STATUS_WORD[lang][sel["status"]])),
           d.table([T["item"], T["value"]], [[kind_label, sel["recipient"]], [T["ref"], sel["ref"] or "—"], [T["contact"], sel["contact"] or "—"],
                              [T["period"], "{} → {}".format(sel["start"], sel["end"])],
                              [T["status"], export.STATUS_FILTER_LABELS[sel["status"]]],
                              [T["lines"], ", ".join(sel["tasks"]) if sel["tasks"] else T["all"]],
                              [T["spaces"], ", ".join(sel["projects"]) if sel["projects"] else T["all"]],
                              [T["rows"], str(len(rows))], [T["hours"], _hours(total)]], [3000, 6400])]
    by_line = {}
    for r in rows:
        by_line.setdefault(r["task_key"], []).append(r)
    out.append(d.heading(1, T["summary"]))
    if not rows:
        return out + [d.para(T["none"])]
    out.append(d.table(["Budget Line", T["label"], T["hours"], T["share"]], [
        [code, names.get(code, code), _hours(sum(r["hours"] for r in items)),
         "{:.0f} %".format(100 * sum(r["hours"] for r in items) / total if total else 0)]
        for code, items in sorted(by_line.items())] + [[T["total"], "", _hours(total), "100 %"]], [1600, 5000, 1400, 1400]))
    people = {}
    for r in rows:
        people.setdefault(r["display_name"], {}).setdefault(r["task_key"], 0)
        people[r["display_name"]][r["task_key"]] += r["hours"]
    out += [d.heading(1, T["people"]), d.table([T["employee"], "Budget Line", T["hours"]], [
        [name, code, _hours(h)] for name, lines in sorted(people.items()) for code, h in sorted(lines.items())],
        [4200, 2600, 2600])]
    out.append(d.heading(1, T["detail"]))
    for code, items in sorted(by_line.items()):
        out += [d.heading(2, "{} — {}".format(code, names.get(code, code))),
                d.table([T["date"], T["employee"], "Space", T["hours"], T["just"]], [
                    [r["work_date"], r["display_name"], r["key"], _hours(r["hours"]), r["description"] or "—"]
                    for r in sorted(items, key=lambda x: (x["work_date"], x["display_name"]))], [1250, 1900, 900, 800, 4550])]
    out += [d.heading(1, T["attest"]), d.para(T["attest_text"]),
            d.table([T["role"], T["name"], T["sign"]], [[T["prepared"], sel["prepared"], ""], [T["approved"], "", ""]], [2400, 3500, 3500])]
    return out + _glossary(conn, lang, "Definitions and Conventions" if lang == "en" else "Définitions et conventions")


def api_report(ctx):
    permissions.require_admin(ctx.user)
    today = dt.date.today()
    start = export._date(ctx, "from", today.replace(day=1).isoformat())
    end = export._date(ctx, "to", today.isoformat())
    if end < start:
        raise ApiError(400, "Période inversée ({} → {}). Correctif : la date de fin suit la date de début.".format(start, end))
    status = ctx.query.get("status", "approved")
    if status not in export.STATUS_FILTERS:
        raise ApiError(400, "Filtre « {} » inconnu. Correctif : approved, submitted ou all.".format(status))
    kind = ctx.query.get("recipient_type", "grant")
    if kind not in KINDS:
        raise ApiError(400, "Type de destinataire « {} » inconnu. Correctif : grant (organisme de subvention), client ou "
                            "other.".format(str(kind)[:20]))
    tasks = export._codes(ctx, "tasks", r"[A-Z]{1,5}-[A-Z0-9]{2,4}")
    projects = export._codes(ctx, "projects", r"[A-Z0-9]{2,10}")
    if tasks == () or projects == ():
        raise ApiError(400, "Aucun Budget Line ou Space coché. Correctif : cochez au moins un « x ».")
    organism = str(ctx.query.get("organism", "")).strip()[:80]
    sel = {"kind": kind, "recipient": _text(ctx, "recipient", required=True), "ref": _text(ctx, "recipient_ref"),
           "contact": _text(ctx, "recipient_contact"), "start": start.isoformat(), "end": end.isoformat(),
           "status": status, "tasks": tasks, "projects": projects, "prepared": ctx.user["display_name"]}
    rows = export.load(ctx.conn, start, end, organism, status, tasks, projects)
    names = {t["key"]: t["label"] for st in budget.structure(ctx.conn).values() for t in st["tasks"]}
    meta = d.meta_from_query(ctx.query, {"title": "Timesheet Report — " + sel["recipient"], "doctype": "Report",
                                         "prepared": ctx.user["display_name"], "rev": "A", "lang": "fr"})
    xml = "".join(body(ctx.conn, rows, names, sel, meta["lang"]))
    data = d.build(meta, xml, "Initial issue" if meta["lang"] == "en" else "Première émission",
                   ctx.user["display_name"])
    weeks.log(ctx, "timesheet_report", None, {"recipient": sel["recipient"], "type": kind, "from": sel["start"],
                                              "to": sel["end"], "rows": len(rows), "status": status,
                                              "tasks": list(tasks) if tasks else "all"})
    slug = re.sub(r"[^A-Za-z0-9]+", "-", sel["recipient"]).strip("-")[:30].strip("-") or "rapport"
    name = "{}Timesheet_{}_{}_{}.docx".format(re.sub(r"[^A-Za-z0-9._-]+", "_", meta["docno"]) + "_" if meta["docno"] else "",
                                              slug, sel["start"], sel["end"])
    return RawFile(data, name,
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

