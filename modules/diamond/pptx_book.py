"""A minimal PowerPoint package written with the standard library (0.60.50, D-O-059): 16:9 slides, one blank layout,
a theme with the platform's colours and Segoe UI. export_pptx.py fills the slides with native, editable shapes.
The parts are the smallest set PowerPoint, LibreOffice and Google Slides open without a repair prompt."""
import datetime as dt
import io
import zipfile
from xml.sax.saxutils import escape

SLIDE_W, SLIDE_H = 12192000, 6858000  # 13.333 in x 7.5 in, in EMU
P = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" ' \
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ' \
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_SLIDE = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"

THEME = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
         '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="DynamiteAgile"><a:themeElements>'
         '<a:clrScheme name="DynamiteAgile"><a:dk1><a:srgbClr val="1F2933"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
         '<a:dk2><a:srgbClr val="0B1B33"/></a:dk2><a:lt2><a:srgbClr val="F4F6F8"/></a:lt2><a:accent1><a:srgbClr val="E0602F"/></a:accent1>'
         '<a:accent2><a:srgbClr val="0E9A9A"/></a:accent2><a:accent3><a:srgbClr val="2F6FDE"/></a:accent3><a:accent4><a:srgbClr val="F2B632"/></a:accent4>'
         '<a:accent5><a:srgbClr val="3CBA6B"/></a:accent5><a:accent6><a:srgbClr val="D64545"/></a:accent6><a:hlink><a:srgbClr val="2F6FDE"/></a:hlink>'
         '<a:folHlink><a:srgbClr val="7A5AF8"/></a:folHlink></a:clrScheme>'
         '<a:fontScheme name="DynamiteAgile"><a:majorFont><a:latin typeface="Segoe UI"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
         '<a:minorFont><a:latin typeface="Segoe UI"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>'
         '<a:fmtScheme name="DynamiteAgile"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
         '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>'
         '<a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="19050"><a:solidFill>'
         '<a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="28575"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
         '</a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle>'
         '<a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/>'
         '</a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
         '</a:bgFillStyleLst></a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>')

_TREE = '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm>' \
        '<a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>{}</p:spTree></p:cSld>'
MAP = '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" ' \
      'accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'


def _rels(items):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{}">{}</Relationships>'
            .format(PKG, "".join('<Relationship Id="{}" Type="{}" Target="{}"/>'.format(
                i, t if t.startswith("http") else REL + "/" + t, target) for i, t, target in items)))


def package(slides, title, author="DynamiteAgile"):
    """slides: [inner XML of each slide's shape tree]. Returns the .pptx bytes."""
    n = len(slides)
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
          '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
          '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
          '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
          '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
          + "".join('<Override PartName="/ppt/slides/slide{}.xml" ContentType="{}"/>'.format(i + 1, CT_SLIDE) for i in range(n)) + '</Types>')
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>{}</dc:title>'
            '<dc:creator>{}</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">{}</dcterms:created>'
            '<dcterms:modified xsi:type="dcterms:W3CDTF">{}</dcterms:modified></cp:coreProperties>').format(escape(title), escape(author), now, now)
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
           'extended-properties"><Application>DynamiteAgile</Application><Slides>{}</Slides></Properties>').format(n)
    pres = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation {}><p:sldMasterIdLst><p:sldMasterId id="2147483648" '
            'r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>{}</p:sldIdLst><p:sldSz cx="{}" cy="{}"/><p:notesSz cx="6858000" cy="9144000"/>'
            '</p:presentation>').format(P, "".join('<p:sldId id="{}" r:id="rId{}"/>'.format(256 + i, i + 3) for i in range(n)), SLIDE_W, SLIDE_H)
    pres_rels = _rels([("rId1", "slideMaster", "slideMasters/slideMaster1.xml"), ("rId2", "theme", "theme/theme1.xml")]
                      + [("rId{}".format(i + 3), "slide", "slides/slide{}.xml".format(i + 1)) for i in range(n)])
    master = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster {}>{}{}<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" '
              'r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>'
              ).format(P, _TREE.format(""), MAP)
    layout = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout {} type="blank" preserve="1">{}'
              '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>').format(P, _TREE.format("").replace("<p:cSld>", '<p:cSld name="Blank">'))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", _rels([("rId1", "officeDocument", "ppt/presentation.xml"),
                                         ("rId2", PKG + "/metadata/core-properties", "docProps/core.xml"),
                                         ("rId3", "extended-properties", "docProps/app.xml")]))
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
        z.writestr("ppt/presentation.xml", pres)
        z.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        z.writestr("ppt/theme/theme1.xml", THEME)
        z.writestr("ppt/slideMasters/slideMaster1.xml", master)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", _rels([("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml"),
                                                                           ("rId2", "theme", "../theme/theme1.xml")]))
        z.writestr("ppt/slideLayouts/slideLayout1.xml", layout)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", _rels([("rId1", "slideMaster", "../slideMasters/slideMaster1.xml")]))
        for i, inner in enumerate(slides):
            z.writestr("ppt/slides/slide{}.xml".format(i + 1),
                       '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld {}>{}<p:clrMapOvr><a:masterClrMapping/>'
                       '</p:clrMapOvr></p:sld>'.format(P, _TREE.format(inner)))
            z.writestr("ppt/slides/_rels/slide{}.xml.rels".format(i + 1), _rels([("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml")]))
    return out.getvalue()
