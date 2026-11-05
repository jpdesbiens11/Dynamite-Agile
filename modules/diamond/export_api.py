"""« Exporter » of Diamond (0.60.33, D-O-041): the three files of a Space's functional analysis.

GET …/export.xlsx   every table (Excel)     -- stamped with its revision and registered by the core (core/stamp.py)
GET …/export.docx   the report (Word)       -- idem
GET …/export.drawio every diagram (draw.io) -- journalled here (not an Office file: the core does not stamp it)
GET …/export.pptx   every diagram (PowerPoint, native shapes; 0.60.50, D-O-059) -- stamped by the core
?only=tree or ?only=structure: the file of one screen (its diagram, its table), from the button « Exporter » on it.
Readers of the Space may export (the same right as reading the screens).
"""
from core import audit, prefs
from core.files import RawFile

from . import export_data as X
from . import export_docx, export_drawio, export_pptx, export_xlsx
from . import functions as F

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DRAWIO = "application/vnd.jgraph.mxfile"
PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
KIND = {None: ("Tableaux", "Diagrammes"), "tree": ("Arbre", "Arbre"), "structure": ("Structure", "Structure")}


def _data(ctx):
    return X.gather(ctx.conn, F.access(ctx))


def _only(ctx):
    only = ctx.query.get("only") or None
    return only if only in ("tree", "structure") else None


def api_xlsx(ctx):
    data, only = _data(ctx), _only(ctx)
    return RawFile(export_xlsx.build(data, only), X.safe_name(data, KIND[only][0], "xlsx"), XLSX)


def api_docx(ctx):
    data = _data(ctx)
    initials = prefs.get(ctx.conn, ctx.user["id"]).get("initials") or ""
    return RawFile(export_docx.build(data, ctx.user["display_name"], initials), X.safe_name(data, "Rapport", "docx"), DOCX)


def api_drawio(ctx):
    data, only = _data(ctx), _only(ctx)
    name = X.safe_name(data, KIND[only][1], "drawio")
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_export_drawio", "project", data["project"]["id"], {"file": name}, ctx.ip)
    return RawFile(export_drawio.build(data, only).encode("utf-8"), name, DRAWIO)


def api_pptx(ctx):
    data, only = _data(ctx), _only(ctx)
    return RawFile(export_pptx.build(data, only), X.safe_name(data, KIND[only][1], "pptx"), PPTX)
