"""A scene of the Storyline as an EMF picture for the Word report (0.60.98, D-O-105).

The stage is the one of the screen (16:9, story_stage.js and diamond.css): each pictogram centred at its x / y in percent,
9, 13 or 19 % of the width for the sizes small, medium, large, mirrored when asked, its label under it. The pictograms
are read from the crisp sprite static/img/story-term.svg (written by tools/make_sketch_assets.py from
tools/story_pictos.py): light fills, then clean strokes -- the same drawing as the screen, made for print. The sprite
is a static file shipped with the platform: the server reads it, it never imports tools/.
"""
import math
import re
from functools import lru_cache
from pathlib import Path

from . import emf

SPRITE = Path(__file__).resolve().parent.parent.parent / "static" / "img" / "story-term.svg"
STAGE_W, STAGE_H = 960, 540
SIZES = {1: 0.09, 2: 0.13, 3: 0.19}
INK, LABEL = "26323F", 16


def _flatten(d):
    """Path data (absolute M, L, Q, C, Z, as the sprite writes them) -> sub-paths: (points, closed)."""
    out, cur = [], []
    tokens = re.findall(r"[MLQCZ]|-?\d*\.?\d+(?:e-?\d+)?", d)
    i, cmd = 0, None
    num = lambda: float(tokens[i])  # noqa: E731
    while i < len(tokens):
        if tokens[i] in "MLQCZ":
            cmd = tokens[i]
            i += 1
            if cmd == "Z":
                if cur:
                    out.append((cur, True))
                cur = []
                continue
        if cmd == "M":
            if len(cur) > 1:
                out.append((cur, False))
            cur = [(num(), float(tokens[i + 1]))]
            i += 2
            cmd = "L"
        elif cmd == "L":
            cur.append((num(), float(tokens[i + 1])))
            i += 2
        elif cmd == "Q":
            (x0, y0), (cx, cy), (x, y) = cur[-1], (num(), float(tokens[i + 1])), (float(tokens[i + 2]), float(tokens[i + 3]))
            cur += [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y)
                    for t in (k / 6 for k in range(1, 7))]
            i += 4
        elif cmd == "C":
            p0, p1 = cur[-1], (num(), float(tokens[i + 1]))
            p2, p3 = (float(tokens[i + 2]), float(tokens[i + 3])), (float(tokens[i + 4]), float(tokens[i + 5]))
            for k in range(1, 9):
                t = k / 8
                a, b, c, e = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
                cur.append((a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]))
            i += 6
        else:
            raise ValueError("path: {}".format(tokens[i]))
    if len(cur) > 1:
        out.append((cur, False))
    return out


def _attr(tag, name):
    m = re.search(r'\s{}="([^"]*)"'.format(name), tag)
    return m.group(1) if m else None


@lru_cache(maxsize=1)
def pictos():
    """{key: [(kind "fill" | "stroke", colour, opacity or width, [(points, closed)])]} from the sprite."""
    out = {}
    text = SPRITE.read_text("utf-8") if SPRITE.exists() else ""
    for key, body in re.findall(r'<symbol id="p-([a-z]+)" viewBox="0 0 24 24">(.*?)</symbol>', text, re.S):
        shapes = []
        for tag in re.findall(r"<path\b[^>]*>", body):
            subs = _flatten(_attr(tag, "d") or "")
            m = re.search(r"translate\(([-\d.]+)[ ,]+([-\d.]+)\)", _attr(tag, "transform") or "")
            if m:
                dx, dy = float(m.group(1)), float(m.group(2))
                subs = [([(x + dx, y + dy) for x, y in pts], closed) for pts, closed in subs]
            if (_attr(tag, "fill") or "none") != "none":
                shapes.append(("fill", _attr(tag, "fill").lstrip("#"), float(_attr(tag, "fill-opacity") or 1), subs))
            else:
                shapes.append(("stroke", INK, float(_attr(tag, "stroke-width") or 1.5), subs))
        out[key] = shapes
    return out


