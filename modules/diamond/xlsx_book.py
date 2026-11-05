"""A small styled .xlsx writer for presentation workbooks (0.60.33, D-O-041), standard library only.

modules/exploration/xlsx.py writes data workbooks (fixed styles, read back by the importers); this one writes the
workbooks people show -- to a teacher, a jury, an investor: any mix of font, fill, border and alignment (styles made
on demand and shared), rich text (the two colours of « DynamiteAgile »), merged cells, row heights, frozen panes,
autofilter, the page header and footer printed on every page (the mark of the workbook), repeated title rows,
landscape fitted to the width.
"""
import io
import re
import zipfile
from xml.sax.saxutils import escape

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
FONT = "Segoe UI"
_BAD = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _x(text):
    return escape(_BAD.sub("", str(text)), {'"': "&quot;"})


def col(i):
    """0 -> A, 26 -> AA"""
    name = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        name = chr(65 + r) + name
    return name


class Book:
    def __init__(self):
        self.sheets = []
        self._fonts, self._fills, self._borders, self._xfs = [], [], [], []
        self.style()  # style 0: the default text

    def _index(self, registry, xml):
        if xml not in registry:
            registry.append(xml)
        return registry.index(xml)

    def style(self, bold=False, italic=False, size=10, color="1F2933", fill=None, border=False, h=None, v="top",
              wrap=False, rotate=0, numfmt=0):
        font = self._index(self._fonts, "<font>{}{}<sz val=\"{}\"/><color rgb=\"FF{}\"/><name val=\"{}\"/></font>".format(
            "<b/>" if bold else "", "<i/>" if italic else "", size, color, FONT))
        fill_id = self._index(self._fills, '<fill><patternFill patternType="solid"><fgColor rgb="FF{}"/></patternFill></fill>'.format(fill)) + 2 \
            if fill else 0
        line = '<{0} style="thin"><color rgb="FFC9D1DB"/></{0}>'
        border_id = self._index(self._borders, "<border>{}</border>".format("".join(line.format(s) for s in ("left", "right", "top", "bottom")))) + 1 \
            if border else 0
        align = '<alignment{}{}{}{}/>'.format(' horizontal="{}"'.format(h) if h else "", ' vertical="{}"'.format(v) if v else "",
                                              ' wrapText="1"' if wrap else "", ' textRotation="{}"'.format(rotate) if rotate else "")
        xf = ('<xf numFmtId="{}" fontId="{}" fillId="{}" borderId="{}" xfId="0" applyFont="1" applyFill="1" applyBorder="1" '
              'applyAlignment="1"{}>{}</xf>').format(numfmt, font, fill_id, border_id, ' applyNumberFormat="1"' if numfmt else "", align)
        return self._index(self._xfs, xf)

    def sheet(self, name, **kwargs):
        s = Sheet(name[:31], **kwargs)
        self.sheets.append(s)
        return s

    def _styles(self):
        fills = '<fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>' + "".join(self._fills)
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="{}">'
                '<fonts count="{}">{}</fonts><fills count="{}">{}</fills><borders count="{}"><border/>{}</borders>'
                '<cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="{}">{}</cellXfs>'
                '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>').format(
            NS, len(self._fonts), "".join(self._fonts), len(self._fills) + 2, fills, len(self._borders) + 1, "".join(self._borders),
            len(self._xfs), "".join(self._xfs))

    def bytes(self, title="", author="DynamiteAgile"):
        buf = io.BytesIO()
        n = len(self.sheets)
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            ws = "".join('<Override PartName="/xl/worksheets/sheet{}.xml" ContentType="application/vnd.openxmlformats-'
                         'officedocument.spreadsheetml.worksheet+xml"/>'.format(i + 1) for i in range(n))
            z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.'
                       'openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.'
                       'openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
                       '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.'
                       'spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.'
                       'openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/docProps/core.xml" '
                       'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>' + ws + "</Types>")
            z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{0}">'
                       '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                       'officeDocument" Target="xl/workbook.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.'
                       'org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>'.format(PKG_REL))
            z.writestr("docProps/core.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties '
                       'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                       'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{}</dc:title><dc:creator>{}</dc:creator>'
                       '</cp:coreProperties>'.format(_x(title), _x(author)))
            names = "".join(s.defined_name(i) for i, s in enumerate(self.sheets))
            z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="{}" xmlns:r="{}">'
                       '<sheets>{}</sheets>{}<calcPr calcId="191029"/></workbook>'.format(
                           NS, REL_NS, "".join('<sheet name="{}" sheetId="{}" r:id="rId{}"/>'.format(_x(s.name), i + 1, i + 1)
                                               for i, s in enumerate(self.sheets)),
                           "<definedNames>{}</definedNames>".format(names) if names else ""))
            z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{}">{}'
                       '<Relationship Id="rId{}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
                       'Target="styles.xml"/></Relationships>'.format(PKG_REL, "".join(
                           '<Relationship Id="rId{0}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                           'worksheet" Target="worksheets/sheet{0}.xml"/>'.format(i + 1) for i in range(n)), n + 1))
            z.writestr("xl/styles.xml", self._styles())
            for i, s in enumerate(self.sheets):
                z.writestr("xl/worksheets/sheet{}.xml".format(i + 1), s.xml())
        return buf.getvalue()


class Sheet:
    def __init__(self, name, landscape=True, tab=None):
        self.name, self.landscape, self.tab = name, landscape, tab
        self.cells = {}          # (row, col) -> (value, style)
        self.widths, self.heights, self.merges = {}, {}, []
        self.freeze = self.autofilter = None
        self.header = self.footer = ""
        self.print_rows = None   # (first, last) 1-based rows repeated on every printed page
        self.row = 0             # next free row, 1-based once used

    def put(self, r, c, value, style=0):
        self.cells[(r, c)] = (value, style)

    def line(self, values, styles=0, height=None):
        """Append a row; styles: one id or one per value. Returns the row number."""
        self.row += 1
        for c, v in enumerate(values):
            self.put(self.row, c, v, styles[c] if isinstance(styles, (list, tuple)) else styles)
        if height:
            self.heights[self.row] = height
        return self.row

    def skip(self, n=1):
        self.row += n

    def merge(self, r1, c1, r2, c2):
        self.merges.append("{}{}:{}{}".format(col(c1), r1, col(c2), r2))

    def defined_name(self, index):
        if not self.print_rows:
            return ""
        return '<definedName name="_xlnm.Print_Titles" localSheetId="{}">\'{}\'!${}:${}</definedName>'.format(
            index, _x(self.name).replace("'", "''"), *self.print_rows)

    def _cell(self, r, c, value, style):
        ref = "{}{}".format(col(c), r)
        s = ' s="{}"'.format(style) if style else ""
        if value is None or value == "":
            return '<c r="{}"{}/>'.format(ref, s)
        if isinstance(value, bool):
            value = "Oui" if value else "Non"
        if isinstance(value, (int, float)):
            return '<c r="{}"{}><v>{}</v></c>'.format(ref, s, value)
        if isinstance(value, list):  # rich text: [(text, {"bold": True, "color": "E0602F", "size": 14}), ...]
            runs = "".join('<r><rPr>{}{}<sz val="{}"/><color rgb="FF{}"/><rFont val="{}"/></rPr><t xml:space="preserve">{}</t></r>'.format(
                "<b/>" if o.get("bold") else "", "<i/>" if o.get("italic") else "", o.get("size", 10), o.get("color", "1F2933"),
                o.get("font", FONT), _x(t)) for t, o in value)
            return '<c r="{}"{} t="inlineStr"><is>{}</is></c>'.format(ref, s, runs)
        return '<c r="{}"{} t="inlineStr"><is><t xml:space="preserve">{}</t></is></c>'.format(ref, s, _x(value))

    def xml(self):
        rows = {}
        for (r, c), (v, s) in self.cells.items():
            rows.setdefault(r, []).append((c, v, s))
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="{}" xmlns:r="{}">'.format(NS, REL_NS),
               '<sheetPr>{}<pageSetUpPr fitToPage="1"/></sheetPr>'.format('<tabColor rgb="FF{}"/>'.format(self.tab) if self.tab else "")]
        view = '<sheetView workbookViewId="0" showGridLines="0" zoomScale="100">'
        if self.freeze:
            c, r = re.match(r"([A-Z]+)(\d+)", self.freeze).groups()
            xs = sum((ord(ch) - 64) * 26 ** i for i, ch in enumerate(reversed(c))) - 1
            view += '<pane{}{} topLeftCell="{}" activePane="bottomRight" state="frozen"/>'.format(
                ' xSplit="{}"'.format(xs) if xs else "", ' ySplit="{}"'.format(int(r) - 1) if int(r) > 1 else "", self.freeze)
        out.append("<sheetViews>{}</sheetView></sheetViews>".format(view))
        out.append('<sheetFormatPr defaultRowHeight="15"/>')
        if self.widths:
            out.append("<cols>{}</cols>".format("".join('<col min="{0}" max="{0}" width="{1}" customWidth="1"/>'.format(i + 1, w)
                                                        for i, w in sorted(self.widths.items()))))
        out.append("<sheetData>")
        for r in sorted(rows):
            ht = ' ht="{}" customHeight="1"'.format(self.heights[r]) if r in self.heights else ""
            out.append('<row r="{}"{}>{}</row>'.format(r, ht, "".join(self._cell(r, c, v, s) for c, v, s in sorted(rows[r], key=lambda x: x[0]))))
        out.append("</sheetData>")
        if self.autofilter:
            out.append('<autoFilter ref="{}"/>'.format(self.autofilter))
        if self.merges:
            out.append('<mergeCells count="{}">{}</mergeCells>'.format(len(self.merges), "".join('<mergeCell ref="{}"/>'.format(m) for m in self.merges)))
        out.append('<pageMargins left="0.4" right="0.4" top="0.75" bottom="0.6" header="0.3" footer="0.3"/>')
        out.append('<pageSetup paperSize="1" orientation="{}" fitToWidth="1" fitToHeight="0"/>'.format("landscape" if self.landscape else "portrait"))
        if self.header or self.footer:
            out.append('<headerFooter><oddHeader>{}</oddHeader><oddFooter>{}</oddFooter></headerFooter>'.format(_x(self.header), _x(self.footer)))
        out.append("</worksheet>")
        return "".join(out)
