"""Exploration plan import / export (D-B-019): Excel (.xlsx) with a real
Gantt (conditional fills, formulas) and a « Lisez-moi » sheet written for
people and AI agents alike, or CSV. The file is the complete plan: an
import creates, updates and removes tasks to match it, after a check that
writes nothing (« Vérifier »). Rows are read by header name, so columns may
be reordered; computed columns (Début, Fin, weeks) are ignored on import.
"""
import csv
import datetime as dt
import io

from core import db, uploads
from core.errors import ApiError
from core.files import RawFile

from . import plan, xlsx

# (header, key) -- key None = computed, exported only.
COLUMNS = [("ID", "code"), ("Phase", "phase"), ("Task", "title"), ("Description", "description"),  # D-B-085: English
           ("Owner", "owner"), ("Predecessors", "predecessors"), ("Duration (wk)", "duration_weeks"),
           ("Start No Earlier Than", "start_date"), ("Start", None), ("Finish", None), ("Status", "status"),
           ("Progress (%)", "progress"), ("Status Note", "note")]
ALIASES = {
    "code": ["id", "code", "no", "n°", "#"],
    "phase": ["phase", "lot", "etape", "workstream", "groupe"],
    "title": ["tache", "task", "nom", "titre", "title", "activite"],
    "description": ["description", "desc", "details", "livrable"],
    "owner": ["responsable", "owner", "assigne", "assignee", "resp."],
    "predecessors": ["predecesseurs", "predecessors", "depend de", "dependances", "depends on", "pred."],
    "duration_weeks": ["duree (sem.)", "duree", "duree (semaines)", "semaines", "duration", "duration (weeks)",
                       "weeks", "duration (wk)"],
    "start_date": ["start no earlier than", "debut impose", "debut au plus tot", "not before", "start not earlier than", "debut force"],
    "status": ["statut", "status", "etat"],
    "progress": ["avancement (%)", "avancement", "avancement %", "progress", "%", "progress (%)"],
    "note": ["status note", "note de suivi", "note", "commentaire", "comment", "notes"],
}
STATUS_LABELS = list(plan.STATUSES.values())
MAX_WEEK_COLUMNS = 156
FIRST_WEEK_COL = len(COLUMNS)


def _owner_label(task):
    return task.get("owner_name") or ""


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------
def _readme(project, start, people):
    sheet = xlsx.Sheet("Lisez-moi")
    sheet.widths = {0: 26, 1: 90}
    sheet.add(("Plan d'exploration — {} ({})".format(project["name"], project["key"]), xlsx.TITLE))
    sheet.add("Exporté le", (dt.date.today(), xlsx.DATE))
    sheet.add()
    sheet.add(("Plan Start", xlsx.HEADER), (start, xlsx.DATE))
    sheet.add()
    rules = [
        ("Principe", "Une ligne = une task du plan. La feuille « Plan » est le plan complet : à l'import, les tasks "
                     "absentes du fichier sont retirées, les autres créées ou mises à jour (vérification sans "
                     "écriture d'abord)."),
        ("ID", "Identifiant court et unique (T1, T2… ou 1.1, 1.2). Sert aux prédécesseurs : ne pas le réutiliser."),
        ("Phase", "Regroupement libre (ex. « Concept », « Conception préliminaire »). Les tasks d'une même phase "
                  "se suivent."),
        ("Task / Description", "Nom court et description générique du travail (niveau abstrait, pas de ticket)."),
        ("Owner", "Identifiant ou nom d'un membre du projet (liste ci-dessous). Vide = non attribuée."),
        ("Predecessors", "ID des tasks qui doivent être finies avant de commencer, séparés par des virgules "
                          "(fin → début). Pas de boucle."),
        ("Duration (wk)", "Nombre de semaines (décimales permises). 0 = milestone."),
        ("Start No Earlier Than", "Optionnel, AAAA-MM-JJ : la task ne commence pas avant cette date."),
        ("Start / Finish", "Calculés (formules) : ignorés à l'import, recalculés par l'interface."),
        ("Status", " / ".join(STATUS_LABELS) + "."),
        ("Progress (%)", "0 à 100. « Done » vaut 100."),
        ("Status Note", "Texte court (500 caractères) mis à jour par l'owner."),
        ("Colonnes semaines", "Le Gantt : barre violette = planifiée, verte = terminée, rouge = en retard, "
                              "orange = milestone. Ne pas y saisir de données."),
        ("Pour un agent IA", "Garder exactement ces en-têtes (l'ordre peut changer), une task par ligne, dates "
                             "AAAA-MM-JJ, status et owners tels que listés ici. Un CSV avec les mêmes "
                             "colonnes est aussi accepté."),
    ]
    sheet.add(("Colonne / règle", xlsx.HEADER), ("Explication", xlsx.HEADER))
    for name, text in rules:
        sheet.add(name, (text, xlsx.WRAP))
    sheet.add()
    sheet.add(("Possible Owners", xlsx.HEADER), ("Nom (identifiant)", xlsx.HEADER))
    for person in people:
        sheet.add(person["display_name"], person["username"])
    return sheet


