"""Validation of a Dynamite page body (D-A-035).

A page is stored as a JSON tree, never as HTML:

    {"type": "doc", "content": [block, ...]}

Blocks: paragraph, heading(level 1-3), bullet_list / ordered_list
(items: [[block, ...], ...]), quote, code(text, lang), rule,
panel(kind info|note|warning|success), ticket(key),
image(id, alt) -- id of an attachment of this space (D-B-004),
table(header, rows: [[cell inline nodes, ...], ...]), toc, children (D-B-006).
Inline nodes (inside paragraph / heading / table cell): text(text, marks)
and status(text, color). Marks are a subset of bold, italic, underline,
strike, code, link(href), color(color).

Anything else is refused with the path of the offending node and what is
accepted there (D-A-031) -- the browser rebuilds pages with el() and
textContent only, so this whitelist is the whole attack surface.
"""
import json
import re

from core.errors import ApiError

MAX_BYTES = 1024 * 1024
MAX_DEPTH = 8
MAX_TEXT = 20000
BLOCKS = ("paragraph", "heading", "bullet_list", "ordered_list", "quote", "code", "rule", "panel", "ticket", "image",
          "table", "toc", "children")
MARKS = ("bold", "italic", "underline", "strike", "code")
PANELS = ("info", "note", "warning", "success")
COLORS = ("red", "orange", "green", "blue", "purple", "gray")          # text colour palette
STATUS_COLORS = ("gray", "blue", "green", "yellow", "red")              # status lozenges
MAX_ROWS, MAX_COLS = 500, 30
KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}-\d+$")
LINK_RE = re.compile(r"^(https?://[^\s\"<>]+|#/[\w/.\-]*)$")


def _bad(path, message, accepted):
    raise ApiError(400, "Contenu de page refusé ({}) : {} Correctif : {}".format(path, message, accepted))


def _inline(nodes, path):
    if not isinstance(nodes, list):
        _bad(path, "liste de texte attendue.", "enregistrez depuis l'éditeur Dynamite.")
    for i, node in enumerate(nodes):
        where = "{}[{}]".format(path, i)
        if isinstance(node, dict) and node.get("type") == "status":
            label = node.get("text")
            if not isinstance(label, str) or not label.strip() or len(label) > 40:
                _bad(where, "status sans texte ou trop long.", "1 à 40 caractères, ex. EN COURS.")
            if node.get("color") not in STATUS_COLORS:
                _bad(where, "couleur de status « {} » inconnue.".format(node.get("color")),
                     "couleurs permises : " + ", ".join(STATUS_COLORS) + ".")
            continue
        if not isinstance(node, dict) or node.get("type") != "text":
            _bad(where, "seul du texte est permis dans un paragraphe ou un titre.",
                 "placez les blocs (listes, panneaux, tickets) sur leur propre ligne.")
        text = node.get("text")
        if not isinstance(text, str) or len(text) > MAX_TEXT:
            _bad(where, "texte manquant ou trop long.", "{} caractères au maximum par segment.".format(MAX_TEXT))
        for mark in node.get("marks", []):
            if isinstance(mark, str) and mark in MARKS:
                continue
            if isinstance(mark, dict) and mark.get("type") == "link":
                if not isinstance(mark.get("href"), str) or not LINK_RE.match(mark["href"]):
                    _bad(where, "lien « {} » non permis.".format(mark.get("href")),
                         "un lien commence par http:// ou https:// (ou #/ pour une page interne).")
                continue
            if isinstance(mark, dict) and mark.get("type") == "color":
                if mark.get("color") not in COLORS:
                    _bad(where, "couleur « {} » inconnue.".format(mark.get("color")),
                         "couleurs permises : " + ", ".join(COLORS) + ".")
                continue
            _bad(where, "mise en forme « {} » inconnue.".format(mark),
                 "gras, italique, souligné, barré, code ou lien.")


