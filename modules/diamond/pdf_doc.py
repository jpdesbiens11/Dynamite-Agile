"""PDF in the format of the platform's Word documents (0.60.123, D-O-136), standard library only.

The same presentation as the .docx built from modules/testing/templates/document.docx:
  - a cover page: title, subject, document type, the « Prepared by / Checked by / Approved by » table (name, date, signature),
    the table of contents (numbered headings, their page) and the log of revision;
  - on every page, the header of the template -- the logo, the title, Doc.-No., Revision, Date, the type and « Page n of N » --
    and its footer (« Document généré par Dynamite | Agile… » and the mark of the platform);
  - numbered headings, paragraphs, bullets, tables with a navy header row repeated on each page, coloured cards.
Letter portrait; Tabloid landscape (11 x 17 in) when a table is too wide to stay readable on Letter. Long tables and long
sections are cut across pages; a row taller than a page is shortened with « … ».

    doc = Doc({"title", "subject", "doctype", "docno", "rev", "prepared", "initials", "date"})
    doc.h(1, "…"); doc.p("…"); doc.bullets([...]); doc.table(header, rows); doc.card(...); doc.note("…")
    data = render(doc)
"""
import datetime as dt
import zipfile
import zlib
from pathlib import Path

from modules.dynamite.export_pdf import clean, pdf_string, png_to_rgb, width

LETTER, TABLOID = (612, 792), (1224, 792)  # points; Tabloid in landscape
MARGIN, HEAD, FOOT = 46, 54, 30
NAVY, INK, MUTED, LINE = (0.11, 0.18, 0.31), (0.09, 0.13, 0.2), (0.4, 0.45, 0.53), (0.79, 0.82, 0.86)
FAMILY = {1: (1, 0.82, 0.25), 2: (0.61, 0.48, 1), 3: (0.24, 0.78, 0.88), 4: (1, 0.54, 0.24), 5: (0.37, 0.82, 0.54),
          6: (1, 0.44, 0.57), 7: (0.3, 0.55, 1), 8: (0.18, 0.77, 0.71)}
FONTS = {"R": "Helvetica", "B": "Helvetica-Bold", "I": "Helvetica-Oblique"}
WIDE_COLUMNS = 6  # a table of more columns goes to Tabloid landscape
TEMPLATE = Path(__file__).resolve().parent.parent / "testing" / "templates" / "document.docx"
FOOTER = "Document généré par Dynamite | Agile. La version électronique fait foi ; la version imprimée est pour référence."
MARK = "DynamiteAgile · Co-Intelligence WorkFlow™"
_LOGO = []


def _logo():
    if not _LOGO:
        try:
            with zipfile.ZipFile(TEMPLATE) as z:
                p = png_to_rgb(z.read("word/media/image1.png"))
            _LOGO.append((p[0], p[1], p[2], zlib.compress(p[3], 6)) if p else None)
        except (OSError, KeyError, zipfile.BadZipFile):
            _LOGO.append(None)
    return _LOGO[0]


def _mix(rgb, k):
    """The colour lightened towards white (k = share of the colour)."""
    return tuple(1 - (1 - c) * k for c in rgb)


class Doc:
    def __init__(self, meta):
        self.meta, self.blocks = meta, []

    def h(self, level, text):
        self.blocks.append(("h", max(1, min(3, int(level))), str(text)))

    def p(self, text, muted=False, italic=False, size=10):
        self.blocks.append(("p", str(text), muted, italic, size))

    def note(self, text):
        self.p(text, muted=True, italic=True, size=8.5)

    def bullets(self, items):
        self.blocks.append(("ul", [str(i) for i in items]))

    def table(self, header, rows):
        self.blocks.append(("table", [str(h) for h in header], [["" if c is None else str(c) for c in r] for r in rows]))

    def card(self, code, title, tag="", color=0, idea="", details=()):
        """details: [(label, text)] -- the last one shaded (« on your project »)."""
        self.blocks.append(("card", str(code), str(title), str(tag), int(color or 0), str(idea), [(str(a), str(b)) for a, b in details]))

    def wide(self):
        return any(b[0] == "table" and len(b[1]) > WIDE_COLUMNS for b in self.blocks)


