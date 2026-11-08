"""Minimal .xlsx (Office Open XML) writer and reader, standard library only
(zipfile + xml.etree): enough for a plan an AI agent or a person edits in
Excel, LibreOffice or openpyxl (D-B-019).

Writer: several sheets, inline strings, numbers, dates (real Excel dates),
formulas with their cached value, bold header, column widths, frozen
header, autofilter, list validations (drop-downs) and conditional fills
(the Gantt bars). Reader: first-found sheet by name, shared or inline
strings, numbers, booleans, formula results; a cell's text is returned as
Excel shows it (dates as ISO text when the cell has a date format).
"""
import datetime as dt
import io
import re
import zipfile
from xml.etree import ElementTree as ET
from core.xmltext import escape  # 0.60.83 (D-O-089): also drops what XML forbids

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
EPOCH = dt.date(1899, 12, 30)
MAX_BYTES = 10 * 1024 * 1024
MAX_UNZIPPED = 60 * 1024 * 1024
# 0.60.87 (D-O-093): a cell « ZZZZZZZ1 » or a row « 999999999 » made a 775-byte file fill the memory (the row is padded
# up to that column, the sheet up to that row). Excel's own limits, and a budget of cells for the whole workbook.
MAX_COLS, MAX_ROW = 16_384, 1_048_576
MAX_CELLS = 2_000_000

# Style ids of the stylesheet below (cellXfs order).
TEXT, HEADER, DATE, WRAP, WEEK, PERCENT, TITLE = 0, 1, 2, 3, 4, 5, 6
INPUT, LOCKED = 7, 8  # yellow cell to fill in / grey read-only cell (Goldmine client package, D-B-037)
# Differential styles for conditional formatting (dxfs order).
DXF_BAR, DXF_DONE, DXF_MILESTONE, DXF_LATE = 0, 1, 2, 3


def col_name(index):
    """0 -> A, 25 -> Z, 26 -> AA."""
    name = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        name = chr(65 + rest) + name
    return name


def date_serial(value):
    return (value - EPOCH).days


class Sheet:
    def __init__(self, name):
        self.name = name[:31]
        self.rows = []          # list of lists of cells: (value, style) or {"f": formula, "v": cached, "s": style}
        self.widths = {}
        self.freeze = None      # "A2"
        self.autofilter = None  # "A1:L40"
        self.validations = []   # (sqref, [choices])
        self.conditional = []   # (sqref, [(formula, dxf_id)])
        self.landscape_fit = False  # print: landscape, one page wide

    def add(self, *cells):
        self.rows.append(list(cells))


def _cell_xml(ref, cell):
    if cell is None:
        return ""
    if isinstance(cell, dict):
        style = cell.get("s", TEXT)
        cached = cell.get("v")
        value = "" if cached is None else "<v>{}</v>".format(cached)
        return '<c r="{}" s="{}"><f>{}</f>{}</c>'.format(ref, style, escape(cell["f"]), value)
    value, style = cell if isinstance(cell, tuple) else (cell, TEXT)
    if value is None or value == "":
        return '<c r="{}" s="{}"/>'.format(ref, style) if style else ""
    if isinstance(value, dt.date):
        return '<c r="{}" s="{}"><v>{}</v></c>'.format(ref, style or DATE, date_serial(value))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return '<c r="{}" s="{}"><v>{}</v></c>'.format(ref, style, value)
    text = escape(str(value))
    space = ' xml:space="preserve"' if text != text.strip() or "\n" in text else ""
    return '<c r="{}" s="{}" t="inlineStr"><is><t{}>{}</t></is></c>'.format(ref, style, space, text)


