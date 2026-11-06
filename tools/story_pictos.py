"""Pictograms of the Diamond « Storyline » (0.60.51, D-O-060): people, places, objects, surroundings and feelings that
a team places on a scene to tell how the product is used. Drawn once on a 24-unit grid, written by
tools/make_sketch_assets.py into two sprites with the same names:
- static/img/story.svg       pencil strokes + highlighter fills (Thème par défaut);
- static/img/story-term.svg  crisp strokes + light fills (Terminal R&D).
No text inside the images (FONDATIONS §5): the label of a pictogram is HTML under it. The French names and the groups
shown in the palette live in static/js/diamond/story_pictos.js (same keys; tests/test_story.py checks both lists).
"""
import math

PI = math.pi


def _person(x, head, body, scale=1.0):
    s = scale
    return [(("ellipse", x, 6 + (1 - s) * 6, 2.6 * s, 2.6 * s), head),
            (("curve", [(x - 5 * s, 21), (x - 4.4 * s, 13.2 + (1 - s) * 5), (x, 10.6 + (1 - s) * 5.5),
                        (x + 4.4 * s, 13.2 + (1 - s) * 5), (x + 5 * s, 21)], False), body)]


def _face(mouth_start):
    return [(("ellipse", 12, 12, 8.5, 8.5), "f:yellow"), (("ellipse", 9, 10, 0.7, 0.9), "s"), (("ellipse", 15, 10, 0.7, 0.9), "s"),
            (("arc", 12, 12.5 if mouth_start < PI else 18, 4.2, 3.2, mouth_start, 0.7 * PI), "s")]


