"""Goldmine Q&A traceability files (D-B-037, D-B-044): the full register and
the archive of every exported / imported Q&A workbook.

- Register (GET .../qa/register.xlsx): every question and answer with its
  stamp, the whole event history, the requirements with their counts.
- Archives: every Q&A workbook exported to or imported from the client is
  kept in data/qa_archives/<KEY>/ (date-time in the name), listed and
  downloadable from the Q&A screen -- the history of the exchanges.
"""
import datetime as dt
import re
from pathlib import Path

from core.errors import ApiError
from core.files import RawFile
from modules.exploration import xlsx

from . import common as c
from . import qa

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
NAME_RE = re.compile(r"^[A-Z0-9]{2,10}_\d{8}-\d{6}_[A-Za-z_]+\.xlsx$")


def _dir(ctx, key):
    return Path(ctx.data_dir) / "qa_archives" / key


def archive(ctx, project_id, kind, data):
    """Keep a copy of an exported or imported workbook; returns its file name."""
    key = c.project_key(ctx.conn, project_id)
    folder = _dir(ctx, key)
    folder.mkdir(parents=True, exist_ok=True)
    name = "{}_{}_{}.xlsx".format(key, dt.datetime.now().strftime("%Y%m%d-%H%M%S"), kind)
    (folder / name).write_bytes(data)
    return name


def archive_and_send(ctx, project_id, kind, sheets):
    data = xlsx.write(sheets)
    name = archive(ctx, project_id, kind, data)
    return RawFile(data, name, XLSX_MIME)


def _requirements(conn, project_id):
    rows = conn.execute(
        "SELECT i.id, i.number, i.title, s.name AS status, r.* FROM agile_issues i JOIN agile_issue_types t ON t.id = i.type_id "
        "JOIN agile_statuses s ON s.id = i.status_id LEFT JOIN agile_requirements r ON r.issue_id = i.id "
        "WHERE i.project_id = ? AND t.is_requirement = 1 ORDER BY i.number", (project_id,)).fetchall()
    return [dict(r) for r in rows]


def _readme(title, lines):
    sheet = xlsx.Sheet("Lisez-moi")
    sheet.add((title, xlsx.TITLE))
    sheet.add()
    for line in lines:
        if isinstance(line, tuple):
            sheet.add((line[0], xlsx.HEADER), (line[1], xlsx.WRAP))
        else:
            sheet.add((line, xlsx.WRAP))
    sheet.widths = {0: 34, 1: 100}
    return sheet


def api_archives(ctx):
    project_id, _ = c.access(ctx, "reader")
    folder = _dir(ctx, c.project_key(ctx.conn, project_id))
    files = sorted(folder.glob("*.xlsx"), reverse=True) if folder.exists() else []
    return {"archives": [{"name": f.name, "size": f.stat().st_size,
                          "kind": "Import" if "import" in f.name else ("Registre" if "registre" in f.name else "Export")}
                         for f in files[:200]]}


def api_archive_file(ctx):
    project_id, _ = c.access(ctx, "reader")
    name = ctx.params.get("name", "")
    key = c.project_key(ctx.conn, project_id)
    path = _dir(ctx, key) / name
    if not NAME_RE.match(name) or not name.startswith(key + "_") or not path.is_file():
        raise ApiError(404, "Archive introuvable.")
    return RawFile(path.read_bytes(), name, XLSX_MIME, export=False)


# --------------------------------------------------------------------------
# Full register (traceability)
# --------------------------------------------------------------------------
def api_register(ctx):
    project_id, _ = c.access(ctx, "reader")
    conn = ctx.conn
    items = qa.list_project(conn, project_id)
    history = qa.events(conn, [q["id"] for q in items])
    reg = xlsx.Sheet("Registre Q&R")
    reg.add(*[(h, xlsx.HEADER) for h in ("Réf.", "Key", "ID client", "Requirement", "Status requirement", "Rév. à la question", "Sens",
                                         "Question", "Posée (date-initiales)", "Posée par", "Réponse", "Answered (date-initiales)",
                                         "Répondue par", "Status", "Closed (date-initiales)", "Assignee (équipe)", "Due Date", "Bloquante")])
    for q in items:
        reg.add(q["ref"], q["req_key"], q["req_external"] or "", q["req_title"], q["req_status"], q["req_revision"],
                "Équipe → client" if q["direction"] == "team" else "Client → équipe", (q["question"], xlsx.WRAP), q["asked_stamp"],
                q["asked_who"], (q["answer"], xlsx.WRAP), q["answered_stamp"], q["answered_who"], q["status_label"],
                q["closed_stamp"], q["owner_name"] or "", q["due_date"] or "", "Oui" if q["blocking"] else "")
    reg.widths = {0: 11, 1: 10, 2: 11, 3: 28, 4: 16, 5: 8, 6: 12, 7: 55, 8: 15, 9: 16, 10: 55, 11: 15, 12: 16, 13: 10,
                  14: 15, 15: 16, 16: 11, 17: 9}
    reg.freeze, reg.autofilter, reg.landscape_fit = "C2", "A1:R{}".format(max(len(items) + 1, 2)), True
    hist = xlsx.Sheet("Historique")
    hist.add(*[(h, xlsx.HEADER) for h in ("Réf.", "Key", "Événement", "Texte", "Date-initiales", "Par", "Horodatage")])
    kinds = qa.EVENT_KINDS
    for q in items:
        for e in history.get(q["id"], []):
            hist.add(q["ref"], q["req_key"], kinds.get(e["kind"], e["kind"]), (e["text"], xlsx.WRAP), e["stamp"],
                     e["name"] or e["user_name"] or "", e["at"].replace("T", " "))
    hist.widths = {0: 11, 1: 10, 2: 12, 3: 80, 4: 15, 5: 18, 6: 18}
    hist.freeze = "A2"
    reqs = xlsx.Sheet("Requirements")
    reqs.add(*[(h, xlsx.HEADER) for h in ("Key", "ID client", "Titre", "Statement", "Status", "Revision", "Questions", "Non closes")])
    key = c.project_key(conn, project_id)
    for r in _requirements(conn, project_id):
        mine = [q for q in items if q["issue_id"] == r["id"]]
        reqs.add("{}-{}".format(key, r["number"]), r["external_id"] or "", r["title"], (r["statement"] or "", xlsx.WRAP),
                 r["status"], r["revision"] or "", len(mine), sum(1 for q in mine if q["status"] not in qa.DONE))
    reqs.widths = {0: 10, 1: 11, 2: 30, 3: 70, 4: 18, 5: 8, 6: 10, 7: 10}
    reqs.freeze = "C2"
    readme = _readme("Registre des questions et réponses — requirements", [
        ("Projet", key), ("Exporté le", dt.datetime.now().strftime("%Y-%m-%d %H:%M")), ("Exporté par", ctx.user["display_name"]),
        ("Questions", str(len(items))), ("Non closes", str(sum(1 for q in items if q["status"] not in qa.DONE))),
        ("Signature", "Chaque question, réponse et fermeture porte « JJMMAAAA-INITIALES » (ex. 06092026-JDE) ; "
                      "la feuille « Historique » garde toutes les étapes, y compris les réponses remplacées."),
        ("Sens", "Équipe → client : question de l'équipe (Qteam), réponse du client (Acust). Client → équipe : question du "
                 "client (Qcust), réponse de l'équipe (Ateam).")])
    c.log(ctx, "goldmine_qa_register", "project", project_id, {"questions": len(items)})
    return archive_and_send(ctx, project_id, "registre_QR", [readme, reg, hist, reqs])
