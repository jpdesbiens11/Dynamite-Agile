"""Visual assets of the default theme (« croquis d'ingénieur », D-B-087): icons, module marks, illustrations.

    python tools/make_sketch_assets.py

Writes (all local, no text inside the images, FONDATIONS §5):
- static/img/icons.svg            sprite of functional icons (<symbol id="i-…">, stroke = currentColor);
- static/img/marks/<key>.svg      colored module marks (left panel of each tool);
- static/img/sketch/<name>.svg    illustrations (sign-in page, empty states);
- static/img/icons-term.svg, static/img/marks-term/<key>.svg   crisp geometric set of the « Terminal R&D » theme (D-B-088).
Shapes are defined once on a 24-unit grid and drawn with tools/sketch_rough.Pen (pencil strokes + highlighter fills).
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sketch_rough import Pen, gear_points  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent / "static" / "img"
INK = "#26323f"
HL = {"yellow": "#ffd23f", "orange": "#ff8a3d", "cyan": "#3ec6e0", "green": "#5fd08a", "pink": "#ff6f91",
      "violet": "#9b7bff", "blue": "#4d8dff", "teal": "#2ec4b6", "red": "#ff5a4f"}
PI = math.pi


def bolt(x, y, s=1.0):
    return ("poly", [(x + 1.2 * s, y), (x - 1.6 * s, y + 4.2 * s), (x + 0.4 * s, y + 4.2 * s), (x - 0.8 * s, y + 8 * s),
                     (x + 2.4 * s, y + 3.2 * s), (x + 0.3 * s, y + 3.2 * s)], True)


# ---------------------------------------------------------------- icons (24-unit grid): [(shape, role)]
# role: "s" = stroke only, "f:<color>" = highlighter fill used by the colored marks only
ICONS = {
    "dashboard": [(("arc", 12, 15, 8.5, 8.5, PI, PI), "s"), (("line", 12, 15, 16.2, 9.6), "s"),
                  (("ellipse", 12, 15, 1.3, 1.3), "f:blue"), (("line", 4.5, 19.5, 19.5, 19.5), "s"),
                  (("line", 6.2, 9.3, 7.3, 10.3), "s"), (("line", 12, 6.8, 12, 8.2), "s"), (("line", 17.8, 9.3, 16.7, 10.3), "s")],
    "home": [(("poly", [(3, 11.5), (12, 4), (21, 11.5)], False), "s"), (("rect", 5.5, 11, 13, 9.5), "f:yellow"),
             (("rect", 10.2, 14.5, 3.6, 6), "s")],
    "goldmine": [(("rect", 5, 4.5, 14, 17), "f:yellow"), (("rect", 9, 2.8, 6, 3.2), "s"),
                 (("poly", [(7.8, 10.2), (9.3, 11.7), (11.8, 8.9)], False), "s"), (("line", 13, 10.6, 16.5, 10.6), "s"),
                 (("poly", [(7.8, 15.2), (9.3, 16.7), (11.8, 13.9)], False), "s"), (("line", 13, 15.6, 16.5, 15.6), "s")],
    "dynamite": [(("curve", [(3, 6.5), (7.5, 4.8), (12, 6.5)], False), "s"), (("line", 12, 6.5, 12, 20), "s"),
                 (("curve", [(3, 19.5), (7.5, 17.8), (12, 20)], False), "s"), (("line", 3, 6.5, 3, 19.5), "s"),
                 (("curve", [(12, 6.5), (16.5, 4.8), (21, 6.5)], False), "s"), (("line", 21, 6.5, 21, 19.5), "s"),
                 (("curve", [(12, 20), (16.5, 17.8), (21, 19.5)], False), "s"), (("line", 5.5, 10, 9.5, 10), "s"),
                 (("line", 5.5, 13, 9, 13), "s"), (("line", 14.5, 10, 18.5, 10), "s"), (("rect", 14, 12.5, 5, 4.5), "f:orange")],
    "agile": [(("rect", 3, 4, 18, 16), "s"), (("line", 9, 4.5, 9, 19.5), "s"), (("line", 15, 4.5, 15, 19.5), "s"),
              (("rect", 4.4, 7, 3.2, 2.6), "f:blue"), (("rect", 10.4, 7, 3.2, 2.6), "f:blue"),
              (("rect", 10.4, 11.4, 3.2, 2.6), "f:yellow"), (("rect", 16.4, 7, 3.2, 2.6), "f:green")],
    "testing": [(("rect", 3, 4.5, 18, 12), "s"),
                (("curve", [(5, 11), (6.5, 7), (8.5, 11), (10.5, 14.5), (12.5, 10.5), (14.5, 7.5), (16.5, 11), (19, 11)], False), "s"),
                (("line", 7, 16.8, 6, 20.2), "s"), (("line", 17, 16.8, 18, 20.2), "s"), (("line", 4.5, 20.5, 19.5, 20.5), "s"),
                (("rect", 3.6, 5.2, 16.8, 10.6), "f:green")],
    "exploration": [(("line", 3.5, 3.5, 3.5, 20.5), "s"), (("line", 3.5, 20.5, 20.5, 20.5), "s"),
                    (("rect", 5, 5, 8, 2.8), "f:violet"), (("rect", 9, 10.2, 9, 2.8), "f:violet"),
                    (("rect", 14, 15.4, 6, 2.8), "f:pink"), (("line", 13, 7.8, 13, 10.2), "s")],
    "tools": [(("line", 12, 4.5, 6, 20.5), "s"), (("line", 12, 4.5, 18, 20.5), "s"), (("ellipse", 12, 4.2, 1.7, 1.7), "s"),
              (("arc", 12, 12, 6.5, 6.5, 0.35 * PI, 0.3 * PI), "s"), (("rect", 4, 20.2, 16, 1.6), "f:cyan")],
    "training": [(("curve", [(9.2, 17), (8.8, 14.2), (6.6, 11.6), (7.2, 6.8), (12, 4.2), (16.8, 6.8), (17.4, 11.6), (15.2, 14.2), (14.8, 17)], False), "s"),
                 (("line", 9.2, 17, 14.8, 17), "s"), (("line", 9.8, 19.6, 14.2, 19.6), "s"), (bolt(12.2, 7.4, 0.95), "f:yellow")],
    "timesheet": [(("ellipse", 12, 12.5, 8.3, 8.3), "f:teal"), (("line", 12, 12.5, 12, 7.5), "s"), (("line", 12, 12.5, 15.8, 14.4), "s"),
                  (("line", 9.5, 2.8, 14.5, 2.8), "s")],
    "help": [(("ellipse", 12, 12, 9, 9), "f:yellow"),
             (("curve", [(9.2, 9.6), (10, 7.4), (12.2, 7.1), (14.6, 8.4), (14.3, 10.7), (12.1, 12.3), (12, 14.2)], False), "s"),
             (("ellipse", 12, 17, 0.6, 0.6), "s")],
    "search": [(("ellipse", 10.5, 10.5, 6.2, 6.2), "f:cyan"), (("line", 15.2, 15.2, 20.5, 20.5), "s")],
    "audit": [(("line", 3.5, 6, 12, 6), "s"), (("line", 3.5, 10, 10, 10), "s"), (("line", 3.5, 14, 8, 14), "s"),
              (("ellipse", 15, 15, 4.3, 4.3), "f:orange"), (("line", 18.2, 18.2, 21, 21), "s")],
    "auditlist": [(("poly", [(3.5, 7), (5, 8.5), (7.5, 5.8)], False), "s"), (("line", 10, 7, 20.5, 7), "s"),
                  (("poly", [(3.5, 12.5), (5, 14), (7.5, 11.3)], False), "s"), (("line", 10, 12.5, 20.5, 12.5), "s"),
                  (("ellipse", 5.5, 18.3, 1.6, 1.6), "s"), (("line", 10, 18.3, 17, 18.3), "s")],
    "admin": [(("poly", gear_points(12, 12, 8.6, 6.8), True), "f:blue"), (("ellipse", 12, 12, 2.8, 2.8), "s")],
    "mine": [(("ellipse", 12, 8.2, 3.6, 3.6), "f:pink"), (("curve", [(5, 20), (6.2, 15), (12, 13.6), (17.8, 15), (19, 20)], False), "s")],
    "mention": [(("ellipse", 12, 12, 3.6, 3.6), "s"),
                (("curve", [(15.6, 12), (15.8, 15.6), (19.2, 15.4), (20.2, 11.5), (18.4, 5.6), (12, 3.6), (5.2, 6.4), (3.8, 13.2), (7.4, 19.2), (13.8, 20.4)], False), "s")],
    "generator": [(("rect", 5.5, 3, 13, 18), "s"), (("line", 8.5, 7.5, 15.5, 7.5), "s"), (("line", 8.5, 10.5, 13.5, 10.5), "s"),
                  (("ellipse", 14.5, 16.5, 2.8, 2.8), "f:red"), (("line", 8.5, 13.5, 11, 13.5), "s")],
    "bolt": [(bolt(12.5, 3, 2.1), "f:yellow")],
    "plus": [(("line", 12, 5, 12, 19), "s"), (("line", 5, 12, 19, 12), "s")],
    "spaces": [(("rect", 3.5, 3.5, 7.5, 7.5), "f:yellow"), (("rect", 13, 3.5, 7.5, 7.5), "s"),
               (("rect", 3.5, 13, 7.5, 7.5), "s"), (("rect", 13, 13, 7.5, 7.5), "f:blue")],
    # 0.60.01: « About » -- an idea (light bulb) over the notebook line
    "about": [(("curve", [(9.4, 15.5), (8.9, 12.8), (6.8, 10.4), (7.3, 6.4), (12, 3.8), (16.7, 6.4), (17.2, 10.4), (15.1, 12.8), (14.6, 15.5)], False), "f:yellow"),
              (("line", 9.4, 15.5, 14.6, 15.5), "s"), (("line", 10, 18, 14, 18), "s"), (("line", 10.8, 20.4, 13.2, 20.4), "s"),
              (("poly", [(10.4, 12.6), (11.2, 9.2), (12, 11.6), (12.8, 9.2), (13.6, 12.6)], False), "s"),
              (("line", 2.8, 8.5, 4.6, 8.5), "s"), (("line", 21.2, 8.5, 19.4, 8.5), "s"), (("line", 5.2, 2.8, 6.4, 4), "s"),
              (("line", 18.8, 2.8, 17.6, 4), "s")],
}

# module marks: icon, accent, doodles
MARKS = {
    "dashboard": ("dashboard", "blue"), "goldmine": ("goldmine", "yellow"), "dynamite": ("dynamite", "orange"),
    "agile": ("agile", "blue"), "testing": ("testing", "green"), "exploration": ("exploration", "violet"),
    "tools": ("tools", "cyan"), "training": ("training", "pink"), "timesheet": ("timesheet", "teal"),
    "generator": ("generator", "red"), "search": ("search", "cyan"), "help": ("help", "yellow"), "about": ("about", "yellow"),
}


def scaled(shape, s, dx, dy):
    kind = shape[0]
    t = lambda x, y: (x * s + dx, y * s + dy)  # noqa: E731
    if kind == "line":
        return ("line", *t(shape[1], shape[2]), *t(shape[3], shape[4]))
    if kind in ("poly", "curve"):
        return (kind, [t(x, y) for x, y in shape[1]], shape[2])
    if kind == "rect":
        x, y = t(shape[1], shape[2])
        return ("rect", x, y, shape[3] * s, shape[4] * s)
    if kind == "ellipse":
        x, y = t(shape[1], shape[2])
        return ("ellipse", x, y, shape[3] * s, shape[4] * s)
    if kind == "arc":
        x, y = t(shape[1], shape[2])
        return ("arc", x, y, shape[3] * s, shape[4] * s, shape[5], shape[6])
    raise ValueError(kind)


def icon_symbol(name, shapes):
    pen = Pen("icon-" + name, jitter=0.28, passes=2)
    body = "".join(pen.stroke(shape, width=1.75) for shape, _role in shapes)
    return '<symbol id="i-{}" viewBox="0 0 24 24">{}</symbol>'.format(name, body)


def mark_svg(key, icon, accent):
    pen = Pen("mark-" + key, jitter=1.1, passes=2)
    parts = []
    # paper tab and highlighter blob behind the drawing
    parts.append(pen.fill(("poly", pen.ellipse_pts(80, 62, 58, 44, 12), True), HL[accent], 0.42, 0, 0))
    for i in range(3):  # quick marker hatching
        y = 26 + i * 7 + pen.j(1)
        parts.append(pen.stroke(("line", 26 + pen.j(3), y + 60, 52 + pen.j(3), y + 52), color=HL[accent], width=3.2))
    s, dx, dy = 4.1, 80 - 12 * 4.1, 60 - 12 * 4.1
    for shape, role in ICONS[icon]:
        big = scaled(shape, s, dx, dy)
        if role.startswith("f:"):
            parts.append(pen.fill(big, HL[role[2:]], 0.62, 3, 2.5))
        parts.append(pen.stroke(big, color=INK, width=3.1, factor=1.0))
    # doodles: a small bolt and sparks, the electric notebook signature
    parts.append(pen.fill(scaled(bolt(12, 3, 1.0), 2.2, 118, 6), HL["yellow"], 0.9, 1.5, 1))
    parts.append(pen.stroke(scaled(bolt(12, 3, 1.0), 2.2, 118, 6), color=INK, width=2.2))
    for x, y in ((24, 20), (30, 102)):
        parts.append(pen.stroke(("line", x - 4, y, x + 4, y), color=INK, width=1.6))
        parts.append(pen.stroke(("line", x, y - 4, x, y + 4), color=INK, width=1.6))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 124" role="img" aria-hidden="true">{}</svg>'
            .format("".join(parts)))


# ---------------------------------------------------------------- illustrations
def hero_svg():
    """Sign-in page (0.60.01): a three-level function tree (primary, secondary, tertiary) next to a pair of gears and a
    pencil, on graph paper -- product design, from the functions to the parts."""
    pen = Pen("hero", jitter=1.4, passes=2)
    p = []

    def box(x, y, w, h, color, alpha=0.45):
        p.append(pen.fill(("rect", x, y, w, h), HL[color], alpha, 3, 2))
        p.append(pen.stroke(("rect", x, y, w, h), color=INK, width=2.6))
        for k in range(2):  # two pencil lines standing for the function's wording (no text in images)
            p.append(pen.stroke(("line", x + 9, y + 12 + 10 * k, x + w - 12 - 14 * k + pen.j(4), y + 12 + 10 * k),
                                color=INK, width=1.5))

    box(30, 150, 96, 44, "yellow", 0.6)  # primary function
    seconds = (60, 150, 240)
    for y in seconds:  # secondary functions
        box(176, y, 96, 40, "orange")
        p.append(pen.stroke(("curve", [(126, 172), (150, 172), (152, y + 20), (176, y + 20)], False), color=INK, width=2.6))
    for i, y in enumerate((40, 82, 130, 170, 222, 262)):  # tertiary functions
        box(320, y, 82, 32, "cyan", 0.35)
        sy = seconds[i // 2] + 20
        p.append(pen.stroke(("curve", [(272, sy), (296, sy), (298, y + 16), (320, y + 16)], False), color=INK, width=2))
    for x, label in ((70, 0), (226, 1), (360, 2)):  # level ticks above the columns
        for k in range(label + 1):
            p.append(pen.stroke(("line", x + 7 * k, 18, x + 7 * k, 28), color=INK, width=2))
    # gears (the parts that will realise the functions)
    p.append(pen.fill(("poly", gear_points(452, 300, 38, 30), True), HL["green"], 0.45, 4, 3))
    p.append(pen.stroke(("poly", gear_points(452, 300, 38, 30), True), color=INK, width=2.6))
    p.append(pen.stroke(("ellipse", 452, 300, 9, 9), color=INK, width=2.4))
    p.append(pen.fill(("poly", gear_points(486, 246, 22, 17), True), HL["violet"], 0.45, 3, 2))
    p.append(pen.stroke(("poly", gear_points(486, 246, 22, 17), True), color=INK, width=2.4))
    p.append(pen.stroke(("ellipse", 486, 246, 5, 5), color=INK, width=2))
    p.append(pen.stroke(("curve", [(404, 280), (420, 296), (414, 312)], False), color=INK, width=2))
    # pencil
    p.append(pen.stroke(("poly", [(60, 330), (190, 300), (194, 314), (64, 344), (44, 342)], True), color=INK, width=2.4))
    p.append(pen.fill(("poly", [(70, 330), (188, 303), (191, 312), (73, 339)], True), HL["pink"], 0.6, 1, 1))
    for x, y in ((470, 60), (40, 60), (250, 340)):  # doodle stars
        p.append(pen.stroke(("line", x - 6, y, x + 6, y), color=INK, width=2))
        p.append(pen.stroke(("line", x, y - 6, x, y + 6), color=INK, width=2))
    body_svg = "".join('<g class="draw">{}</g>'.format(x) for x in p)
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 380" role="img" aria-hidden="true">{}</svg>'.format(body_svg)


def empty_svg():
    """Empty state: an open notebook with a pencil and a small bolt."""
    pen = Pen("empty", jitter=1.1, passes=2)
    p = []
    book = [(("curve", [(20, 40), (70, 26), (120, 40)], False), "s"), (("line", 120, 40, 120, 130), "s"),
            (("curve", [(20, 126), (70, 114), (120, 130)], False), "s"), (("line", 20, 40, 20, 126), "s"),
            (("curve", [(120, 40), (170, 26), (220, 40)], False), "s"), (("line", 220, 40, 220, 126), "s"),
            (("curve", [(120, 130), (170, 114), (220, 126)], False), "s")]
    p.append(pen.fill(("rect", 26, 40, 188, 84), HL["yellow"], 0.25, 3, 3))
    for shape, _r in book:
        p.append(pen.stroke(shape, color=INK, width=2.4))
    for y in (62, 78, 94):
        p.append(pen.stroke(("line", 36, y, 102 + pen.j(8), y), color=INK, width=1.4))
    p.append(pen.stroke(("rect", 140, 60, 60, 44), color=INK, width=1.6, extra=' stroke-dasharray="4 5"'))
    p.append(pen.fill(scaled(bolt(12, 3, 1.0), 2.4, 142, 58), HL["orange"], 0.85, 1, 1))
    p.append(pen.stroke(scaled(bolt(12, 3, 1.0), 2.4, 142, 58), color=INK, width=2))
    p.append(pen.stroke(("poly", [(196, 150), (236, 104), (244, 111), (204, 157), (192, 160)], True), color=INK, width=2.2))
    p.append(pen.fill(("poly", [(203, 144), (236, 106), (243, 112), (210, 150)], True), HL["pink"], 0.6, 1, 1))
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 170" role="img" aria-hidden="true">{}</svg>'.format("".join(p))


def favicon_svg():
    pen = Pen("favicon", jitter=0.5, passes=1)
    p = [pen.fill(("rect", 3, 3, 26, 26), HL["yellow"], 0.95, 0, 0),
         pen.stroke(("rect", 3, 3, 26, 26), color=INK, width=2.2),
         pen.stroke(scaled(bolt(12, 3, 1.0), 2.4, -13, -3), color=INK, width=2.4)]
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">{}</svg>'.format("".join(p))


# ---------------------------------------------------------------- « Terminal R&D » theme (D-B-088): crisp geometric set
TERM = {"dashboard": "#58a6ff", "goldmine": "#e3b341", "dynamite": "#ffa657", "agile": "#79c0ff", "testing": "#7ee787",
        "exploration": "#d2a8ff", "tools": "#56d4dd", "training": "#ff7eb6", "timesheet": "#3fb9a3", "generator": "#ff7b72",
        "search": "#56d4dd", "help": "#e3b341", "about": "#f2cc60"}


def term_symbol(name, shapes):
    pen = Pen("term-" + name, jitter=0, passes=1)
    body = "".join(pen.stroke(shape, width=1.6) for shape, _role in shapes)
    return '<symbol id="i-{}" viewBox="0 0 24 24">{}</symbol>'.format(name, body)


def term_mark(key, icon, color):
    """Dark tile, corner brackets, dot grid and the icon glowing in the module colour (no text)."""
    pen = Pen("tmark-" + key, jitter=0, passes=1)
    p = ['<defs><filter id="g" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.2" result="b"/>'
         '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>',
         '<rect x="6" y="6" width="148" height="112" rx="10" fill="#0d1117" stroke="{}" stroke-opacity=".35"/>'.format(color)]
    for x in range(18, 150, 12):
        for y in range(16, 116, 12):
            p.append('<circle cx="{}" cy="{}" r=".7" fill="#30363d"/>'.format(x, y))
    for x, y, dx, dy in ((12, 12, 1, 1), (148, 12, -1, 1), (12, 112, 1, -1), (148, 112, -1, -1)):
        p.append('<path d="M{} {}h{}M{} {}v{}" stroke="{}" stroke-width="2" fill="none" stroke-linecap="square"/>'.format(
            x, y, 12 * dx, x, y, 12 * dy, color))
    s, dx, dy = 3.7, 80 - 12 * 3.7, 62 - 12 * 3.7
    icon_body = "".join(pen.stroke(scaled(shape, s, dx, dy), color=color, width=2.6) for shape, _r in ICONS[icon])
    p.append('<g filter="url(#g)">{}</g>'.format(icon_body))
    p.append('<rect x="118" y="100" width="14" height="4" fill="{}"><animate attributeName="opacity" values="1;0;1" '
             'dur="1.1s" repeatCount="indefinite"/></rect>'.format(color))  # blinking cursor
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 124" role="img" aria-hidden="true">{}</svg>'.format("".join(p))


def main():
    sprite = ['<svg xmlns="http://www.w3.org/2000/svg" style="display:none">']
    sprite += [icon_symbol(n, s) for n, s in ICONS.items()]
    sprite.append("</svg>")
    (ROOT / "icons.svg").write_text("\n".join(sprite) + "\n", encoding="utf-8")
    (ROOT / "marks").mkdir(exist_ok=True)
    for key, (icon, accent) in MARKS.items():
        (ROOT / "marks" / (key + ".svg")).write_text(mark_svg(key, icon, accent) + "\n", encoding="utf-8")
    (ROOT / "sketch").mkdir(exist_ok=True)
    (ROOT / "sketch" / "hero.svg").write_text(hero_svg() + "\n", encoding="utf-8")
    (ROOT / "sketch" / "empty.svg").write_text(empty_svg() + "\n", encoding="utf-8")
    (ROOT.parent / "favicon.svg").write_text(favicon_svg() + "\n", encoding="utf-8")
    term = ['<svg xmlns="http://www.w3.org/2000/svg" style="display:none">'] + [term_symbol(n, s) for n, s in ICONS.items()] + ["</svg>"]
    (ROOT / "icons-term.svg").write_text("\n".join(term) + "\n", encoding="utf-8")
    (ROOT / "marks-term").mkdir(exist_ok=True)
    for key, (icon, _accent) in MARKS.items():
        (ROOT / "marks-term" / (key + ".svg")).write_text(term_mark(key, icon, TERM[key]) + "\n", encoding="utf-8")
    print("{} icons, {} marks, 2 illustrations, favicon; Terminal: {} icons, {} marks".format(len(ICONS), len(MARKS), len(ICONS), len(MARKS)))


if __name__ == "__main__":
    main()
