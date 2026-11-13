"""Export of Diamond (0.60.33, D-O-041): everything a Space's functional analysis holds, read once, for the three files.

  export_xlsx.py   every table           -> Excel   (functions, structure, parts x functions, risks, DFMEA)
  export_drawio.py every diagram         -> draw.io (functional tree, functional structure x 2 views, risk map)
  export_docx.py   the report            -> Word    (for a teacher, a jury, an investor; Save as PDF in Word), with the
                   Storyline and the diagrams as figures since 0.60.98 (report_figures.py, figures.py, story_figure.py)
Each file carries the mark « DynamiteAgile · Co-Intelligence WorkFlow™ »: in the page header of the workbook, the
footer of the report, the title block of each diagram. The Golden Nuggets are the tool's reference text, not the
Space's content: they stay in the tool.
"""
import datetime as dt
import re

from core import APP_VERSION

from . import classes as CL
from . import dfmea as DF
from . import dfmea_complete as DC
from . import functions as F
from . import parts as P
from . import risks as R
from . import story as ST
from . import structure as S

MARK = "DynamiteAgile · Co-Intelligence WorkFlow™"
BRAND, WORKFLOW = "DynamiteAgile", "Co-Intelligence WorkFlow™"
ORANGE, TEAL, NAVY, INK, MUTED = "E0602F", "0E9A9A", "0B1B33", "1F2933", "5B6573"
LEVEL_FILL = {1: "FFE7A3", 2: "FBD3BF", 3: "CDEEF2", 4: "E6E8EB"}  # the colours of the tree screen (yellow, orange, cyan)
AP_STYLE = {"H": ("FDE2E1", "9B1C1C"), "M": ("FFF1C7", "7A5B00"), "L": ("E2F4E7", "1E6B3A")}
RISK_STYLE = {"critique": ("D64545", "FFFFFF"), "eleve": ("F59E5B", "1F2933"), "moyen": ("FFE08A", "1F2933"),
              "faible": ("CDEFD8", "1F2933"), "none": ("F2F4F7", "5B6573")}


def gather(conn, pid):
    project = dict(conn.execute("SELECT id, key, name, description FROM projects WHERE id = ?", (pid,)).fetchone())
    tree, kids = DC._tree(conn, pid)
    by_id = {f["id"]: f for f in tree}
    view_nodes, _items = S.nodes(conn, pid)
    structure = S.payload(conn, pid)
    parts = structure["parts"]
    risks = R.rows(conn, pid)
    dfmea = DF._rows(conn, pid)
    now = dt.datetime.now()
    data = {"project": project, "version": APP_VERSION, "date": now.strftime("%Y-%m-%d"), "stamp": now.strftime("%Y-%m-%d %H:%M"),
            "tree": tree, "kids": kids, "by_id": by_id, "views": view_nodes, "structure": structure, "parts": parts,
            "part_stats": structure["part_stats"], "part_checks": structure["part_checks"], "risks": risks, "dfmea": dfmea,
            "story": ST.rows(conn, pid),  # the scenes of the Storyline: figures of the Word report (0.60.98)
            "classes": CL.info(conn, pid, dfmea),  # 0.61.0 (D-O-107): rules, the customer's symbols, the counts
            "checks": {"tree": F.checks(F.rows(conn, pid)), "structure": structure["checks"], "risks": R.checks(risks),
                       "dfmea": DF.checks(conn, pid, dfmea)},
            "labels": {"types": F.TYPES, "kano": F.KANO, "importance": F.IMPORTANCE, "levels": F.LEVELS, "kinds": S.KINDS,
                       "sides": S.SIDES, "views": S.VIEWS, "part_kinds": P.KINDS, "categories": R.CATEGORIES,
                       "phases": R.PHASES, "responses": R.RESPONSES, "statuses": R.STATUSES}}
    data["summary"] = summary(data)
    return data


def code(f):
    return "F{}".format(f["number"])


def label_of(f, data):
    return data["labels"]["levels"].get(f["level"], "Hors arbre") if f.get("in_tree", True) else "Hors arbre"


def summary(data):
    tree = data["tree"]
    in_tree = [f for f in tree if f["in_tree"]]
    rows = data["dfmea"]
    return {"functions": len(in_tree), "outside": len(tree) - len(in_tree),
            "by_level": {lv: sum(1 for f in in_tree if f["level"] == lv) for lv in (1, 2, 3, 4)},
            "critical": sum(1 for f in tree if f["critical"]),
            "inputs": sum(1 for p in data["structure"]["ports"] if p["side"] == "in"),
            "outputs": sum(1 for p in data["structure"]["ports"] if p["side"] == "out"),
            "flows": len(data["structure"]["flows"]), "parts": len(data["parts"]), "scenes": len(data["story"]),
            "risks": len(data["risks"]), "risks_high": sum(1 for r in data["risks"] if r["level"]["key"] in ("critique", "eleve")),
            "dfmea": len(rows), "ap": {k: sum(1 for r in rows if r["ap"] == k) for k in ("H", "M", "L")},
            "dfmea_unrated": sum(1 for r in rows if not r["ap"]), "dfmea_tested": sum(1 for r in rows if r["test_id"]),
            "classes": {k: sum(1 for r in rows if r["class_status"] == "confirmed" and r["class_code"] == k) for k in CL.CLASSES},
            "class_proposed": sum(1 for r in rows if r["class_status"] == "proposed"),
            "class_refused": sum(1 for r in rows if r["class_status"] == "refused")}


def safe_name(data, kind, ext):
    key = re.sub(r"[^A-Za-z0-9_-]+", "_", data["project"]["key"])
    return "Diamond_{}_{}_{}.{}".format(key, kind, data["date"], ext)


def part_codes(data, fid):
    return ", ".join("P-{}".format(p["number"]) for p in data["parts"] if fid in p["functions"])
