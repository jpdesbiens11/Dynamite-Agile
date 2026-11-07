"""Diamond · « Coûts et budget » → Importer (0.60.66, D-O-075): the CSV of the export, back in.

The file is the one « Exporter (.csv) » writes, or the one an AI assistant returns from the prompt of costs_prompt.py:
  - « Budget du projet ;CAD »            → the currency;
  - the « NRE ; Intitulé ; Catégorie… » table → NRE lines: « NRE-3 » updates NRE 3 of the Space, an empty code adds one;
  - the « Pièce ; Désignation ; Quantité ; Prix prototype ; Prix à 100… » table → cost lines: « P-5 » is part 5 of
    Diamond (its line is created or updated), an empty code is a free line (packaging, assembly…), matched by its name;
    the « Prix à N » headers set the three volumes.
The summary and the volume table are computed, never read. Nothing is deleted: a line absent from the file stays.
POST …/costs/import with {"file": text, "apply": false} answers what would change (dry run); "apply": true does it, in one
transaction, every change journalled. Separator « ; », « , » or tab; decimal comma or point; « $ », spaces ignored.
"""
import csv
import io
import re

from core import db
from core.errors import ApiError

from . import costs as C
from . import functions as F

MAX_BYTES = 400_000


def _label_map(labels):
    out = {}
    for key, label in labels.items():
        out[key.lower()] = key
        out[label.lower()] = key
    return out


CATEGORY = _label_map(C.CATEGORIES)
BASIS = _label_map(C.BASES)
PHASE = dict(_label_map(C.PHASES), **{k.lower() + ".": k for k in C.PHASES if k})


