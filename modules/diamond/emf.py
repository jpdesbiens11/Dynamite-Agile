"""EMF pictures for the figures of the Word report of Diamond (0.60.98, D-O-105), standard library only.

EMF (Enhanced Metafile) is Office's own vector picture: Word (Windows, Mac, web) and LibreOffice draw it natively, so a
figure stays sharp when zoomed or printed (a dense diagram reads zoomed in, as in the PowerPoint) and its text is drawn
by the reader's own Arial (or Liberation Sans, its metric twin) -- nothing to rasterise, no font to ship. A PNG would
need a font rasteriser the standard library does not have.

The writer knows the few records the figures need: solid pens, solid brushes, fonts, rectangles with round corners,
ellipses, polygons, polylines (dashes are cut here, so every reader draws the same pattern) and text placed character
by character (the Dx array, from the Helvetica / Arial metrics of the PDF export: a line keeps the width measured for
its layout whatever font the reader substitutes). Coordinates: 1 unit = 1/960 inch = 1/10 of a pixel at 96 dpi.
"""
import math
import struct

from modules.dynamite.export_pdf import width as _helvetica

UNIT = 10                          # EMF units per pixel (96 dpi)
FONT = "Arial"
LINE = 1.2                         # line height, in em
ASCENT = 0.92                      # from the top of a line to its baseline, in em
NULL_BRUSH, NULL_PEN = 0x80000005, 0x80000008
HMM_PER_UNIT = 2540.0 / (96 * UNIT)  # 0.01 mm per unit


ARIAL = {"→": 1000, "←": 1000, "↑": 500, "↓": 500, "×": 584, "·": 333, "™": 1000, "≤": 549, "≥": 549, "€": 556}


def measure(text, size, bold=False):
    """Width in pixels of a text in Arial at size px."""
    extra = sum(ARIAL[ch] for ch in text if ch in ARIAL) * size / 1000.0
    return extra + _helvetica("".join(ch for ch in text if ch not in ARIAL), "B" if bold else "R", size)


def _rgb(hexa):
    v = int((hexa or "000000").lstrip("#")[:6], 16)
    return ((v & 0xFF) << 16) | (v & 0xFF00) | (v >> 16)  # COLORREF 0x00BBGGRR


def blend(hexa, opacity, over="FFFFFF"):
    """A transparent fill painted on white -> its opaque colour (EMF has no alpha)."""
    a, b = int(hexa.lstrip("#")[:6], 16), int(over, 16)
    mix = [round(((a >> s) & 0xFF) * opacity + ((b >> s) & 0xFF) * (1 - opacity)) for s in (16, 8, 0)]
    return "{:02X}{:02X}{:02X}".format(*mix)


def dashes(points, on, off):
    """A polyline cut into dashes (lists of points), on / off in pixels (not positive: the line stays solid)."""
    if not points or on <= 0 or off <= 0:
        return [list(points)]
    out, cur, left, drawing = [], [points[0]], on, True
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        pos = 0.0
        while seg - pos > left:
            pos += left
            pt = (x1 + (x2 - x1) * pos / seg, y1 + (y2 - y1) * pos / seg)
            if drawing:
                cur.append(pt)
                out.append(cur)
            else:
                cur = [pt]
            drawing, left = not drawing, (on if not drawing else off)
        left -= seg - pos
        if drawing:
            cur.append((x2, y2))
    if drawing and len(cur) > 1:
        out.append(cur)
    return out


