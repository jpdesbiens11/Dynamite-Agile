"""Diamond -> PowerPoint (0.60.50, D-O-059): the diagrams of draw.io, slide by slide, with native shapes a student moves,
recolours and retypes in PowerPoint, Keynote, LibreOffice Impress or Google Slides.

The boxes and arrows are the ones export_drawio.py lays out (Page.items): one source for both files. A large tree is cut
for a slide that stays readable: an overview (primary and secondary functions) then one slide per branch. Arrows are
connectors glued to their boxes: move a box, the arrow follows.
"""
import re
from html.parser import HTMLParser
from xml.sax.saxutils import escape

from . import export_data as X
from . import export_drawio as D
from .pptx_book import SLIDE_H, SLIDE_W, package

PT = 12700          # EMU per point
MARGIN = 0.03       # of the slide, around a diagram
SPLIT_LEAVES = 10   # beyond this many leaves, the tree goes overview + one slide per branch


def _style(s):
    out = {}
    for part in (s or "").split(";"):
        if part:
            k, _, v = part.partition("=")
            out[k] = v if _ else "1"
    return out


def _hex(v, default=None):
    v = (v or "").lstrip("#")
    return v.upper() if re.fullmatch(r"[0-9A-Fa-f]{6}", v) else default


class _Label(HTMLParser):
    """The little HTML of a draw.io label (<b>, <i>, <font>, <br>) -> paragraphs of runs."""

    def __init__(self, size, color, bold, italic):
        super().__init__(convert_charrefs=True)
        self.stack = [{"size": size, "color": color, "b": bold, "i": italic}]
        self.paras = [[]]

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.paras.append([])
            return
        top, a = dict(self.stack[-1]), dict(attrs)
        if tag == "b":
            top["b"] = True
        elif tag == "i":
            top["i"] = True
        elif tag == "font":
            top["color"] = _hex(a.get("color"), top["color"])
            m = re.search(r"font-size:\s*([\d.]+)px", a.get("style") or "")
            if m:
                top["size"] = float(m.group(1))
        self.stack.append(top)

    def handle_endtag(self, tag):
        if tag in ("b", "i", "font") and len(self.stack) > 1:
            self.stack.pop()

    def handle_data(self, data):
        if data:
            self.paras[-1].append((data, dict(self.stack[-1])))


