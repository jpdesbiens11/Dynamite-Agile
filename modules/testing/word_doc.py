"""Word documents from the tool's data (D-B-083), standard library only.

The template (templates/document.docx; logo and footer: tools/brand_doc_template.py) carries the
cover page, header / footer, styles and the table of content; this module fills its placeholders and writes the
body with the template's own styles: numbered headings (Titre1..3), gray-header tables, bullets, and the
Codebeamer item styles (CB_item_name_requirement in blue with a rule above, CB_Attributes in ochre, CB_description,
CB_Rationale in gray italics, CB_upstream in green) -- the look of a requirement document exported from Codebeamer.
"""
import datetime as dt
import io
import re
import zipfile
from pathlib import Path
from core.xmltext import escape  # 0.60.83 (D-O-089): also drops what XML forbids

from core.errors import ApiError

TEMPLATE = Path(__file__).parent / "templates" / "document.docx"
BULLET_NUM = "190"  # bullet list of the template (numbering.xml)
_BAD = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")

LIMITS = {"title": 160, "docno": 40, "rev": 10, "subject": 80, "doctype": 60, "prepared": 80}


def _x(text):
    return escape(_BAD.sub("", str(text if text is not None else "")))


def run(text, bold=False, italic=False, color=None, size=None):
    props = ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "") + \
            ('<w:color w:val="{}"/>'.format(color) if color else "") + \
            ('<w:sz w:val="{0}"/><w:szCs w:val="{0}"/>'.format(size) if size else "")
    parts = str(text if text is not None else "").split("\n")
    body = '<w:br/>'.join('<w:t xml:space="preserve">{}</w:t>'.format(_x(p)) for p in parts)
    return "<w:r>{}{}</w:r>".format("<w:rPr>{}</w:rPr>".format(props) if props else "", body)


def para(content, style=None, keep_next=False, align=None, bullet=False, space_after=None):
    """content: a string or a list of run() strings."""
    runs = content if isinstance(content, list) else [run(content)]
    ppr = ""
    if style:
        ppr += '<w:pStyle w:val="{}"/>'.format(style)
    if keep_next:
        ppr += "<w:keepNext/>"
    if bullet:
        ppr += '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{}"/></w:numPr>'.format(BULLET_NUM)
    if space_after is not None:
        ppr += '<w:spacing w:after="{}"/>'.format(space_after)
    if align:
        ppr += '<w:jc w:val="{}"/>'.format(align)
    return "<w:p>{}{}</w:p>".format("<w:pPr>{}</w:pPr>".format(ppr) if ppr else "", "".join(runs))


def heading(level, text):
    return para([run(text)], style="Titre{}".format(level))


def bullets(items, style="Paragraphedeliste"):
    return "".join(para(i if isinstance(i, list) else [run(i)], style=style, bullet=True) for i in items)


def _cell(content, width, fill=None, bold=False, borders=True):
    paras = content if isinstance(content, list) else [content]
    xml = []
    for p in paras:
        if isinstance(p, str) and p.startswith("<w:p"):
            xml.append(p)
        else:
            xml.append(para([run(p, bold=bold)], space_after=0, align="left"))
    tcpr = '<w:tcW w:w="{}" w:type="dxa"/>'.format(width)
    if not borders:
        tcpr += '<w:tcBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/></w:tcBorders>'
    if fill:
        tcpr += '<w:shd w:val="clear" w:color="auto" w:fill="{}"/>'.format(fill)
    return "<w:tc><w:tcPr>{}</w:tcPr>{}</w:tc>".format(tcpr, "".join(xml) or "<w:p/>")


def table(header, rows, widths, fill="D9D9D9"):
    """Grid table, gray bold header row repeated on each page."""
    grid = "".join('<w:gridCol w:w="{}"/>'.format(w) for w in widths)
    out = ['<w:tbl><w:tblPr><w:tblStyle w:val="Grilledutableau"/><w:tblW w:w="{}" w:type="dxa"/>'
           '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" '
           'w:noVBand="1"/></w:tblPr><w:tblGrid>{}</w:tblGrid>'.format(sum(widths), grid)]
    out.append("<w:tr><w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>{}</w:tr>".format(
        "".join(_cell(h, w, fill, bold=True) for h, w in zip(header, widths))))
    for r in rows:
        out.append("<w:tr><w:trPr><w:cantSplit/></w:trPr>{}</w:tr>".format("".join(_cell(c, w) for c, w in zip(r, widths))))
    out.append("</w:tbl>")
    return "".join(out) + para("", space_after=60)


