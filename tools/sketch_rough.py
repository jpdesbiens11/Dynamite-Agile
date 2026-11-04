"""Hand-drawn (« carnet d'ingénieur ») SVG primitives (D-B-087), standard library only.

Each shape is drawn like a pencil: a slightly bowed main stroke plus a faint second pass, with a small overshoot at the
ends. The randomness is seeded by the name of the drawing, so the same asset is regenerated identically.
Used by tools/make_sketch_assets.py (icons sprite, module marks, illustrations).
"""
import math
import random


class Pen:
    def __init__(self, seed, jitter=0.6, passes=2):
        self.rng = random.Random(seed)
        self.jitter = jitter
        self.passes = passes

    def j(self, amount=None):
        a = self.jitter if amount is None else amount
        return self.rng.uniform(-a, a)

    @staticmethod
    def f(v):
        return ("%.2f" % v).rstrip("0").rstrip(".")

    # ---------------------------------------------------------------- strokes (return path "d" strings)
    def line_d(self, x1, y1, x2, y2, factor=1.0):
        a = self.jitter * factor
        length = math.hypot(x2 - x1, y2 - y1) or 1
        over = min(length * 0.04, a * 1.5)
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        sx, sy = x1 - ux * over * self.rng.random() + self.j(a), y1 - uy * over * self.rng.random() + self.j(a)
        ex, ey = x2 + ux * over * self.rng.random() + self.j(a), y2 + uy * over * self.rng.random() + self.j(a)
        bow = self.j(a) * min(length / 12, 2.5)
        mx, my = (sx + ex) / 2 - uy * bow, (sy + ey) / 2 + ux * bow
        f = self.f
        return "M{} {}Q{} {} {} {}".format(f(sx), f(sy), f(mx), f(my), f(ex), f(ey))

    def poly_d(self, points, closed=False, factor=1.0):
        pts = list(points) + ([points[0]] if closed else [])
        return "".join(self.line_d(*pts[i], *pts[i + 1], factor=factor) for i in range(len(pts) - 1))

    def curve_d(self, points, closed=False, factor=1.0):
        """Smooth Catmull-Rom curve through the points, each point jittered."""
        pts = [(x + self.j(self.jitter * factor), y + self.j(self.jitter * factor)) for x, y in points]
        if closed:
            pts = pts + pts[:3]
        f = self.f
        d = "M{} {}".format(f(pts[0][0]), f(pts[0][1]))
        for i in range(len(pts) - 1 - (2 if closed else 0)):
            p0 = pts[i - 1] if i > 0 else pts[i]
            p1, p2 = pts[i], pts[i + 1]
            p3 = pts[i + 2] if i + 2 < len(pts) else p2
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            d += "C{} {} {} {} {} {}".format(f(c1[0]), f(c1[1]), f(c2[0]), f(c2[1]), f(p2[0]), f(p2[1]))
        return d

    def rect_pts(self, x, y, w, h):
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]

    def ellipse_pts(self, cx, cy, rx, ry, n=14, start=0.0, sweep=2 * math.pi, overshoot=0.18):
        pts = []
        total = sweep + (overshoot if sweep >= 2 * math.pi - 1e-6 else 0)
        for i in range(n + 1):
            t = start + total * i / n
            k = 1 + (self.j(0.04) if self.jitter else 0)
            pts.append((cx + rx * k * math.cos(t), cy + ry * k * math.sin(t)))
        return pts

    # ---------------------------------------------------------------- SVG elements
    def stroke(self, shape, color="currentColor", width=1.8, factor=1.0, extra=""):
        """shape: ('line', x1, y1, x2, y2) | ('poly', pts, closed) | ('curve', pts, closed) | ('rect', x, y, w, h)
        | ('ellipse', cx, cy, rx, ry) | ('arc', cx, cy, rx, ry, start, sweep) | ('path', d)."""
        out = []
        for p in range(self.passes):
            d = self._d(shape, factor * (1 if p == 0 else 1.6))
            opacity = "" if p == 0 else ' stroke-opacity=".38"'
            w = width if p == 0 else width * 0.7
            out.append('<path d="{}" fill="none" stroke="{}" stroke-width="{}" stroke-linecap="round" '
                       'stroke-linejoin="round"{}{}/>'.format(d, color, self.f(w), opacity, extra))
        return "".join(out)

    def fill(self, shape, color, opacity=0.55, dx=2.0, dy=1.5):
        """Highlighter fill, slightly off the outline like a marker."""
        d = self._d(shape, 0.6, filled=True)
        return '<path d="{}" fill="{}" fill-opacity="{}" transform="translate({} {})"/>'.format(
            d, color, opacity, self.f(dx + self.j(0.6)), self.f(dy + self.j(0.6)))

    def area_d(self, points):
        """One closed polygon (a fill must be a single sub-path), corners jittered."""
        f = self.f
        pts = [(x + self.j(), y + self.j()) for x, y in points]
        return "M" + "L".join("{} {}".format(f(x), f(y)) for x, y in pts) + "Z"

    def _d(self, shape, factor, filled=False):
        kind = shape[0]
        if filled:
            if kind == "rect":
                return self.area_d(self.rect_pts(*shape[1:5]))
            if kind == "ellipse":
                return self.area_d(self.ellipse_pts(*shape[1:5], n=18, overshoot=0))
            if kind in ("poly", "curve"):
                return self.area_d(shape[1])
        if kind == "line":
            return self.line_d(*shape[1:5], factor=factor)
        if kind == "poly":
            pts, closed = shape[1], shape[2]
            return self.curve_d(pts, closed) if filled and closed else self.poly_d(pts, closed, factor)
        if kind == "curve":
            return self.curve_d(shape[1], shape[2], factor)
        if kind == "rect":
            pts = self.rect_pts(*shape[1:5])
            return self.poly_d(pts, True, factor) + ("Z" if filled else "")
        if kind == "ellipse":
            return self.curve_d(self.ellipse_pts(*shape[1:5], overshoot=0 if filled else 0.25), False, factor)
        if kind == "arc":
            cx, cy, rx, ry, start, sweep = shape[1:7]
            return self.curve_d(self.ellipse_pts(cx, cy, rx, ry, 10, start, sweep, 0), False, factor)
        if kind == "path":
            return shape[1]
        raise ValueError(kind)


def gear_points(cx, cy, r_out, r_in, teeth=8):
    pts = []
    for i in range(teeth * 2):
        a = math.pi * i / teeth
        r = r_out if i % 2 == 0 else r_in
        for da in (-0.18, 0.18):
            pts.append((cx + r * math.cos(a + da), cy + r * math.sin(a + da)))
    return pts
