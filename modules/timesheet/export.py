"""Timesheet Excel export (D-B-023): hours per funding organism and period,
for the claims sent to the organisms that fund our contracts.

Workbook (standard-library writer of modules/exploration/xlsx.py):
- « Sommaire » : organism > project > employee > task, hours, subtotal per
  organism (SUM formulas with cached values, so the sheet reads the same
  in Excel, LibreOffice or a viewer);
- « Détail » : one line per time range, with its description;
- « Budget Lines » (D-B-036): hours per Budget Line (task code),
  then every time range of each line with its justification, subtotals;
- « Lisez-moi » : period, filters, Budget Lines claimed, who exported and when.
A claim picks any combination of Budget Lines (task codes) and projects.
Administrators only.
"""
import datetime as dt
import re

from core import db, permissions
from core.errors import ApiError
from core.files import RawFile
from modules.exploration import xlsx

from . import budget, catalog, weeks

STATUS_FILTERS = {"approved": ("approved",), "submitted": ("submitted", "approved"),
                  "all": ("draft", "submitted", "approved", "returned")}
STATUS_FILTER_LABELS = {"approved": "Approuvées seulement", "submitted": "Soumises et approuvées",
                        "all": "Toutes (brouillons compris)"}
DETAIL_COLUMNS = ["Organisme", "No de contrat", "Space", "Space Name", "Employé", "Date", "Semaine du",
                  "Budget Line", "Budget Line Label", "Heures", "Description", "Status", "Décidé par", "Décidé le (UTC)"]


def _date(ctx, name, default):
    value = ctx.query.get(name) or default
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        raise ApiError(400, "Date « {} » invalide pour {}. Correctif : format AAAA-MM-JJ.".format(value, name))


def _codes(ctx, name, pattern):
    """Comma list from the query (?tasks=B-09,B-11) -> validated tuple, or None for « all »."""
    raw = str(ctx.query.get(name, "") or "").strip()
    if not raw:
        return None
    values = tuple(dict.fromkeys(v.strip().upper() for v in raw.split(",") if v.strip()))
    bad = [v for v in values if not re.fullmatch(pattern, v)]
    if bad:
        raise ApiError(400, "Valeur(s) « {} » refusée(s) pour {}. Correctif : codes séparés par des virgules.".format(
            ", ".join(bad[:5]), name))
    return values


def load(conn, start, end, organism, status, tasks=None, projects=None):
    params = [start.isoformat(), end.isoformat()] + list(STATUS_FILTERS[status])
    where = "e.work_date BETWEEN ? AND ? AND w.status IN ({})".format(",".join("?" * len(STATUS_FILTERS[status])))
    if organism:
        where += " AND COALESCE(t.organism, '') = ?"
        params.append(organism)
    if tasks is not None:  # Budget Lines (D-B-036)
        where += " AND e.task_key IN ({})".format(",".join("?" * len(tasks)) or "NULL")
        params += list(tasks)
    if projects is not None:
        where += " AND p.key IN ({})".format(",".join("?" * len(projects)) or "NULL")
        params += list(projects)
    rows = conn.execute(
        "SELECT COALESCE(t.organism, '') AS organism, COALESCE(t.contract_ref, '') AS contract_ref, p.key, p.name, "
        "u.display_name, e.work_date, w.week_start, e.task_key, e.hours, e.description, w.status, "
        "d.display_name AS decided_by, w.decided_at FROM timesheet_entries e "
        "JOIN timesheet_weeks w ON w.id = e.week_id JOIN users u ON u.id = w.user_id "
        "JOIN projects p ON p.id = e.project_id LEFT JOIN timesheet_projects t ON t.project_id = p.id "
        "LEFT JOIN users d ON d.id = w.decided_by WHERE " + where +
        " ORDER BY organism, p.key, u.display_name, e.work_date, e.task_key", params).fetchall()
    return db.rows(rows)


