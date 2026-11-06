"""0.60.62 (D-O-071): Mermaid diagrams kept as drawings in the PDF / Word exports.

The drawings are made by the platform's own engine, in the browser (mermaid_*.js). For an export, the browser:
  1. asks GET .../pages/<id>/export/mermaid[?children=1] for the Mermaid sources of the page (and its sub-pages);
  2. draws each one and turns it into a PNG (canvas, white background);
  3. sends POST .../pages/<id>/export.(pdf|docx) {children, diagrams: {source: base64 PNG}}.
The server puts the image in place of the code block and keeps the code under it, in small type, for the audit.
A diagram the browser could not draw (or an export by the old GET link) stays as code, as before.
"""
import base64
import binascii
import re

from core.errors import ApiError

from . import export

SCALE = 2  # the browser draws at twice the size, for a sharp print; the writers divide by it
MAX_DIAGRAMS = 60
MAX_PNG = 1_500_000
LOOKS = re.compile(r"^(flowchart|graph)\s+(TB|TD|BT|RL|LR)\b|^(sequenceDiagram|stateDiagram(-v2)?|classDiagram|erDiagram|gantt)\s*$")


def looks(text):
    """Same test as mermaid_parse.js looks(): the first meaningful line names a diagram type."""
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = 0
    if raw and raw[0].strip() == "---":  # front matter (title, config)
        i = 1
        while i < len(raw) and raw[i].strip() != "---":
            i += 1
        i += 1
    for line in raw[i:]:
        t = re.sub(r"%%.*$", "", line).strip()
        if t:
            return bool(LOOKS.search(t))
    return False


def is_mermaid(node):
    lang = str(node.get("lang") or "").lower()
    return lang == "mermaid" or (not lang and looks(node.get("text", "")))


def _sources(nodes, out):
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        if node.get("type") == "code" and is_mermaid(node):
            text = node.get("text", "")
            if text and text not in out:
                out.append(text)
        for key in ("content", "items"):
            child = node.get(key)
            if isinstance(child, list):
                _sources([c for c in child if isinstance(c, dict)] + [x for c in child if isinstance(c, list) for x in c], out)


def api_sources(ctx):
    """The Mermaid sources the browser has to draw before an export."""
    project_id, page = export.check(ctx)
    with_children = str(ctx.query.get("children", "0")) in ("1", "true", "oui")
    out = []
    for _p, body, _level in export._collect(ctx, project_id, page, with_children):
        _sources(body.get("content"), out)
    return {"sources": out[:MAX_DIAGRAMS]}


def _diagrams(raw):
    if raw is None:
        return {}
    if not isinstance(raw, dict) or len(raw) > MAX_DIAGRAMS:
        raise ApiError(400, "Diagrammes invalides : au plus {} diagrammes, sous forme {{code: PNG base64}}.".format(MAX_DIAGRAMS))
    out = {}
    for source, b64 in raw.items():
        if not isinstance(source, str) or not isinstance(b64, str):
            raise ApiError(400, "Diagramme invalide : le code et l'image doivent être du texte.")
        try:
            data = base64.b64decode(b64.split(",", 1)[-1], validate=True)
        except (binascii.Error, ValueError):
            raise ApiError(400, "Diagramme invalide : image PNG base64 attendue.")
        if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) > MAX_PNG:
            raise ApiError(400, "Diagramme invalide : image PNG de 1,5 Mo au plus attendue.")
        out[source] = data
    return out


def api_export(ctx):
    """POST export: the same document as the GET link, with the drawings of the Mermaid diagrams."""
    body = ctx.body or {}
    return export.api_export(ctx, with_children=bool(body.get("children")), diagrams=_diagrams(body.get("diagrams")))
