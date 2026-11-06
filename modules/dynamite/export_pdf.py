"""PDF writer for the Dynamite export (D-B-050), standard library only.

Letter pages, the 14 standard PDF fonts (Helvetica family, Courier) in
WinAnsi encoding -- nothing to embed. Word wrap from the Helvetica metrics,
headings, lists, quotes / panels, code, rules, tables with a header row and
borders, JPEG images (as is) and PNG images (decoded with zlib, alpha
dropped); an image too large or in another format becomes a short note.
Page numbers and the export line in the footer.
"""
import struct
import unicodedata
import zlib

PAGE_W, PAGE_H, MARGIN = 612, 792, 54
WIDTH = PAGE_W - 2 * MARGIN
HELV = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278] + [556] * 10 + \
    [278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778,
     722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222,
     500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]
BOLD = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278] + [556] * 10 + \
    [333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778, 667, 778,
     722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556, 333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278,
     556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584]
SPECIAL = {"•": 350, "—": 1000, "–": 556, "«": 556, "»": 556, "’": 222, "‘": 222, "“": 333, "”": 333, "…": 1000, "°": 400, "±": 584}
REPLACE = {"→": "->", "←": "<-", "≤": "<=", "≥": ">=", "◆": "*", "✓": "v", "✕": "x", "⇩": "", "⇧": "", "↺": "", "↶": "",
           "×": "x", " ": " ", " ": " ", "≈": "~", "Ω": "Ohm", "µ": "u", "μ": "u", "▾": ""}
COLORS = {"red": (0.79, 0.22, 0.17), "orange": (0.9, 0.41, 0.06), "green": (0.13, 0.43, 0.31), "blue": (0.05, 0.4, 0.89),
          "purple": (0.43, 0.36, 0.78), "gray": (0.38, 0.44, 0.53), "yellow": (0.65, 0.28, 0), None: (0.09, 0.17, 0.3)}
FONTS = {"R": "Helvetica", "B": "Helvetica-Bold", "I": "Helvetica-Oblique", "BI": "Helvetica-BoldOblique", "C": "Courier"}


def clean(text):
    out = []
    for ch in str(text):
        ch = REPLACE.get(ch, ch)
        try:
            ch.encode("cp1252")
            out.append(ch)
        except UnicodeEncodeError:
            base = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode()
            out.append(base or "?")
    return "".join(out)


def width(text, font, size):
    if font == "C":
        return 0.6 * size * len(text)
    table = BOLD if font in ("B", "BI") else HELV
    total = 0
    for ch in text:
        code = ord(ch)
        if 32 <= code <= 126:
            total += table[code - 32]
        elif ch in SPECIAL:
            total += SPECIAL[ch]
        else:
            base = unicodedata.normalize("NFKD", ch)[:1]
            total += table[ord(base) - 32] if base and 32 <= ord(base) <= 126 else 556
    return total * size / 1000.0


def pdf_string(text):
    raw = clean(text).encode("cp1252", "replace")
    return b"(" + raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)") + b")"


def _font(style):
    if style.get("code"):
        return "C"
    bold, italic = style.get("bold"), style.get("italic")
    return "BI" if bold and italic else "B" if bold else "I" if italic else "R"


