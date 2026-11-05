"""Diamond -> draw.io (0.60.33, D-O-041): every diagram of the functional analysis, one .drawio file, one page each.

Pages: Arbre fonctionnel (left -> right « Comment ? », right -> left « Pourquoi ? », the colours of the levels, the
critical path in red, the parts under each function), Structure — vue générale and — vue détaillée (the boundary
diagram as on the screen: inputs on the left, the system frame and its sub-systems, outputs on the right, flows by
kind: energy, material, information), Carte des risques (P x I, now and residual). Each page has its title block
(« DynamiteAgile », the Space, the date) and, at the bottom, « Co-Intelligence WorkFlow™ ». Every box and arrow stays
editable in draw.io (diagrams.net, desktop or web), then exports to PNG / SVG / PDF for Word or PowerPoint.
"""
import html
from xml.sax.saxutils import escape

from . import export_data as X

W, H, VGAP, HGAP = 240, 58, 16, 64        # tree boxes
SW, SH, PW, PH, GAP, LEFT, FRAME_X, TOP = 184, 56, 184, 58, 70, 16, 260, 64  # the structure screen (structure_draw.js)
AIR = 1.6  # a printed diagram needs more room between the boxes than the screen: lanes for the flows (default layout only)
HEAD = 150                                # room for the title block above a diagram
FONT = "fontFamily=Segoe UI;"
LEVEL_FILL = {lv: "#" + c for lv, c in X.LEVEL_FILL.items()}
FLOW = {"energy": "strokeColor=#E0602F;strokeWidth=2.4;", "material": "strokeColor=#1F2933;strokeWidth=4;",
        "information": "strokeColor=#2F6FD0;strokeWidth=2;dashed=1;dashPattern=7 5;"}
RISK_FILL = {k: "#" + f for k, (f, _c) in X.RISK_STYLE.items()}
RISK_INK = {k: "#" + c for k, (_f, c) in X.RISK_STYLE.items()}


def _a(text):
    return escape(str(text), {'"': "&quot;", "\n": "&#10;"})


def _h(text):
    return html.escape(str(text or ""), quote=False)


class Page:
    COUNT = 0

    def __init__(self, name):
        Page.COUNT += 1
        self.name, self.cells, self.n, self.tag = name, [], 0, "p{}".format(Page.COUNT)  # ids unique in the whole file
        self.width = self.height = 0
        self.items = []  # the same boxes and arrows, kept structured for PowerPoint (export_pptx.py, 0.60.50)

    def _id(self, prefix):
        self.n += 1
        return "{}{}{}".format(self.tag, prefix, self.n)

    def box(self, x, y, w, h, value, style, html_label=True):
        cid = self._id("v")
        self.cells.append('<mxCell id="{}" value="{}" style="{}{}{}" vertex="1" parent="{}L"><mxGeometry x="{}" y="{}" width="{}" '
                          'height="{}" as="geometry"/></mxCell>'.format(cid, _a(value), "html=1;whiteSpace=wrap;" if html_label else "",
                                                                         FONT, style, self.tag, round(x), round(y), round(w), round(h)))
        self.width, self.height = max(self.width, x + w), max(self.height, y + h)
        self.items.append({"kind": "box", "id": cid, "x": x, "y": y, "w": w, "h": h, "value": value, "style": style})
        return cid

    def edge(self, src, dst, style, value="", at=0):
        """at: where the label sits along the arrow, -1 (source) to 1 (target)"""
        cid = self._id("e")
        self.cells.append('<mxCell id="{}" value="{}" style="html=1;{}{}" edge="1" parent="{}L" source="{}" target="{}">'
                          '<mxGeometry{} relative="1" as="geometry"/></mxCell>'.format(cid, _a(value), FONT, style, self.tag, src, dst,
                                                                                     ' x="{}"'.format(at) if at else ""))
        self.items.append({"kind": "edge", "id": cid, "src": src, "dst": dst, "style": style, "value": value, "at": at})
        return cid

    def to_back(self):
        """The last box goes behind everything (the frame of the system)."""
        self.cells.insert(0, self.cells.pop())
        self.items.insert(0, self.items.pop())

    def xml(self, index):
        w, h = int(self.width + 60), int(self.height + 60)
        return ('<diagram id="da-{}" name="{}"><mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" '
                'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{}" pageHeight="{}" math="0" shadow="0">'
                '<root><mxCell id="{t}R"/><mxCell id="{t}L" parent="{t}R"/>{cells}</root></mxGraphModel></diagram>').format(
            index, _a(self.name), w, h, t=self.tag, cells="".join(self.cells))


