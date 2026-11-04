"""Excel export of a Pugh matrix (D-B-062), standard library writer of
modules/exploration/xlsx.py: the matrix with + / S / - drop-downs, green and
red fills, and totals (Σ+, ΣS, Σ-, net, rank) as live formulas, so the sheet
can still be played with in Excel; plus the list of the requirements used.
"""
import re

from core.files import RawFile
from modules.exploration import xlsx

from . import common as c
from . import pugh

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
FIXED = ["Key", "External ID", "Requirement (critère)", "Category", "Phase"]


def build(data, space):
    m, concepts, criteria = data["matrix"], data["concepts"], data["criteria"]
    scores = {(s["criterion_id"], s["concept_id"]): s for s in data["scores"]}
    cats, phases = data["labels"]["categories"], data["labels"]["lifecycle"]
    sheet = xlsx.Sheet("Pugh")
    sheet.add(("Pugh Matrix — {} (tour {})".format(m["title"], m["round"]), xlsx.TITLE))
    datum = next((x["name"] for x in concepts if x["id"] == m["datum_id"]), "—")
    sheet.add("Space : {} · Référence (datum) : {} · Status : {}".format(space, datum, m["status_label"]))
    sheet.add("+ : meilleur que la référence · S : pareil · - : moins bon. La colonne de référence vaut S.")
    header_row = len(sheet.rows) + 1
    sheet.add(*[(h, xlsx.HEADER) for h in FIXED + [x["name"] + (" (réf.)" if x["id"] == m["datum_id"] else "")
                                                    for x in concepts]])
    first = header_row + 1
    for crit in criteria:
        cells = [crit["key"], crit["external_id"] or "", (crit["title"], xlsx.WRAP),
                 cats.get(crit["category"], crit["category"] or ""), phases.get(crit["lifecycle"], "")]
        for x in concepts:
            if x["id"] == m["datum_id"]:
                cells.append(("S", xlsx.LOCKED))
            else:
                cells.append((scores.get((crit["id"], x["id"]), {}).get("score", ""), xlsx.INPUT))
        sheet.add(*cells)
    last = max(len(sheet.rows), first)
    col0 = len(FIXED)
    letters = [xlsx.col_name(col0 + i) for i in range(len(concepts))]
    if concepts and criteria:
        sheet.validations.append(("{}{}:{}{}".format(letters[0], first, letters[-1], last), list(pugh.SCORES)))
        sheet.conditional.append(("{}{}:{}{}".format(letters[0], first, letters[-1], last),
                                  [('{}{}="+"'.format(letters[0], first), xlsx.DXF_DONE),
                                   ('{}{}="-"'.format(letters[0], first), xlsx.DXF_LATE)]))
    sheet.add()
    labels = [("Σ +", '"+"'), ("Σ S", '"S"'), ("Σ -", '"-"')]
    rows = {}
    for label, needle in labels:
        rows[label] = len(sheet.rows) + 1
        sheet.add(*([("", xlsx.TEXT)] * (col0 - 1) + [(label, xlsx.HEADER)]
                    + [{"f": 'COUNTIF({0}{1}:{0}{2},{3})'.format(L, first, last, needle)} for L in letters]))
    net_row = len(sheet.rows) + 1
    sheet.add(*([("", xlsx.TEXT)] * (col0 - 1) + [("Net (+ moins -)", xlsx.HEADER)]
                + [{"f": "{0}{1}-{0}{2}".format(L, rows["Σ +"], rows["Σ -"])} for L in letters]))
    if letters:
        span = "${}${}:${}${}".format(letters[0], net_row, letters[-1], net_row)
        sheet.add(*([("", xlsx.TEXT)] * (col0 - 1) + [("Rang", xlsx.HEADER)]
                    + [{"f": "RANK({}{},{})".format(L, net_row, span)} for L in letters]))
    if m["status"] == "decided":
        chosen = next((x["name"] for x in concepts if x["id"] == m["decision_concept_id"]), "")
        sheet.add()
        sheet.add(("Décision : " + chosen, xlsx.HEADER))
        sheet.add((m["decision_note"], xlsx.WRAP))
    sheet.widths = {0: 11, 1: 12, 2: 48, 3: 18, 4: 22}
    sheet.widths.update({col0 + i: 14 for i in range(len(concepts))})
    sheet.freeze = "{}{}".format(xlsx.col_name(col0), first)
    sheet.landscape_fit = True
    notes = xlsx.Sheet("Notes")
    notes.add(*[(h, xlsx.HEADER) for h in ("Critère", "Concept", "Note", "Commentaire")])
    names = {x["id"]: x["name"] for x in concepts}
    keys = {k["id"]: k["key"] for k in criteria}
    for s in data["scores"]:
        if s.get("note"):
            notes.add(keys.get(s["criterion_id"], ""), names.get(s["concept_id"], ""), s["score"], (s["note"], xlsx.WRAP))
    notes.widths = {0: 11, 1: 20, 2: 6, 3: 70}
    reqs = xlsx.Sheet("Requirements")
    reqs.add(*[(h, xlsx.HEADER) for h in ("Key", "Titre", "Statement", "Status", "Criticality")])
    for k in criteria:
        reqs.add(k["key"], k["title"], (k["statement"] or "", xlsx.WRAP), k["status_name"], k["criticality"] or "")
    reqs.widths = {0: 11, 1: 34, 2: 80, 3: 14, 4: 6}
    return xlsx.write([sheet, notes, reqs])


def api_export(ctx):
    project_id, _ = c.access(ctx)
    data = pugh.detail(ctx.conn, pugh._matrix(ctx, project_id))
    key = c.project_key(ctx.conn, project_id)
    c.log(ctx, "pugh_export", "goldmine_pugh", data["matrix"]["id"], None)
    name = re.sub(r"[^\w\-]+", "_", "{}_Pugh_{}_tour{}".format(key, data["matrix"]["title"], data["matrix"]["round"]),
                  flags=re.UNICODE).strip("_")[:90]
    return RawFile(build(data, key), name + ".xlsx", XLSX)