def summary_sheet(rows, names):
    sheet = xlsx.Sheet("Sommaire")
    sheet.add(*[(h, xlsx.HEADER) for h in ("Organisme", "No de contrat", "Space", "Employé", "Budget Line", "Budget Line Label",
                                           "Heures")])
    groups = {}
    for r in rows:
        k = (r["organism"] or "(sans organisme)", r["contract_ref"], r["key"], r["display_name"], r["task_key"])
        groups[k] = groups.get(k, 0) + r["hours"]
    org_totals = []
    current, first_row, subtotal = None, 2, 0.0
    for (org, contract, key, person, task), hours in sorted(groups.items()):
        if current is not None and org != current:
            _subtotal(sheet, current, first_row, subtotal)
            org_totals.append(len(sheet.rows))
            first_row, subtotal = len(sheet.rows) + 1, 0.0
        current = org
        sheet.add(org, contract, key, person, task, names.get(task, task), round(hours, 2))
        subtotal += hours
    if current is not None:
        _subtotal(sheet, current, first_row, subtotal)
        org_totals.append(len(sheet.rows))
        total = sum(groups.values())
        sheet.add(("TOTAL GÉNÉRAL", xlsx.HEADER), *[("", xlsx.HEADER)] * 5,
                  {"f": "+".join("G{}".format(r) for r in org_totals), "v": round(total, 2), "s": xlsx.HEADER})
    sheet.widths = {0: 24, 1: 16, 2: 10, 3: 24, 4: 11, 5: 40, 6: 10}
    sheet.freeze = "A2"
    return sheet


def _subtotal(sheet, org, first_row, value):
    last = len(sheet.rows)
    sheet.add(("Total " + org, xlsx.HEADER), *[("", xlsx.HEADER)] * 5,
              {"f": "SUM(G{}:G{})".format(first_row, last), "v": round(value, 2), "s": xlsx.HEADER})


def detail_sheet(rows, names):
    sheet = xlsx.Sheet("Détail")
    sheet.add(*[(h, xlsx.HEADER) for h in DETAIL_COLUMNS])
    for r in rows:
        sheet.add(r["organism"], r["contract_ref"], r["key"], r["name"], r["display_name"],
                  (dt.date.fromisoformat(r["work_date"]), xlsx.DATE), (dt.date.fromisoformat(r["week_start"]), xlsx.DATE),
                  r["task_key"], names.get(r["task_key"], r["task_key"]), r["hours"],
                  (r["description"], xlsx.WRAP), catalog.STATUSES.get(r["status"], r["status"]),
                  r["decided_by"] or "", (r["decided_at"] or "")[:16].replace("T", " "))
    n = max(len(rows) + 1, 2)
    sheet.add(*[""] * 8, ("Total", xlsx.HEADER),
              {"f": "SUBTOTAL(9,J2:J{})".format(n), "v": round(sum(r["hours"] for r in rows), 2), "s": xlsx.HEADER})
    sheet.widths = {0: 20, 1: 14, 2: 9, 3: 26, 4: 22, 5: 11, 6: 11, 7: 10, 8: 34, 9: 8, 10: 60, 11: 11, 12: 18, 13: 16}
    sheet.freeze = "A2"
    sheet.autofilter = "A1:N{}".format(n)
    sheet.landscape_fit = True
    return sheet


def budget_sheet(rows, names):
    """Hours per Budget Line, then each range of the line with its justification."""
    sheet = xlsx.Sheet("Budget Lines")
    sheet.add(("Heures par Budget Line (code de task)", xlsx.TITLE))
    sheet.add(*[(h, xlsx.HEADER) for h in ("Budget Line", "Label", "Heures", "Employés", "Plages")])
    lines = {}
    for r in rows:
        lines.setdefault(r["task_key"], []).append(r)
    first = len(sheet.rows) + 1
    for code in sorted(lines):
        items = lines[code]
        sheet.add(code, names.get(code, code), round(sum(r["hours"] for r in items), 2),
                  len({r["display_name"] for r in items}), len(items))
    last = len(sheet.rows)
    total = round(sum(r["hours"] for r in rows), 2)
    sheet.add(("Total des Budget Lines réclamées", xlsx.HEADER), ("", xlsx.HEADER),
              {"f": "SUM(C{}:C{})".format(first, max(first, last)), "v": total, "s": xlsx.HEADER}, ("", xlsx.HEADER), ("", xlsx.HEADER))
    sheet.add()
    sheet.add(("Rationale des heures, code par code", xlsx.TITLE))
    sheet.add(*[(h, xlsx.HEADER) for h in ("Budget Line", "Space", "Employé", "Date", "Heures", "Justification (description saisie)",
                                           "Status")])
    for code in sorted(lines):
        start_row = len(sheet.rows) + 1
        for r in sorted(lines[code], key=lambda x: (x["key"], x["display_name"], x["work_date"])):
            sheet.add(code, r["key"], r["display_name"], (dt.date.fromisoformat(r["work_date"]), xlsx.DATE), r["hours"],
                      (r["description"], xlsx.WRAP), catalog.STATUSES.get(r["status"], r["status"]))
        sheet.add(("Total " + code, xlsx.HEADER), *[("", xlsx.HEADER)] * 3,
                  {"f": "SUM(E{}:E{})".format(start_row, len(sheet.rows)), "v": round(sum(r["hours"] for r in lines[code]), 2),
                   "s": xlsx.HEADER}, ("", xlsx.HEADER), ("", xlsx.HEADER))
    sheet.widths = {0: 12, 1: 34, 2: 22, 3: 11, 4: 9, 5: 80, 6: 11}
    sheet.landscape_fit = True
    return sheet