def _rows(text):
    text = text.lstrip("﻿").strip()
    fence = re.search(r"```(?:csv)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    sample = "\n".join(text.splitlines()[:20])
    delimiter = max(";,\t", key=sample.count) if any(c in sample for c in ";,\t") else ";"
    return [[c.strip() for c in row] for row in csv.reader(io.StringIO(text), delimiter=delimiter)]


def _money(value):
    value = re.sub(r"[\s  $€]|CAD|USD|EUR", "", str(value or ""))
    return value


def _cell(row, i):
    return row[i] if i < len(row) else ""


def parse(text):
    """{currency, volumes, nre: [...], lines: [...], problems: [...]} from the file, nothing written."""
    out = {"currency": None, "volumes": None, "nre": [], "lines": [], "problems": []}
    section = None
    for n, row in enumerate(_rows(text), 1):
        if not any(row):
            section = None if section in ("summary", "volumes") else section
            continue
        head = row[0].lower()
        if head.startswith("budget du projet"):
            cur = _cell(row, 1).upper()
            if cur in C.CURRENCIES:
                out["currency"] = cur
            section = "summary"
        elif head == "volume":
            section = "volumes"
        elif head == "nre" and _cell(row, 1).lower().startswith("intitul"):
            section = "nre"
        elif head in ("pièce", "piece") and _cell(row, 1).lower().startswith("désignation"):
            section = "lines"
            vols = [re.sub(r"\D", "", c) for c in row[4:7]]
            if len(vols) == 3 and all(vols) and int(vols[0]) < int(vols[1]) < int(vols[2]):
                out["volumes"] = [int(v) for v in vols]
        elif section == "nre":
            code = row[0]
            if code and not re.fullmatch(r"NRE-\d+", code, re.I):
                out["problems"].append("Ligne {} : code NRE « {} » inconnu. Correctif : NRE-3, ou laissez vide pour une nouvelle ligne.".format(n, code[:20]))
                continue
            out["nre"].append({"line": n, "number": int(code.split("-")[1]) if code else None, "body": {
                "title": _cell(row, 1), "category": CATEGORY.get(_cell(row, 2).lower(), _cell(row, 2) or "ingenierie"),
                "phase": PHASE.get(_cell(row, 3).lower(), _cell(row, 3)), "amount": _money(_cell(row, 4)),
                "basis": BASIS.get(_cell(row, 5).lower(), _cell(row, 5) or "estimation"), "supplier": _cell(row, 6), "notes": _cell(row, 7)}})
        elif section == "lines":
            code = row[0]
            if code and not re.fullmatch(r"P-\d+", code, re.I):
                out["problems"].append("Ligne {} : code de pièce « {} » inconnu. Correctif : P-5 (pièce de Diamond), ou vide pour une ligne libre.".format(n, code[:20]))
                continue
            out["lines"].append({"line": n, "part": int(code.split("-")[1]) if code else None, "body": {
                "name": _cell(row, 1), "qty": _money(_cell(row, 2)) or 1, "proto_unit": _money(_cell(row, 3)), "prod_1": _money(_cell(row, 4)),
                "prod_2": _money(_cell(row, 5)), "prod_3": _money(_cell(row, 6)), "supplier": _cell(row, 7),
                "basis": BASIS.get(_cell(row, 8).lower(), _cell(row, 8) or "estimation"), "notes": _cell(row, 9)}})
    if not out["nre"] and not out["lines"] and not out["currency"]:
        raise ApiError(400, "Aucun tableau « NRE » ni « Pièce » trouvé. Correctif : partez du fichier « Exporter (.csv) » de cette page "
                            "et gardez ses lignes d'en-tête.")
    return out


def _plan(conn, pid, data):
    """What the file would change, each line checked with the same rules as the screen."""
    nre_by_number = {r["number"]: r for r in C.nre_rows(conn, pid)}
    parts = {r["number"]: r["id"] for r in conn.execute("SELECT id, number FROM diamond_parts WHERE project_id = ?", (pid,))}
    current = C.lines(conn, pid)
    by_part = {ln["part_id"]: ln for ln in current if ln["part_id"]}
    free = {ln["name"].lower(): ln for ln in current if not ln["part_id"]}
    plan, problems = [], list(data["problems"])
    for item in data["nre"]:
        try:
            fields = C._nre_fields(item["body"], partial=False)
        except ApiError as err:
            problems.append("Ligne {} : {}".format(item["line"], err.message))
            continue
        row = nre_by_number.get(item["number"]) if item["number"] else None
        if item["number"] and row is None:
            problems.append("Ligne {} : NRE-{} absent de ce Space ; la ligne sera ajoutée.".format(item["line"], item["number"]))
        if row is not None and all(row.get(k) == v for k, v in fields.items()):
            continue  # unchanged
        plan.append(("nre", row, fields))
    for item in data["lines"]:
        part_id = None
        if item["part"]:
            part_id = parts.get(item["part"])
            if part_id is None:
                problems.append("Ligne {} : P-{} n'est pas une pièce de Diamond. Correctif : ajoutez la pièce dans la Structure, "
                                "ou videz le code pour une ligne libre.".format(item["line"], item["part"]))
                continue
        try:
            fields = C._line_fields(item["body"], partial=False, free=part_id is None)
        except ApiError as err:
            problems.append("Ligne {} : {}".format(item["line"], err.message))
            continue
        row = by_part.get(part_id) if part_id else free.get(fields["name"].lower())
        if row is not None and row.get("id") is None:
            row = None  # a part of Diamond without its cost line yet
        if row is not None and all(row.get(k) == v for k, v in fields.items() if k != "name" or part_id is None):
            continue  # unchanged
        plan.append(("line", row, dict(fields, part_id=part_id)))
    return plan, problems


def _apply(ctx, pid, data, plan):
    counts = {"nre_new": 0, "nre_updated": 0, "lines_new": 0, "lines_updated": 0}
    now, uid = db.utc_now(), ctx.user["id"]
    if data["currency"] or data["volumes"]:
        s = C.settings(ctx.conn, pid)
        s.update({k: v for k, v in (("currency", data["currency"]), ("volumes", data["volumes"])) if v})
        C.save_settings(ctx.conn, pid, s, uid)
    for kind, row, fields in plan:
        if kind == "nre":
            if row is None:
                C.add_nre(ctx.conn, uid, pid, fields); counts["nre_new"] += 1
            else:
                ctx.conn.execute("UPDATE diamond_cost_nre SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(
                    ", ".join("{} = ?".format(k) for k in fields)), list(fields.values()) + [uid, now, row["id"]])
                counts["nre_updated"] += 1
        else:
            part_id = fields.pop("part_id")
            if part_id:
                fields.pop("name", None)
            if row is None:
                C.add_line(ctx.conn, uid, pid, part_id, fields); counts["lines_new"] += 1
            else:
                ctx.conn.execute("UPDATE diamond_cost_parts SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(
                    ", ".join("{} = ?".format(k) for k in fields)), list(fields.values()) + [uid, now, row["id"]])
                counts["lines_updated"] += 1
    C._log(ctx, "diamond_cost_import", "projects", pid, counts)
    return counts


def api_import(ctx):
    raw = ctx.body.get("file")
    if not isinstance(raw, str) or not raw.strip():
        raise ApiError(400, "Fichier vide. Correctif : choisissez le .csv ou collez le texte rendu par l'assistant IA.")
    if len(raw.encode("utf-8")) > MAX_BYTES:
        raise ApiError(400, "Fichier trop gros ({} Ko au maximum).".format(MAX_BYTES // 1000))
    apply = bool(ctx.body.get("apply"))
    pid = F.access(ctx, "editor")
    data = parse(raw)
    plan, problems = _plan(ctx.conn, pid, data)
    preview = {"nre_new": sum(1 for k, r, _ in plan if k == "nre" and r is None),
               "nre_updated": sum(1 for k, r, _ in plan if k == "nre" and r is not None),
               "lines_new": sum(1 for k, r, _ in plan if k == "line" and r is None),
               "lines_updated": sum(1 for k, r, _ in plan if k == "line" and r is not None),
               "currency": data["currency"], "volumes": data["volumes"], "problems": problems[:30]}
    if not apply:
        return {"preview": preview}
    imported = _apply(ctx, pid, data, plan)  # before the payload: the page shows the new figures at once
    return dict(C.payload(ctx.conn, pid), imported=imported, problems=problems[:30])