def _draw_picto(pic, key, x, y, size, mirror):
    k = size / 24.0
    place = lambda pts: [(x + (24 - px if mirror else px) * k, y + py * k) for px, py in pts]  # noqa: E731
    for kind, color, value, subs in pictos().get(key, []):
        for pts, closed in subs:
            if kind == "fill":
                pic.polygon(place(pts), fill=emf.blend(color, value))
            else:
                pic.polyline(place(pts + ([pts[0]] if closed else [])), color, value * k)


def _fit(text, size, width):
    if emf.measure(text, size) <= width:
        return text
    while text and emf.measure(text + "…", size) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _item(item):
    """A stored pictogram, read defensively (story.clean_items checks every write, but a restored or edited row may not
    be clean): None when it cannot be placed -- the scene is drawn without it rather than the report failing."""
    if not isinstance(item, dict):
        return None
    try:
        x, y, s = float(item.get("x", 50)), float(item.get("y", 50)), int(item.get("s") or 2)
    except (TypeError, ValueError, OverflowError):
        return None
    if not (math.isfinite(x) and math.isfinite(y)):
        return None
    return {"p": str(item.get("p") or ""), "x": min(100.0, max(0.0, x)), "y": min(100.0, max(0.0, y)), "s": s,
            "f": bool(item.get("f")), "t": " ".join(str(item.get("t") or "").split())}


COMIC_H, BOOST = 720, 1.3  # the comic panel (0.60.113): 4:3, the pictograms 1.3x larger than on the 16:9 stage


def _zoom(items, w, h, boost):
    """(k, dx, dy) that brings the group of pictograms to fill the panel like a comic (0.60.113, D-O-126): the group's box
    (pictograms and labels) centred and enlarged up to 1.6x (or drawn in a little), never cut by the frame."""
    if not items:
        return 1.0, 0.0, 0.0
    boxes = []
    for it in items:
        size = SIZES.get(it["s"], 0.13) * STAGE_W * boost
        bh = size + (LABEL * 1.5 + 4 if it["t"] else 0)
        bw = max(size, min(220, emf.measure(it["t"], LABEL)) + 12) if it["t"] else size
        cx, cy = it["x"] / 100 * w, it["y"] / 100 * h
        boxes.append((cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2))
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    k = max(0.7, min(1.6, w * 0.92 / max(1.0, x1 - x0), h * 0.9 / max(1.0, y1 - y0)))
    return k, w / 2 - (x0 + x1) / 2 * k, h / 2 - (y0 + y1) / 2 * k


def render(scene, fit=False):
    """A scene -> (emf bytes, width px, height px); fit: a comic panel, 4:3, the group enlarged to fill it."""
    w, h, boost = (STAGE_W, COMIC_H, BOOST) if fit else (STAGE_W, STAGE_H, 1.0)
    pic = emf.Picture(w, h)
    pic.rect(1, 1, w - 2, h - 2, fill="F6F7F9", stroke="9AA5B1", width=1.5, radius=10)
    items = list(filter(None, map(_item, scene.get("items") if isinstance(scene.get("items"), list) else [])))
    k, dx, dy = _zoom(items, w, h, boost) if fit else (1.0, 0.0, 0.0)
    font = round(LABEL * min(max(k, 1.0), 1.3))
    for item in items:
        size = SIZES.get(item["s"], 0.13) * STAGE_W * boost * k
        label = _fit(item["t"], font, 220 * max(k, 1.0))
        height = size + (font * 1.5 + 4 if label else 0)
        cx, cy = item["x"] / 100 * w * k + dx, item["y"] / 100 * h * k + dy
        top = cy - height / 2
        _draw_picto(pic, item["p"], cx - size / 2, top, size, item["f"])
        if label:
            lw = emf.measure(label, font)
            ly = top + size + 4
            pic.rect(cx - lw / 2 - 6, ly, lw + 12, font * 1.5, fill="FFFFFF", stroke="C9D1DB", width=1, radius=5)
            pic.text(cx - lw / 2, ly + font * 1.08, label, font, "1F2933")
    return pic.data(), w, h