class Writer:
    def __init__(self, size):
        self.W, self.H = size
        self.left, self.right = MARGIN, self.W - MARGIN
        self.top, self.bottom = self.H - MARGIN - HEAD, MARGIN + FOOT
        self.width = self.right - self.left
        self.pages, self.ops = [], []
        self.y = self.top

    def new_page(self):
        self.pages.append(self.ops)
        self.ops, self.y = [], self.top

    def need(self, h):
        if self.y - h < self.bottom and self.y < self.top - 1:
            self.new_page()

    def text(self, x, y, s, font="R", size=10, rgb=INK):
        self.ops.append(b"BT %.3f %.3f %.3f rg /F%s %.1f Tf %.2f %.2f Td " % (rgb + (font.encode(), size, x, y)) + pdf_string(s) + b" Tj ET")

    def rect(self, x, y, w, h, rgb):
        self.ops.append(b"%.3f %.3f %.3f rg %.2f %.2f %.2f %.2f re f" % (rgb + (x, y, w, h)))

    def line(self, x1, y1, x2, y2, rgb=LINE, w=0.6):
        self.ops.append(b"%.3f %.3f %.3f RG %.2f w %.2f %.2f m %.2f %.2f l S" % (rgb + (w, x1, y1, x2, y2)))

    @staticmethod
    def wrap(text, font, size, max_w):
        out = []
        for raw in clean(text).replace("\t", "    ").split("\n"):
            line, used = "", 0.0
            for word in raw.split(" "):
                token = (" " if line else "") + word
                w = width(token, font, size)
                if line and used + w > max_w:
                    out.append(line)
                    line, used = word, width(word, font, size)
                else:
                    line, used = line + token, used + w
                while used > max_w and len(line) > 1:  # one word wider than the column: cut it
                    cut = len(line)
                    while cut > 1 and width(line[:cut], font, size) > max_w:
                        cut -= 1
                    out.append(line[:cut])
                    line = line[cut:]
                    used = width(line, font, size)
            out.append(line)
        return out

    def para(self, text, font="R", size=10, rgb=INK, indent=0, before=2, after=5, lead=1.35):
        lines = self.wrap(text, font, size, self.width - indent)
        self.y -= before
        for ln in lines:
            self.need(size * lead)
            self.text(self.left + indent, self.y - size, ln, font, size, rgb)
            self.y -= size * lead
        self.y -= after


def _widths(header, rows, avail, size):
    """Each column gets at least its longest word (or its title), then the rest in proportion to how much text it holds:
    a column of long texts (Prevention, Notes) gets the room, a column of codes stays narrow."""
    sample = rows[:400]
    floors, weights, natural = [], [], []
    for c, h in enumerate(header):
        texts = [clean(r[c] if c < len(r) else "") for r in sample]
        words = [w for t in texts for w in t.split()] or [""]
        longest_word = max(width(w, "R", size) for w in words[:4000])
        floors.append(max(30.0, min(max(longest_word, width(clean(h).split(" ")[0], "B", size)) + 8, 110.0)))
        widths = [width(t, "R", size) for t in texts] or [0.0]
        natural.append(max([width(clean(h), "B", size) + 8] + [w + 8 for w in widths]))
        weights.append((sum(widths) / len(widths)) ** 0.5 + 1)
    if sum(natural) <= avail:
        return [w * avail / sum(natural) for w in natural]
    floors = [f * min(1.0, avail * 0.6 / sum(floors)) for f in floors]
    rest = avail - sum(floors)
    out = [f + rest * w / sum(weights) for f, w in zip(floors, weights)]
    over = [max(0.0, o - n) for o, n in zip(out, natural)]  # never wider than the column needs: give the surplus back
    if sum(over):
        spare = sum(over)
        out = [min(o, n) for o, n in zip(out, natural)]
        room = [w if o < n else 0 for o, n, w in zip(out, natural, weights)]
        out = [o + spare * r / (sum(room) or 1) for o, r in zip(out, room)]
    return out


