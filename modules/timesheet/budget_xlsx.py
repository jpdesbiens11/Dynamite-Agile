"""Timesheet → Spaces et organismes: Funding Spaces in Excel (D-B-101).

Export: one Funding Space per sheet (or all of them, one sheet each) -- key, label, active, then its Budget Lines
(Code, Label, Claimable, Active). The same layout comes back in.
Import, reviewed space by space before anything is written: each sheet is « new » (key empty or unknown), « no
change », or the list of changes found (label, active, lines added, line labels, Claimable, Active). The administrator
accepts or refuses each Funding Space; only the accepted ones are applied, in one transaction. Rules kept from
budget.py: a code never changes and never moves to another space; nothing is deleted (a line absent from the file
stays as it is); a space used by a Space is not deactivated. Every problem names the cell value and the fix.
"""
import json
import re
from pathlib import Path

from core import audit, db, permissions, validate
from core.errors import ApiError
from core.files import RawFile
from modules.exploration import xlsx

from . import budget

YES = {"oui", "yes", "x", "1", "true", "vrai", "o", "y"}
NO = {"non", "no", "", "0", "false", "faux", "n"}
HEAD = ["Code", "Label", "Claimable", "Active"]


def _yes(value, where, problems):
    v = str(value or "").strip().lower()
    if v in YES:
        return True
    if v in NO:
        return False
    problems.append("{} : « {} » n'est ni oui ni non. Correctif : écrivez oui ou non.".format(where, value))
    return None


def _sheet(s, sheet_name):
    sheet = xlsx.Sheet(sheet_name)
    sheet.add(("Funding Space key (ne pas modifier ; vide = nouvel espace)", xlsx.HEADER), (s["key"] or "", xlsx.LOCKED))
    sheet.add(("Label", xlsx.HEADER), (s["label"], xlsx.INPUT))
    sheet.add(("Active", xlsx.HEADER), ("oui" if s["active"] else "non", xlsx.INPUT))
    sheet.add()
    sheet.add(*[(h, xlsx.HEADER) for h in HEAD])
    for t in s["tasks"]:
        sheet.add((t["key"], xlsx.LOCKED), (t["label"], xlsx.INPUT), ("oui" if t["claimable"] else "non", xlsx.INPUT),
                  ("oui" if t["active"] else "non", xlsx.INPUT))
    sheet.widths = {0: 22, 1: 48, 2: 12, 3: 10}
    sheet.freeze = "A6"
    return sheet


