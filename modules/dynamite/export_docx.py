"""Word (.docx) writer for the Dynamite export (D-B-050), standard library only:
WordprocessingML written by hand in a zip -- styles (title, headings 1-3,
code, quote), runs (bold, italic, underline, strike, code, colour, links),
indented list items, tables with a header row, images (PNG, JPEG, GIF)."""
import io
import struct
import zipfile
from xml.sax.saxutils import escape

COLORS = {"red": "C9372C", "orange": "E56910", "green": "216E4E", "blue": "0C66E4", "purple": "6E5DC6", "gray": "626F86",
          "yellow": "A54800"}
EMU_PER_PX = 9525
MAX_WIDTH_PX = 600
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ' \
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ' \
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" ' \
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" ' \
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Segoe UI" w:hAnsi="Segoe UI" w:cs="Segoe UI"/><w:sz w:val="21"/><w:color w:val="172B4D"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="100" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="60"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/><w:color w:val="0B1B33"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="280" w:after="100"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="32"/><w:color w:val="0C66E4"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="220" w:after="80"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="26"/><w:color w:val="172B4D"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="160" w:after="60"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="23"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/><w:pPr><w:shd w:val="clear" w:color="auto" w:fill="F1F2F4"/><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="18"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="360"/><w:pBdr><w:left w:val="single" w:sz="18" w:space="8" w:color="DCDFE4"/></w:pBdr></w:pPr><w:rPr><w:color w:val="44546F"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Panel"><w:name w:val="Panel"/><w:basedOn w:val="Normal"/><w:pPr><w:shd w:val="clear" w:color="auto" w:fill="E9F2FF"/><w:ind w:left="120" w:right="120"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Meta"><w:name w:val="Meta"/><w:basedOn w:val="Normal"/><w:rPr><w:sz w:val="17"/><w:color w:val="626F86"/></w:rPr></w:style>
<w:style w:type="table" w:styleId="Grid"><w:name w:val="Grid"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:color="DCDFE4"/><w:left w:val="single" w:sz="4" w:color="DCDFE4"/><w:bottom w:val="single" w:sz="4" w:color="DCDFE4"/><w:right w:val="single" w:sz="4" w:color="DCDFE4"/><w:insideH w:val="single" w:sz="4" w:color="DCDFE4"/><w:insideV w:val="single" w:sz="4" w:color="DCDFE4"/></w:tblBorders><w:tblCellMar><w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
</w:styles>"""


def image_size(data, mime):
    try:
        if mime == "image/png":
            return struct.unpack(">II", data[16:24])
        if mime == "image/gif":
            return struct.unpack("<HH", data[6:10])
        if mime == "image/jpeg":
            i = 2
            while i < len(data):
                marker, length = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
                if marker in (0xC0, 0xC1, 0xC2):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                i += 2 + length
    except (struct.error, IndexError):
        pass
    return None


class Writer:
    def __init__(self):
        self.body = []
        self.rels = []   # (rid, type, target, external)
        self.media = []  # (name, data)

    def rel(self, kind, target, external=False):
        rid = "rId{}".format(len(self.rels) + 10)
        self.rels.append((rid, kind, target, external))
        return rid

    def run(self, text, style=None):
        style = style or {}
        props = []
        if style.get("bold"):
            props.append("<w:b/>")
        if style.get("italic"):
            props.append("<w:i/>")
        if style.get("underline") or style.get("link"):
            props.append('<w:u w:val="single"/>')
        if style.get("strike"):
            props.append("<w:strike/>")
        if style.get("small"):
            props.append('<w:sz w:val="14"/>')
        if style.get("code"):
            props.append('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:shd w:val="clear" w:color="auto" w:fill="F1F2F4"/>')
        color = COLORS.get(style.get("color")) or ("0C66E4" if style.get("link") else None)
        if color:
            props.append('<w:color w:val="{}"/>'.format(color))
        parts = []
        for i, line in enumerate(str(text).split("\n")):
            if i:
                parts.append("<w:br/>")
            parts.append('<w:t xml:space="preserve">{}</w:t>'.format(escape(line)))
        xml = "<w:r>{}{}</w:r>".format("<w:rPr>{}</w:rPr>".format("".join(props)) if props else "", "".join(parts))
        if style.get("link", "").startswith("http"):
            rid = self.rel("http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", style["link"], True)
            xml = '<w:hyperlink r:id="{}">{}</w:hyperlink>'.format(rid, xml)
        return xml

    def para(self, runs, style=None, indent=0, keep=False):
        ppr = []
        if style:
            ppr.append('<w:pStyle w:val="{}"/>'.format(style))
        if indent:
            ppr.append('<w:ind w:left="{}" w:hanging="280"/>'.format(360 * indent + 280))
        self.body.append("<w:p>{}{}</w:p>".format("<w:pPr>{}</w:pPr>".format("".join(ppr)) if ppr else "",
                                                   "".join(self.run(t, s) for t, s in runs)))

    def table(self, header, rows):
        cols = max(len(r) for r in rows)
        width = int(9000 / cols)
        out = ['<w:tbl><w:tblPr><w:tblStyle w:val="Grid"/><w:tblW w:w="5000" w:type="pct"/></w:tblPr><w:tblGrid>',
               "".join('<w:gridCol w:w="{}"/>'.format(width) for _ in range(cols)), "</w:tblGrid>"]
        for r, row in enumerate(rows):
            head = header and r == 0
            out.append("<w:tr>{}".format('<w:trPr><w:tblHeader/></w:trPr>' if head else ""))
            for c in range(cols):
                runs = row[c] if c < len(row) else []
                if head:
                    runs = [(t, dict(s, bold=True)) for t, s in runs]
                shade = '<w:shd w:val="clear" w:color="auto" w:fill="F1F2F4"/>' if head else ""
                out.append('<w:tc><w:tcPr><w:tcW w:w="{}" w:type="dxa"/>{}</w:tcPr><w:p>{}</w:p></w:tc>'.format(
                    width, shade, "".join(self.run(t, s) for t, s in runs)))
            out.append("</w:tr>")
        out.append("</w:tbl>")
        self.body.append("".join(out))
        self.body.append("<w:p/>")

    def image(self, data, mime, alt, scale=1):
        size = image_size(data, mime) if data else None
        if not size:
            self.para([("[image : {}]".format(alt or "non incluse"), {"italic": True, "color": "gray"})], "Meta")
            return
        w, h = size[0] // scale, size[1] // scale  # scale: a Mermaid drawing made at 2x (0.60.62)
        if w > MAX_WIDTH_PX:
            w, h = MAX_WIDTH_PX, int(h * MAX_WIDTH_PX / w)
        n = len(self.media) + 1
        ext = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif"}[mime]
        name = "image{}.{}".format(n, ext)
        self.media.append((name, data))
        rid = self.rel("http://schemas.openxmlformats.org/officeDocument/2006/relationships/image", "media/" + name)
        cx, cy = w * EMU_PER_PX, h * EMU_PER_PX
        self.body.append(
            '<w:p><w:r><w:drawing><wp:inline><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{n}" name="Image {n}" descr="{alt}"/>'
            '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
            '<pic:nvPicPr><pic:cNvPr id="{n}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
            '<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            '</pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'.format(
                cx=cx, cy=cy, n=n, alt=escape(alt or "", {'"': "&quot;"}), name=name, rid=rid))
        if alt:
            self.para([(alt, {"italic": True})], "Meta")


def build(docs, meta):
    w = Writer()
    w.para([(meta["title"], {})], "Title")
    w.para([("Space {} · exporté par {} le {} · Dynamite | Agile".format(meta["space"], meta["by"], meta["at"]), {})], "Meta")
    for d, doc in enumerate(docs):
        if d:
            w.para([(doc["title"], {})], "Heading{}".format(min(3, doc["level"])))
        w.para([("Version {} · modifiée le {}".format(doc["version"], (doc["updated"] or "")[:10]), {})], "Meta")
        for item in doc["items"]:
            kind = item[0]
            if kind == "h":
                w.para(item[2], "Heading{}".format(item[1]))
            elif kind == "p":
                style = {"quote": "Quote", "panel": "Panel"}.get(item[2])
                w.para(item[1], style)
            elif kind == "li":
                w.para([(item[2] + "\t", {})] + item[3], None, indent=item[1] + 1)
            elif kind == "code":
                small = len(item) > 2 and item[2] == "small"  # the code under a Mermaid drawing (0.60.62)
                for line in (item[1] or " ").split("\n"):
                    w.para([(line or " ", {"small": True, "color": "gray"} if small else {})], "Code")
                w.para([], None)
            elif kind == "rule":
                w.body.append('<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="DCDFE4"/></w:pBdr></w:pPr></w:p>')
            elif kind == "table":
                w.table(item[1], item[2])
            elif kind == "image":
                w.image(item[1], item[2], item[3], item[4] if len(item) > 4 else 1)
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {}><w:body>{}'
                '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080" '
                'w:header="560" w:footer="560" w:gutter="0"/></w:sectPr></w:body></w:document>').format(W, "".join(w.body))
    rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>']
    for rid, kind, target, external in w.rels:
        rels.append('<Relationship Id="{}" Type="{}" Target="{}"{}/>'.format(rid, kind, escape(target, {'"': "&quot;"}),
                                                                              ' TargetMode="External"' if external else ""))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Default Extension="png" ContentType="image/png"/><Default Extension="jpg" ContentType="image/jpeg"/>'
                   '<Default Extension="gif" ContentType="image/gif"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                   '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                   '</Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                   'Target="word/document.xml"/></Relationships>')
        z.writestr("word/_rels/document.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{}</Relationships>'.format("".join(rels)))
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/document.xml", document)
        for name, data in w.media:
            z.writestr("word/media/" + name, data)
    return buf.getvalue()