def _sheet_xml(sheet):
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="{}" xmlns:r="{}">'.format(NS, REL_NS)]
    if sheet.landscape_fit:
        out.append('<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>')
    if sheet.freeze:
        col, row = re.match(r"([A-Z]+)(\d+)", sheet.freeze).groups()
        pane = ['<pane', ' ySplit="{}"'.format(int(row) - 1) if int(row) > 1 else "",
                ' xSplit="{}"'.format(_col_index(col)) if col != "A" else "",
                ' topLeftCell="{}" activePane="bottomRight" state="frozen"/>'.format(sheet.freeze)]
        out.append('<sheetViews><sheetView workbookViewId="0">{}</sheetView></sheetViews>'.format("".join(pane)))
    if sheet.widths:
        out.append("<cols>" + "".join('<col min="{0}" max="{0}" width="{1}" customWidth="1"/>'.format(i + 1, w)
                                      for i, w in sorted(sheet.widths.items())) + "</cols>")
    out.append("<sheetData>")
    for r, cells in enumerate(sheet.rows, start=1):
        xml = "".join(_cell_xml("{}{}".format(col_name(c), r), cell) for c, cell in enumerate(cells))
        out.append('<row r="{}">{}</row>'.format(r, xml))
    out.append("</sheetData>")
    if sheet.autofilter:
        out.append('<autoFilter ref="{}"/>'.format(sheet.autofilter))
    priority = 1
    for sqref, rules in sheet.conditional:
        out.append('<conditionalFormatting sqref="{}">'.format(sqref))
        for formula, dxf in rules:
            out.append('<cfRule type="expression" dxfId="{}" priority="{}" stopIfTrue="1"><formula>{}</formula>'
                       '</cfRule>'.format(dxf, priority, escape(formula)))
            priority += 1
        out.append("</conditionalFormatting>")
    if sheet.validations:
        out.append('<dataValidations count="{}">'.format(len(sheet.validations)))
        for sqref, choices in sheet.validations:
            if isinstance(choices, str) and choices.startswith("="):  # a range, e.g. ='Requirements'!$A$2:$A$40
                formula = escape(choices[1:])
            else:
                formula = '"{}"'.format(escape(",".join(c.replace(",", " ").replace('"', "'") for c in choices)[:250]))
            out.append('<dataValidation type="list" allowBlank="1" showErrorMessage="0" sqref="{}">'
                       '<formula1>{}</formula1></dataValidation>'.format(sqref, formula))
        out.append("</dataValidations>")
    if sheet.landscape_fit:
        out.append('<pageMargins left="0.3" right="0.3" top="0.4" bottom="0.4" header="0.2" footer="0.2"/>'
                   '<pageSetup orientation="landscape" fitToWidth="1" fitToHeight="0"/>')
    out.append("</worksheet>")
    return "".join(out)


def _col_index(name):
    n = 0
    for ch in name:
        n = n * 26 + ord(ch) - 64
    return n - 1


STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="{ns}">
<numFmts count="2"><numFmt numFmtId="164" formatCode="yyyy-mm-dd"/><numFmt numFmtId="165" formatCode="dd mmm"/></numFmts>
<fonts count="3"><font><sz val="10"/><name val="Segoe UI"/></font><font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Segoe UI"/></font><font><b/><sz val="14"/><name val="Segoe UI"/></font></fonts>
<fills count="5"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF0B1B33"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFF2B3"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFEEF1F4"/></patternFill></fill></fills>
<borders count="2"><border/><border><left style="thin"><color rgb="FFB8C0CC"/></left><right style="thin"><color rgb="FFB8C0CC"/></right><top style="thin"><color rgb="FFB8C0CC"/></top><bottom style="thin"><color rgb="FFB8C0CC"/></bottom></border></borders>
<cellStyleXfs count="1"><xf/></cellStyleXfs>
<cellXfs count="9">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" applyNumberFormat="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="165" fontId="1" fillId="2" borderId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyAlignment="1"><alignment textRotation="90" horizontal="center"/></xf>
<xf numFmtId="9" fontId="0" fillId="0" borderId="0" applyNumberFormat="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" applyFont="1"/>
<xf numFmtId="0" fontId="0" fillId="3" borderId="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="4" borderId="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
<dxfs count="4">
<dxf><fill><patternFill patternType="solid"><bgColor rgb="FF7446B0"/></patternFill></fill></dxf>
<dxf><fill><patternFill patternType="solid"><bgColor rgb="FF2E9E5B"/></patternFill></fill></dxf>
<dxf><fill><patternFill patternType="solid"><bgColor rgb="FFEE6A10"/></patternFill></fill></dxf>
<dxf><fill><patternFill patternType="solid"><bgColor rgb="FFD64545"/></patternFill></fill></dxf>
</dxfs>
</styleSheet>""".format(ns=NS)


def write(sheets):
    """Return the bytes of an .xlsx holding `sheets` (list of Sheet)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        overrides = "".join(
            '<Override PartName="/xl/worksheets/sheet{}.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'.format(i + 1) for i in range(len(sheets)))
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/'
                   'vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/styles.xml" ContentType="application/'
                   'vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' + overrides + "</Types>")
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{}">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                   'relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'.format(PKG_REL_NS))
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="{}" xmlns:r="{}">'
                   '<sheets>{}</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>'.format(
                       NS, REL_NS, "".join('<sheet name="{}" sheetId="{}" r:id="rId{}"/>'.format(
                           escape(s.name, {'"': "&quot;"}), i + 1, i + 1) for i, s in enumerate(sheets))))
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{}">{}'
                   '<Relationship Id="rId{}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                   'relationships/styles" Target="styles.xml"/></Relationships>'.format(
                       PKG_REL_NS, "".join(
                           '<Relationship Id="rId{0}" Type="http://schemas.openxmlformats.org/officeDocument/'
                           '2006/relationships/worksheet" Target="worksheets/sheet{0}.xml"/>'.format(i + 1)
                           for i in range(len(sheets))), len(sheets) + 1))
        z.writestr("xl/styles.xml", STYLES)
        for i, sheet in enumerate(sheets):
            z.writestr("xl/worksheets/sheet{}.xml".format(i + 1), _sheet_xml(sheet))
    return buf.getvalue()


# --------------------------------------------------------------------------
# Reader
# --------------------------------------------------------------------------
class XlsxError(ValueError):
    pass


def _q(tag):
    return "{%s}%s" % (NS, tag)


def _text(node):
    """Text of a <si> or <is>: plain <t> or rich-text runs <r><t>."""
    return "".join(t.text or "" for t in node.iter(_q("t")))


def _date_styles(z):
    """Indexes of cellXfs whose number format is a date."""
    try:
        root = ET.fromstring(z.read("xl/styles.xml"))
    except KeyError:
        return set()
    custom = {int(n.get("numFmtId")): n.get("formatCode", "") for n in root.iter(_q("numFmt"))}
    builtin_dates = set(range(14, 23)) | {45, 46, 47}
    out = set()
    xfs = root.find(_q("cellXfs"))
    for i, xf in enumerate(xfs if xfs is not None else []):
        fmt = int(xf.get("numFmtId", 0))
        code = custom.get(fmt, "").lower().replace('"', "")
        if fmt in builtin_dates or (fmt in custom and re.search(r"[dy]", re.sub(r"\[[^\]]*\]", "", code))):
            out.add(i)
    return out