def title_block(page, data, title, subtitle, width=760):
    brand = '<b><font style="font-size:26px" color="#E0602F">Dynamite</font><font style="font-size:26px" color="#0E9A9A">Agile</font></b>'
    page.box(40, 24, 320, 40, brand, "text;align=left;verticalAlign=middle;strokeColor=none;fillColor=none;")
    page.box(40, 66, width, 32, "<b>{}</b>".format(_h(title)), "text;align=left;verticalAlign=middle;fontSize=20;fontColor=#0B1B33;strokeColor=none;fillColor=none;")
    page.box(40, 98, max(width, 1100), 24, _h("{} — Space {} · {} · {}".format(data["project"]["name"], data["project"]["key"], data["date"], subtitle)),
             "text;align=left;verticalAlign=middle;fontSize=12;fontColor=#5B6573;fontStyle=2;strokeColor=none;fillColor=none;")


def footer(page, data):
    y = page.height + 30
    page.box(40, y, 600, 22, _h("{} ({}) · DynamiteAgile v{} · {}".format(data["project"]["name"], data["project"]["key"], data["version"], data["stamp"])),
             "text;align=left;verticalAlign=middle;fontSize=10;fontColor=#5B6573;strokeColor=none;fillColor=none;")
    page.box(max(page.width - 260, 640), y, 260, 22, _h(X.WORKFLOW), "text;align=right;verticalAlign=middle;fontSize=11;fontStyle=3;"
             "fontColor=#0E9A9A;strokeColor=none;fillColor=none;")


def legend(page, x, y, items, title="Légende"):
    """items: [(swatch style, label)]"""
    h = 34 + 26 * len(items)
    page.box(x, y, 280, h, "", "rounded=1;arcSize=6;fillColor=#FFFFFF;strokeColor=#C9D1DB;")
    page.box(x + 12, y + 6, 250, 22, "<b>{}</b>".format(_h(title)), "text;align=left;fontSize=12;fontColor=#0B1B33;strokeColor=none;fillColor=none;")
    for i, (style, label) in enumerate(items):
        yy = y + 34 + 26 * i
        page.box(x + 14, yy + 3, 34, 16, "", style)
        page.box(x + 58, yy, 210, 22, _h(label), "text;align=left;verticalAlign=middle;fontSize=11;fontColor=#1F2933;strokeColor=none;fillColor=none;")


def _fn_label(f, data):
    parts = X.part_codes(data, f["id"])
    tail = '<br><font style="font-size:10px" color="#5B6573">{}</font>'.format(_h(parts)) if parts else ""
    return "<b>{}</b> {}{}".format(X.code(f), _h(f["text"]), tail)


def _fn_style(f):
    lv = f["level"] if f.get("in_tree", True) else 4
    stroke = "strokeColor=#D64545;strokeWidth=3;" if f["critical"] else "strokeColor=#26323F;strokeWidth={};".format(2.5 if lv == 1 else 1.4)
    return "rounded=1;arcSize=12;fillColor={};{}fontSize=12;fontColor=#1F2933;{}".format(LEVEL_FILL[lv], stroke, "fontStyle=1;" if lv == 1 else "")