class Slide:
    def __init__(self, page):
        self.page, self.shapes, self.n, self.geo = page, [], 1, {}
        boxes = [i for i in page.items if i["kind"] == "box"]
        x0 = min([b["x"] for b in boxes] + [0]) - 20
        y0 = min([b["y"] for b in boxes] + [0]) - 10
        w, h = page.width + 40 - x0, page.height + 40 - y0
        self.k = min(SLIDE_W * (1 - 2 * MARGIN) / w, SLIDE_H * (1 - 2 * MARGIN) / h)  # EMU per draw.io pixel
        self.ox = (SLIDE_W - w * self.k) / 2 - x0 * self.k
        self.oy = (SLIDE_H - h * self.k) / 2 - y0 * self.k

    def _id(self):
        self.n += 1
        return self.n

    def px(self, x, y):
        return int(self.ox + x * self.k), int(self.oy + y * self.k)

    def pt(self, size):
        return max(1.0, size * self.k / PT)  # proportional: the slide is vector, a dense diagram reads zoomed in

    def _runs(self, value, st):
        lab = _Label(float(st.get("fontSize", 11)), _hex(st.get("fontColor"), X.INK),
                     int(st.get("fontStyle", 0) or 0) & 1 == 1, int(st.get("fontStyle", 0) or 0) & 2 == 2)
        lab.feed(str(value or ""))
        algn = {"left": "l", "right": "r"}.get(st.get("align"), "ctr")
        paras = []
        for runs in lab.paras:
            body = "".join('<a:r><a:rPr lang="fr-CA" sz="{}" b="{}" i="{}" dirty="0"><a:solidFill><a:srgbClr val="{}"/></a:solidFill>'
                           '</a:rPr><a:t>{}</a:t></a:r>'.format(int(self.pt(f["size"]) * 100), int(bool(f["b"])), int(bool(f["i"])),
                                                                 f["color"] or X.INK, escape(t)) for t, f in runs)
            end = int(self.pt(float(st.get("fontSize", 11))) * 100)
            paras.append('<a:p><a:pPr algn="{}"/>{}<a:endParaRPr lang="fr-CA" sz="{}" dirty="0"/></a:p>'.format(algn, body, end))
        return "".join(paras)

    def _line(self, st, default_w=1.0):
        color = _hex(st.get("strokeColor"), X.INK if st.get("strokeColor") != "none" else None)
        if not color:
            return "<a:ln><a:noFill/></a:ln>"
        dash = '<a:prstDash val="dash"/>' if st.get("dashed") == "1" else ""
        return '<a:ln w="{}"><a:solidFill><a:srgbClr val="{}"/></a:solidFill>{}</a:ln>'.format(
            max(3175, int(float(st.get("strokeWidth", default_w)) * self.k)), color, dash)

    def box(self, item):
        st, sid = _style(item["style"]), self._id()
        x, y = self.px(item["x"], item["y"])
        w, h = max(1, int(item["w"] * self.k)), max(1, int(item["h"] * self.k))
        self.geo[item["id"]] = (sid, x, y, w, h)
        name = escape(re.sub(r"<[^>]+>", " ", str(item["value"] or ""))[:60].strip() or "Forme", {'"': "&quot;"})
        if st.get("shape") == "line":  # a legend swatch: the line itself
            self.shapes.append('<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{}" name="{}"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr><p:spPr><a:xfrm>'
                               '<a:off x="{}" y="{}"/><a:ext cx="{}" cy="0"/></a:xfrm><a:prstGeom prst="line"><a:avLst/></a:prstGeom>{}'
                               '</p:spPr></p:cxnSp>'.format(sid, name, x, y + h // 2, w, self._line(st)))
            return
        text = "text" in st
        fill = _hex(st.get("fillColor")) if not text else None
        geom = '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        if st.get("rounded") == "1" and not text:
            geom = '<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val {}"/></a:avLst></a:prstGeom>'.format(
                min(50000, int(float(st.get("arcSize", 15)) * 1000)))
        anchor = {"top": "t", "bottom": "b"}.get(st.get("verticalAlign"), "ctr")
        ins = lambda key, d: int(float(st.get(key, d)) * self.k)  # noqa: E731
        self.shapes.append(
            '<p:sp><p:nvSpPr><p:cNvPr id="{}" name="{}"/><p:cNvSpPr{}/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{}" y="{}"/>'
            '<a:ext cx="{}" cy="{}"/></a:xfrm>{}{}{}</p:spPr><p:txBody><a:bodyPr wrap="square" lIns="{}" tIns="{}" rIns="{}" bIns="{}" '
            'anchor="{}" rtlCol="0"><a:noAutofit/></a:bodyPr><a:lstStyle/>{}</p:txBody></p:sp>'.format(
                sid, name, ' txBox="1"' if text else "", x, y, w, h, geom,
                '<a:solidFill><a:srgbClr val="{}"/></a:solidFill>'.format(fill) if fill else "<a:noFill/>",
                "<a:ln><a:noFill/></a:ln>" if text else self._line(st), ins("spacingLeft", 4), ins("spacingTop", 2), ins("spacingRight", 4),
                ins("spacingBottom", 2), anchor, self._runs(item["value"], st)))

    def _point(self, g, ex, ey):
        _sid, x, y, w, h = g
        return x + w * ex, y + h * ey

    def edge(self, item):
        st = _style(item["style"])
        a, b = self.geo.get(item["src"]), self.geo.get(item["dst"])
        if not a or not b:
            return
        horizontal = st.get("elbow") == "horizontal" or (st.get("exitX") in ("0", "1") and st.get("entryX") in ("0", "1")
                                                         and st.get("exitX") != st.get("entryX"))
        if st.get("elbow") == "horizontal":
            ex, ey, nx, ny = 1, 0.5, 0, 0.5
        else:
            ex, ey = float(st.get("exitX", 1)), float(st.get("exitY", 0.5))
            nx, ny = float(st.get("entryX", 0)), float(st.get("entryY", 0.5))
        (x1, y1), (x2, y2) = self._point(a, ex, ey), self._point(b, nx, ny)
        site = lambda px_, py_: 3 if px_ >= 1 else 1 if px_ <= 0 else 2 if py_ >= 1 else 0  # noqa: E731  right, left, bottom, top
        flip = "{}{}".format(' flipH="1"' if x2 < x1 else "", ' flipV="1"' if y2 < y1 else "")
        prst = "bentConnector3" if horizontal and abs(y2 - y1) > 1 else "straightConnector1"
        head = '<a:tailEnd type="triangle"/>' if st.get("endArrow") != "none" else ""
        line = self._line(st, 1.4).replace("</a:ln>", head + "</a:ln>")
        self.shapes.append(
            '<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{}" name="Flux"/><p:cNvCxnSpPr><a:stCxn id="{}" idx="{}"/><a:endCxn id="{}" idx="{}"/>'
            '</p:cNvCxnSpPr><p:nvPr/></p:nvCxnSpPr><p:spPr><a:xfrm{}><a:off x="{}" y="{}"/><a:ext cx="{}" cy="{}"/></a:xfrm>'
            '<a:prstGeom prst="{}"><a:avLst/></a:prstGeom>{}</p:spPr></p:cxnSp>'.format(
                self._id(), a[0], site(ex, ey), b[0], site(nx, ny), flip, int(min(x1, x2)), int(min(y1, y2)),
                int(abs(x2 - x1)), int(abs(y2 - y1)), prst, line))
        if item["value"]:
            t = (float(item["at"] or 0) + 1) / 2
            lx, ly = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            w, h = int(150 * self.k), int(20 * self.k)
            self.box({"id": item["id"] + "t", "x": (lx - w / 2 - self.ox) / self.k, "y": (ly - h / 2 - self.oy) / self.k, "w": 150, "h": 20,
                      "value": item["value"], "style": "text;align=center;fontSize={};fillColor=#FFFFFF;fontColor=#1F2933;".format(
                          st.get("fontSize", 10))})

    def xml(self):
        for item in self.page.items:
            (self.box if item["kind"] == "box" else self.edge)(item)
        return "".join(self.shapes)


def _title_slide(data, what):
    run = lambda text, size, color, b=1: ('<a:r><a:rPr lang="fr-CA" sz="{}" b="{}" dirty="0"><a:solidFill><a:srgbClr val="{}"/>'  # noqa: E731
                                          '</a:solidFill></a:rPr><a:t>{}</a:t></a:r>').format(size * 100, b, color, escape(text))
    para = lambda *runs: '<a:p><a:pPr algn="l"/>{}</a:p>'.format("".join(runs))  # noqa: E731
    body = "".join([para(run("Dynamite", 40, X.ORANGE), run("Agile", 40, X.TEAL)), para(run(" ", 14, X.INK, 0)),
                    para(run("{} — {}".format(data["project"]["name"], what), 30, X.NAVY)),
                    para(run("Space {} · {} · DynamiteAgile v{}".format(data["project"]["key"], data["date"], data["version"]), 16, X.MUTED, 0)),
                    para(run(" ", 14, X.INK, 0)), para(run(X.WORKFLOW, 16, X.TEAL))])
    return ('<p:sp><p:nvSpPr><p:cNvPr id="2" name="Titre"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{}" y="{}"/>'
            '<a:ext cx="{}" cy="{}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody>'
            '<a:bodyPr wrap="square" anchor="ctr"><a:noAutofit/></a:bodyPr><a:lstStyle/>{}</p:txBody></p:sp>').format(
        SLIDE_W // 12, SLIDE_H // 6, SLIDE_W * 5 // 6, SLIDE_H * 2 // 3, body)


def _leaves(data, fid):
    kids = data["kids"].get(fid, [])
    return 1 if not kids else sum(_leaves(data, k["id"]) for k in kids)


def tree_pages(data):
    """The whole tree on one slide while it stays readable; otherwise an overview, then one slide per branch."""
    roots = [f for f in data["kids"].get(None, []) if f["in_tree"]]
    if sum(_leaves(data, r["id"]) for r in roots) <= SPLIT_LEAVES:
        return [D.tree_page(data)]
    over = dict(data, kids={None: data["kids"].get(None, []), **{r["id"]: data["kids"].get(r["id"], []) for r in roots}})
    pages = [D.tree_page(over, "Arbre fonctionnel — vue d'ensemble")]
    for r in roots:
        for s in data["kids"].get(r["id"], []):
            if not data["kids"].get(s["id"]):
                continue
            branch, todo = [], [s]
            while todo:
                f = todo.pop(0)
                branch.append(f)
                todo += data["kids"].get(f["id"], [])
            sub = dict(data, kids={**data["kids"], None: [s]}, tree=branch)
            pages.append(D.tree_page(sub, "Arbre fonctionnel — {} {}".format(X.code(s), s["text"])))
    return pages


def build(data, only=None):
    pages = []
    if only in (None, "tree"):
        pages += tree_pages(data)
    if only in (None, "structure"):
        pages += [D.structure_page(data, "general"), D.structure_page(data, "detail")]
    if only is None:
        pages.append(D.risk_page(data))
    what = {"tree": "arbre fonctionnel", "structure": "structure fonctionnelle"}.get(only, "analyse fonctionnelle (Diamond)")
    slides = [_title_slide(data, what)] + [Slide(p).xml() for p in pages]
    return package(slides, "Diamond — {} ({})".format(data["project"]["name"], data["project"]["key"]))
