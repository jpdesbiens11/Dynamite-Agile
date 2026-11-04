"""Goldmine Q&A exchange with the client in one Excel table (D-B-037, D-B-044).

« Exporter les Q&R » (GET .../qa/client.xlsx):
- « Lisez-moi »: how to fill it in;
- « Q&R »: EVERY question of the project in one table, whatever its state
  (open, answered, closed, cancelled). Nothing is locked: the client may
  change an answer, a status (drop-down), add a follow-up comment, or add a
  new question on an empty line (requirement key + question). Yellow =
  expected to be filled in; the status cell is coloured by a rule;
- « Synthèse »: live counts per status and per direction (COUNTIF
  formulas on the Q&R table, updated while the client edits);
- « Requirements »: the requirements for reference, with live counts.
« Importer les Q&R » (POST .../qa/import?dry_run=1): each line is compared
with the register -- new question, new answer, status change, comment --
dry run first, then applied, every change stamped « JJMMAAAA-INI ».
Importing the same file twice changes nothing. Every exported and imported
workbook is archived (qa_register.py).
"""
import re
import unicodedata

from core import uploads
from core.errors import ApiError
from modules.exploration import xlsx

from . import common as c
from . import qa
from .qa_register import _readme, _requirements, archive, archive_and_send

SHEET = "Q&R"
LEGACY = ("Requirements",)  # 0.19 package: still accepted
HEAD = ["Réf.", "Requirement Key", "Requirement", "Requirement Statement", "Sens", "Question", "Posée le", "Posée par",
        "Réponse", "Répondue le", "Répondue par", "Status", "Commentaire / suivi", "Vos initiales", "Due Date", "Blocking"]
# D-B-085: headers of files exported before the English vocabulary (a customer may send one back)
LEGACY_HEAD = {"Requirement Key": "Clé exigence", "Requirement": "Exigence", "Requirement Statement": "Énoncé de l'exigence",
               "Status": "Statut", "Due Date": "Échéance", "Blocking": "Bloquante"}
DIRECTION_LABEL = {"team": "Équipe → client", "cust": "Client → équipe"}
STATUS_BY_LABEL = {qa._ascii(v).lower(): k for k, v in qa.STATUSES.items()}
STATUS_BY_LABEL.update({qa._ascii(v).lower(): k for k, v in {  # D-B-085: former French labels still read
    "open": "Ouverte", "answered": "Répondue", "closed": "Close", "cancelled": "Annulée"}.items()})
EMPTY_LINES = 40