def png_to_rgb(data):
    """(width, height, colors, raw 8-bit pixels) of a non-interlaced 8-bit PNG, or None."""
    if not data.startswith(b"\x89PNG"):
        return None
    pos, idat, head = 8, [], None
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            head = struct.unpack(">IIBBBBB", chunk)
        elif kind == b"IDAT":
            idat.append(chunk)
        pos += 12 + length
    if not head:
        return None
    w, h, depth, ctype, _c, _f, interlace = head
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(ctype)
    if depth != 8 or interlace or channels is None or w * h > 3_000_000:
        return None
    raw = zlib.decompress(b"".join(idat))
    stride = w * channels
    out = bytearray(stride * h)
    prev = bytearray(stride)
    for y in range(h):
        ft = raw[y * (stride + 1)]
        cur = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        if ft == 1:
            for i in range(channels, stride):
                cur[i] = (cur[i] + cur[i - channels]) & 255
        elif ft == 2:
            cur = bytearray((a + b) & 255 for a, b in zip(cur, prev))
        elif ft == 3:
            for i in range(stride):
                left = cur[i - channels] if i >= channels else 0
                cur[i] = (cur[i] + ((left + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                a = cur[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                cur[i] = (cur[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out[y * stride:(y + 1) * stride] = cur
        prev = cur
    if channels == 4:  # drop alpha
        rgb = bytearray(w * h * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = out[0::4], out[1::4], out[2::4]
        return w, h, 3, bytes(rgb)
    if channels == 2:
        return w, h, 1, bytes(out[0::2])
    return w, h, channels, bytes(out)


def jpeg_info(data):
    i = 2
    while i + 9 < len(data):
        marker, length = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h, data[i + 9]
        i += 2 + length
    return None


class Pdf:
    def __init__(self, footer):
        self.pages, self.ops, self.images, self.footer = [], [], [], footer
        self.y = PAGE_H - MARGIN
        self.new_page()

    def new_page(self):
        if self.ops:
            self.pages.append(self.ops)
        self.ops = []
        self.y = PAGE_H - MARGIN

    def need(self, height):
        if self.y - height < MARGIN + 20:
            self.new_page()

    def text(self, x, y, s, font, size, color=None):
        r, g, b = COLORS.get(color, COLORS[None])
        self.ops.append(b"BT %.3f %.3f %.3f rg /%s %.1f Tf %.2f %.2f Td " % (r, g, b, font.encode(), size, x, y)
                        + pdf_string(s) + b" Tj ET")

    def line(self, x1, y1, x2, y2, gray=0.86, w=0.6):
        self.ops.append(b"%.2f G %.2f w %.2f %.2f m %.2f %.2f l S" % (gray, w, x1, y1, x2, y2))

    def rect(self, x, y, w, h, gray):
        self.ops.append(b"%.3f g %.2f %.2f %.2f %.2f re f" % (gray, x, y, w, h))

    def wrap(self, runs, size, max_width):
        """Runs -> lines of (text, font, color, underline) segments."""
        lines, current, used = [], [], 0.0
        for text, style in runs:
            font, color = _font(style), style.get("color") or ("blue" if style.get("link") else None)
            underline = bool(style.get("underline") or style.get("link"))
            for n, part in enumerate(clean(text).replace("\t", "    ").split("\n")):
                if n:  # a line break inside the text
                    lines.append(current)
                    current, used = [], 0.0
                words = part.split(" ")
                for k, word in enumerate(words):
                    token = word if k == len(words) - 1 else word + " "
                    if not token:
                        continue
                    w = width(token, font, size)
                    if used + w > max_width and current:
                        lines.append(current)
                        current, used = [], 0.0
                        token = token.lstrip()
                        w = width(token, font, size)
                    current.append((token, font, color, underline))
                    used += w
        if current or not lines:
            lines.append(current)
        return lines

    def paragraph(self, runs, size=10, indent=0, before=2, after=5, bar=None, fill=None):
        lines = self.wrap(runs, size, WIDTH - indent - (10 if bar or fill else 0))
        lead = size * 1.35
        self.y -= before
        for i, segs in enumerate(lines):
            self.need(lead)
            if fill is not None:
                self.rect(MARGIN + indent - 4, self.y - lead, WIDTH - indent + 8, lead, fill)  # 0.60.62: never over the line above
            if bar:
                self.line(MARGIN + indent - 2, self.y + 2, MARGIN + indent - 2, self.y - lead + 3, 0.8, 2)
            x = MARGIN + indent + (8 if bar or fill else 0)
            for token, font, color, underline in segs:
                self.text(x, self.y - size, token, font_ref(font), size, color)
                w = width(token, font, size)
                if underline:
                    self.line(x, self.y - size - 1.5, x + w, self.y - size - 1.5, 0.4, 0.5)
                x += w
            self.y -= lead
        self.y -= after

    def table(self, header, rows, size=8.5):
        cols = max(len(r) for r in rows)
        cw = WIDTH / cols
        for r, row in enumerate(rows):
            cells = [self.wrap([(t, dict(s, bold=True) if header and r == 0 else s) for t, s in (row[c] if c < len(row) else [])],
                               size, cw - 8) for c in range(cols)]
            lead = size * 1.3
            height = max(len(c) for c in cells) * lead + 6
            self.need(height)
            top = self.y
            if header and r == 0:
                self.rect(MARGIN, top - height, WIDTH, height, 0.95)
            for c, lines in enumerate(cells):
                y = top - 3
                for segs in lines:
                    x = MARGIN + c * cw + 4
                    for token, font, color, _u in segs:
                        self.text(x, y - size, token, font_ref(font), size, color)
                        x += width(token, font, size)
                    y -= lead
            self.line(MARGIN, top, MARGIN + WIDTH, top)
            self.line(MARGIN, top - height, MARGIN + WIDTH, top - height)
            for c in range(cols + 1):
                self.line(MARGIN + c * cw, top, MARGIN + c * cw, top - height)
            self.y = top - height
        self.y -= 8

    def image(self, data, mime, alt, scale=1):
        info = None
        if data and mime == "image/jpeg":
            j = jpeg_info(data)
            if j and j[2] in (1, 3):
                info = (j[0], j[1], j[2], data, "DCTDecode")
        elif data and mime == "image/png":
            p = png_to_rgb(data)
            if p:
                info = (p[0], p[1], p[2], zlib.compress(p[3], 6), "FlateDecode")
        if not info:
            self.paragraph([("[image : {} — voir l'export Word]".format(alt or "format non pris en charge"), {"italic": True, "color": "gray"})], 9)
            return
        w, h = info[0], info[1]
        dw = min(WIDTH, w * 0.75 / scale)  # scale: a Mermaid drawing made at 2x (0.60.62)
        dh = h * dw / w
        if dh > PAGE_H - 2 * MARGIN - 40:
            dh = PAGE_H - 2 * MARGIN - 40
            dw = w * dh / h
        self.need(dh + 6)
        name = "Im{}".format(len(self.images) + 1)
        self.images.append((name, info))
        self.ops.append(b"q %.2f 0 0 %.2f %.2f %.2f cm /%s Do Q" % (dw, dh, MARGIN, self.y - dh, name.encode()))
        self.y -= dh + 6
        if alt:
            self.paragraph([(alt, {"italic": True, "color": "gray"})], 8.5, before=0)

    def output(self):
        self.pages.append(self.ops)
        objects = [b"<< /Type /Catalog /Pages 2 0 R >>", None]
        font_ids = {}
        for key, name in FONTS.items():
            objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /%s /Encoding /WinAnsiEncoding >>" % name.encode())
            font_ids[key] = len(objects)
        image_ids = {}
        for name, (w, h, colors, stream, flt) in self.images:
            space = b"/DeviceRGB" if colors == 3 else b"/DeviceGray"
            objects.append(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace %s /BitsPerComponent 8 "
                           b"/Filter /%s /Length %d >>\nstream\n" % (w, h, space, flt.encode(), len(stream)) + stream + b"\nendstream")
            image_ids[name] = len(objects)
        resources = b"<< /Font << %s >> /XObject << %s >> >>" % (
            b" ".join(b"/F%s %d 0 R" % (k.encode(), v) for k, v in font_ids.items()),
            b" ".join(b"/%s %d 0 R" % (k.encode(), v) for k, v in image_ids.items()))
        page_ids = []
        total = len(self.pages)
        for n, ops in enumerate(self.pages, start=1):
            foot = []
            r, g, b = COLORS["gray"]
            for x, s in ((MARGIN, self.footer), (PAGE_W - MARGIN - 60, "Page {} / {}".format(n, total))):
                foot.append(b"BT %.3f %.3f %.3f rg /FR 7.5 Tf %.2f %.2f Td " % (r, g, b, x, MARGIN - 24) + pdf_string(s) + b" Tj ET")
            stream = zlib.compress(b"\n".join(ops + foot))
            objects.append(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream) + stream + b"\nendstream")
            objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources %s /Contents %d 0 R >>" % (
                PAGE_W, PAGE_H, resources, len(objects)))
            page_ids.append(len(objects))
        objects[1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (b" ".join(b"%d 0 R" % i for i in page_ids), len(page_ids))
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, obj in enumerate(objects, start=1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
        out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
        out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
        return bytes(out)


def font_ref(key):
    return "F" + key


def build(docs, meta):
    pdf = Pdf("{} · {} · exporté par {} le {} · Dynamite | Agile".format(meta["title"][:60], meta["space"][:40], meta["by"], meta["at"]))
    pdf.paragraph([(meta["title"], {"bold": True})], 20, before=0, after=2)
    pdf.paragraph([("Space {}".format(meta["space"]), {"color": "gray"})], 9, before=0, after=10)
    for d, doc in enumerate(docs):
        if d:
            pdf.paragraph([(doc["title"], {"bold": True, "color": "blue"})], 15 if doc["level"] == 1 else 13, before=12)
        pdf.paragraph([("Version {} · modifiée le {}".format(doc["version"], (doc["updated"] or "")[:10]), {"color": "gray"})], 8, before=0)
        for item in doc["items"]:
            kind = item[0]
            if kind == "h":
                size = {1: 15, 2: 12.5, 3: 11}[item[1]]
                pdf.need(size * 3)
                pdf.paragraph([(t, dict(s, bold=True, color=s.get("color") or ("blue" if item[1] == 1 else None))) for t, s in item[2]],
                              size, before=8, after=3)
            elif kind == "p":
                style = item[2]
                pdf.paragraph(item[1], 10, bar=style == "quote", fill=0.95 if style == "panel" else None)
            elif kind == "li":
                pdf.paragraph([(item[2] + "  ", {})] + item[3], 10, indent=14 * (item[1] + 1), before=0, after=2)
            elif kind == "code":
                small = len(item) > 2 and item[2] == "small"  # the code under a Mermaid drawing (0.60.62)
                for line in (item[1] or "").split("\n"):
                    pdf.paragraph([(line or " ", {"code": True, "color": "gray"} if small else {"code": True})], 6.5 if small else 8.5,
                                  before=0, after=0, fill=0.95)
                pdf.y -= 6
            elif kind == "rule":
                pdf.need(10)
                pdf.line(MARGIN, pdf.y - 4, MARGIN + WIDTH, pdf.y - 4)
                pdf.y -= 10
            elif kind == "table":
                pdf.table(item[1], item[2])
            elif kind == "image":
                pdf.image(item[1], item[2], item[3], item[4] if len(item) > 4 else 1)
    return pdf.output()