def _table(wr, header, rows, size=8):
    """A navy header row on every page of the table; a row taller than what is left of the page goes on, cell by cell,
    on the next page (after the header row again) -- nothing is lost, nothing overflows the footer."""
    cw = _widths(header, rows, wr.width, size)
    lead = size * 1.28

    def chunk(parts, head):
        """Draws one slice of a row (lines per cell) at wr.y."""
        h = max(len(x) for x in parts) * lead + 6
        top = wr.y
        if head:
            wr.rect(wr.left, top - h, wr.width, h, NAVY)
        x = wr.left
        for lines, w in zip(parts, cw):
            y = top - 3
            for ln in lines:
                wr.text(x + 3.5, y - size, ln, "B" if head else "R", size, (1, 1, 1) if head else INK)
                y -= lead
            wr.line(x, top, x, top - h)
            x += w
        wr.line(wr.right, top, wr.right, top - h)
        wr.line(wr.left, top - h, wr.right, top - h)
        wr.line(wr.left, top, wr.right, top)
        wr.y = top - h

    head = [wr.wrap(t, "B", size, w - 7) for t, w in zip(header, cw)]
    head_h = max(len(x) for x in head) * lead + 6

    def row(cells):
        parts = [wr.wrap(t, "R", size, w - 7)[:600] for t, w in zip(cells, cw)]
        while any(parts):
            fit = int((wr.y - wr.bottom - 6) / lead)
            need = max(len(x) for x in parts)
            if fit < min(need, 3):
                wr.new_page()
                chunk(head, True)  # the header row on every page of the table
                continue
            chunk([x[:fit] for x in parts], False)
            parts = [x[fit:] for x in parts]

    if wr.y - head_h - 3 * lead - 6 < wr.bottom:
        wr.new_page()
    chunk(head, True)
    for r in rows:
        row((r + [""] * len(header))[:len(header)])
    wr.y -= 10


def _card(wr, b):
    _kind, code, title, tag, color, idea, details = b
    rgb = FAMILY.get(color, NAVY)
    inner = wr.width - 18
    parts = [(code + "   " + tag if tag else code, "B", 7.5, MUTED, 0), (title, "B", 11, INK, 2), (idea, "R", 9.5, INK, 2)]
    for n, (label, text) in enumerate(details):
        parts.append(((label + ". " if label else "") + text, "R", 9, INK if n == len(details) - 1 else MUTED, 3))
    blocks = [(wr.wrap(t, f, s, inner - 8), f, s, c, gap) for t, f, s, c, gap in parts if t.strip()]
    h = sum(len(lines) * s * 1.32 + gap for lines, f, s, c, gap in blocks) + 14
    wr.need(min(h, wr.top - wr.bottom - 10))
    top = wr.y
    if h <= wr.top - wr.bottom - 10:
        wr.rect(wr.left, top - h, wr.width, h, _mix(rgb, 0.10))
        wr.rect(wr.left, top - h, 4, h, rgb)
    y = top - 8
    for i, (lines, f, s, c, gap) in enumerate(blocks):
        y -= gap
        for ln in lines:
            if y - s < wr.bottom:
                wr.new_page()
                y = wr.top - 6
            wr.text(wr.left + 12, y - s, ln, f, s, c)
            y -= s * 1.32
    wr.y = y - 12


def _body(doc, size):
    wr = Writer(size)
    toc, numbers = [], [0, 0, 0]
    for b in doc.blocks:
        kind = b[0]
        if kind == "h":
            level = b[1]
            numbers[level - 1] += 1
            for i in range(level, 3):
                numbers[i] = 0
            num = ".".join(str(n) for n in numbers[:level])
            s = {1: 15, 2: 12.5, 3: 11}[level]
            if level == 1 and wr.y < wr.top - 1:
                wr.need(s * 6)
            else:
                wr.need(s * 4)
            toc.append((level, num, b[2], len(wr.pages) + 2))
            wr.para(num + "   " + b[2], "B", s, NAVY if level == 1 else INK, before=10 if wr.y < wr.top - 1 else 0, after=4)
        elif kind == "p":
            _k, text, muted, italic, s = b
            wr.para(text, "I" if italic else "R", s, MUTED if muted else INK)
        elif kind == "ul":
            for item in b[1]:
                wr.need(14)
                wr.text(wr.left + 6, wr.y - 10, "•", "B", 10)
                wr.para(item, "R", 10, indent=18, before=0, after=2)
            wr.y -= 4
        elif kind == "table":
            if b[2]:
                _table(wr, b[1], b[2])
            else:
                wr.para("Aucune ligne.", "I", 9, MUTED)
        elif kind == "card":
            _card(wr, b)
    wr.pages.append(wr.ops)
    return wr, toc