def tree_page(data, title="Arbre fonctionnel"):
    page = Page(title)
    title_block(page, data, title, "Comment ? → vers la droite · ← Pourquoi ? vers la gauche · Quand ? de haut en bas")
    kids, ids, ypos = data["kids"], {}, {}
    nxt = [HEAD + 20]

    def place(f):
        children = kids.get(f["id"], [])
        if not children:
            ypos[f["id"]] = nxt[0]
            nxt[0] += H + VGAP
        else:
            for c in children:
                place(c)
            ypos[f["id"]] = (ypos[children[0]["id"]] + ypos[children[-1]["id"]]) / 2
    roots = [f for f in kids.get(None, []) if f["in_tree"]]
    outside = [f for f in data["tree"] if not f["in_tree"] and f["parent_id"] is None]
    for r in roots:
        place(r)
    for f in data["tree"]:
        if f["in_tree"] and f["id"] in ypos:
            ids[f["id"]] = page.box(40 + (f["level"] - 1) * (W + HGAP), ypos[f["id"]], W, H, _fn_label(f, data), _fn_style(f))
    for f in data["tree"]:
        if f["in_tree"] and f["parent_id"] in ids and f["id"] in ids:
            critical = f["critical"] and data["by_id"][f["parent_id"]]["critical"]
            page.edge(ids[f["parent_id"]], ids[f["id"]], "edgeStyle=elbowEdgeStyle;elbow=horizontal;rounded=1;endArrow=none;"
                      + ("strokeColor=#D64545;strokeWidth=2.6;" if critical else "strokeColor=#5B6573;strokeWidth=1.4;"))
    right = page.width + 40
    if outside:
        y = nxt[0] + 30
        page.box(40, y, W * 2 + HGAP, 26, "<b>Hors arbre</b> — fonctions d'estime et fonctions à placer", "text;align=left;fontSize=13;"
                 "fontColor=#0B1B33;strokeColor=none;fillColor=none;")
        for i, f in enumerate(outside):
            page.box(40 + (i % 3) * (W + HGAP), y + 34 + (i // 3) * (H + VGAP), W, H, _fn_label(f, data), _fn_style(f))
    legend(page, right, HEAD + 20, [("rounded=1;fillColor={};strokeColor=#26323F;strokeWidth=2.5;".format(LEVEL_FILL[1]), "Fonction primaire"),
                                    ("rounded=1;fillColor={};strokeColor=#26323F;".format(LEVEL_FILL[2]), "Fonction secondaire (sous-système)"),
                                    ("rounded=1;fillColor={};strokeColor=#26323F;".format(LEVEL_FILL[3]), "Fonction tertiaire"),
                                    ("rounded=1;fillColor={};strokeColor=#26323F;".format(LEVEL_FILL[4]), "Technique · hors arbre"),
                                    ("rounded=1;fillColor=#FFFFFF;strokeColor=#D64545;strokeWidth=3;", "Fonction critique (chemin critique)"),
                                    ("text;fontSize=10;fontColor=#5B6573;strokeColor=none;fillColor=none;", "P-n : pièces qui réalisent la fonction")])
    footer(page, data)
    return page


def _structure_layout(data, view):
    st = data["structure"]
    saved = {("function" if p["function_id"] else "port", p["function_id"] or p["port_id"]): (p["x"], p["y"])
             for p in st["positions"] if p["view"] == view}
    boxes = {}

    def put(kind, item, x, y, w, h):
        x, y = saved.get((kind, item["id"]), (x, y))
        boxes[(kind, item["id"])] = {"x": x, "y": y, "w": w, "h": h, "item": item, "kind": kind}
    fx = FRAME_X + 80
    if view == "general":
        cols, row = (2 if len(st["secondaries"]) > 3 else 1), SH + 64
        for i, f in enumerate(st["secondaries"]):
            c = i % cols
            put("function", f, fx + c * (SW + 120 * AIR), TOP + 40 + (i // cols) * row * AIR + (row * AIR / 2 if c else 0), SW, SH)
    else:
        y = TOP + 34
        for s in st["secondaries"]:
            kids = [f for f in st["views"]["detail"] if f["parent_id"] == s["id"] and f["level"] == 3]
            for j, f in enumerate(kids or [f for f in st["views"]["detail"] if f["id"] == s["id"]]):
                put("function", f, fx + j * (SW + GAP * AIR), y + 28, SW, SH)
            y += SH + 28 + 70 * AIR
    funcs = list(boxes.values())
    right = max([fx + SW] + [b["x"] + b["w"] for b in funcs]) + 40
    bottom = max([TOP] + [b["y"] + b["h"] for b in funcs])
    ins = [p for p in st["ports"] if p["side"] == "in"]
    outs = [p for p in st["ports"] if p["side"] == "out"]
    step = lambda n: max(PH + 22, (bottom - TOP) / max(n, 1))  # noqa: E731
    for i, p in enumerate(ins):
        put("port", p, LEFT, TOP + 30 + i * step(len(ins)), PW, PH)
    for i, p in enumerate(outs):
        put("port", p, right + 110, TOP + 30 + i * step(len(outs)), PW, PH)
    return boxes


def _bound(boxes, pad, head):
    if not boxes:
        return None
    x, y = min(b["x"] for b in boxes) - pad, min(b["y"] for b in boxes) - pad - head
    return x, y, max(b["x"] + b["w"] for b in boxes) + pad - x, max(b["y"] + b["h"] for b in boxes) + pad - y


def _sides(a, b):
    """Where a flow leaves and enters: left to right as a boundary diagram reads, top / bottom inside a column."""
    ax, bx = a["x"] + a["w"] / 2, b["x"] + b["w"] / 2
    if b["x"] >= a["x"] + a["w"] - 10:
        return "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"
    if b["x"] + b["w"] <= a["x"] + 10:
        return "exitX=0;exitY=0.5;entryX=1;entryY=0.5;"
    if abs(b["y"] - a["y"]) > 2.2 * a["h"]:  # a box may stand between: down the lane on the right of the column
        return "exitX=1;exitY=0.75;entryX=1;entryY=0.25;" if b["y"] > a["y"] else "exitX=1;exitY=0.25;entryX=1;entryY=0.75;"
    if b["y"] > a["y"]:
        return "exitX=0.5;exitY=1;entryX=0.5;entryY=0;" if abs(ax - bx) < 1 else "exitX=0.6;exitY=1;entryX=0.4;entryY=0;"
    return "exitX=0.4;exitY=0;entryX=0.6;entryY=1;"


def structure_page(data, view):
    names = {"general": "Structure — vue générale", "detail": "Structure — vue détaillée"}
    page = Page(names[view])
    title_block(page, data, "Structure fonctionnelle — " + data["labels"]["views"][view].lower(),
                "boundary diagram : entrées à gauche, sorties à droite")
    boxes = _structure_layout(data, view)
    dy = HEAD + 10
    funcs = [b for b in boxes.values() if b["kind"] == "function"]
    groups = []
    if view == "detail":
        for s in data["structure"]["secondaries"]:
            members = [b for b in funcs if b["item"]["parent_id"] == s["id"] or b["item"]["id"] == s["id"]]
            r = _bound(members, 12, 22)
            if r:
                groups.append(r)
                page.box(r[0], r[1] + dy, r[2], r[3], "<b>F{}</b> {}".format(s["number"], _h(s["text"])),
                         "rounded=1;arcSize=4;fillColor=#FBF3EE;strokeColor=#E7B9A3;verticalAlign=top;align=left;spacingLeft=8;"
                         "spacingTop=2;fontSize=11;fontColor=#7A3E1E;")
    system = _bound([{"x": g[0], "y": g[1], "w": g[2], "h": g[3]} for g in groups] if groups else funcs, 24, 30)
    if system:
        primary = data["structure"]["primary"]
        page.box(system[0], system[1] + dy, system[2], system[3],
                         "<b>Système</b>{}".format(" — " + _h(primary["text"]) if primary else ""),
                         "rounded=1;arcSize=3;dashed=1;dashPattern=8 4;fillColor=none;strokeColor=#0B1B33;strokeWidth=2;"
                         "verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;fontSize=12;fontColor=#0B1B33;")
        page.to_back()  # the frame behind everything
    ids = {}
    for key, b in boxes.items():
        item = b["item"]
        if b["kind"] == "function":
            ids[key] = page.box(b["x"], b["y"] + dy, b["w"], b["h"], _fn_label(item, data), _fn_style(item))
        else:
            side = "Entrée" if item["side"] == "in" else "Sortie"
            kind = item["kind"]
            stroke = {"energy": "strokeColor=#E0602F;strokeWidth=2;", "material": "strokeColor=#1F2933;strokeWidth=2.5;",
                      "information": "strokeColor=#2F6FD0;strokeWidth=1.6;dashed=1;"}[kind]
            ids[key] = page.box(b["x"], b["y"] + dy, b["w"], b["h"], '<font style="font-size:10px" color="#5B6573">{} · {}</font><br><b>{}</b>'.format(
                side, _h(data["labels"]["kinds"].get(kind, kind)), _h(item["label"])),
                "rounded=1;arcSize=30;fillColor=#FFFFFF;fontSize=12;fontColor=#1F2933;" + stroke)
    for fl in data["structure"]["flows"]:
        if fl["view"] != view:
            continue
        src = ("port", fl["src_port_id"]) if fl["src_port_id"] else ("function", fl["src_function_id"])
        dst = ("port", fl["dst_port_id"]) if fl["dst_port_id"] else ("function", fl["dst_function_id"])
        if src in ids and dst in ids:
            page.edge(ids[src], ids[dst], "edgeStyle=orthogonalEdgeStyle;rounded=1;jettySize=auto;orthogonalLoop=1;endArrow=block;"
                      "endFill=1;fontSize=10;fontColor=#1F2933;labelBackgroundColor=#FFFFFF;" + _sides(boxes[src], boxes[dst])
                      + FLOW.get(fl["kind"], ""), _h(fl["label"]), at=-0.45)
    legend(page, page.width + 50, HEAD + 20, [("endArrow=none;html=1;shape=line;" + FLOW["energy"], "Énergie"),
                                              ("shape=line;" + FLOW["material"], "Matière"),
                                              ("shape=line;" + FLOW["information"], "Information (signal)"),
                                              ("rounded=1;dashed=1;fillColor=none;strokeColor=#0B1B33;strokeWidth=2;", "Frontière du système"),
                                              ("rounded=1;arcSize=30;fillColor=#FFFFFF;strokeColor=#5B6573;", "Entrée / sortie du système"),
                                              ("rounded=1;fillColor=#FFFFFF;strokeColor=#D64545;strokeWidth=3;", "Fonction critique")],
           title="Légende des flux")
    footer(page, data)
    return page


def risk_page(data):
    page = Page("Carte des risques")
    title_block(page, data, "Carte des risques projet — probabilité × impact", "maintenant et après les actions (résiduel)")
    size, gx = 112, 120
    for k, (label, pkey, ikey) in enumerate((("Maintenant", "probability", "impact"), ("Résiduel (après action)", "residual_p", "residual_i"))):
        x0, y0 = 120 + k * (5 * size + 220), HEAD + 50
        page.box(x0, y0 - 40, 5 * size, 30, "<b>{}</b>".format(label), "text;align=center;fontSize=14;fontColor=#0B1B33;strokeColor=none;fillColor=none;")
        for impact in range(5, 0, -1):
            for p in range(1, 6):
                lvl = X.R.level(p * impact)["key"]
                here = ["R-{}".format(r["number"]) for r in data["risks"] if r[pkey] == p and r[ikey] == impact]
                page.box(x0 + (p - 1) * size, y0 + (5 - impact) * size, size, size, "<b>{}</b>".format(_h(", ".join(here))) if here else "",
                         "rounded=0;fillColor={};strokeColor=#FFFFFF;strokeWidth=3;fontSize=12;fontColor={};".format(RISK_FILL[lvl], RISK_INK[lvl]))
            page.box(x0 - 34, y0 + (5 - impact) * size, 28, size, str(impact), "text;align=center;verticalAlign=middle;fontSize=13;fontStyle=1;"
                     "strokeColor=none;fillColor=none;")
        for p in range(1, 6):
            page.box(x0 + (p - 1) * size, y0 + 5 * size + 4, size, 24, str(p), "text;align=center;fontSize=13;fontStyle=1;strokeColor=none;fillColor=none;")
        page.box(x0, y0 + 5 * size + 30, 5 * size, 22, "Probabilité →", "text;align=center;fontSize=12;fontColor=#5B6573;strokeColor=none;fillColor=none;")
        page.box(x0 - 110, y0 + 2 * size, 70, size, "Impact ↑", "text;align=center;verticalAlign=middle;fontSize=12;fontColor=#5B6573;strokeColor=none;fillColor=none;")
    lines = "<br>".join("<b>R-{}</b> {} — P×I {} ({})".format(r["number"], _h(r["title"]), r["score"], _h(r["level"]["label"])) for r in data["risks"])
    page.box(120, HEAD + 50 + 5 * size + 70, 2 * 5 * size + 220, 22 * max(len(data["risks"]), 1) + 20,
             lines or "Aucun risque au registre.", "text;align=left;verticalAlign=top;fontSize=11;fontColor=#1F2933;strokeColor=none;fillColor=none;")
    legend(page, 120 + 2 * (5 * size) + 260, HEAD + 50, [("fillColor={};strokeColor=none;".format(RISK_FILL["critique"]), "Critique : 15 à 25"),
                                                         ("fillColor={};strokeColor=none;".format(RISK_FILL["eleve"]), "Élevé : 10 à 14"),
                                                         ("fillColor={};strokeColor=none;".format(RISK_FILL["moyen"]), "Moyen : 5 à 9"),
                                                         ("fillColor={};strokeColor=none;".format(RISK_FILL["faible"]), "Faible : 1 à 4")],
           title="Niveaux (P × I)")
    footer(page, data)
    return page


PARTS = ("tree", "structure", "risks")


def pages(data, only=None):
    """only: "tree" or "structure" -- the diagram of one screen (0.60.50, D-O-059); None: every diagram."""
    out = []
    if only in (None, "tree"):
        out.append(tree_page(data))
    if only in (None, "structure"):
        out += [structure_page(data, "general"), structure_page(data, "detail")]
    if only is None:
        out.append(risk_page(data))
    return out


def build(data, only=None):
    pages_ = pages(data, only)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="DynamiteAgile" agent="DynamiteAgile v{}" version="24.0.0">{}</mxfile>\n'
            .format(_a(data["version"]), "".join(p.xml(i + 1) for i, p in enumerate(pages_))))
