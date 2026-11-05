"""A tiny writer of Dynamite page bodies for the Rover example: p("text with **bold**"), h(2, "title"), ul([...]),
ol([...]), table(header, rows), panel(kind, text), code(text), children(), toc()."""
import re


def _inline(text):
    out = []
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", str(text))):
        if part:
            out.append({"type": "text", "text": part, "marks": ["bold"]} if i % 2 else {"type": "text", "text": part})
    return out


def p(text):
    return {"type": "paragraph", "content": _inline(text)}


def h(level, text):
    return {"type": "heading", "level": level, "content": [{"type": "text", "text": text}]}


def ul(items):
    return {"type": "bullet_list", "items": [[p(x)] for x in items]}


def ol(items):
    return {"type": "ordered_list", "items": [[p(x)] for x in items]}


def table(header, rows):
    cells = lambda row: [_inline(c) for c in row]  # noqa: E731
    return {"type": "table", "header": True, "rows": [cells(header)] + [cells(r) for r in rows]}


def panel(kind, text):
    return {"type": "panel", "kind": kind, "content": [p(text)]}


def code(text, lang=""):
    node = {"type": "code", "text": text}
    if lang:
        node["lang"] = lang
    return node


def children():
    return {"type": "children"}


def toc():
    return {"type": "toc"}


def doc(*blocks):
    return {"type": "doc", "content": [b for b in blocks if b]}


def page(ref, title, parent, *blocks):
    return {"ref": ref, "title": title, "parent": parent, "body": doc(*blocks)}