def _blocks(nodes, path, depth):
    if depth > MAX_DEPTH:
        _bad(path, "imbrication trop profonde.", "{} niveaux au maximum.".format(MAX_DEPTH))
    if not isinstance(nodes, list):
        _bad(path, "liste de blocs attendue.", "enregistrez depuis l'éditeur Dynamite.")
    for i, node in enumerate(nodes):
        where = "{}[{}]".format(path, i)
        kind = node.get("type") if isinstance(node, dict) else None
        if kind not in BLOCKS:
            _bad(where, "bloc « {} » inconnu.".format(kind), "blocs permis : " + ", ".join(BLOCKS) + ".")
        if kind in ("paragraph", "heading"):
            _inline(node.get("content", []), where)
            if kind == "heading" and node.get("level") not in (1, 2, 3):
                _bad(where, "niveau de titre {} invalide.".format(node.get("level")), "titres de niveau 1 à 3.")
        elif kind in ("bullet_list", "ordered_list"):
            items = node.get("items")
            if not isinstance(items, list) or not items:
                _bad(where, "liste vide.", "au moins un élément.")
            for j, item in enumerate(items):
                _blocks(item, "{}.items[{}]".format(where, j), depth + 1)
        elif kind in ("quote", "panel"):
            if kind == "panel" and node.get("kind") not in PANELS:
                _bad(where, "panneau « {} » inconnu.".format(node.get("kind")),
                     "panneaux permis : " + ", ".join(PANELS) + ".")
            _blocks(node.get("content", []), where, depth + 1)
        elif kind == "code":
            if not isinstance(node.get("text"), str) or len(node["text"]) > 100000:
                _bad(where, "bloc de code invalide.", "100 000 caractères au maximum.")
            if not isinstance(node.get("lang", ""), str) or len(node.get("lang", "")) > 20:
                _bad(where, "langage de code invalide.", "20 caractères au maximum.")
        elif kind == "ticket":
            if not isinstance(node.get("key"), str) or not KEY_RE.match(node["key"]):
                _bad(where, "clé de ticket « {} » invalide.".format(node.get("key")),
                     "format PROJET-numéro, ex. EQP-4.")
        elif kind == "image":
            image_id = node.get("id")
            if isinstance(image_id, bool) or not isinstance(image_id, int) or image_id <= 0:
                _bad(where, "image sans numéro valide.", "insérez l'image avec le bouton Image, ou collez-la.")
            alt = node.get("alt", "")
            if not isinstance(alt, str) or len(alt) > 300:
                _bad(where, "texte alternatif de l'image invalide.", "300 caractères au maximum.")
        elif kind == "table":
            rows = node.get("rows")
            if not isinstance(rows, list) or not rows or len(rows) > MAX_ROWS:
                _bad(where, "tableau sans ligne ou trop grand.", "1 à {} lignes.".format(MAX_ROWS))
            if not isinstance(node.get("header", False), bool):
                _bad(where, "en-tête de tableau invalide.", "vrai ou faux.")
            for r, row in enumerate(rows):
                if not isinstance(row, list) or not row or len(row) > MAX_COLS:
                    _bad("{}.rows[{}]".format(where, r), "ligne vide ou trop large.",
                         "1 à {} colonnes.".format(MAX_COLS))
                for c, cell in enumerate(row):
                    _inline(cell, "{}.rows[{}][{}]".format(where, r, c))


def validate(body):
    """Return the canonical JSON text of a valid page body."""
    if not isinstance(body, dict) or body.get("type") != "doc":
        _bad("racine", "document attendu.", "enregistrez depuis l'éditeur Dynamite.")
    _blocks(body.get("content", []), "contenu", 0)
    text = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    if len(text.encode("utf-8")) > MAX_BYTES:
        _bad("racine", "page de plus de 1 Mo.", "découpez-la en sous-pages.")
    return text


def image_ids(body):
    """Every image id referenced by a (validated) page body."""
    found = []

    def walk(nodes):
        for node in nodes or []:
            kind = node.get("type")
            if kind == "image":
                found.append(node["id"])
            elif kind in ("bullet_list", "ordered_list"):
                for item in node.get("items", []):
                    walk(item)
            elif kind in ("quote", "panel"):
                walk(node.get("content"))
    walk(body.get("content"))
    return sorted(set(found))


def plain_text(body):
    """Flatten a page body to text (search index, version compare)."""
    out = []

    def walk(nodes):
        for node in nodes or []:
            kind = node.get("type")
            if kind == "text":
                out.append(node.get("text", ""))
            elif kind in ("paragraph", "heading"):
                walk(node.get("content"))
                out.append("\n")
            elif kind in ("bullet_list", "ordered_list"):
                for item in node.get("items", []):
                    walk(item)
            elif kind in ("quote", "panel"):
                walk(node.get("content"))
            elif kind == "code":
                out.append(node.get("text", "") + "\n")
            elif kind == "ticket":
                out.append("[[{}]]\n".format(node.get("key")))
            elif kind == "image":
                out.append("[image {} : {}]\n".format(node.get("id"), node.get("alt", "")))
            elif kind == "status":
                out.append("[{}]".format(node.get("text", "")))
            elif kind == "table":
                for row in node.get("rows", []):
                    for cell in row:
                        walk(cell)
                        out.append(" | ")
                    out.append("\n")
    walk(body.get("content"))
    return "".join(out)
