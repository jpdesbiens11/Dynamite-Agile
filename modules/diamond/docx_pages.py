"""« Word » of a Diamond page (0.60.124, D-O-137): the same document as its « PDF » (pdf_pages.py), as a .docx on the template
of the Diamond report -- the functional analysis and DFMEA exports (export_docx.py): cover page with the signature table,
table of contents, numbered headings, header with Doc.-No. and Revision, log of revision, and in the footer the mark
« DynamiteAgile · Co-Intelligence WorkFlow™ ».

POST /api/diamond/p/<pid>/docx  {title, view, sections?: [keys], blocks?: [...]} -- the body of POST …/pdf, checked by the same
code (pdf_pages.fill). Golden Nuggets sends the parts the reader chose (one or the four), each with its guide; a card becomes
a one-cell table tinted with its family colour, its colour bar on the left. Readers of the Space may export; journal
`diamond_export_docx`; the core stamps the file with its revision and registers it (RawFile).
"""
import re

from core import audit
from core.files import RawFile
from modules.testing import word_doc as WD

from . import export_data as X
from . import pdf_doc as P
from . import pdf_pages
from .export_docx import WIDTH, _mark, _note, table

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _hex(rgb):
    return "".join("{:02X}".format(max(0, min(255, int(round(c * 255))))) for c in rgb)


def _widths(header, rows):
    """Column widths that follow the amount of text of each column (as the PDF)."""
    out = []
    for i, h in enumerate(header):
        longest = max([len(str(h))] + [len(str(r[i])) for r in rows[:400] if i < len(r)])
        out.append(max(6, min(60, longest)))
    return out


class WordDoc:
    """The interface of pdf_doc.Doc (h, p, note, bullets, table, card), written as WordprocessingML."""

    def __init__(self, meta):
        self.meta, self.parts = meta, []

    def h(self, level, text):
        self.parts.append(WD.heading(max(1, min(3, int(level))), str(text)))

    def p(self, text, muted=False, italic=False, size=10):
        self.parts.append(WD.para([WD.run(str(text), italic=italic, color=X.MUTED if muted else None)], space_after=120))

    def note(self, text):
        self.parts.append(_note(str(text)))

    def bullets(self, items):
        if items:
            self.parts.append(WD.bullets([str(i) for i in items]) + WD.para("", space_after=60))

    def numbered(self, items):
        for n, item in enumerate(items, start=1):
            self.parts.append('<w:p><w:pPr><w:spacing w:after="60"/><w:ind w:left="720" w:hanging="360"/></w:pPr>{}{}</w:p>'.format(
                WD.run("{}.".format(n), bold=True), '<w:r><w:tab/></w:r>' + WD.run(str(item))))
        if items:
            self.parts.append(WD.para("", space_after=60))

    def table(self, header, rows):
        if header:
            rows = [(list(r) + [""] * len(header))[:len(header)] for r in rows]
            self.parts.append(table([str(h) for h in header], rows, _widths(header, rows), size=16 if len(header) > 6 else 17))

    def card(self, code, title, tag="", color=0, idea="", details=()):
        rgb = P.FAMILY.get(int(color or 0), P.NAVY)
        top = " ".join(x for x in (str(code), "·" if tag and code else "", str(tag)) if x)
        paras = [WD.para([WD.run(top, bold=True, color=X.MUTED, size=15)], space_after=20),
                 WD.para([WD.run(str(title), bold=True, size=22)], space_after=40, keep_next=True)]
        if idea:
            paras.append(WD.para([WD.run(str(idea), size=19)], space_after=60))
        for n, (label, text) in enumerate(details):
            last = n == len(details) - 1
            paras.append(WD.para(([WD.run(str(label) + ". ", bold=True, size=18)] if label else [])
                                 + [WD.run(str(text), size=18, color=None if last else X.MUTED)], space_after=60))
        border = '<w:tcBorders><w:top w:val="single" w:sz="4" w:color="{0}"/><w:bottom w:val="single" w:sz="4" w:color="{0}"/>' \
                 '<w:right w:val="single" w:sz="4" w:color="{0}"/><w:left w:val="single" w:sz="36" w:color="{1}"/></w:tcBorders>'.format(
                     "D5DAE1", _hex(rgb))
        cell = '<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{b}<w:shd w:val="clear" w:color="auto" w:fill="{f}"/></w:tcPr>{p}</w:tc>'.format(
            w=WIDTH, b=border, f=_hex(P._mix(rgb, 0.12)), p="".join(paras))
        self.parts.append('<w:tbl><w:tblPr><w:tblW w:w="{w}" w:type="dxa"/><w:tblCellMar><w:top w:w="90" w:type="dxa"/>'
                          '<w:left w:w="160" w:type="dxa"/><w:bottom w:w="40" w:type="dxa"/><w:right w:w="140" w:type="dxa"/>'
                          '</w:tblCellMar></w:tblPr><w:tblGrid><w:gridCol w:w="{w}"/></w:tblGrid>'
                          '<w:tr><w:trPr><w:cantSplit/></w:trPr>{c}</w:tr></w:tbl>'.format(w=WIDTH, c=cell) + WD.para("", space_after=60))

    def render(self):
        m = self.meta
        meta = {"title": m["title"], "subject": m["subject"][:80], "prepared": m["prepared"], "docno": m["docno"], "rev": m["rev"],
                "doctype": m["doctype"][:60], "lang": "fr"}
        body = "".join(self.parts) or WD.para([WD.run("Aucun contenu.", italic=True, color=X.MUTED)])
        return _mark(WD.build(meta, body, "Export de Diamond", m.get("initials") or ""))


def api_docx(ctx):
    pid, meta, project = pdf_pages.prepare(ctx)
    doc = WordDoc(meta)
    scope = pdf_pages.fill(ctx, pid, doc)
    data = doc.render()
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_export_docx", "project", pid,
                     {"page": meta["view"], "sections": scope, "bytes": len(data)}, ctx.ip)
    name = re.sub(r"[^\w\-]+", "_", "Diamond_{}_{}".format(project["key"], meta["title"]), flags=re.UNICODE).strip("_")[:90]
    return RawFile(data, name + ".docx", DOCX)
