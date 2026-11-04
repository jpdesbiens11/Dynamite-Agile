"""Base template of a new project's Dynamite space (D-B-012).

The home page carries the project's name and shows, on real structure the
team fills in, the blocks worth knowing: table of contents, panel, tables,
status lozenges, internal links to the project's Agile board, Change
Management and Goldmine, and the list of sub-pages. No fictitious ticket
or requirement: example data lives only in the example Spaces.
"""
from core import db

from . import content, pages


def _t(text, *marks):
    node = {"type": "text", "text": text}
    if marks:
        node["marks"] = list(marks)
    return node


def _p(*nodes):
    return {"type": "paragraph", "content": [n if isinstance(n, dict) else _t(n) for n in nodes]}


def _h(level, text):
    return {"type": "heading", "level": level, "content": [_t(text)]}


def _status(text, color):
    return {"type": "status", "text": text, "color": color}


def _table(header, *rows):
    cells = lambda row: [[c] if isinstance(c, dict) else ([_t(c)] if c else []) for c in row]  # noqa: E731
    return {"type": "table", "header": True, "rows": [cells(header)] + [cells(r) for r in rows]}


def _link(text, href):
    return _t(text, {"type": "link", "href": href})


def home_body(key, name):
    todo = _status("TO COMPLETE", "gray")
    return {"type": "doc", "content": [
        _p("Space de documentation du projet ", _t(name, "bold"), "."),
        {"type": "panel", "kind": "info", "content": [_p(
            "Le Space porte la clé ", _t(key, "code"), " dans les trois onglets : Dynamite (documentation), "
            "Agile (tasks et Change Management) et Goldmine (requirements). Cliquez sur « Modifier » pour "
            "compléter cette page ; tapez « / » dans l'éditeur pour insérer un bloc.")]},
        {"type": "toc"},
        _h(1, "Objet et Scope"),
        _p(todo, " Décrire le produit, le client, les deliverables et ce qui est hors périmètre."),
        _h(1, "Équipe"),
        _table(["Role", "Nom", "Status"],
               ["Project Manager", "", todo], ["Systems Engineering", "", todo],
               ["Quality / Compliance", "", todo], ["Requirements Manager", "", todo]),
        _h(1, "Milestones"),
        _table(["Milestone", "Target Date", "Status"],
               ["SRR — System Requirements Review", "", _status("UPCOMING", "blue")],
               ["PDR — Preliminary Design Review", "", _status("UPCOMING", "blue")],
               ["CDR — Critical Design Review", "", _status("UPCOMING", "blue")]),
        _h(1, "Accès rapides"),
        {"type": "bullet_list", "items": [
            [_p(_link("Board Agile", "#/agile/{}/board".format(key)), " — les tasks du sprint.")],
            [_p(_link("Change Management", "#/agile/{}/changes".format(key)),
                " — PR, Bugs et ECN (CCB Approval, Implementation, Verification).")],
            [_p(_link("Goldmine", "#/goldmine/{}".format(key)), " — les requirements et leur traçabilité.")],
        ]},
        _h(1, "Pages du projet"),
        {"type": "children"},
    ]}


def create_home(ctx, project_id):
    conn = ctx.conn
    project = conn.execute("SELECT key, name FROM projects WHERE id = ?", (project_id,)).fetchone()
    body_text = content.validate(home_body(project["key"], project["name"]))
    now = db.utc_now()
    page_id = conn.execute(
        "INSERT INTO dynamite_pages (project_id, parent_id, title, position, current_version, created_by, "
        "created_at, updated_by, updated_at) VALUES (?, NULL, ?, 0, 1, ?, ?, ?, ?)",
        (project_id, project["name"], ctx.user["id"], now, ctx.user["id"], now)).lastrowid
    conn.execute("INSERT INTO dynamite_versions (page_id, version, title, body, author_id, created_at, note) "
                 "VALUES (?, 1, ?, ?, ?, ?, 'Modèle de base du projet')",
                 (page_id, project["name"], body_text, ctx.user["id"], now))
    pages._log(ctx, "dynamite_page_create", page_id, {"title": project["name"], "template": "home"})
    return page_id
