"""The diagrams of Diamond as EMF pictures for the Word report (0.60.98, D-O-105).

The boxes and arrows are the ones export_drawio.py lays out (Page.items), the same source as the PowerPoint export:
one layout for the three files. Left out of a figure: the title block and the footer of a draw.io page (role
« chrome »: the caption and the page of the report carry them) and, on request, its legend (the lead-in of the
figure explains the colours). The picture is cropped to what is left. Labels are wrapped here with the Arial metrics;
arrows follow orthogonal routes from the exit to the entry points of the style, as draw.io and PowerPoint draw them.
"""
import html
import math
import re

from . import emf
from .export_pptx import _Label, _hex, _style

PAD = 12                       # around the cropped figure, in pixels
SPACING = {"spacingLeft": 4, "spacingTop": 2, "spacingRight": 4, "spacingBottom": 2}
DASH = {"7 5": (7, 5), "8 4": (8, 4)}
INK = "1F2933"
TAIL = re.compile(r'<br><font style="font-size:10px" color="#5B6573">[^<]*</font>$')  # the parts under a label (_fn_label)
BADGES, BADGE_SIZE = 4, 10


def _f(st, key, default):
    try:
        return float(st.get(key, default))
    except ValueError:
        return float(default)


def paragraphs(value, st):
    """The little HTML of a label -> paragraphs of (text, size, colour, bold, italic) runs."""
    lab = _Label(_f(st, "fontSize", 11), _hex(st.get("fontColor"), INK), int(_f(st, "fontStyle", 0)) & 1 == 1,
                 int(_f(st, "fontStyle", 0)) & 2 == 2)
    lab.feed(str(value or ""))
    return [[(t, f["size"], f["color"] or INK, bool(f["b"]), bool(f["i"])) for t, f in para if t] for para in lab.paras]


def wrap(paras, width):
    """Paragraphs of runs -> lines: [(height, [(x, text, size, colour, bold, italic)], line width)]."""
    lines = []
    for para in paras:
        words = []  # (text, run) with the spaces kept at the end of a word
        for text, *fmt in para:
            for w in re.findall(r"\S+\s*|\s+", text):
                words.append((w, fmt))
        cur, x, size = [], 0.0, max([fmt[0] for _t, *fmt in para] or [11])
        for w, fmt in words:
            ww = emf.measure(w.rstrip(), fmt[0], fmt[2])
            if cur and x + ww > width:
                lines.append((size * emf.LINE, cur, x))
                cur, x = [], 0.0
                w = w.lstrip()
                if not w:
                    continue
                ww = emf.measure(w.rstrip(), fmt[0], fmt[2])
            cur.append((x, w, *fmt))
            x += emf.measure(w, fmt[0], fmt[2])
        lines.append((size * emf.LINE, cur, max(0.0, x - (emf.measure(" ", 11) if cur and cur[-1][1].endswith(" ") else 0))))
    return lines


def draw_text(pic, value, st, x, y, w, h):
    lines = wrap(paragraphs(value, st), max(10.0, w - _f(st, "spacingLeft", SPACING["spacingLeft"]) - _f(st, "spacingRight", 4)))
    total = sum(lh for lh, _r, _w in lines)
    top = {"top": y + _f(st, "spacingTop", 2), "bottom": y + h - _f(st, "spacingBottom", 2) - total}.get(
        st.get("verticalAlign"), y + (h - total) / 2)
    align = st.get("align", "center")
    for lh, runs, lw in lines:
        if align == "left":
            x0 = x + _f(st, "spacingLeft", 4)
        elif align == "right":
            x0 = x + w - _f(st, "spacingRight", 4) - lw
        else:
            x0 = x + (w - lw) / 2
        size = lh / emf.LINE
        merged = []  # the words of one style on a line: one text record (one piece when edited in Word)
        for run in runs:
            if merged and merged[-1][2:] == run[2:]:
                merged[-1] = (merged[-1][0], merged[-1][1] + run[1]) + run[2:]
            else:
                merged.append(run)
        for rx, text, rsize, color, bold, italic in merged:
            pic.text(x0 + rx, top + (lh - size) / 2 + size * emf.ASCENT, text.rstrip(), rsize, color, bold, italic)
        top += lh


