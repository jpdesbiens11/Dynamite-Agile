"""« PDF » of every Diamond page (0.60.123, D-O-136), next to « ↔ IA » at the top right of the page.

POST /api/diamond/p/<pid>/pdf  {title, view, sections?: [keys], blocks?: [...]}
  - sections: the artefacts of the page, as the round trip knows them (rt.py): one numbered chapter per section, its guide,
    then one table -- the code and every field that has a value in at least one row. A table of more than COLS columns is
    cut into several tables of COLS columns that all start with the code (« suite »); a table of more than
    pdf_doc.WIDE_COLUMNS columns puts the whole document in Tabloid landscape.
  - blocks: a document the page builds itself (Golden Nuggets: static content), checked here -- h / p / note / ul / ol / table / card.
  - neither (Idéation, Kepner-Tregoe, Prioriser, Exporter: no artefact of their own): every section of Diamond.
The format of the platform's Word documents (pdf_doc.py): cover page, header, footer. Readers of the Space may export, as
for the other files of Diamond; the core stamps the file with its revision and registers it (RawFile, core/stamp.py).
0.60.124 (D-O-137): prepare() and fill() are shared with « Word » (docx_pages.py), which renders the same body as a .docx.
"""
import json
import re

from core import audit, permissions, prefs, validate
from core.errors import ApiError
from core.files import RawFile

from . import pdf_doc as P
from . import rt

COLS = 11            # columns of one table (the code included) before it is cut
MAX_BLOCKS = 3000
MAX_TEXT = 6000
KINDS = ("h", "p", "note", "ul", "ol", "table", "card")  # ol: 0.60.124


def label(key):
    """A JSON key of the round trip as a column title: failure_mode -> Failure mode."""
    text = re.sub(r"_+", " ", str(key)).strip()
    return text[:1].upper() + text[1:]


def cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Oui" if value else "Non"
    if isinstance(value, float):
        return ("{:.2f}".format(value)).rstrip("0").rstrip(".")
    if isinstance(value, list):
        return ", ".join(cell(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def section(doc, sec, items):
    doc.h(1, sec.label)
    if sec.guide:
        doc.note(sec.guide)
    keys = ["code"] + [f.key for f in sec.fields]
    keys = [k for k in keys if k == "code" or any(cell(it.get(k)) for it in items)]
    if not items:
        doc.p("Aucun élément pour l'instant.", muted=True, italic=True)
        return
    rest = keys[1:]
    chunks = [rest[i:i + COLS - 1] for i in range(0, len(rest), COLS - 1)] or [[]]
    for n, chunk in enumerate(chunks):
        if len(chunks) > 1:
            doc.note("Colonnes {} à {} sur {}{}.".format(n * (COLS - 1) + 1, n * (COLS - 1) + len(chunk), len(rest),
                                                          "" if n == 0 else " (suite du tableau)"))
        doc.table(["Code"] + [label(k) for k in chunk], [[cell(it.get("code"))] + [cell(it.get(k)) for k in chunk] for it in items])


def _text(value, name, limit=MAX_TEXT):
    text = str(value if value is not None else "")
    if len(text) > limit:
        raise ApiError(400, "« {} » : {} caractères (au plus {}). Correctif : raccourcissez ce texte.".format(name, len(text), limit))
    return text


def from_blocks(doc, blocks):
    """The document a page built itself, checked block by block."""
    if not isinstance(blocks, list) or len(blocks) > MAX_BLOCKS:
        raise ApiError(400, "blocks : une liste d'au plus {} blocs attendue. Correctif : exportez moins de contenu.".format(MAX_BLOCKS))
    for n, b in enumerate(blocks, start=1):
        kind = b.get("type") if isinstance(b, dict) else None
        if kind not in KINDS:
            raise ApiError(400, "Bloc {} : type « {} » inconnu. Correctif : un de {}.".format(n, kind, ", ".join(KINDS)))
        if kind == "h":
            level = b.get("level")
            doc.h(int(level) if str(level).isdigit() else 1, _text(b.get("text"), "titre", 300))
        elif kind in ("p", "note"):
            (doc.note if kind == "note" else doc.p)(_text(b.get("text"), "paragraphe"))
        elif kind in ("ul", "ol"):
            (doc.numbered if kind == "ol" else doc.bullets)([_text(i, "liste") for i in (b.get("items") or [])[:200]])
        elif kind == "table":
            header = [_text(h, "en-tête", 120) for h in (b.get("header") or [])[:40]]
            doc.table(header, [[_text(c, "cellule") for c in (r or [])[:40]] for r in (b.get("rows") or [])[:3000]])
        else:
            doc.card(_text(b.get("code"), "code", 20), _text(b.get("title"), "titre", 300), _text(b.get("tag"), "famille", 80),
                     int(b.get("color") or 0) if str(b.get("color") or 0).isdigit() else 0, _text(b.get("idea"), "idée"),
                     [(_text(d[0], "libellé", 80), _text(d[1], "détail")) for d in (b.get("details") or [])[:6]
                      if isinstance(d, (list, tuple)) and len(d) == 2])


def prepare(ctx):
    """(pid, meta, project) of a page export: the reader's right, the title and the fields of the header (PDF and Word)."""
    pid = validate.int_param(ctx.params, "pid")
    permissions.require_project_role(ctx.conn, ctx.user, pid, "reader")
    project = ctx.conn.execute("SELECT key, name FROM projects WHERE id = ?", (pid,)).fetchone()
    title = _text(ctx.body.get("title") or "Diamond", "titre", 120).strip() or "Diamond"
    view = re.sub(r"[^a-z]", "", str(ctx.body.get("view") or ""))[:20]
    initials = prefs.get(ctx.conn, ctx.user["id"]).get("initials") or ""
    meta = {"title": title, "subject": "{} ({})".format(project["name"], project["key"])[:110], "doctype": "Diamond · " + title,
            "docno": "DM-{}-{}".format(project["key"], view.upper() or "ALL")[:40], "rev": "A", "prepared": ctx.user["display_name"][:80],
            "initials": initials, "view": view}
    return pid, meta, project


def fill(ctx, pid, doc):
    """The body of the request into doc (pdf_doc.Doc or docx_pages.WordDoc); returns the scope for the journal."""
    if ctx.body.get("blocks") is not None:
        from_blocks(doc, ctx.body.get("blocks"))
        return "page"
    trip = rt.RoundTrip(ctx, pid)
    wanted = [k for k in (ctx.body.get("sections") or []) if isinstance(k, str)]
    keys = [k for k in wanted if k in trip.sections and trip.sections[k].listed] or [k for k, s in trip.sections.items() if s.listed]
    dumped = rt.dump(trip, keys)
    for key in keys:
        section(doc, trip.sections[key], dumped[key])
    return ",".join(keys) if wanted else "all"


def api_pdf(ctx):
    pid, meta, project = prepare(ctx)
    doc = P.Doc(meta)
    scope = fill(ctx, pid, doc)
    data = P.render(doc)
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_export_pdf", "project", pid, {"page": meta["view"], "sections": scope, "bytes": len(data)}, ctx.ip)
    name = re.sub(r"[^\w\-]+", "_", "Diamond_{}_{}".format(project["key"], meta["title"]), flags=re.UNICODE).strip("_")[:90]
    return RawFile(data, name + ".pdf", "application/pdf")