def _cover(doc, size, toc, total):
    m = doc.meta
    wr = Writer(size)
    wr.y -= 30
    wr.para(m.get("title", ""), "B", 24, NAVY, after=6)
    if m.get("subject"):
        wr.para(m["subject"], "R", 13, INK, after=4)
    wr.para(m.get("doctype", ""), "I", 10, MUTED, after=18)
    when = m.get("date") or dt.date.today().strftime("%d.%m.%Y")
    _table(wr, ["", "Nom", "Date", "Signature"], [["Prepared by", m.get("prepared", ""), when, ""], ["Checked by", "", "", ""],
                                                  ["Approved by", "", "", ""]], size=9)
    wr.y -= 8
    wr.para("Table des matières", "B", 13, NAVY, after=6)
    entries = [t for t in toc if t[0] == 1 or len(toc) <= 34]
    room = int((wr.y - wr.bottom - 120) / 13)
    for level, num, text, page in entries[:max(room, 1)]:
        indent = 0 if level == 1 else 16
        label = clean(num + "   " + text)
        font = "B" if level == 1 else "R"
        while width(label, font, 9.5) > wr.width - indent - 40 and len(label) > 4:
            label = label[:-2]
        wr.text(wr.left + indent, wr.y - 9.5, label, font, 9.5)
        wr.text(wr.right - 20, wr.y - 9.5, str(page), font, 9.5)
        wr.y -= 13
    if len(entries) > room:
        wr.para("… et {} autres titres.".format(len(entries) - room), "I", 8.5, MUTED)
    wr.y -= 10
    wr.para("Journal des révisions", "B", 13, NAVY, after=6)
    _table(wr, ["Révision", "Date", "Description", "Par"],
           [[m.get("rev", "A"), when, "Export de la plateforme ({} pages)".format(total), m.get("initials") or m.get("prepared", "")]], size=9)
    return wr.ops


def _decorate(ops, n, total, size, meta, logo):
    W, H = size
    wr = Writer(size)
    top = H - MARGIN
    if logo:
        wr.ops.append(b"q 34 0 0 34 %.2f %.2f cm /Logo Do Q" % (MARGIN, top - 38))
    wr.text(MARGIN + 44, top - 16, clean(meta.get("title", ""))[:90], "B", 11, NAVY)
    if meta.get("subject"):
        wr.text(MARGIN + 44, top - 30, clean(meta["subject"])[:110], "R", 8.5, MUTED)
    when = meta.get("date") or dt.date.today().strftime("%d.%m.%Y")
    right = [("Doc.-No. : " + meta.get("docno", "")) + "     Revision : " + meta.get("rev", "A") + "     Date : " + when,
             meta.get("doctype", "") + "     Page : {} of {}".format(n, total)]
    for i, s in enumerate(right):
        wr.text(W - MARGIN - width(clean(s), "R", 8), top - 14 - 12 * i, s, "R", 8, INK)
    wr.line(MARGIN, top - 44, W - MARGIN, top - 44, NAVY, 0.9)
    wr.line(MARGIN, MARGIN + 18, W - MARGIN, MARGIN + 18)
    wr.text(MARGIN, MARGIN + 6, FOOTER, "R", 7, MUTED)
    wr.text(W - MARGIN - width(clean(MARK), "B", 7), MARGIN + 6, MARK, "B", 7, MUTED)
    return ops + wr.ops


def render(doc):
    size = TABLOID if doc.wide() else LETTER
    body, toc = _body(doc, size)
    pages = [None] + body.pages
    total = len(pages)
    pages[0] = _cover(doc, size, toc, total)
    logo = _logo()
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", None]
    font_ids = {}
    for key, name in FONTS.items():
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /%s /Encoding /WinAnsiEncoding >>" % name.encode())
        font_ids[key] = len(objects)
    xobj = b""
    if logo:
        w, h, colors, stream = logo
        objects.append(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /%s /BitsPerComponent 8 /Filter /FlateDecode "
                       b"/Length %d >>\nstream\n" % (w, h, b"DeviceRGB" if colors == 3 else b"DeviceGray", len(stream)) + stream + b"\nendstream")
        xobj = b"/XObject << /Logo %d 0 R >>" % len(objects)
    resources = b"<< /Font << %s >> %s >>" % (b" ".join(b"/F%s %d 0 R" % (k.encode(), v) for k, v in font_ids.items()), xobj)
    page_ids = []
    for n, ops in enumerate(pages, start=1):
        stream = zlib.compress(b"\n".join(_decorate(ops, n, total, size, doc.meta, logo)))
        objects.append(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream) + stream + b"\nendstream")
        objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources %s /Contents %d 0 R >>" % (
            size[0], size[1], resources, len(objects)))
        page_ids.append(len(objects))
    objects[1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (b" ".join(b"%d 0 R" % i for i in page_ids), len(page_ids))
    info = b"<< /Title %s /Producer (Dynamite | Agile) >>" % pdf_string(doc.meta.get("title", ""))
    objects.append(info)
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, len(objects), xref)
    return bytes(out)
