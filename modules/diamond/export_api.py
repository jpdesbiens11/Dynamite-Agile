"""« Exporter » of Diamond (0.60.33, D-O-041): the three files of a Space's functional analysis.

GET …/export.xlsx   every table (Excel)     -- stamped with its revision and registered by the core (core/stamp.py)
GET …/export.docx   the report (Word)       -- idem
GET …/export.drawio every diagram (draw.io) -- journalled here (not an Office file: the core does not stamp it)
Readers of the Space may export (the same right as reading the screens).
"""
from core import audit, prefs
from core.files import RawFile

from . import export_data as X
from . import export_docx, export_drawio, export_xlsx
from . import functions as F

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DRAWIO = "application/vnd.jgraph.mxfile"


def _data(ctx):
    return X.gather(ctx.conn, F.access(ctx))


def api_xlsx(ctx):
    data = _data(ctx)
    return RawFile(export_xlsx.build(data), X.safe_name(data, "Tableaux", "xlsx"), XLSX)


def api_docx(ctx):
    data = _data(ctx)
    initials = prefs.get(ctx.conn, ctx.user["id"]).get("initials") or ""
    return RawFile(export_docx.build(data, ctx.user["display_name"], initials), X.safe_name(data, "Rapport", "docx"), DOCX)


def api_drawio(ctx):
    data = _data(ctx)
    name = X.safe_name(data, "Diagrammes", "drawio")
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_export_drawio", "project", data["project"]["id"], {"file": name}, ctx.ip)
    return RawFile(export_drawio.build(data).encode("utf-8"), name, DRAWIO)