def api_export(ctx):
    permissions.require_admin(ctx.user)
    sets = budget.structure(ctx.conn)
    sid = ctx.params.get("sid")
    chosen = [(k, s) for k, s in sets.items() if sid is None or str(s["id"]) == str(sid)]
    if not chosen:
        raise ApiError(404, "Funding Space introuvable.")
    sheets = [_sheet(dict(s, key=k), re.sub(r"[\[\]:*?/\\]", "-", s["label"])[:28] + " " + str(i + 1)) for i, (k, s) in enumerate(chosen)]
    name = "Funding_Spaces.xlsx" if sid is None else "Funding_Space_{}.xlsx".format(re.sub(r"\W+", "_", chosen[0][1]["label"])[:40])
    audit.log_action(ctx.conn, ctx.user["id"], "timesheet_budget_export", "timesheet", None, {"sets": [k for k, _ in chosen]}, ctx.ip)
    return RawFile(xlsx.write(sheets), name, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# --------------------------------------------------------------------------
# Import: read, compare, review, apply
# --------------------------------------------------------------------------
def _parse(name, rows):
    """{sheet, key, label, active, lines: [{code, label, claimable, active, row}], problems} or None (not a Funding Space)."""
    if len(rows) < 5 or not str((rows[0] or [""])[0]).startswith("Funding Space key"):
        return None
    cell = lambda r, c: str(rows[r][c]).strip() if r < len(rows) and c < len(rows[r]) and rows[r][c] is not None else ""
    problems = []
    out = {"sheet": name, "key": cell(0, 1), "label": cell(1, 1), "problems": problems, "lines": []}
    out["active"] = _yes(cell(2, 1), "Feuille « {} », cellule B3 (Active)".format(name), problems)
    if not out["label"]:
        problems.append("Feuille « {} », cellule B2 : Label vide. Correctif : nommez le Funding Space.".format(name))
    for r in range(5, len(rows)):
        code = cell(r, 0).upper()
        if not code and not cell(r, 1):
            continue
        where = "Feuille « {} », ligne {}".format(name, r + 1)
        if not budget.CODE_RE.match(code):
            problems.append("{} : code « {} » invalide. Correctif : 2 à 5 lettres, un tiret, 2 à 4 lettres ou chiffres (ex. "
                            "PARI-03).".format(where, code))
            continue
        if not cell(r, 1):
            problems.append("{} : Label vide pour {}.".format(where, code))
        out["lines"].append({"code": code, "label": cell(r, 1)[:120], "row": r + 1,
                             "claimable": _yes(cell(r, 2), where + " (Claimable)", problems),
                             "active": _yes(cell(r, 3), where + " (Active)", problems)})
    return out


def _compare(conn, item, sets, taken):
    """Adds status / changes / problems to a parsed sheet, against the database."""
    by_key = {k: s for k, s in sets.items()}
    current = by_key.get(item["key"]) if item["key"] else None
    if current is None and not item["key"]:
        current = next(((k, s) for k, s in sets.items() if s["label"].lower() == item["label"].lower()), (None, None))[1]
        if current is not None:
            item["key"] = next(k for k, s in sets.items() if s is current)
    elif item["key"] and current is None:
        item["problems"].append("Feuille « {} » : clé « {} » inconnue ici. Correctif : videz la cellule B1 pour créer un nouvel "
                                "espace.".format(item["sheet"], item["key"]))
    owner = {t["key"]: k for k, s in sets.items() for t in s["tasks"]}
    changes = []
    if current is None:
        item["status"] = "new"
        changes.append("Nouveau Funding Space « {} » ({} code(s))".format(item["label"], len(item["lines"])))
    else:
        if item["label"] and item["label"] != current["label"]:
            changes.append("Label : « {} » → « {} »".format(current["label"], item["label"]))
        if item["active"] is not None and item["active"] != current["active"]:
            changes.append("Active : {} → {}".format("oui" if current["active"] else "non", "oui" if item["active"] else "non"))
            if not item["active"]:
                used = [r[0] for r in conn.execute("SELECT p.key FROM timesheet_projects t JOIN projects p ON p.id = t.project_id "
                                                   "WHERE t.task_set = ? AND p.is_archived = 0", (item["key"],))]
                if used:
                    item["problems"].append("« {} » est utilisé par {} : il ne peut pas être désactivé. Correctif : rattachez "
                                            "d'abord ces Spaces à un autre espace.".format(current["label"], ", ".join(used)))
    have = {t["key"]: t for t in (current or {"tasks": []})["tasks"]}
    for line in item["lines"]:
        code = line["code"]
        if code in taken:
            item["problems"].append("{} apparaît deux fois dans le fichier.".format(code))
        taken.add(code)
        if code in owner and owner[code] != item["key"]:
            item["problems"].append("{} appartient déjà à l'espace « {} » : un code ne change jamais d'espace.".format(
                code, sets[owner[code]]["label"]))
            continue
        old = have.get(code)
        if old is None:
            changes.append("{} ajouté : « {} »".format(code, line["label"]))
            continue
        if line["label"] and line["label"] != old["label"]:
            changes.append("{} libellé : « {} » → « {} »".format(code, old["label"], line["label"]))
        for f, name in (("claimable", "Claimable"), ("active", "Active")):
            if line[f] is not None and line[f] != old[f]:
                changes.append("{} {} : {} → {}".format(code, name, "oui" if old[f] else "non", "oui" if line[f] else "non"))
    missing = [k for k in have if k not in {l["code"] for l in item["lines"]}]
    if missing:
        item["kept"] = missing  # never deleted
    if current is not None:
        item["status"] = "changed" if changes else "same"
    item["changes"] = changes
    return item


def _folder(ctx):
    path = Path(ctx.data_dir) / "updates" / "incoming"
    path.mkdir(parents=True, exist_ok=True)
    return path


def api_import(ctx):
    """Read an uploaded workbook: the review, nothing written."""
    permissions.require_admin(ctx.user)
    upload = getattr(ctx, "upload", None)
    if upload is None or not upload.data:
        raise ApiError(400, "Aucun fichier reçu. Correctif : choisissez le classeur .xlsx exporté de cet écran.")
    try:
        book = xlsx.read(upload.data, prefer=())
    except xlsx.XlsxError as exc:
        raise ApiError(400, "{} Correctif : enregistrez le fichier au format .xlsx.".format(exc))
    sets, taken = budget.structure(ctx.conn), set()
    items = [_compare(ctx.conn, it, sets, taken) for it in (_parse(n, rows) for n, rows in book.items()) if it]
    if not items:
        raise ApiError(400, "Aucune feuille « Funding Space » dans ce classeur. Correctif : partez d'un export de cet écran "
                            "(cellule A1 « Funding Space key… »).")
    import secrets
    token = secrets.token_hex(16)
    (_folder(ctx) / (token + ".funding.json")).write_text(json.dumps(items, ensure_ascii=False), "utf-8")
    return {"token": token, "spaces": items}


def _apply_one(ctx, item, pid):
    now = db.utc_now()
    if item["status"] == "new":
        n = ctx.conn.execute("SELECT COUNT(*) FROM timesheet_budget_sets").fetchone()[0] + 1
        key = "set{}".format(n)
        while ctx.conn.execute("SELECT 1 FROM timesheet_budget_sets WHERE key = ?", (key,)).fetchone():
            n += 1
            key = "set{}".format(n)
        set_id = ctx.conn.execute("INSERT INTO timesheet_budget_sets (project_id, key, label, position, active, created_at, updated_at) "
                                  "VALUES (?, ?, ?, ?, ?, ?, ?)", (pid, key, item["label"], n, int(item["active"] is not False), now, now)).lastrowid
    else:
        row = ctx.conn.execute("SELECT * FROM timesheet_budget_sets WHERE key = ?", (item["key"],)).fetchone()
        set_id = row["id"]
        ctx.conn.execute("UPDATE timesheet_budget_sets SET label = ?, active = ?, updated_at = ? WHERE id = ?",
                         (item["label"] or row["label"], int(row["active"] if item["active"] is None else item["active"]), now, set_id))
    for line in item["lines"]:
        old = ctx.conn.execute("SELECT * FROM timesheet_budget_lines WHERE code = ?", (line["code"],)).fetchone()
        if old is None:
            pos = ctx.conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM timesheet_budget_lines WHERE set_id = ?", (set_id,)).fetchone()[0]
            ctx.conn.execute("INSERT INTO timesheet_budget_lines (set_id, code, label, claimable, position, active, created_at, updated_at) "
                             "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (set_id, line["code"], line["label"] or line["code"],
                                                                 int(line["claimable"] is not False), pos, int(line["active"] is not False), now, now))
        else:
            ctx.conn.execute("UPDATE timesheet_budget_lines SET label = ?, claimable = ?, active = ?, updated_at = ? WHERE id = ?",
                             (line["label"] or old["label"], int(old["claimable"] if line["claimable"] is None else line["claimable"]),
                              int(old["active"] if line["active"] is None else line["active"]), now, old["id"]))