PICTOS = {
    # people
    "adulte": _person(12, "f:pink", "f:blue"),
    "enfant": _person(12, "f:yellow", "f:green", 0.72),
    "aine": _person(10.5, "f:pink", "f:violet") + [(("line", 17.5, 13.5, 18.6, 21), "s"), (("curve", [(17.5, 13.5), (17.8, 12.2), (16.6, 12)], False), "s")],
    "technicien": _person(12, "f:pink", "f:orange") + [(("arc", 12, 5.6, 3.3, 2.6, PI, PI), "f:yellow"), (("line", 8.2, 5.6, 15.8, 5.6), "s")],
    "groupe": _person(8, "f:pink", "f:blue", 0.85) + _person(16, "f:yellow", "f:green", 0.85),
    "main": [(("poly", [(7, 21), (6.5, 13), (8, 11.5), (17, 11.5), (18, 13), (16.5, 21)], True), "f:pink"),
             (("line", 8.5, 11.5, 8.5, 5.5), "s"), (("line", 11.2, 11.5, 11.2, 3.8), "s"), (("line", 13.9, 11.5, 13.9, 4.6), "s"),
             (("line", 16.4, 12, 16.6, 6.8), "s"), (("line", 6.6, 15, 3.8, 11.8), "s")],
    # places
    "maison": [(("poly", [(3, 11.5), (12, 4), (21, 11.5)], False), "s"), (("rect", 5.5, 11, 13, 9.5), "f:yellow"),
               (("rect", 10.2, 14.5, 3.6, 6), "s"), (("rect", 6.8, 13, 2.4, 2.2), "s")],
    "cuisine": [(("rect", 3, 13, 18, 8), "f:orange"), (("line", 3, 16, 21, 16), "s"), (("rect", 8.5, 7.5, 7, 5.5), "f:cyan"),
                (("line", 7, 8.8, 8.5, 8.8), "s"), (("line", 15.5, 8.8, 17, 8.8), "s"),
                (("curve", [(10.5, 6), (10, 4.8), (10.8, 3.5)], False), "s"), (("curve", [(13.5, 6), (13, 4.8), (13.8, 3.5)], False), "s")],
    "atelier": [(("rect", 3, 10, 18, 2.6), "f:orange"), (("line", 5, 12.6, 5, 21), "s"), (("line", 19, 12.6, 19, 21), "s"),
                (("line", 5, 18, 19, 18), "s"), (("rect", 6.5, 6.5, 4, 3.5), "f:blue"), (("line", 13, 9.8, 18.5, 4.5), "s"),
                (("ellipse", 18.8, 4.2, 1.6, 1.6), "s")],
    "bureau": [(("line", 3, 14, 21, 14), "s"), (("line", 5, 14, 5, 21), "s"), (("line", 19, 14, 19, 21), "s"),
               (("rect", 7.5, 6, 9, 6.2), "f:cyan"), (("poly", [(6.5, 13.6), (7.5, 12.2), (16.5, 12.2), (17.5, 13.6)], True), "s")],
    "exterieur": [(("ellipse", 12, 9, 6.2, 5.6), "f:green"), (("rect", 11, 14.2, 2, 6.6), "s"), (("line", 3, 21, 21, 21), "s"),
                  (("curve", [(3.5, 21), (5, 19.2), (6.5, 21)], False), "s")],
    "route": [(("line", 9, 3, 3, 21), "s"), (("line", 15, 3, 21, 21), "s"), (("line", 12, 4, 12, 7), "s"), (("line", 12, 10, 12, 13.5), "s"),
              (("line", 12, 16.5, 12, 20.5), "s"), (("poly", [(9, 3), (15, 3), (21, 21), (3, 21)], True), "f:violet")],
    "magasin": [(("rect", 4, 9.5, 16, 11.5), "s"), (("poly", [(3, 9.5), (5, 4), (19, 4), (21, 9.5)], True), "f:red"),
                (("rect", 10, 14, 4, 7), "f:yellow"), (("rect", 5.5, 12, 3, 3), "s"), (("rect", 15.5, 12, 3, 3), "s")],
    # objects
    "produit": [(("poly", [(12, 3), (20, 7.5), (12, 12), (4, 7.5)], True), "f:ice"), (("poly", [(4, 7.5), (4, 16.5), (12, 21), (12, 12)], True), "f:ice"),
                (("poly", [(20, 7.5), (20, 16.5), (12, 21), (12, 12)], True), "s")],
    "telephone": [(("rect", 7.5, 2.5, 9, 19), "f:cyan"), (("line", 10.5, 4.6, 13.5, 4.6), "s"), (("rect", 8.8, 6.2, 6.4, 11), "s"),
                  (("ellipse", 12, 19.3, 0.8, 0.8), "s")],
    "ordinateur": [(("rect", 5, 5, 14, 9.5), "f:cyan"), (("poly", [(3, 18.5), (5, 14.5), (19, 14.5), (21, 18.5)], True), "s"),
                   (("line", 10, 16.6, 14, 16.6), "s")],
    "batterie": [(("rect", 4, 8, 15, 9), "s"), (("rect", 19, 10.5, 2, 4), "s"), (("rect", 5.5, 9.5, 8, 6), "f:green"),
                 (("poly", [(12.5, 9), (9.5, 12.8), (12, 12.8), (10.5, 16)], False), "s")],
    "prise": [(("rect", 4, 4, 9, 13), "f:yellow"), (("line", 7, 8.5, 7, 10.5), "s"), (("line", 10, 8.5, 10, 10.5), "s"),
              (("ellipse", 8.5, 13.5, 0.8, 0.8), "s"), (("curve", [(13, 12), (17, 12), (19, 16), (17.5, 21)], False), "s")],
    "outil": [(("line", 5, 19, 15, 9), "s"), (("line", 6.5, 20.5, 16.5, 10.5), "s"), (("ellipse", 17.2, 6.8, 3.6, 3.6), "f:orange"),
              (("poly", [(16.5, 5.5), (18.5, 7.5)], False), "s")],
    "colis": [(("rect", 4, 7, 16, 13), "f:orange"), (("line", 12, 7, 12, 20), "s"), (("poly", [(4, 7), (7, 3.5), (17, 3.5), (20, 7)], True), "s"),
              (("line", 9, 14, 15, 14), "s")],
    "voiture": [(("poly", [(3, 16), (4, 11.5), (7.5, 11), (9.5, 7), (15, 7), (17.5, 11), (21, 12), (21, 16)], True), "f:red"),
                (("ellipse", 7.5, 16.5, 2.2, 2.2), "s"), (("ellipse", 16.5, 16.5, 2.2, 2.2), "s"), (("line", 12, 7.5, 12, 11), "s")],
    "panier": [(("poly", [(2.5, 5), (5.5, 5), (8, 15.5), (18, 15.5), (20.5, 8), (6.5, 8)], False), "s"),
               (("poly", [(7, 9), (19.5, 9), (17.6, 14.5), (8.2, 14.5)], True), "f:green"),
               (("ellipse", 9, 19, 1.4, 1.4), "s"), (("ellipse", 17, 19, 1.4, 1.4), "s")],
    "argent": [(("ellipse", 12, 12, 8.5, 8.5), "f:yellow"), (("curve", [(14.8, 8.6), (12, 7.6), (9.4, 9), (12, 12), (14.8, 14.6), (12, 16.4), (9.2, 15.4)], False), "s"),
               (("line", 12, 5.8, 12, 18.2), "s")],
    "horloge": [(("ellipse", 12, 12.5, 8.3, 8.3), "f:teal"), (("line", 12, 12.5, 12, 7.5), "s"), (("line", 12, 12.5, 15.8, 14.4), "s")],
    "notice": [(("poly", [(3, 5.5), (11.5, 7), (11.5, 20), (3, 18.5)], True), "f:violet"), (("poly", [(21, 5.5), (12.5, 7), (12.5, 20), (21, 18.5)], True), "s"),
               (("line", 5, 10, 9.5, 10.8), "s"), (("line", 5, 13, 9.5, 13.8), "s"), (("line", 14.5, 10.8, 19, 10), "s")],
    # surroundings
    "soleil": [(("ellipse", 12, 12, 4.5, 4.5), "f:yellow")] + [(("line", 12 + 6.5 * math.cos(a), 12 + 6.5 * math.sin(a), 12 + 9 * math.cos(a),
                                                                     12 + 9 * math.sin(a)), "s") for a in [i * PI / 4 for i in range(8)]],
    "pluie": [(("curve", [(6, 13), (3.5, 11), (5.5, 7.5), (9, 7.5), (11, 4), (16, 4.5), (17.5, 8), (21, 9), (20, 13)], False), "f:ice"),
              (("line", 6, 13, 20, 13), "s"), (("line", 8, 15.5, 7, 19), "s"), (("line", 12.5, 15.5, 11.5, 19), "s"), (("line", 17, 15.5, 16, 19), "s")],
    "froid": [(("line", 12, 3, 12, 21), "s"), (("line", 4.2, 7.5, 19.8, 16.5), "s"), (("line", 4.2, 16.5, 19.8, 7.5), "s"),
              (("ellipse", 12, 12, 2.2, 2.2), "f:ice"), (("poly", [(10, 4.8), (12, 6.4), (14, 4.8)], False), "s"),
              (("poly", [(10, 19.2), (12, 17.6), (14, 19.2)], False), "s")],
    "nuit": [(("curve", [(15, 3.5), (8, 5), (6.5, 13), (12, 19.5), (19.5, 17.5), (12.5, 15), (11.5, 8.5), (15, 3.5)], True), "f:violet"),
             (("line", 18, 6, 18, 9), "s"), (("line", 16.5, 7.5, 19.5, 7.5), "s")],
    "bruit": [(("poly", [(3, 9.5), (7, 9.5), (11.5, 5), (11.5, 19), (7, 14.5), (3, 14.5)], True), "f:pink"),
              (("arc", 12, 12, 4, 4, -0.3 * PI, 0.6 * PI), "s"), (("arc", 12, 12, 7, 7, -0.3 * PI, 0.6 * PI), "s"),
              (("arc", 12, 12, 10, 10, -0.28 * PI, 0.56 * PI), "s")],
    "eau": [(("curve", [(12, 3), (8, 10), (6.5, 14.5), (8.5, 19.5), (12, 21), (15.5, 19.5), (17.5, 14.5), (16, 10), (12, 3)], True), "f:blue"),
            (("curve", [(9.5, 15), (10, 17.5), (12, 18.6)], False), "s")],
    "poussiere": [(("ellipse", 6, 8, 1.2, 1.2), "f:orange"), (("ellipse", 11, 5, 0.9, 0.9), "s"), (("ellipse", 17, 9, 1.4, 1.4), "f:orange"),
                  (("ellipse", 8, 15, 1, 1), "s"), (("ellipse", 15, 16, 1.2, 1.2), "f:orange"), (("ellipse", 19, 19, 0.8, 0.8), "s"),
                  (("curve", [(3, 20), (8, 18), (11, 20.5), (16, 19)], False), "s")],
    # ideas and feelings
    "idee": [(("curve", [(9.2, 17), (8.8, 14.2), (6.6, 11.6), (7.2, 6.8), (12, 4.2), (16.8, 6.8), (17.4, 11.6), (15.2, 14.2), (14.8, 17)], False), "f:yellow"),
             (("line", 9.2, 17, 14.8, 17), "s"), (("line", 9.8, 19.6, 14.2, 19.6), "s")],
    "question": [(("curve", [(4, 11), (4.5, 4.5), (12, 3), (19.5, 4.5), (20, 11), (16, 16.5), (10, 16.5), (6, 20.5), (6.5, 16), (4, 11)], True), "f:cyan"),
                 (("arc", 12, 8.2, 2.6, 2.4, PI, 1.35 * PI), "s"), (("line", 12, 10.6, 12, 12.2), "s"), (("ellipse", 12, 14, 0.6, 0.6), "s")],
    "danger": [(("poly", [(12, 3), (21.5, 20), (2.5, 20)], True), "f:orange"), (("line", 12, 9, 12, 14.5), "s"), (("ellipse", 12, 17, 0.7, 0.7), "s")],
    "content": _face(0.15 * PI),
    "frustre": _face(1.15 * PI),
    "coeur": [(("curve", [(12, 20), (5, 14.5), (3.5, 9), (6.5, 5), (10.5, 5.5), (12, 8.5), (13.5, 5.5), (17.5, 5), (20.5, 9), (19, 14.5), (12, 20)], True), "f:pink")],
    "mouvement": [(("line", 3, 12, 19, 12), "s"), (("poly", [(14.5, 7), (20.5, 12), (14.5, 17)], False), "s"),
                  (("line", 4, 7.5, 9, 7.5), "s"), (("line", 4, 16.5, 9, 16.5), "s"), (("rect", 3, 10.6, 3, 2.8), "f:green")],
}


def sprite(pen_cls, hl, term=False):
    """The two sprites: pencil (fills then strokes) or crisp (light fills, clean strokes). Symbols are « p-<key> »."""
    out = ['<svg xmlns="http://www.w3.org/2000/svg" style="display:none">']
    for key, shapes in PICTOS.items():
        pen = pen_cls(("tstory-" if term else "story-") + key, jitter=0 if term else 0.26, passes=1 if term else 2)
        body = []
        for shape, role in shapes:
            if role.startswith("f:"):
                body.append(pen.fill(shape, hl[role[2:]], 0.28 if term else 0.6, 0 if term else 0.6, 0 if term else 0.4))
        body += [pen.stroke(shape, width=1.5 if term else 1.6) for shape, _role in shapes]
        out.append('<symbol id="p-{}" viewBox="0 0 24 24">{}</symbol>'.format(key, "".join(body)))
    out.append("</svg>")
    return "\n".join(out) + "\n"
