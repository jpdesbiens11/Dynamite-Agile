"""Export a Dynamite page (and optionally its sub-pages) as Word or PDF (D-B-050).

GET .../pages/<id>/export.docx | export.pdf [?children=1]
POST the same with {children, diagrams}: Mermaid drawings as PNG from the browser (0.60.62, export_mermaid.py)
Right: reader of the space AND the export right given by an administrator
to that person (Administration → Droits, column « Export »; administrators
always have it). Every export is journalled -- and refused while the
administrator's « block print » protection is on, for non-administrators.

The page JSON is first flattened (flatten()) into simple items shared by
both writers (export_docx.py, export_pdf.py): headings, paragraphs with
runs (bold, italic, underline, strike, code, link, colour), list items,
tables, code, rules, images (attachment bytes) and ticket lines.
"""
import datetime as dt
import json
import re

from core import audit, permissions, prefs, uploads, validate
from core.errors import ApiError
from core.files import RawFile

from . import export_mermaid
from .pages import _page

PANEL_LABEL = {"info": "Info", "note": "Note", "warning": "Attention", "success": "Réussite"}
MIME = {"docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "pdf": "application/pdf"}


def can_export(conn, user):
    return bool(user["is_admin"]) or bool(prefs.get(conn, user["id"]).get("can_export"))


def _runs(nodes):
    runs = []
    for n in nodes or []:
        if n.get("type") == "status":
            runs.append((" {} ".format(n.get("text", "").upper()), {"bold": True, "color": n.get("color")}))
            continue
        style = {}
        for m in n.get("marks", []):
            if isinstance(m, str):
                style[m] = True
            elif m.get("type") == "link":
                style["link"] = m.get("href")
            elif m.get("type") == "color":
                style["color"] = m.get("color")
        runs.append((n.get("text", ""), style))
    return runs


def flatten(ctx, project_id, page, body, depth_offset=0, diagrams=None):
    conn = ctx.conn
    items = []
    diagrams = diagrams or {}

    def blocks(nodes, depth, prefix_style=None):
        for node in nodes or []:
            kind = node.get("type")
            if kind == "heading":
                items.append(("h", min(3, node.get("level", 1) + depth_offset), _runs(node.get("content"))))
            elif kind == "paragraph":
                items.append(("p", _runs(node.get("content")), prefix_style))
            elif kind in ("bullet_list", "ordered_list"):
                for i, item in enumerate(node.get("items", []), start=1):
                    first, rest = (item[0], item[1:]) if item else ({"type": "paragraph", "content": []}, [])
                    mark = "•" if kind == "bullet_list" else "{}.".format(i)
                    runs = _runs(first.get("content")) if first.get("type") in ("paragraph", "heading") else []
                    items.append(("li", depth, mark, runs))
                    if first.get("type") not in ("paragraph", "heading"):
                        blocks([first], depth + 1)
                    blocks(rest, depth + 1)
            elif kind in ("quote", "panel"):
                label = PANEL_LABEL.get(node.get("kind"), "Citation") if kind == "panel" else None
                if label:
                    items.append(("p", [(label + " — ", {"bold": True})], kind))
                blocks(node.get("content"), depth, kind)
            elif kind == "code":
                text = node.get("text", "")
                png = diagrams.get(text) if export_mermaid.is_mermaid(node) else None
                if png:  # 0.60.62 (D-O-071): the drawing, then its code in small type for the audit
                    items.append(("image", png, "image/png", "Diagramme Mermaid", export_mermaid.SCALE))
                    items.append(("code", text, "small"))
                else:
                    items.append(("code", text))
            elif kind == "rule":
                items.append(("rule",))
            elif kind == "table":
                items.append(("table", bool(node.get("header")), [[_runs(cell) for cell in row] for row in node.get("rows", [])]))
            elif kind == "image":
                row = conn.execute("SELECT * FROM attachments WHERE id = ? AND project_id = ?", (node.get("id"), project_id)).fetchone()
                data = None
                if row is not None:
                    try:
                        data = uploads.read(ctx.data_dir, row)
                    except OSError:
                        data = None
                items.append(("image", data, row["mime"] if row else "", node.get("alt", "")))
            elif kind == "ticket":
                key = node.get("key", "")
                line = key
                prefix, _, number = key.rpartition("-")
                proj = conn.execute("SELECT id FROM projects WHERE key = ?", (prefix,)).fetchone()
                if proj and permissions.project_role(conn, ctx.user, proj["id"]):
                    t = conn.execute("SELECT i.title, s.name FROM agile_issues i JOIN agile_statuses s ON s.id = i.status_id "
                                     "WHERE i.project_id = ? AND i.number = ?", (proj["id"], int(number))).fetchone()
                    if t:
                        line = "{} — {} [{}]".format(key, t["title"], t["name"])
                items.append(("p", [("Ticket ", {"bold": True}), (line, {})], "panel"))
            elif kind == "children":
                for child in conn.execute("SELECT title FROM dynamite_pages WHERE parent_id = ? ORDER BY position, id", (page["id"],)):
                    items.append(("li", 0, "•", [(child["title"], {})]))
            # toc: the exported document carries its own headings; nothing to add
    blocks(body.get("content"), 0)
    return items


def _collect(ctx, project_id, page, with_children):
    """[(page, body, level)] -- the page, then its sub-pages depth-first."""
    out = []

    def walk(p, level):
        row = ctx.conn.execute("SELECT body FROM dynamite_versions WHERE page_id = ? AND version = ?",
                               (p["id"], p["current_version"])).fetchone()
        out.append((p, json.loads(row["body"]) if row else {"type": "doc", "content": []}, level))
        if with_children:
            for child in ctx.conn.execute("SELECT * FROM dynamite_pages WHERE parent_id = ? ORDER BY position, id", (p["id"],)).fetchall():
                walk(child, level + 1)
    walk(page, 0)
    return out


def check(ctx):
    """The Space and the page, once the person may export them (reader + export right, no print block)."""
    project_id = validate.int_param(ctx.params, "pid")
    permissions.require_project_role(ctx.conn, ctx.user, project_id, "reader")
    if not can_export(ctx.conn, ctx.user):
        raise ApiError(403, "Export non autorisé pour votre compte. Correctif : demandez à un administrateur d'activer "
                            "« Export PDF / Word » pour vous (Admin → Droits).")
    if not ctx.user["is_admin"] and prefs.policy(ctx.conn).get("block_print"):
        raise ApiError(403, "Export suspendu : l'administrateur a activé le blocage de l'impression.")
    return project_id, _page(ctx.conn, project_id, validate.int_param(ctx.params, "page"))


def api_export(ctx, with_children=None, diagrams=None):
    fmt = ctx.params.get("fmt")
    project_id, page = check(ctx)
    if with_children is None:
        with_children = str(ctx.query.get("children", "0")) in ("1", "true", "oui")
    project = ctx.conn.execute("SELECT key, name FROM projects WHERE id = ?", (project_id,)).fetchone()
    docs = []
    for p, body, level in _collect(ctx, project_id, page, with_children):
        docs.append({"title": p["title"], "level": level, "version": p["current_version"], "updated": p["updated_at"],
                     "items": flatten(ctx, project_id, p, body, diagrams=diagrams)})
    meta = {"space": "{} — {}".format(project["key"], project["name"]), "by": ctx.user["display_name"],
            "at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "title": page["title"]}
    if fmt == "docx":
        from .export_docx import build
    else:
        from .export_pdf import build
    data = build(docs, meta)
    audit.log_action(ctx.conn, ctx.user["id"], "dynamite_page_export", "dynamite_page", page["id"],
                     {"format": fmt, "pages": len(docs), "diagrams": len(diagrams or {})}, ctx.ip)
    name = re.sub(r"[^\w\-]+", "_", "{}_{}".format(project["key"], page["title"]), flags=re.UNICODE).strip("_")[:80]
    return RawFile(data, "{}.{}".format(name, fmt), MIME[fmt])
