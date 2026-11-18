"""Icons of the competencies of Diamond (0.60.116, D-O-129): one per competency of the default catalogue
(modules/diamond/data_competencies.py), plus a few spare ones an administrator may give to a competency he adds.
Drawn once on a 24-unit grid, in the shapes of tools/story_pictos.py, written by tools/make_sketch_assets.py into two sprites
with the same names (symbols « k-<key> »):
- static/img/competencies.svg       pencil strokes + highlighter fills (Thème par défaut);
- static/img/competencies-term.svg  crisp strokes + light fills (Terminal R&D).
No text inside the images (FONDATIONS §5): the name of a competency is HTML next to its icon (the legend of the grid).
"""
import math

from sketch_rough import gear_points
from story_pictos import _person

PI = math.pi

ICONS = {
    "gear": [(("poly", gear_points(12, 12, 9, 7), True), "f:orange"), (("ellipse", 12, 12, 2.8, 2.8), "s")],
    "thermo": [(("rect", 9.5, 3, 5, 12.5), "s"), (("ellipse", 12, 18, 3.6, 3.6), "f:red"), (("line", 12, 15, 12, 7), "s"),
               (("curve", [(17, 6), (18.5, 7.5), (17, 9), (18.5, 10.5)], False), "s"),
               (("curve", [(20, 6), (21.5, 7.5), (20, 9), (21.5, 10.5)], False), "s")],
    "mesh": [(("poly", [(3, 20), (12, 4), (21, 20)], True), "f:cyan"), (("line", 7.5, 12, 16.5, 12), "s"),
             (("line", 7.5, 12, 12, 20), "s"), (("line", 16.5, 12, 12, 20), "s")],
    "flow": [(("ellipse", 12, 13, 6.5, 2.6), "f:blue"), (("curve", [(2, 9), (8, 7.5), (16, 7.5), (22, 9.5)], False), "s"),
             (("curve", [(2, 17), (8, 18.5), (16, 18.5), (22, 16.5)], False), "s"), (("line", 2, 13, 5, 13), "s")],
    "pcb": [(("rect", 3, 4, 18, 16), "f:green"), (("rect", 9, 9, 6, 6), "s"), (("line", 15, 12, 19, 12), "s"),
            (("line", 12, 4, 12, 9), "s"), (("line", 5, 17, 9, 13), "s"), (("ellipse", 19, 12, 0.9, 0.9), "s"),
            (("ellipse", 5, 17, 0.9, 0.9), "s")],
    "code": [(("rect", 2, 4, 20, 16), "f:violet"), (("poly", [(8.5, 8), (5, 12), (8.5, 16)], False), "s"),
             (("poly", [(15.5, 8), (19, 12), (15.5, 16)], False), "s"), (("line", 13.5, 7, 10.5, 17), "s")],
    "power": [(("poly", [(13.5, 2), (5.5, 13.5), (11, 13.5), (9, 22), (18.5, 9.5), (13, 9.5)], True), "f:yellow")],
    "plug": [(("rect", 6, 9, 12, 7.5), "f:orange"), (("line", 9.5, 9, 9.5, 3.5), "s"), (("line", 14.5, 9, 14.5, 3.5), "s"),
             (("curve", [(12, 16.5), (12, 19.5), (15, 20.5), (18, 21.5)], False), "s")],
    "cells": [(("rect", 3, 7, 5, 13), "f:green"), (("rect", 9.5, 7, 5, 13), "f:green"), (("rect", 16, 7, 5, 13), "f:green"),
              (("rect", 4.5, 5, 2, 2), "s"), (("rect", 11, 5, 2, 2), "s"), (("rect", 17.5, 5, 2, 2), "s")],
    "shield": [(("curve", [(12, 2.5), (19.5, 5), (19, 13), (12, 21.5), (5, 13), (4.5, 5), (12, 2.5)], True), "f:teal"),
               (("line", 12, 7, 12, 13.5), "s"), (("ellipse", 12, 16.5, 0.8, 0.8), "s")],
    "factory": [(("poly", [(3, 21), (3, 11), (8, 14), (8, 11), (13, 14), (13, 11), (17, 13.5), (17, 4), (21, 4), (21, 21)], True), "f:orange"),
                (("rect", 6, 16.5, 2.5, 2.5), "s"), (("rect", 11, 16.5, 2.5, 2.5), "s"), (("line", 1.5, 21, 22.5, 21), "s")],
    "torch": [(("poly", [(3, 18.5), (5.5, 21), (14.5, 12), (12, 9.5)], True), "f:blue"), (("line", 14, 10, 16.5, 7.5), "s"),
              (("ellipse", 18, 6, 1.8, 1.8), "f:yellow"), (("line", 19.5, 4.5, 21.5, 2.5), "s"), (("line", 20, 6.5, 22.5, 6.5), "s"),
              (("line", 17.5, 3.5, 17.5, 1.5), "s")],
    "flask": [(("poly", [(10, 3), (10, 9), (4.5, 19), (5.5, 21), (18.5, 21), (19.5, 19), (14, 9), (14, 3)], True), "s"),
              (("poly", [(7, 15), (17, 15), (19.5, 19), (18.5, 21), (5.5, 21), (4.5, 19)], True), "f:teal"),
              (("line", 8.5, 3, 15.5, 3), "s")],
    "blocks": [(("rect", 9, 3, 6, 5), "f:violet"), (("rect", 3, 15, 6, 5), "f:violet"), (("rect", 15, 15, 6, 5), "f:violet"),
               (("line", 12, 8, 12, 11.5), "s"), (("line", 6, 11.5, 18, 11.5), "s"), (("line", 6, 11.5, 6, 15), "s"),
               (("line", 18, 11.5, 18, 15), "s")],
    "cert": [(("rect", 4, 3, 16, 13), "f:yellow"), (("line", 7, 7, 17, 7), "s"), (("line", 7, 10, 14, 10), "s"),
             (("ellipse", 15.5, 17, 3, 3), "f:red"), (("line", 14, 19.6, 13, 22.5), "s"), (("line", 17, 19.6, 18, 22.5), "s")],
    "caliper": [(("rect", 2.5, 5, 19, 3), "f:cyan"), (("rect", 3.5, 8, 2.8, 10), "s"), (("rect", 13, 8, 2.8, 6), "s"),
                (("line", 9, 5, 9, 6.5), "s"), (("line", 12, 5, 12, 6.5), "s"), (("line", 18, 5, 18, 6.5), "s")],
    # spare icons for a competency an administrator adds
    "chart": [(("line", 3, 3, 3, 21), "s"), (("line", 3, 21, 21, 21), "s"), (("rect", 6, 13, 3, 8), "f:blue"),
              (("rect", 11, 9, 3, 12), "f:blue"), (("rect", 16, 5, 3, 16), "f:blue")],
    "magnet": [(("curve", [(5, 4), (5, 14), (12, 20.5), (19, 14), (19, 4)], False), "s"),
               (("curve", [(9, 4), (9, 13), (12, 16), (15, 13), (15, 4)], False), "s"),
               (("rect", 5, 4, 4, 3), "f:red"), (("rect", 15, 4, 4, 3), "f:blue")],
    "book": [(("poly", [(12, 6), (3, 4), (3, 19), (12, 21), (21, 19), (21, 4)], True), "f:yellow"), (("line", 12, 6, 12, 21), "s")],
    "eye": [(("curve", [(2, 12), (7, 6.5), (12, 5.5), (17, 6.5), (22, 12), (17, 17.5), (12, 18.5), (7, 17.5), (2, 12)], True), "f:cyan"),
            (("ellipse", 12, 12, 3.2, 3.2), "f:blue"), (("ellipse", 12, 12, 1, 1), "s")],
    "person": _person(12, "f:pink", "f:orange"),
}


def sprite(pen_cls, hl, term=False):
    """The two sprites: pencil (fills then strokes) or crisp (light fills, clean strokes). Symbols are « k-<key> »."""
    out = ['<svg xmlns="http://www.w3.org/2000/svg" style="display:none">']
    for key, shapes in ICONS.items():
        pen = pen_cls(("tcomp-" if term else "comp-") + key, jitter=0 if term else 0.26, passes=1 if term else 2)
        body = []
        for shape, role in shapes:
            if role.startswith("f:"):
                body.append(pen.fill(shape, hl[role[2:]], 0.28 if term else 0.6, 0 if term else 0.6, 0 if term else 0.4))
        body += [pen.stroke(shape, width=1.5 if term else 1.6) for shape, _role in shapes]
        out.append('<symbol id="k-{}" viewBox="0 0 24 24">{}</symbol>'.format(key, "".join(body)))
    out.append("</svg>")
    return "\n".join(out) + "\n"