def api_apply(ctx):
    permissions.require_admin(ctx.user)
    token = re.sub(r"[^a-f0-9]", "", str(ctx.params.get("token") or ""))[:32]
    path = _folder(ctx) / (token + ".funding.json")
    if not token or not path.exists():
        raise ApiError(404, "Import introuvable ou déjà appliqué. Correctif : importez le classeur de nouveau.")
    accepted = {str(s) for s in (ctx.body.get("accept") or [])}
    items = json.loads(path.read_text("utf-8"))
    sets, taken = budget.structure(ctx.conn), set()
    fresh = [_compare(ctx.conn, dict(it, problems=[p for p in it["problems"] if "cellule" in p or "ligne" in p]), sets, taken)
             for it in items]  # compared again: the database may have changed since the review
    pid = budget._company_id(ctx.conn)
    done, refused = [], []
    for it in fresh:
        if it["sheet"] not in accepted or it["status"] == "same":
            refused.append(it["sheet"])
            continue
        if it["problems"]:
            raise ApiError(409, "« {} » a des problèmes : {} Rien n'a été écrit.".format(it["sheet"], " | ".join(it["problems"][:5])))
        _apply_one(ctx, it, pid)
        done.append({"sheet": it["sheet"], "label": it["label"], "changes": len(it["changes"])})
    path.unlink()
    audit.log_action(ctx.conn, ctx.user["id"], "timesheet_budget_import", "timesheet", None,
                     {"applied": [d["label"] for d in done], "refused": refused}, ctx.ip)
    return {"applied": done, "refused": refused}


api_import.accepts_binary = True
