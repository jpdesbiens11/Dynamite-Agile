"""The summary of « Compétences et équipe » as Excel and Word (0.60.116, D-O-129): per competency, the lines that need it,
its points, its share, its average, the lines at 4 or 5, the people to hire or gather and the note; then the ratings line by
line (function, brick, one column per competency used). GET …/competencies/summary.xlsx and summary.docx (RawFile: the core
stamps the revision); also a sheet of the workbook and a section of the report of Diamond → Exporter, when the part is on.
"""
from core import prefs
from core.files import RawFile

from . import char_export as CE
from . import competencies as CP
from . import export_data as X
from . import functions as F

HEADER = ["Compétence", "Code", "Lignes", "Points", "Part", "Moyenne", "Notes 4–5", "À embaucher / réunir", "Note"]


def num(value):
    return ("{:.1f}".format(value).rstrip("0").rstrip(".") if isinstance(value, float) else str(value)).replace(".", ",")


def summary_rows(data):
    return [[s["name"], s["code"], s["lines"], s["points"], num(s["share"]) + " %", num(s["average"]), s["high"], num(float(s["people"])),
             s["note"]] for s in data["summary"]]


def total_row(data):
    return ["Total", "", "", data["total_points"], "100 %" if data["total_points"] else "—", "", "", num(float(data["people_total"])), ""]


def columns(data):
    used = {c for ln in data["lines"] for c in ln["ratings"]}
    return [c for c in data["catalog"] if c["code"] in used]


def line_rows(data, cols):
    out = []
    for ln in data["lines"]:
        brick = "{} {}".format(ln["brick"]["code"], ln["brick"]["frozen_text"] if ln["brick"]["frozen"] else ln["brick"]["name"])
        out.append(["{} {}".format(ln["code"], ln["text"]), brick + (" (figée)" if ln["brick"]["frozen"] else "")]
                   + [ln["ratings"].get(c["code"], "") for c in cols])
    return out


def note(data):
    return ("Note de 1 (presque pas) à 5 (au cœur du développement) par ligne fonction → brique de l'arbre fonctionnel. Points = somme "
            "des notes d'une compétence ; Part = ses points sur le total ({} points, {} lignes). « À embaucher / réunir » : la décision "
            "de l'évaluateur. Le profil, la formation, les outils et les livrables de chaque compétence sont dans la Base de connaissances "
            "(BDC) → Compétences de l'équipe (Diamond).").format(data["total_points"], len(data["lines"]))


def sheets(book, kit, data, frame):
    """Two sheets: the summary, then the ratings line by line."""
    from .export_xlsx import _frame, _table
    s = book.sheet("Compétences — synthèse")
    widths = [30, 9, 8, 8, 9, 9, 10, 14, 40]
    _frame(s, frame, "Compétences et équipe — synthèse", widths, kit, "0E7490")
    values = summary_rows(data)
    styles = lambda v: [kit.bold, kit.center] + [kit.center] * 6 + [kit.wrap]  # noqa: E731
    top = _table(s, kit, HEADER, (values + [total_row(data)]) if values else [["—"] + [""] * (len(HEADER) - 1)], widths,
                 styles if values else None)
    s.freeze = "B{}".format(top + 1)
    s.skip()
    r = s.line([note(data)], kit.note, height=58)
    s.merge(r, 0, r, len(widths) - 1)
    cols = columns(data)
    t = book.sheet("Compétences — par ligne")
    widths = [44, 40] + [6] * len(cols)
    _frame(t, frame, "Compétences par ligne fonction → brique", widths, kit, "0E7490")
    head = ["Fonction", "Brique"] + [c["code"] for c in cols]
    rows = line_rows(data, cols)
    top = _table(t, kit, head, rows or [["—", ""]], widths, (lambda v: [kit.wrap, kit.wrap] + [kit.center] * len(cols)) if rows else None)
    t.freeze = "C{}".format(top + 1)
    t.skip()
    r = t.line(["Codes : " + " · ".join("{} {}".format(c["code"], c["name"]) for c in cols)], kit.note, height=44)
    t.merge(r, 0, r, max(len(widths) - 1, 1))


def api_xlsx(ctx):
    from .export_xlsx import Kit
    from .xlsx_book import Book
    pid = F.access(ctx)
    data, fd = CP.payload(ctx.conn, pid), CE.frame_data(ctx.conn, pid)
    book = Book()
    sheets(book, Kit(book), data, fd)
    content = book.bytes(title="Compétences et équipe — {} ({})".format(fd["project"]["name"], fd["project"]["key"]))
    return RawFile(content, X.safe_name(fd, "Competences_et_equipe", "xlsx"), CE.XLSX)


def _text(rows):
    return [[str(x) for x in r] for r in rows]


def section(data, level=1):
    """The summary and the ratings line by line as a Word section (dedicated file, and the report of Diamond → Exporter)."""
    from modules.testing import word_doc as WD
    from .export_docx import _intro, _note, table
    out = [WD.heading(level, "Compétences et équipe"),
           _intro("{} lignes fonction → brique, {} compétences sollicitées, {} points ; {} personne(s) à embaucher ou réunir.".format(
               len(data["lines"]), sum(1 for s in data["summary"] if s["points"]), data["total_points"], num(float(data["people_total"]))))]
    values = summary_rows(data)
    if values:
        out.append(table(HEADER, _text(values + [total_row(data)]), [14, 5, 5, 5, 6, 6, 6, 8, 20], size=15,
                         aligns=["left", "center", "center", "center", "center", "center", "center", "center", "left"]))
    else:
        out.append(_intro("Aucune compétence n'est encore notée dans l'arbre fonctionnel."))
    cols = columns(data)
    if cols:
        out.append(WD.heading(level + 1, "Notes par ligne"))
        out.append(table(["Fonction", "Brique"] + [c["code"] for c in cols], _text(line_rows(data, cols)),
                         [14, 12] + [4] * len(cols), size=12, aligns=["left", "left"] + ["center"] * len(cols)))
        out.append(_note("Codes : " + " · ".join("{} {}".format(c["code"], c["name"]) for c in cols)))
    out.append(_note(note(data)))
    return "".join(out)


def api_docx(ctx):
    from modules.testing import word_doc as WD
    from .export_docx import _mark
    pid = F.access(ctx)
    data, fd = CP.payload(ctx.conn, pid), CE.frame_data(ctx.conn, pid)
    initials = prefs.get(ctx.conn, ctx.user["id"]).get("initials") or ""
    meta = {"title": "Compétences et équipe", "subject": "{} ({})".format(fd["project"]["name"], fd["project"]["key"])[:80],
            "prepared": ctx.user["display_name"][:80], "docno": "CE-{}".format(fd["project"]["key"])[:40], "rev": "A",
            "doctype": "Sommaire", "lang": "fr"}
    raw = WD.build(meta, section(data), "Export de Diamond", initials)
    return RawFile(_mark(raw), X.safe_name(fd, "Competences_et_equipe", "docx"), CE.DOCX)