def _stroke(st, default_w=1.0):
    color = st.get("strokeColor")
    if color == "none":
        return None, 0, None
    dash = DASH.get(st.get("dashPattern"), (6, 4)) if st.get("dashed") == "1" else None
    return _hex(color, "26323F"), _f(st, "strokeWidth", default_w), dash


def round_rect_points(x, y, w, h, r, n=5):
    """The outline of a rectangle with round corners (to cut a dashed frame)."""
    r = max(0.0, min(r, w / 2, h / 2))
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts + [pts[0]]


def draw_box(pic, item, ox, oy):
    st = _style(item["style"])
    x, y, w, h = item["x"] - ox, item["y"] - oy, item["w"], item["h"]
    color, sw, dash = _stroke(st)
    if st.get("shape") == "line":  # a legend swatch: the line itself
        pic.polyline([(x, y + h / 2), (x + w, y + h / 2)], color, sw, dash)
        return
    text_only = "text" in st
    fill = None if text_only else _hex(st.get("fillColor"))
    radius = min(w, h) * _f(st, "arcSize", 15) / 100 if st.get("rounded") == "1" and not text_only else 0
    if not text_only:
        if dash:
            pic.rect(x, y, w, h, fill=fill, radius=radius)
            pic.polyline(round_rect_points(x, y, w, h, radius), color, sw, dash)
        elif fill or color:
            pic.rect(x, y, w, h, fill=fill, stroke=color, width=sw, radius=radius)
    value = item["value"]
    if item.get("badges"):  # the parts are drawn as badges: not twice in the label
        value = TAIL.sub("", str(value))
    if value:
        draw_text(pic, value, st, x, y, w, h)
    if item.get("badges"):
        draw_badges(pic, item["badges"], x, y, w, h)


def draw_badges(pic, badges, x, y, w, h):
    """The P-n badges of the structure screen on the lower edge of a box, from the right: green for a part that carries out
    several functions (integrated), orange edge when the function needs several parts; four at most, then « +n »."""
    shown = badges[:BADGES] + ([("+{}".format(len(badges) - BADGES), False)] if len(badges) > BADGES else [])
    right, bh = x + w - 6, BADGE_SIZE * 1.45
    for code, multi in reversed(shown):
        bw = emf.measure(code, BADGE_SIZE, True) + 8
        right -= bw
        edge = "2E9E5B" if multi else ("E08A00" if len(badges) >= 2 and not code.startswith("+") else "9AA5B1")
        pic.rect(right, y + h - bh / 2, bw, bh, fill=emf.blend("2E9E5B", 0.22) if multi else "FFFFFF", stroke=edge, width=1, radius=bh / 2)
        pic.text(right + 4, y + h - bh / 2 + BADGE_SIZE * 1.08, code, BADGE_SIZE, INK, bold=True)
        right -= 3


def _anchor(box, fx, fy):
    return box["x"] + box["w"] * fx, box["y"] + box["h"] * fy


def _side(fx, fy):
    """The direction leaving a box at (fx, fy): (dx, dy)."""
    if fx >= 1:
        return 1, 0
    if fx <= 0:
        return -1, 0
    return (0, 1) if fy >= 1 else (0, -1)


def route(st, a, b):
    """Orthogonal route from box a to box b: a list of points."""
    if st.get("elbow") == "horizontal":
        ex, ey, nx, ny = 1, 0.5, 0, 0.5
    else:
        ex, ey = _f(st, "exitX", 1), _f(st, "exitY", 0.5)
        nx, ny = _f(st, "entryX", 0), _f(st, "entryY", 0.5)
    (x1, y1), (x2, y2) = _anchor(a, ex, ey), _anchor(b, nx, ny)
    d1, d2 = _side(ex, ey), _side(nx, ny)
    if d1[0] and d2[0]:
        if d1[0] == -d2[0] and (x2 - x1) * d1[0] > 0:      # facing: one vertical step half way
            xm = (x1 + x2) / 2
            return [(x1, y1), (xm, y1), (xm, y2), (x2, y2)]
        lane = (max(x1, x2) + 24) if d1[0] > 0 else (min(x1, x2) - 24)  # same side: a lane beside the column
        return [(x1, y1), (lane, y1), (lane, y2), (x2, y2)]
    if d1[1] and d2[1]:
        ym = (y1 + y2) / 2
        return [(x1, y1), (x1, ym), (x2, ym), (x2, y2)]
    return [(x1, y1), (x2, y1), (x2, y2)] if d1[0] else [(x1, y1), (x1, y2), (x2, y2)]