def cb_item(item_id, kind, title, attributes, description, rationale=(), upstream=()):
    """One Codebeamer-style item: « REQ-001 - Requirement - Title » in blue with a rule above,
    three columns of attributes (ochre), the description, the rationale (gray italics), the trace links (green)."""
    out = [para([run("{} - {} - {}".format(item_id, kind, title))], style="CBitemnamerequirement")]
    widths = [2600, 2900, 3900]
    cols = [(attributes + [[], [], []])[i] for i in range(3)]
    cells = "".join(_cell([para([run(line)], style="CBAttributes", align="left") for line in col]
                          or [para("", style="CBAttributes")],
                          w, borders=False) for col, w in zip(cols, widths))
    out.append('<w:tbl><w:tblPr><w:tblW w:w="{}" w:type="dxa"/><w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/>'
               '<w:bottom w:val="nil"/><w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'
               '<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>'
               '<w:tblGrid>{}</w:tblGrid><w:tr><w:trPr><w:cantSplit/></w:trPr>{}</w:tr></w:tbl>'.format(
                   sum(widths), "".join('<w:gridCol w:w="{}"/>'.format(w) for w in widths), cells))
    out.append(para("", style="CBdescription"))
    for block in description:
        out.append(block if block.startswith("<w:") else para([run(block)], style="CBdescription"))
    if rationale:
        out.append(para("", style="CBdescription"))
        out += [para([run(r)], style="CBRationale") for r in rationale if r]
    if upstream:
        out.append(para("", style="CBdescription"))
        out += [para([run(u)], style="CBupstream") for u in upstream if u]
    out.append(para("", style="CBdescription"))
    return "".join(out)


def labelled(label, text):
    """« Acceptance criteria: … » -- bold label, then the value, as a description paragraph."""
    return para([run(label + " : ", bold=True), run(text)], style="CBdescription")


def revision_table(rev, reason, name, date):
    widths = [1100, 4300, 1500, 900, 1300]
    return table(["Rev/Baseline", "Reason for revision", "Affected sections", "Name", "Date"],
                 [[rev, reason, "All", name, date]], widths, fill="EFEFEF")


def meta_from_query(query, defaults):
    meta = {}
    for key, limit in LIMITS.items():
        value = str(query.get(key) or defaults.get(key, "")).strip()
        if len(value) > limit:
            raise ApiError(400, "Champ « {} » du document : {} caractères au maximum.".format(key, limit))
        meta[key] = value
    meta["lang"] = "en" if query.get("lang", defaults.get("lang", "en")) == "en" else "fr"
    return meta


def build(meta, body, revision_reason, initials):
    """The .docx bytes: template + cover / header fields + log of revision + body."""
    if not TEMPLATE.exists():
        raise ApiError(500, "Gabarit Word introuvable (modules/testing/templates/document.docx). Correctif : "
                            "remettez le fichier livré avec l'outil (git checkout), puis tools/brand_doc_template.py.")
    today = dt.date.today().strftime("%d.%m.%Y")
    values = {"{{TITLE}}": _x(meta["title"]), "{{SUBJECT}}": _x(meta["subject"]), "{{PREPARED}}": _x(meta["prepared"]),
              "{{PDATE}}": today, "{{HTITLE}}": _x(meta["title"]), "{{DOCNO}}": _x(meta["docno"]),
              "{{REV}}": _x(meta["rev"]), "{{DOCTYPE}}": _x(meta["doctype"].upper())}
    buf = io.BytesIO()
    with zipfile.ZipFile(TEMPLATE) as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in ("word/document.xml", "word/header1.xml"):
                text = data.decode("utf-8")
                for key, value in values.items():
                    text = text.replace(key, value)
                if item.filename == "word/document.xml":
                    text = text.replace("{{REVTABLE}}", revision_table(meta["rev"], revision_reason, initials, today))
                    text = text.replace("{{BODY}}", body)
                data = text.encode("utf-8")
            elif item.filename == "docProps/core.xml":
                text = data.decode("utf-8")
                for tag, value in (("dc:title", meta["title"]), ("dc:subject", meta["subject"]), ("cp:category", meta["doctype"]),
                                   ("cp:keywords", meta["rev"]), ("dc:creator", meta["prepared"])):
                    text = text.replace("<{0}></{0}>".format(tag), "<{0}>{1}</{0}>".format(tag, _x(value)))
                stamp = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                text = re.sub(r"(<dcterms:(?:created|modified)[^>]*>)[^<]*(</dcterms:)", r"\g<1>{}\g<2>".format(stamp), text)
                data = text.encode("utf-8")
            zout.writestr(item, data)
    return buf.getvalue()


def filename(meta, fallback):
    base = meta["docno"] or fallback
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", "{}_{}_rev{}".format(base, meta["title"][:60], meta["rev"] or "A")).strip("_")
    return safe + ".docx"
