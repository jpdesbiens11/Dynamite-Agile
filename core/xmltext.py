"""0.60.83 (D-O-089): text written into an XML document (Word, PowerPoint, Excel, draw.io, the export stamp).

`xml.sax.saxutils.escape` escapes & < > but keeps the control characters U+0000-U+001F (except tab, line feed and
carriage return), U+FFFE and U+FFFF, which XML 1.0 forbids even escaped: one of them, pasted from a PDF or a terminal
into a function, a page or a test, made the whole file refused (« fichier endommagé »). Same signature, so a writer only
changes its import:  from core.xmltext import escape
"""
import re
from xml.sax.saxutils import escape as _escape

_FORBIDDEN = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿\ud800-\udfff]")


def clean(text):
    """The text without the characters XML 1.0 forbids."""
    return _FORBIDDEN.sub("", str(text))


def escape(data, entities=None):
    return _escape(clean(data), entities or {})