class Picture:
    """One figure: draw in pixels from the top left corner, then .data() gives the .emf bytes."""

    def __init__(self, width, height, background="FFFFFF"):
        self.w, self.h = max(1.0, float(width)), max(1.0, float(height))
        self.records, self.objects, self.current = [], {}, {}
        self._rec(17, struct.pack("<I", 1))          # EMR_SETMAPMODE MM_TEXT: 1 unit = 1 device pixel of the reference
        self._rec(18, struct.pack("<I", 1))          # EMR_SETBKMODE TRANSPARENT
        self._rec(19, struct.pack("<I", 2))          # EMR_SETPOLYFILLMODE WINDING
        self._rec(22, struct.pack("<I", 24))         # EMR_SETTEXTALIGN TA_BASELINE | TA_LEFT
        if background:
            self.rect(0, 0, self.w, self.h, fill=background)

    # ------------------------------------------------------------------ records
    def _rec(self, kind, payload):
        pad = (-len(payload)) % 4
        self.records.append(struct.pack("<II", kind, 8 + len(payload) + pad) + payload + b"\0" * pad)

    @staticmethod
    def _u(v):
        v = float(v) * UNIT
        return int(round(v)) if math.isfinite(v) else 0  # never a NaN or an infinity in a record

    def _box(self, pts):
        xs, ys = [self._u(x) for x, _y in pts], [self._u(y) for _x, y in pts]
        return struct.pack("<iiii", min(xs), min(ys), max(xs), max(ys))

    def _select(self, slot, key, create):
        if self.current.get(slot) == key:
            return
        if isinstance(key, int):
            handle = key  # a stock object
        elif key in self.objects:
            handle = self.objects[key]
        else:
            handle = self.objects[key] = len(self.objects) + 1
            create(handle)
        self._rec(37, struct.pack("<I", handle))     # EMR_SELECTOBJECT
        self.current[slot] = key

    def _pen(self, color, width):
        if not color:
            return self._select("pen", NULL_PEN, None)
        key = ("pen", color.upper(), max(1, self._u(width)))
        # EMR_EXTCREATEPEN: geometric, solid, round caps and joins; no bitmap (offsets and sizes 0)
        self._select("pen", key, lambda h: self._rec(95, struct.pack("<IIIIIIIIIII", h, 0, 0, 0, 0, 0x00010000, key[2], 0,
                                                                       _rgb(color), 0, 0)))

    def _brush(self, color):
        if not color:
            return self._select("brush", NULL_BRUSH, None)
        key = ("brush", color.upper())
        self._select("brush", key, lambda h: self._rec(39, struct.pack("<IIII", h, 0, _rgb(color), 0)))  # EMR_CREATEBRUSHINDIRECT

    def _font(self, size, bold, italic):
        key = ("font", self._u(size), bool(bold), bool(italic))

        def create(h):
            face = FONT.encode("utf-16-le").ljust(64, b"\0")
            logfont = struct.pack("<iiiiiBBBBBBBB", -key[1], 0, 0, 0, 700 if bold else 400, int(bool(italic)), 0, 0,
                                  1, 4, 0, 4, 0x22) + face  # DEFAULT_CHARSET, OUT_TT_PRECIS, ANTIALIASED, VARIABLE_PITCH|FF_SWISS
            full = face.ljust(128, b"\0") + b"\0" * 64 + struct.pack("<IIIIII", 0, 0, 0, 0, 0, 0) + b"\0" * 12
            self._rec(82, struct.pack("<I", h) + logfont + full)  # EMR_EXTCREATEFONTINDIRECTW (EXTLOGFONTW, 320 bytes)
        self._select("font", key, create)

    def _points(self, pts):
        return b"".join(struct.pack("<ii", self._u(x), self._u(y)) for x, y in pts)

    # ------------------------------------------------------------------ drawing
    def rect(self, x, y, w, h, fill=None, stroke=None, width=1.0, radius=0.0):
        self._pen(stroke, width)
        self._brush(fill)
        box = struct.pack("<iiii", self._u(x), self._u(y), self._u(x + w), self._u(y + h))
        if radius > 0.5:
            r = self._u(min(radius, w / 2, h / 2) * 2)
            self._rec(44, box + struct.pack("<ii", r, r))  # EMR_ROUNDRECT
        else:
            self._rec(43, box)                             # EMR_RECTANGLE

    def ellipse(self, cx, cy, rx, ry, fill=None, stroke=None, width=1.0):
        self._pen(stroke, width)
        self._brush(fill)
        self._rec(42, struct.pack("<iiii", self._u(cx - rx), self._u(cy - ry), self._u(cx + rx), self._u(cy + ry)))  # EMR_ELLIPSE

    def polygon(self, pts, fill=None, stroke=None, width=1.0):
        if len(pts) < 3:
            return
        self._pen(stroke, width)
        self._brush(fill)
        self._rec(3, self._box(pts) + struct.pack("<I", len(pts)) + self._points(pts))  # EMR_POLYGON

    def polyline(self, pts, stroke, width=1.0, dash=None):
        """dash: (on, off) in pixels, or None for a solid line."""
        if len(pts) < 2 or not stroke:
            return
        self._pen(stroke, width)
        lines = dashes(pts, *dash) if dash else [pts]
        lines = [ln for ln in lines if len(ln) > 1]
        if not lines:
            return
        flat = [p for ln in lines for p in ln]
        self._rec(7, self._box(flat) + struct.pack("<II", len(lines), len(flat))  # EMR_POLYPOLYLINE
                  + b"".join(struct.pack("<I", len(ln)) for ln in lines) + self._points(flat))

    def text(self, x, baseline, text, size, color="1F2933", bold=False, italic=False):
        """One line from x at its baseline; the advance of each character is fixed (the Dx array)."""
        text = str(text)
        if not text.strip():
            return 0.0
        self._font(size, bold, italic)
        if self.current.get("color") != color:
            self._rec(24, struct.pack("<I", _rgb(color)))  # EMR_SETTEXTCOLOR
            self.current["color"] = color
        units = text.encode("utf-16-le")
        n = len(units) // 2
        dx, cum, done = [], 0.0, 0
        for ch in text:
            cum += measure(ch, size, bold) * UNIT
            step = int(round(cum)) - done
            done += step
            dx += [step] + [0] * (len(ch.encode("utf-16-le")) // 2 - 1)
        string = units + b"\0" * ((-len(units)) % 4)
        x0, y0 = self._u(x), self._u(baseline)
        top, bottom = y0 - self._u(size * ASCENT), y0 + self._u(size * (LINE - ASCENT))
        bounds = struct.pack("<iiii", x0, top, x0 + done, bottom)
        # EmrText: reference point, chars, offset of the string, options, rectangle, offset of the Dx array
        emr_text = struct.pack("<iiIII", x0, y0, n, 76, 0) + bounds + struct.pack("<I", 76 + len(string))
        self._rec(84, bounds + struct.pack("<Iff", 1, HMM_PER_UNIT, HMM_PER_UNIT) + emr_text + string  # EMR_EXTTEXTOUTW
                  + struct.pack("<{}i".format(n), *dx))
        return done / float(UNIT)

    # ------------------------------------------------------------------ file
    def data(self):
        body = b"".join(self.records)
        eof = struct.pack("<IIIII", 14, 20, 0, 16, 20)   # EMR_EOF: no palette
        wu, hu = self._u(self.w), self._u(self.h)
        frame = (0, 0, int(round(wu * HMM_PER_UNIT)), int(round(hu * HMM_PER_UNIT)))
        size = 108 + len(body) + len(eof)
        header = struct.pack("<II", 1, 108) + struct.pack("<iiii", 0, 0, wu - 1, hu - 1) + struct.pack("<iiii", *frame) + \
            struct.pack("<IIIIHHIII", 0x464D4520, 0x00010000, size, len(self.records) + 2, len(self.objects) + 1, 0, 0, 0, 0) + \
            struct.pack("<ii", 96 * UNIT * 10, 96 * UNIT * 10) + struct.pack("<ii", 254, 254) + \
            struct.pack("<III", 0, 0, 0) + struct.pack("<ii", 254000, 254000)  # reference: 960 dpi, 10 in x 10 in
        return header + body + eof