def readme_sheet(start, end, organism, status, who, count, tasks=None, projects=None, names_struct=None):
    sheet = xlsx.Sheet("Lisez-moi")
    sheet.add(("Feuilles de temps — export pour organisme", xlsx.TITLE))
    sheet.add()
    for label, value in (("Période du", start), ("au", end), ("Organisme", organism or "Tous"),
                         ("Status des semaines", STATUS_FILTER_LABELS[status]), ("Plages exportées", count),
                         ("Projets", ", ".join(projects) if projects is not None else "Tous"),
                         ("Budget Lines réclamés", ", ".join(tasks) if tasks is not None else "Tous"),
                         ("Exporté par", who), ("Exporté le", dt.datetime.now().strftime("%Y-%m-%d %H:%M"))):
        sheet.add((label, xlsx.HEADER), value)
    sheet.add()
    sheet.add(("Chaque plage porte la justification saisie par l'employé (feuille « Détail » et feuille "
               "« Budget Lines ») : elle est lisible telle quelle par l'organisme.", xlsx.WRAP))
    sheet.add()
    sheet.add(("Budget Lines", xlsx.HEADER))
    for key, s in names_struct.items():
        for t in s["tasks"]:
            sheet.add(t["key"], "{} — {}{}{}".format(s["label"], t["label"], "" if t["claimable"] else " (non réclamable)",
                                                   "" if t["active"] else " (inactif)"))
    sheet.widths = {0: 22, 1: 60}
    return sheet


def api_export(ctx):
    permissions.require_admin(ctx.user)
    today = dt.date.today()
    start = _date(ctx, "from", today.replace(day=1).isoformat())
    end = _date(ctx, "to", today.isoformat())
    if end < start:
        raise ApiError(400, "Période inversée ({} → {}). Correctif : la date de fin suit la date de début.".format(start, end))
    status = ctx.query.get("status", "approved")
    if status not in STATUS_FILTERS:
        raise ApiError(400, "Filtre « {} » inconnu. Correctif : approved, submitted ou all.".format(status))
    organism = str(ctx.query.get("organism", "")).strip()[:80]
    tasks = _codes(ctx, "tasks", r"[A-Z]{1,5}-[A-Z0-9]{2,4}")
    projects = _codes(ctx, "projects", r"[A-Z0-9]{2,10}")
    if tasks == () or projects == ():
        raise ApiError(400, "Aucun Budget Line ou projet coché. Correctif : cochez au moins un « x ».")
    rows = load(ctx.conn, start, end, organism, status, tasks, projects)
    struct = budget.structure(ctx.conn)  # D-B-084: labels of the Budget Lines administered in « Spaces et organismes »
    names = {t["key"]: t["label"] for st in struct.values() for t in st["tasks"]}
    data = xlsx.write([summary_sheet(rows, names), budget_sheet(rows, names), detail_sheet(rows, names),
                       readme_sheet(start, end, organism, status, ctx.user["display_name"], len(rows), tasks, projects,
                                    struct)])
    weeks.log(ctx, "timesheet_export", None, {"from": start.isoformat(), "to": end.isoformat(),
                                              "organism": organism, "status": status, "rows": len(rows),
                                              "tasks": list(tasks) if tasks else "all",
                                              "projects": list(projects) if projects else "all"})
    slug = re.sub(r"[^A-Za-z0-9]+", "-", organism).strip("-") or "tous"
    if tasks is not None:
        slug += "_" + ("-".join(tasks) if len(tasks) <= 3 else "{}-codes".format(len(tasks)))
    return RawFile(data, "timesheet_{}_{}_{}.xlsx".format(slug, start.isoformat(), end.isoformat()),
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