def _along(pts, t):
    """The point at a fraction t of the length of a polyline."""
    segs = [math.hypot(bx - ax, by - ay) for (ax, ay), (bx, by) in zip(pts, pts[1:])]
    goal = sum(segs) * max(0.0, min(1.0, t))
    for (ax, ay), (bx, by), s in zip(pts, pts[1:], segs):
        if goal <= s and s:
            return ax + (bx - ax) * goal / s, ay + (by - ay) * goal / s
        goal -= s
    return pts[-1]


def draw_edge(pic, item, pts, ox, oy, label=False):
    """The line and its arrowhead, or (label=True) only its label: labels go on top of everything."""
    st = _style(item["style"])
    pts = [(x - ox, y - oy) for x, y in pts]
    if label:
        return draw_label(pic, item, st, pts)
    color, sw, dash = _stroke(st, 1.4)
    if st.get("endArrow") != "none":
        (ax, ay), (bx, by) = pts[-2], pts[-1]
        d = math.hypot(bx - ax, by - ay) or 1.0
        ux, uy = (bx - ax) / d, (by - ay) / d
        size, half = 7 + 1.6 * sw, 3.5 + 0.9 * sw
        base = (bx - ux * size, by - uy * size)
        pic.polyline(pts[:-1] + [base], color, sw, dash)
        pic.polygon([(bx, by), (base[0] - uy * half, base[1] + ux * half), (base[0] + uy * half, base[1] - ux * half)], fill=color)
    else:
        pic.polyline(pts, color, sw, dash)


def draw_label(pic, item, st, pts):
    if item["value"]:
        lx, ly = _along(pts, (_f(item, "at", 0) + 1) / 2 if item.get("at") else 0.5)
        size = _f(st, "fontSize", 10)
        text = re.sub(r"<[^>]+>", " ", str(item["value"]))
        text = " ".join(html.unescape(text).split())
        tw = emf.measure(text, size)
        pic.rect(lx - tw / 2 - 3, ly - size * 0.7, tw + 6, size * 1.4, fill="FFFFFF", stroke="C9D1DB", width=0.6, radius=size * 0.5)
        pic.text(lx - tw / 2, ly + size * 0.35, text, size, _hex(st.get("fontColor"), INK))


def render(page, legend=True):
    """A draw.io page -> (emf bytes, width px, height px), cropped to its drawing."""
    skip = {"chrome"} | (set() if legend else {"legend"})
    items = [i for i in page.items if i.get("role") not in skip]
    boxes = {i["id"]: i for i in items if i["kind"] == "box"}
    routes = {}
    for i in items:
        if i["kind"] == "edge" and i["src"] in boxes and i["dst"] in boxes:
            routes[i["id"]] = route(_style(i["style"]), boxes[i["src"]], boxes[i["dst"]])
    xs = [b["x"] for b in boxes.values()] + [p[0] for r in routes.values() for p in r]
    ys = [b["y"] for b in boxes.values()] + [p[1] for r in routes.values() for p in r]
    xe = [b["x"] + b["w"] for b in boxes.values()] + xs
    ye = [b["y"] + b["h"] + (BADGE_SIZE if b.get("badges") else 0) for b in boxes.values()] + ys  # badges hang below
    if not xs:
        return emf.Picture(100, 40).data(), 100, 40
    ox, oy = min(xs) - PAD, min(ys) - PAD
    w, h = max(xe) + PAD - ox, max(ye) + PAD - oy
    pic = emf.Picture(w, h)
    # the frames of the system, then the flows, then the boxes over the flows (a flow that crosses a column passes
    # behind its boxes), then the labels of the flows
    for i in [i for i in items if i.get("role") == "frame"]:
        draw_box(pic, i, ox, oy)
    for i in [i for i in items if i["id"] in routes]:
        draw_edge(pic, i, routes[i["id"]], ox, oy)
    for i in [i for i in items if i["kind"] == "box" and i.get("role") != "frame"]:
        draw_box(pic, i, ox, oy)
    for i in [i for i in items if i["id"] in routes]:
        draw_edge(pic, i, routes[i["id"]], ox, oy, label=True)
    return pic.data(), w, h