def export_xlsx(conn, project):
    start, tasks = plan.load(conn, project["id"])
    people = plan.members(conn, project["id"])
    week0 = start - dt.timedelta(days=start.weekday())
    last = max([dt.date.fromisoformat(t["end"]) for t in tasks] + [start + dt.timedelta(weeks=12)])
    weeks = min(MAX_WEEK_COLUMNS, (last - week0).days // 7 + 2)
    sheet = xlsx.Sheet("Plan")
    sheet.add(*[(h, xlsx.HEADER) for h, _ in COLUMNS],
              *[(week0 + dt.timedelta(weeks=w), xlsx.WEEK) for w in range(weeks)])
    row_of = {t["code"]: i + 2 for i, t in enumerate(tasks)}
    col = {key or header: xlsx.col_name(i) for i, (header, key) in enumerate(COLUMNS)}
    for i, t in enumerate(tasks):
        r = i + 2
        refs = ["'Lisez-moi'!$B$4", "{}{}".format(col["start_date"], r)] + [
            "{}{}".format(col["Finish"], row_of[p]) for p in t["predecessors"] if p in row_of]
        begin = dt.date.fromisoformat(t["start"])
        end = dt.date.fromisoformat(t["end"])
        sheet.add(t["code"], t["phase"], t["title"], (t["description"], xlsx.WRAP), _owner_label(t),
                  ", ".join(t["predecessors"]), t["duration_weeks"],
                  (plan.parse_date(t["start_date"]), xlsx.DATE) if t["start_date"] else "",
                  {"f": "MAX({})".format(",".join(refs)), "v": xlsx.date_serial(begin), "s": xlsx.DATE},
                  {"f": "{0}{2}+ROUND({1}{2}*7,0)".format(col["Start"], col["duration_weeks"], r),
                   "v": xlsx.date_serial(end), "s": xlsx.DATE},
                  t["status_label"], t["progress"], (t["note"], xlsx.WRAP))
    n = len(tasks) + 1
    sheet.widths = {0: 7, 1: 18, 2: 38, 3: 48, 4: 20, 5: 14, 6: 10, 7: 12, 8: 11, 9: 11, 10: 11, 11: 12, 12: 30}
    sheet.widths.update({FIRST_WEEK_COL + w: 3.2 for w in range(weeks)})
    sheet.freeze = "D2"
    sheet.landscape_fit = True
    sheet.autofilter = "A1:{}{}".format(xlsx.col_name(FIRST_WEEK_COL - 1), max(n, 2))
    if tasks:
        first, last_col = xlsx.col_name(FIRST_WEEK_COL), xlsx.col_name(FIRST_WEEK_COL + weeks - 1)
        c0 = first
        within = "{c}$1<${e}2,{c}$1+7>${s}2".format(c=c0, s=col["Start"], e=col["Finish"])
        sheet.conditional.append(("{}2:{}{}".format(first, last_col, n), [
            ("AND(${d}2=0,{c}$1<=${s}2,${s}2<{c}$1+7)".format(d=col["duration_weeks"], c=c0, s=col["Start"]),
             xlsx.DXF_MILESTONE),
            ('AND({},${}2="Done")'.format(within, col["status"]), xlsx.DXF_DONE),
            ('AND({},${}2<TODAY(),${}2<>"Done")'.format(within, col["Finish"], col["status"]), xlsx.DXF_LATE),
            ("AND({})".format(within), xlsx.DXF_BAR)]))
    rows = max(n + 50, 100)
    sheet.validations = [("{0}2:{0}{1}".format(col["status"], rows), STATUS_LABELS)]
    names = [p["display_name"] for p in people]
    if names and len(",".join(names)) < 250:
        sheet.validations.append(("{0}2:{0}{1}".format(col["owner"], rows), names))
    project_row = conn.execute("SELECT key, name FROM projects WHERE id = ?", (project["id"],)).fetchone()
    return xlsx.write([sheet, _readme(project_row, start, people)])


def export_csv(conn, project_id):
    _, tasks = plan.load(conn, project_id)
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow([h for h, _ in COLUMNS])
    for t in tasks:
        writer.writerow([t["code"], t["phase"], t["title"], t["description"], _owner_label(t),
                         ", ".join(t["predecessors"]), t["duration_weeks"], t["start_date"] or "", t["start"],
                         t["end"], t["status_label"], t["progress"], t["note"]])
    return out.getvalue()


def _project(ctx):
    project_id, _ = plan.access(ctx)
    return ctx.conn.execute("SELECT id, key, name FROM projects WHERE id = ?", (project_id,)).fetchone()


def api_export_xlsx(ctx):
    project = _project(ctx)
    name = "{}_exploration_{}.xlsx".format(project["key"], dt.date.today().isoformat())
    return RawFile(export_xlsx(ctx.conn, project), name,
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def api_export_csv(ctx):
    project = _project(ctx)
    return RawFile.csv(export_csv(ctx.conn, project["id"]),
                       "{}_exploration_{}.csv".format(project["key"], dt.date.today().isoformat()))


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------
def _map_headers(header):
    lookup = {plan.norm(alias): key for key, names in ALIASES.items() for alias in names}
    return {i: lookup.get(plan.norm(h)) for i, h in enumerate(header)}


def read_file(data, filename=""):
    """Bytes of an .xlsx or .csv -> (rows as dicts with their line number, plan start or None)."""
    start = None
    if data[:2] == b"PK":
        try:
            sheets = xlsx.read(data)
        except xlsx.XlsxError as exc:
            raise ApiError(400, "{} Correctif : enregistrez le fichier au format .xlsx (Classeur Excel).".format(exc))
        name = next((n for n in sheets if plan.norm(n) == "plan"), None) or next(iter(sheets), None)
        table = sheets.get(name) or []
        readme = next((sheets[n] for n in sheets if plan.norm(n) in ("lisez-moi", "readme", "parametres")), [])
        for row in readme:
            if len(row) > 1 and plan.norm(row[0]) in ("debut du plan", "plan start"):
                start = plan.parse_date(row[1])
    else:
        text = None
        for encoding in ("utf-8-sig", "cp1252"):
            try:
                text = data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        first = text.splitlines()[0] if text and text.splitlines() else ""
        table = list(csv.reader(io.StringIO(text or ""), delimiter=";" if first.count(";") > first.count(",") else ","))
    header_at = next((i for i, row in enumerate(table[:10])
                      if {"code", "title"} <= set(_map_headers(row).values())), None)
    if header_at is None:
        raise ApiError(400, "En-têtes « ID » et « Task » introuvables dans les 10 premières lignes. Correctif : "
                            "partez d'un export (bouton « Exporter Excel ») et gardez la première ligne.")
    mapping = _map_headers(table[header_at])
    rows = []
    for offset, row in enumerate(table[header_at + 1:], start=header_at + 2):
        values = {}
        for i, cell in enumerate(row[:len(mapping)]):
            key = mapping.get(i)
            if key and key not in values:
                values[key] = str(cell or "").strip()
        if any(values.values()):
            rows.append((offset, values))
    if len(rows) > plan.MAX_TASKS:
        raise ApiError(413, "{} tasks au maximum ({} lues).".format(plan.MAX_TASKS, len(rows)))
    return rows, start


def _progress(text):
    raw = str(text or "").replace("%", "").replace(",", ".").strip()
    try:
        value = float(raw) if raw else 0.0
    except ValueError:
        return text
    return value * 100 if 0 < value < 1 and "." in raw else value


def validate_rows(conn, project_id, rows):
    people = plan.members(conn, project_id)
    report, tasks, seen = [], [], set()
    for line, values in rows:
        entry = {"line": line, "code": values.get("code", ""), "title": values.get("title", ""), "detail": ""}
        warnings = []
        body = {k: v for k, v in values.items() if k != "owner"}
        if not body.get("code"):
            body["code"] = "T{}".format(len(tasks) + 1)
            while body["code"] in seen:
                body["code"] += "b"
            warnings.append("ID absent : {} attribué.".format(body["code"]))
        body.setdefault("duration_weeks", "1")
        if body.get("duration_weeks", "") == "":
            body["duration_weeks"] = "1"
        if "progress" in body:
            body["progress"] = _progress(body["progress"])
        owner = plan.find_member(people, values.get("owner", ""))
        if owner is False:
            warnings.append("Owner « {} » inconnu dans ce projet : laissé vide.".format(values["owner"]))
            owner = None
        try:
            clean = plan.clean(body, people)
        except ApiError as exc:
            report.append(dict(entry, action="refusée", detail=exc.message))
            continue
        clean["owner_id"] = owner
        if not clean.get("title"):
            report.append(dict(entry, action="refusée", detail="Nom de task (colonne « Task ») manquant."))
            continue
        if clean["code"] in seen:
            report.append(dict(entry, action="refusée", detail="ID {} en double dans le fichier.".format(clean["code"])))
            continue
        seen.add(clean["code"])
        clean = dict({"phase": "", "description": "", "start_date": None, "predecessors": "", "status": "todo",
                      "progress": 0, "note": ""}, **clean)
        entry.update(code=clean["code"], title=clean.get("title", ""), detail=" ".join(warnings))
        tasks.append((entry, clean))
        report.append(entry)
    return report, tasks


def import_plan(ctx, project_id, data, dry_run):
    conn = ctx.conn
    rows, start = read_file(data)
    report, tasks = validate_rows(conn, project_id, rows)
    problems = []
    try:
        plan.schedule([dict(t, predecessors=plan.split_codes(t["predecessors"])) for _, t in tasks],
                      start or dt.date.today())
    except plan.PlanError as exc:
        problems.append("{} Correctif : corrigez la colonne Prédécesseurs.".format(exc))
    existing = {r["code"]: r for r in conn.execute("SELECT * FROM exploration_tasks WHERE project_id = ?",
                                                   (project_id,)).fetchall()}
    fields = ("phase", "title", "description", "owner_id", "duration_weeks", "start_date", "predecessors",
              "status", "progress", "note")
    for position, (entry, task) in enumerate(tasks):
        current = existing.get(task["code"])
        if current is None:
            entry["action"] = "créée"
        else:
            changed = [f for f in fields if current[f] != task[f]]
            entry["action"] = "mise à jour" if changed or current["position"] != position else "inchangée"
            if changed:
                entry["detail"] = (entry["detail"] + " Modifié : " + ", ".join(changed) + ".").strip()
    in_file = {t["code"] for _, t in tasks}
    for code, row in existing.items():
        if code not in in_file:
            report.append({"line": "—", "code": code, "title": row["title"], "action": "supprimée",
                           "detail": "Absente du fichier : retirée du plan."})
    refused = sum(1 for r in report if r["action"] == "refusée")
    summary = {a: sum(1 for r in report if r["action"] == a)
               for a in ("créée", "mise à jour", "inchangée", "supprimée", "refusée")}
    result = {"dry_run": dry_run, "report": report, "summary": summary, "problems": problems,
              "start_date": start.isoformat() if start else None, "applied": False}
    if dry_run or refused or problems:
        return result
    for code in existing:
        if code not in in_file:
            conn.execute("DELETE FROM exploration_tasks WHERE project_id = ? AND code = ?", (project_id, code))
    now = db.utc_now()
    for position, (entry, task) in enumerate(tasks):
        current = existing.get(task["code"])
        if current is None:
            plan.insert(ctx, project_id, task, position)
        elif entry["action"] == "mise à jour":
            conn.execute("UPDATE exploration_tasks SET position = ?, {}, updated_by = ?, updated_at = ? WHERE id = ?"
                         .format(", ".join("{} = ?".format(f) for f in fields)),
                         (position,) + tuple(task[f] for f in fields) + (ctx.user["id"], now, current["id"]))
    if start:
        plan.set_start(conn, project_id, start)
    plan.log(ctx, "exploration_import", project_id, summary)
    result["applied"] = True
    return result


@uploads.binary_body
def api_import(ctx):
    project_id, _ = plan.access(ctx, "admin")
    upload = getattr(ctx, "upload", None)
    if upload is None or not upload.data:
        raise ApiError(400, "Aucun fichier reçu. Correctif : choisissez un fichier .xlsx ou .csv.")
    if len(upload.data) > xlsx.MAX_BYTES:
        raise ApiError(413, "Fichier de plus de 10 Mo.")
    dry = str((ctx.query or {}).get("dry_run", "1")) not in ("0", "false", "non")
    return import_plan(ctx, project_id, upload.data, dry)
