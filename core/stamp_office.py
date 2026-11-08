"""Revision stamp inside Office files (core lot v0.33, D-B-129), standard library only (zipfile + text edits of the
Open XML parts; nothing else in the file is touched):

- .docx  the lines in every page header (word/header*.xml); a document without header gets them as its first
         paragraph instead;
- .xlsx  a last sheet « Révision » with the lines (the importers of the platform read their sheets by name, so a
         workbook sent back still imports);
- .pptx  the lines in the notes of the document properties only (the platform makes no slides today);
- all    custom document properties « DA Revision », « DA Revision date », « DA Extracted by », « DA Extracted
         at », « DA Extract no » (File → Info → Properties in Office) -- read by a script without opening the file.
"""
import io
import re
import zipfile
from .xmltext import escape  # 0.60.83 (D-O-089): also drops what XML forbids

CT_CUSTOM = "application/vnd.openxmlformats-officedocument.custom-properties+xml"
CT_SHEET = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
REL_CUSTOM = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"
REL_SHEET = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
FMTID = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"
SHEET_NAME = "Révision"


def _x(text):
    return escape(str(text), {'"': "&quot;"})


def _word_paragraphs(lines):
    runs = []
    for i, line in enumerate(lines):
        if i:
            runs.append("<w:r><w:br/></w:r>")
        runs.append('<w:r><w:rPr><w:sz w:val="14"/><w:szCs w:val="14"/><w:color w:val="555555"/></w:rPr>'
                    '<w:t xml:space="preserve">{}</w:t></w:r>'.format(_x(line)))
    return '<w:p><w:pPr><w:jc w:val="right"/></w:pPr>{}</w:p>'.format("".join(runs))


def _docx(parts, lines):
    para = _word_paragraphs(lines)
    headers = [n for n in parts if re.fullmatch(r"word/header\d*\.xml", n)]
    for name in headers:
        text = parts[name].decode("utf-8")
        parts[name] = text.replace("</w:hdr>", para + "</w:hdr>", 1).encode("utf-8")
    if not headers and "word/document.xml" in parts:
        text = parts["word/document.xml"].decode("utf-8")
        m = re.search(r"<w:body(\s[^>]*)?>", text)
        if m:
            parts["word/document.xml"] = (text[:m.end()] + para + text[m.end():]).encode("utf-8")


def _cell(ref, text):
    return '<c r="{}" t="inlineStr"><is><t xml:space="preserve">{}</t></is></c>'.format(ref, _x(text))


def _xlsx(parts, rows):
    if "xl/workbook.xml" not in parts or "xl/_rels/workbook.xml.rels" not in parts:
        return
    body = "".join('<row r="{0}">{1}{2}</row>'.format(i, _cell("A%d" % i, k), _cell("B%d" % i, v))
                   for i, (k, v) in enumerate(rows, start=1))
    parts["xl/worksheets/sheetDArev.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<cols><col min="1" max="1" width="28" customWidth="1"/><col min="2" max="2" width="90" customWidth="1"/></cols>'
        '<sheetData>{}</sheetData></worksheet>'.format(body)).encode("utf-8")
    rels = parts["xl/_rels/workbook.xml.rels"].decode("utf-8")
    parts["xl/_rels/workbook.xml.rels"] = rels.replace("</Relationships>", '<Relationship Id="rIdDArev" Type="{}" '
                                                       'Target="worksheets/sheetDArev.xml"/></Relationships>'.format(REL_SHEET), 1).encode("utf-8")
    wb = parts["xl/workbook.xml"].decode("utf-8")
    ids = [int(x) for x in re.findall(r'sheetId="(\d+)"', wb)] or [0]
    rel_prefix = "r"
    m = re.search(r'xmlns:(\w+)="http://schemas.openxmlformats.org/officeDocument/2006/relationships"', wb)
    if m:
        rel_prefix = m.group(1)
    else:
        wb = re.sub(r"<workbook(\s|>)", '<workbook xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/'
                                        'relationships"\\1', wb, count=1)
    sheet = '<sheet name="{}" sheetId="{}" {}:id="rIdDArev"/>'.format(SHEET_NAME, max(ids) + 1, rel_prefix)
    parts["xl/workbook.xml"] = wb.replace("</sheets>", sheet + "</sheets>", 1).encode("utf-8")
    _content_type(parts, "/xl/worksheets/sheetDArev.xml", CT_SHEET)


def _content_type(parts, part, ctype):
    ct = parts["[Content_Types].xml"].decode("utf-8")
    if 'PartName="{}"'.format(part) not in ct:
        ct = ct.replace("</Types>", '<Override PartName="{}" ContentType="{}"/></Types>'.format(part, ctype), 1)
    parts["[Content_Types].xml"] = ct.encode("utf-8")


def _custom(parts, props):
    items = "".join('<property fmtid="{}" pid="{}" name="{}"><vt:lpwstr>{}</vt:lpwstr></property>'
                    .format(FMTID, 100 + i, _x(k), _x(v)) for i, (k, v) in enumerate(props))
    if "docProps/custom.xml" in parts:
        text = parts["docProps/custom.xml"].decode("utf-8")
        parts["docProps/custom.xml"] = text.replace("</Properties>", items + "</Properties>", 1).encode("utf-8")
        return
    parts["docProps/custom.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">{}</Properties>'
        .format(items)).encode("utf-8")
    _content_type(parts, "/docProps/custom.xml", CT_CUSTOM)
    rels = parts.get("_rels/.rels", b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships '
                     b'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>').decode("utf-8")
    parts["_rels/.rels"] = rels.replace("</Relationships>", '<Relationship Id="rIdDAcustom" Type="{}" '
                                        'Target="docProps/custom.xml"/></Relationships>'.format(REL_CUSTOM), 1).encode("utf-8")


def stamp(data, ext, lines, rows, props):
    """Bytes of the stamped Office file; the original bytes if it is not a readable Open XML package."""
    try:
        src = zipfile.ZipFile(io.BytesIO(data))
        order = [i.filename for i in src.infolist()]
        parts = {n: src.read(n) for n in order}
    except (zipfile.BadZipFile, KeyError, OSError):
        return data
    if "[Content_Types].xml" not in parts:
        return data
    if ext == "docx":
        _docx(parts, lines)
    elif ext == "xlsx":
        _xlsx(parts, rows)
    _custom(parts, props)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in order + [n for n in parts if n not in order]:
            z.writestr(name, parts[name])
    return out.getvalue()