def _norm(text):
    text = unicodedata.normalize("NFKD", str(text or "").strip().casefold())
    return re.sub(r"[^a-z0-9]+", " ", "".join(ch for ch in text if not unicodedata.combining(ch))).strip()


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------
def api_client_package(ctx):
    project_id, _ = c.access(ctx, "reader")
    conn = ctx.conn
    key = c.project_key(conn, project_id)
    items = qa.list_project(conn, project_id)
    history = qa.events(conn, [q["id"] for q in items])
    project = conn.execute("SELECT name FROM projects WHERE id = ?", (project_id,)).fetchone()
    L, I = xlsx.LOCKED, xlsx.INPUT
    table = xlsx.Sheet(SHEET)
    table.add(*[(h, xlsx.HEADER) for h in HEAD])
    for q in sorted(items, key=lambda x: (x["number"], x["direction"], x["seq"])):
        last_comment = next((e["text"] for e in reversed(history.get(q["id"], [])) if e["kind"] == "comment"), "")
        table.add((q["ref"], L), (q["req_key"], L), (q["req_title"], L), (q["req_statement"] or "", L),
                  (DIRECTION_LABEL[q["direction"]], L), (q["question"], L), (q["asked_stamp"], L), (q["asked_who"], L),
                  (q["answer"], I), (q["answered_stamp"], L), (q["answered_who"], L), (q["status_label"], I),
                  (last_comment, I), ("", I), (q["due_date"] or "", L), ("Oui" if q["blocking"] else "", L))
    first_empty = len(table.rows) + 1
    for _ in range(EMPTY_LINES):  # new client questions: key + question
        table.add(("", L), ("", I), ("", L), ("", L), ("Client → équipe", L), ("", I), ("", L), ("", L),
                  ("", L), ("", L), ("", L), ("", L), ("", I), ("", I), ("", L), ("", L))
    last = len(table.rows)
    table.validations.append(("L2:L{}".format(last), list(qa.STATUSES.values())))
    n_req = len(_requirements(conn, project_id))
    table.validations.append(("B{}:B{}".format(first_empty, last), "='Requirements'!$A$2:$A${}".format(max(n_req + 1, 2))))
    table.conditional.append(("L2:L{}".format(last), [('$L2="Closed"', 1), ('$L2="Open"', 2), ('$L2="Cancelled"', 0)]))
    table.widths = {0: 11, 1: 11, 2: 26, 3: 40, 4: 12, 5: 50, 6: 14, 7: 16, 8: 50, 9: 14, 10: 16, 11: 12, 12: 40, 13: 9, 14: 11, 15: 9}
    table.freeze, table.autofilter = "C2", "A1:P{}".format(last)
    rng = "'{}'!{{}}2:{{}}{}".format(SHEET, last)
    summary = xlsx.Sheet("Synthèse")
    summary.add(("Synthèse des Q&R (se met à jour pendant la saisie)", xlsx.TITLE))
    summary.add()
    summary.add(*[(h, xlsx.HEADER) for h in ("Status", "Équipe → client", "Client → équipe", "Total")])
    for label in qa.STATUSES.values():
        n = len(summary.rows) + 1
        summary.add(label, {"f": 'COUNTIFS({},"{}",{},"Équipe → client")'.format(rng.format("L", "L"), label, rng.format("E", "E"))},
                    {"f": 'COUNTIFS({},"{}",{},"Client → équipe",{},"<>")'.format(rng.format("L", "L"), label, rng.format("E", "E"),
                                                                               rng.format("F", "F"))},
                    {"f": "B{0}+C{0}".format(n)})
    summary.add(("Nouvelles questions saisies", xlsx.HEADER),
                {"f": 'COUNTIFS({},"",{},"<>")'.format(rng.format("A", "A"), rng.format("F", "F"))})
    summary.widths = {0: 30, 1: 14, 2: 14, 3: 10}
    reqs = xlsx.Sheet("Requirements")
    reqs.add(*[(h, xlsx.HEADER) for h in ("Key", "ID client", "Titre", "Statement", "Revision", "Questions", "Open")])
    for r in _requirements(conn, project_id):
        n = len(reqs.rows) + 1
        reqs.add("{}-{}".format(key, r["number"]), r["external_id"] or "", r["title"], (r["statement"] or "", xlsx.WRAP), r["revision"] or "",
                 {"f": "COUNTIF({},A{})".format(rng.format("B", "B"), n)},
                 {"f": 'COUNTIFS({},A{},{},"Open")'.format(rng.format("B", "B"), n, rng.format("L", "L"))})
    reqs.widths = {0: 10, 1: 11, 2: 30, 3: 70, 4: 8, 5: 10, 6: 10}
    reqs.freeze = "C2"
    readme = _readme("Q&A sur les requirements", [
        ("Projet", "{} — {}".format(key, project["name"])),
        ("Feuille « Q&R »", "Toutes les questions du projet, quel que soit leur status. Rien n'est verrouillé."),
        ("Répondre", "Écrivez dans « Réponse » (colonne I) les questions « Équipe → client » ouvertes."),
        ("Status", "Menu de la colonne L : Open, Answered, Closed (réponse acceptée), Cancelled. Vous pouvez le changer."),
        ("Suivi", "Un commentaire dans « Commentaire / suivi » (colonne M) est ajouté à l'historique signé."),
        ("Nouvelle question", "Sur une ligne vide en bas : la clé du requirement (colonne B, menu) et la question (colonne F)."),
        ("Signature", "Indiquez vos initiales (colonne N) : chaque changement est daté et signé à l'import (traçabilité)."),
        ("Synthèse", "La feuille « Synthèse » compte les questions par status pendant que vous travaillez."),
        "Renvoyez le fichier tel quel : l'équipe l'importe, les changements apparaissent dans la plateforme et le fichier est archivé."])
    c.log(ctx, "goldmine_qa_export", "project", project_id, {"questions": len(items)})
    return archive_and_send(ctx, project_id, "export_QR", [readme, table, summary, reqs])


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------
def _rows(sheet_rows):
    if not sheet_rows:
        return []
    heads = [_norm(h) for h in sheet_rows[0]]
    col = {name: heads.index(_norm(name)) for name in HEAD if _norm(name) in heads}
    for name, old in LEGACY_HEAD.items():
        if name not in col and _norm(old) in heads:
            col[name] = heads.index(_norm(old))
    out = []
    for n, row in enumerate(sheet_rows[1:], start=2):
        get = lambda name: (str(row[col[name]]).strip() if name in col and col[name] < len(row) and row[col[name]] is not None else "")
        values = {name: get(name) for name in HEAD}
        if any(values[k] for k in ("Réf.", "Question", "Réponse", "Commentaire / suivi")):
            out.append((n, values))
    return out


