"""The summary of the special characteristics (0.60.102, D-O-110): one line per characteristic C-n whose DFMEA row has a
confirmed class, read from the links -- class (the customer's process symbol), characteristic, specification, Diamond
part, company PN, DFMEA line, PFMEA, Control Plan, required Cpk, Cpk, status. Company PN, PFMEA, Control Plan and the
measured Cpk come with the next increments of D-O-109; until then their cells say so instead of staying blank.
GET …/characteristics/summary.xlsx and summary.docx (RawFile: the core stamps the revision); a sheet of the workbook of
Diamond → Exporter and a section of its Word report.
"""
import datetime as dt

from core import APP_VERSION, prefs
from core.files import RawFile

from . import char_spec as SP
from . import characteristics as CH
from . import export_data as X
from . import functions as F

HEADER = ["Char.", "Class", "Characteristic", "Specification", "Part (Diamond)", "Company PN", "DFMEA", "PFMEA", "Control Plan",
          "Cpk req.", "Cpk", "Status"]
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def cpk_req(c):
    if c["control"] == "test100":
        return "100 %"
    return SP.fmt(c["cpk_req"], 2) if c["cpk_req"] is not None else "—"


def cpk(c):
    return {"test100": "essai 100 %", "design": "—"}.get(c["control"], "à mesurer")


def parts(c):
    first = " ".join(x for x in (c["part"], c["part_name"] or "") if x)
    return first + (" · " + c["part2"] if c["part2"] else "") if first else "à préciser"


def line(c):
    return [c["code"], c["class_symbol"], c["label"], c["spec"] or "à écrire", parts(c), "—",
            "L{}".format(c["dfmea"]["line"]) if c["dfmea"] else "—", "—", "—", cpk_req(c), cpk(c), c["status_label"]]


def rows(data):
    return [line(c) for c in data["summary"]]


def note(data):
    cust = data["customer"]
    return ("Symboles du client « {} » : {} = {}, {} = {}. Une ligne par caractéristique dont la ligne du DFMEA a une classe confirmée ; "
            "rien n'y est ressaisi. Company PN, PFMEA, Control Plan et Cpk mesuré : à venir (numéros de pièce de l'entreprise, procédés, "
            "plans de contrôle).").format(cust["name"], cust["cc_symbol"], cust["cc_label"], cust["sc_symbol"], cust["sc_label"])


def _project(conn, pid):
    return dict(conn.execute("SELECT id, key, name FROM projects WHERE id = ?", (pid,)).fetchone())


def sheet(book, kit, data, frame_data):
    """The sheet « Caractéristiques spéciales » (dedicated file and the workbook of Diamond → Exporter)."""
    from .export_xlsx import _frame, _table
    s = book.sheet("Caractéristiques spéciales")
    widths = [8, 8, 30, 18, 26, 14, 8, 9, 10, 8, 12, 26]
    _frame(s, frame_data, "Sommaire des caractéristiques spéciales", widths, kit, "D97706")
    values = rows(data)
    styles = lambda v: [kit.bold, kit.cls.get({data["customer"]["cc_symbol"]: "CC", data["customer"]["sc_symbol"]: "SC"}.get(v[1]), kit.center)] + \
        [kit.wrap] * 4 + [kit.center] * 6 + [kit.wrap]  # noqa: E731
    top = _table(s, kit, HEADER, values or [["—"] + [""] * (len(HEADER) - 1)], widths, styles if values else None)
    s.freeze = "C{}".format(top + 1)
    s.skip()
    r = s.line([note(data)], kit.note, height=44)  # wrapped: the whole note prints on the page
    s.merge(r, 0, r, len(widths) - 1)


def frame_data(conn, pid):
    now = dt.datetime.now()
    return {"project": _project(conn, pid), "date": now.strftime("%Y-%m-%d"), "version": APP_VERSION, "stamp": now.strftime("%Y-%m-%d %H:%M")}


def api_xlsx(ctx):
    from .export_xlsx import Kit
    from .xlsx_book import Book
    pid = F.access(ctx)
    data, fd = CH.payload(ctx.conn, pid), frame_data(ctx.conn, pid)
    book = Book()
    sheet(book, Kit(book), data, fd)
    content = book.bytes(title="Caractéristiques spéciales — {} ({})".format(fd["project"]["name"], fd["project"]["key"]))
    return RawFile(content, X.safe_name(fd, "Caracteristiques_speciales", "xlsx"), XLSX)


def section(data, level=1):
    """The summary as a Word section (dedicated file, and the report of Diamond → Exporter)."""
    from modules.testing import word_doc as WD
    from .export_docx import _intro, _note, table
    counts = data["counts"]
    out = [WD.heading(level, "Sommaire des caractéristiques spéciales"),
           _intro("{} CC et {} SC, chacune sur une cote ou un seuil exact d'une pièce, avec sa ligne du DFMEA, son Cpk exigé et "
                  "l'état de son contrôle.".format(counts.get("CC", 0), counts.get("SC", 0)))]
    values = rows(data)
    if values:
        out.append(table(HEADER, values, [5, 5, 13, 10, 11, 7, 6, 6, 6, 5, 7, 10], size=14,
                         aligns=["left", "center", "left", "left", "left", "center", "center", "center", "center", "center", "center", "left"]))
    else:
        out.append(_intro("Aucune caractéristique n'a encore de classe confirmée dans le DFMEA."))
    out.append(_note(note(data)))
    return "".join(out)


def api_docx(ctx):
    from modules.testing import word_doc as WD
    from .export_docx import _mark
    pid = F.access(ctx)
    data, fd = CH.payload(ctx.conn, pid), frame_data(ctx.conn, pid)
    initials = prefs.get(ctx.conn, ctx.user["id"]).get("initials") or ""
    meta = {"title": "Sommaire des caractéristiques spéciales", "subject": "{} ({})".format(fd["project"]["name"], fd["project"]["key"])[:80],
            "prepared": ctx.user["display_name"][:80], "docno": "CS-{}".format(fd["project"]["key"])[:40], "rev": "A",
            "doctype": "Sommaire", "lang": "fr"}
    raw = WD.build(meta, section(data), "Export de Diamond", initials)
    return RawFile(_mark(raw), X.safe_name(fd, "Caracteristiques_speciales", "docx"), DOCX)
