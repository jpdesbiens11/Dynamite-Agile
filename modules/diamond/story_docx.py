"""« Export .docx » of the Storyline (0.60.113, D-O-126): the scenes alone, as a comic -- one scene per page, its title on
top, the scene in the middle, what happens and the notes at the bottom (report_figures.comic, the same pages as the
Storyline section of the Diamond report). The platform's template (cover page, header with the document number and
revision, table of contents) and the DynamiteAgile mark in its footer, like every report; the core stamps and registers
the file (RawFile). Readers of the Space may export.
"""
import datetime as dt

from core import prefs
from core.files import RawFile
from modules.testing import word_doc as WD

from . import export_data as X
from . import functions as F
from . import report_figures as RF
from . import story
from .docx_figures import Figures
from .export_docx import _mark

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def build(conn, pid, prepared, initials):
    project = dict(conn.execute("SELECT key, name, description FROM projects WHERE id = ?", (pid,)).fetchone())
    scenes = story.rows(conn, pid)
    figs = Figures()
    intro = [WD.heading(1, "Storyline"),
             WD.para([WD.run("L'usage de {} raconté scène par scène, avant l'arbre fonctionnel : qui, où, avec quoi, ce qui se "
                             "passe et ce qu'on ressent. Une scène par page.".format(project["name"]))], space_after=120)]
    if project["description"]:
        intro.append(WD.para([WD.run(" ".join(project["description"].split()), italic=True, color=X.MUTED)], space_after=120))
    body = "".join(intro) + (RF.comic(scenes, figs) if scenes else
                             WD.para([WD.run("Aucune scène : la Storyline de ce Space est vide.", italic=True, color=X.MUTED)]))
    meta = {"title": "Storyline", "subject": "{} ({})".format(project["name"], project["key"])[:80], "prepared": prepared[:80],
            "docno": "STY-{}".format(project["key"])[:40], "rev": "A", "doctype": "Storyline", "lang": "fr"}
    return figs.package(_mark(WD.build(meta, body, "Export de la Storyline", initials))), project


def api_docx(ctx):
    pid = F.access(ctx)
    initials = prefs.get(ctx.conn, ctx.user["id"]).get("initials") or ""
    data, project = build(ctx.conn, pid, ctx.user["display_name"], initials)
    name = X.safe_name({"project": project, "date": dt.date.today().strftime("%Y-%m-%d")}, "Storyline", "docx")
    return RawFile(data, name, DOCX)