def read(data, prefer=("Plan",)):
    """Return {sheet name: [[cell text, ...], ...]} for every sheet.
    Dates come back as 'YYYY-MM-DD', whole numbers without '.0'."""
    if len(data) > MAX_BYTES:
        raise XlsxError("Fichier de plus de 10 Mo.")
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise XlsxError("Ce fichier n'est pas un classeur Excel .xlsx valide.")
    with z:
        if sum(i.file_size for i in z.infolist()) > MAX_UNZIPPED:
            raise XlsxError("Classeur trop volumineux une fois décompressé.")
        try:
            workbook = ET.fromstring(z.read("xl/workbook.xml"))
            rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        except (KeyError, ET.ParseError):
            raise XlsxError("Classeur illisible (workbook.xml manquant).")
        targets = {r.get("Id"): r.get("Target") for r in rels}
        shared = []
        try:  # 0.60.89 (D-O-095): a malformed part is a 400 with its message, never a 500
            if "xl/sharedStrings.xml" in z.namelist():
                shared = [_text(si) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(_q("si"))]
            dates = _date_styles(z)
        except (ValueError, ET.ParseError):
            raise XlsxError("Classeur illisible (styles ou textes partagés mal formés).")
        result, budget = {}, [MAX_CELLS]
        for sheet in workbook.iter(_q("sheet")):
            target = targets.get(sheet.get("{%s}id" % REL_NS), "")
            path = target.lstrip("/") if target.startswith("/") else "xl/" + target
            try:
                root = ET.fromstring(z.read(path))
            except (KeyError, ET.ParseError):
                continue
            result[sheet.get("name")] = _rows(root, shared, dates, budget)
        return result


def _rows(root, shared, dates, budget=None):
    budget = budget if budget is not None else [MAX_CELLS]
    rows = []
    for row in root.iter(_q("row")):
        values = {}
        for c in row.iter(_q("c")):
            ref = re.match(r"([A-Z]+)", c.get("r", "A"))
            col = _col_index(ref.group(1)) if ref else len(values)
            if col >= MAX_COLS:
                raise XlsxError("Cellule {} hors des colonnes d'Excel (XFD au plus). Correctif : enregistrez le classeur "
                                "depuis Excel ou LibreOffice, puis réessayez.".format(c.get("r", "")[:20]))
            try:
                values[col] = _cell_text(c, shared, dates).strip()
            except ValueError:  # 0.60.89 (D-O-095): a style or a shared-string index that is not a number
                raise XlsxError("Classeur illisible (cellule {} mal formée). Correctif : enregistrez le classeur "
                                "depuis Excel ou LibreOffice, puis réessayez.".format(c.get("r", "")[:20]))
        try:
            index = int(row.get("r", len(rows) + 1)) - 1
        except ValueError:
            index = len(rows)
        if not 0 <= index < MAX_ROW:
            raise XlsxError("Ligne {} hors des lignes d'Excel (1 048 576 au plus). Correctif : enregistrez le classeur "
                            "depuis Excel ou LibreOffice, puis réessayez.".format(str(row.get("r"))[:20]))
        width = max(values) + 1 if values else 0
        budget[0] -= max(0, index - len(rows)) + width
        if budget[0] < 0:
            raise XlsxError("Classeur trop grand : plus de {} cellules. Correctif : gardez seulement les feuilles et les "
                            "lignes utiles.".format(MAX_CELLS))
        while len(rows) < index:
            rows.append([])
        rows.append([values.get(i, "") for i in range(width)] if values else [])
    return rows


def _cell_text(c, shared, dates):
    """Text of one <c>; ValueError when its style or its shared-string index is not a number."""
    kind, style = c.get("t", "n"), int(c.get("s", 0))
    v = c.find(_q("v"))
    raw = v.text if v is not None else None
    if kind == "s" and raw is not None:
        index = int(raw)
        return shared[index] if 0 <= index < len(shared) else ""  # 0.60.89: -1 was the last string of the table
    if kind == "inlineStr":
        node = c.find(_q("is"))
        return _text(node) if node is not None else ""
    if kind == "b":
        return "VRAI" if raw == "1" else "FAUX"
    if raw is None:
        return ""
    if kind in ("str", "e"):
        return raw
    try:
        number = float(raw)
    except ValueError:
        number = None
    if number is None or number != number or number in (float("inf"), float("-inf")):
        return raw  # « inf », « nan », a malformed number: kept as written, never a 500
    if style in dates and 1 <= number < 200000:
        return (EPOCH + dt.timedelta(days=int(number))).isoformat()
    return str(int(number)) if number == int(number) else repr(round(number, 6))