def plan_import(conn, project_id, sheets):
    key = c.project_key(conn, project_id)
    issues = {"{}-{}".format(key, r["number"]): r for r in _requirements(conn, project_id)}
    items = {q["ref"]: q for q in qa.list_project(conn, project_id)}
    history = qa.events(conn, [q["id"] for q in items.values()])
    plan = []

    def add(line, ref, action, message, **op):
        plan.append(dict(sheet=SHEET, line=line, ref=ref, action=action, message=message, **op))

    for line, v in _rows(sheets.get(SHEET, [])):
        ref, who = v["Réf."], v["Vos initiales"]
        if not ref:
            k, text = v["Requirement Key"].upper(), v["Question"]
            if not text:
                continue
            if k not in issues:
                add(line, k or "—", "refused", "Key de requirement « {} » inconnue. Correctif : choisissez-la dans le menu de la colonne B.".format(k))
            elif any(q["issue_id"] == issues[k]["id"] and q["question"] == text for q in items.values()):
                add(line, k, "unchanged", "Question déjà enregistrée.")
            else:
                add(line, k, "create", "Nouvelle question du client : " + text[:120], issue_id=issues[k]["id"], text=text, who=who)
            continue
        q = items.get(ref)
        if q is None:
            add(line, ref, "refused", "Référence inconnue. Correctif : ne modifiez pas la colonne « Réf. ».")
            continue
        changed = False
        answer = v["Réponse"]
        if answer and answer != q["answer"]:
            if q["direction"] == "team":
                add(line, ref, "answer", "Réponse du client : " + answer[:120], qa_id=q["id"], text=answer, who=who)
            else:
                add(line, ref, "comment", "Le client propose de modifier la réponse de l'équipe : " + answer[:100], qa_id=q["id"],
                    text="Modification proposée par le client : " + answer, who=who, reopen=True)
            changed = True
        comment = v["Commentaire / suivi"]
        last = next((e["text"] for e in reversed(history.get(q["id"], [])) if e["kind"] == "comment"), "")
        if comment and comment != last:
            add(line, ref, "comment", "Commentaire : " + comment[:120], qa_id=q["id"], text=comment, who=who)
            changed = True
        label = v["Status"]
        if label:
            status = STATUS_BY_LABEL.get(qa._ascii(label).lower())
            if status is None:
                add(line, ref, "refused", "Status « {} » inconnu. Correctif : {}.".format(label, ", ".join(qa.STATUSES.values())))
                continue
            # the status after the answer / contested answer above, then the client's own choice if he changed it
            after = "answered" if (answer and answer != q["answer"] and q["direction"] == "team") else (
                "open" if (answer and answer != q["answer"]) else q["status"])
            # an « Open » left untouched next to an answer that is already recorded is not a request to reopen
            stale = status == "open" and q["status"] == "answered" and answer and answer == q["answer"]
            if status != q["status"] and status != after and not stale:
                add(line, ref, "status", "Status : {} → {}".format(q["status_label"], qa.STATUSES[status]), qa_id=q["id"],
                    status=status, who=who)
                changed = True
        if not changed:
            add(line, ref, "unchanged", "Aucun changement.")
    return plan


def apply_plan(ctx, project_id, plan):
    conn = ctx.conn
    for op in plan:
        name = (op.get("who") or "").strip()[:20] or qa.CLIENT_DEFAULT
        row = conn.execute("SELECT * FROM goldmine_qa WHERE id = ?", (op["qa_id"],)).fetchone() if op.get("qa_id") else None
        if op["action"] == "create":
            issue = conn.execute("SELECT * FROM agile_issues WHERE id = ?", (op["issue_id"],)).fetchone()
            qa_id = qa.create(conn, issue, "cust", op["text"], ctx.user["id"], name, issue["assignee_id"])
            op["ref"] += " · " + qa.ref("cust", conn.execute("SELECT seq FROM goldmine_qa WHERE id = ?", (qa_id,)).fetchone()[0])
        elif op["action"] == "answer":
            qa.answer(conn, row, op["text"], ctx.user["id"], name)
        elif op["action"] == "comment":
            qa.comment(conn, row, op["text"], ctx.user["id"], name)
            if op.get("reopen") and row["status"] != "open":
                qa.set_status(conn, row, "open", ctx.user["id"], name, "Réponse de l'équipe contestée par le client.")
        elif op["action"] == "status":
            qa.set_status(conn, row, op["status"], ctx.user["id"], name)


@uploads.binary_body
def api_import(ctx):
    project_id, _ = c.access(ctx, "editor")
    upload = getattr(ctx, "upload", None)
    if upload is None or not upload.data:
        raise ApiError(400, "Aucun fichier reçu. Correctif : choisissez le fichier .xlsx renvoyé par le client.")
    try:
        sheets = xlsx.read(upload.data)
    except xlsx.XlsxError as exc:
        raise ApiError(400, "{} Correctif : utilisez le fichier exporté par « Exporter les Q&R ».".format(exc))
    if SHEET not in sheets:
        hint = " (fichier de la version 0.19 : exportez de nouveau)" if any(n in sheets for n in LEGACY) else ""
        raise ApiError(400, "Aucune feuille « {} »{}. Correctif : renvoyez le fichier « Exporter les Q&R » sans renommer "
                            "ses feuilles.".format(SHEET, hint))
    plan = plan_import(ctx.conn, project_id, sheets)
    dry = str(ctx.query.get("dry_run", "1")) not in ("0", "false", "non")
    summary = {}
    for op in plan:
        summary[op["action"]] = summary.get(op["action"], 0) + 1
    archived = None
    if not dry:
        apply_plan(ctx, project_id, plan)
        archived = archive(ctx, project_id, "import_QR", upload.data)
        c.log(ctx, "goldmine_qa_import", "project", project_id, dict(summary, archive=archived))
    public = [{k: op[k] for k in ("sheet", "line", "ref", "action", "message")} for op in plan]
    return {"dry_run": dry, "summary": summary, "lines": public, "applied": not dry, "archive": archived}
