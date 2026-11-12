"""The figures of the Word report of Diamond (0.60.98, D-O-105).

A figure: a short lead-in sentence, the EMF picture inline and centred, fitted to the text width of the template (never
enlarged), then its caption « Figure n — … » in the template's caption style, numbered by a SEQ Figure field (Word
renumbers it with F9, like the table of contents; the number is already written for LibreOffice and the first opening).
The pictures go into the package of the template: word/media/diamond_figN.emf, a relationship each, the content type of
.emf. The core then stamps the file as any export (RawFile).
"""
import io
import re
import zipfile

from core.xmltext import escape
from modules.testing import word_doc as WD

EMU_PER_PX = 9525                    # 96 dpi
MAX_W = 9400 * 635                   # the text width of the template (dxa -> EMU)
MAX_H = int(6.0 * 914400)            # a portrait page less a heading, a lead-in and the caption
CT_EMF = '<Default Extension="emf" ContentType="image/x-emf"/>'
REL_IMAGE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
DOCPR = 900                          # ids of the pictures, clear of the template's own


def _q(text):
    return escape(str(text), {'"': "&quot;"})


def scale(w_px, h_px, max_w=MAX_W, max_h=MAX_H):
    """The factor that fits a picture of w x h pixels in the box: 1 (its own size) or less."""
    return min(1.0, max_w / float(w_px * EMU_PER_PX), max_h / float(h_px * EMU_PER_PX))


def fit(w_px, h_px, max_w=MAX_W, max_h=MAX_H, k=None):
    """Size in EMU of a picture: at k (a common scale for a series of figures, never beyond the box) or fitted."""
    k = min(k or 1.0, scale(w_px, h_px, max_w, max_h))
    return int(w_px * EMU_PER_PX * k), int(h_px * EMU_PER_PX * k)


def caption(n, text):
    field = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> SEQ Figure \\* ARABIC </w:instrText>'
             '</w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:rPr><w:noProof/></w:rPr><w:t>{}</w:t></w:r>'
             '<w:r><w:fldChar w:fldCharType="end"/></w:r>').format(n)
    return ('<w:p><w:pPr><w:pStyle w:val="Lgende"/><w:jc w:val="center"/></w:pPr><w:r><w:t xml:space="preserve">Figure </w:t></w:r>{}'
            '<w:r><w:t xml:space="preserve"> — {}</w:t></w:r></w:p>').format(field, WD._x(text))


class Figures:
    def __init__(self):
        self.media = []  # (file name, bytes)

    @property
    def count(self):
        return len(self.media)

    def picture(self, data, w_px, h_px, alt, max_h=MAX_H, k=None):
        """The paragraph of one picture (kept with its caption)."""
        n = len(self.media) + 1
        name = "diamond_fig{}.emf".format(n)
        self.media.append((name, data))
        cx, cy = fit(w_px, h_px, max_h=max_h, k=k)
        return ('<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="60"/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
                '<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
                '<wp:docPr id="{id}" name="Figure {n}" descr="{alt}"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="{a}" '
                'noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="{a}"><a:graphicData uri="{p}"><pic:pic xmlns:pic="{p}">'
                '<pic:nvPicPr><pic:cNvPr id="{id}" name="{name}" descr="{alt}"/><pic:cNvPicPr><a:picLocks noChangeAspect="1"/></pic:cNvPicPr>'
                '</pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdDaFig{n}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
                '<pic:spPr bwMode="auto"><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect">'
                '<a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>').format(
            cx=cx, cy=cy, id=DOCPR + n, n=n, alt=_q(alt[:200]), name=name, a=NS_A, p=NS_PIC)

    def figure(self, picture, title, lead=None, after=(), max_h=MAX_H, k=None):
        """lead: the sentence before (bold prefix allowed as a (bold, text) pair); after: paragraphs under the caption;
        k: a common scale (the branches of a tree read at the same size)."""
        data, w, h = picture
        out = []
        if lead:
            runs = [WD.run(lead[0], bold=True), WD.run(" " + lead[1])] if isinstance(lead, tuple) else [WD.run(lead)]
            out.append(WD.para(runs, keep_next=True, space_after=80))
        out.append(self.picture(data, w, h, title, max_h, k))
        out.append(caption(len(self.media), title))
        out += list(after)
        return "".join(out)

    def package(self, raw):
        """The .docx bytes with the pictures added (media, relationships, content type)."""
        if not self.media:
            return raw
        buf = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "[Content_Types].xml" and b'Extension="emf"' not in data:
                    data = data.replace(b"<Default ", CT_EMF.encode() + b"<Default ", 1)
                elif item.filename == "word/_rels/document.xml.rels":
                    rels = "".join('<Relationship Id="rIdDaFig{}" Type="{}" Target="media/{}"/>'.format(i + 1, REL_IMAGE, name)
                                   for i, (name, _d) in enumerate(self.media))
                    data = re.sub(rb"</Relationships>\s*$", rels.encode() + b"</Relationships>", data)
                zout.writestr(item, data)
            for name, data in self.media:
                zout.writestr("word/media/" + name, data)
        return buf.getvalue()
