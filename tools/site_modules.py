"""The « Modules » page of the website (0.60.45, D-O-054), built from the same text as the HeadLamp library of the tool
(modules/help/module_docs*.py): for every module, why it exists, the need it covers, the steps, what it does from MVP 0 to
MVP x, and its references from the most to the least relevant. The « why » of each reference is written in French only."""
import base64
import html

from modules.help.module_docs import MODULES, MVP_X, MVPS
from modules.help.module_docs_refs import ACCESS, REFS

WORDS = {"fr": {"why": "Pourquoi ce module", "need": "Le besoin couvert", "steps": "Pas à pas", "mvp": "De MVP 0 à MVP x",
                "loop": "Boucle du PDP", "here": "Ce qu'on fait ici", "parts": "Les facettes", "depth": "À {} m dans la mine",
                "refs": "Références, de la plus à la moins pertinente"},
         "en": {"why": "Why this module", "need": "The need it covers", "steps": "Step by step", "mvp": "From MVP 0 to MVP x",
                "loop": "PDP loop", "here": "What you do here", "parts": "The facets", "depth": "{} m down the mine",
                "refs": "References, from the most to the least relevant"}}


def _refs(ids, lang):
    out = []
    for rid in ids:
        name, source, year, url, rlang, access, why = REFS[rid]
        note = ' <span class="why">{}</span>'.format(html.escape(why)) if lang == "fr" else ""
        out.append('<li><a href="{}" rel="noopener">{}</a> — {}{} · {} · <i>{}</i>.{}</li>'.format(
            html.escape(url), html.escape(name), html.escape(source), ", " + html.escape(year) if year else "", rlang,
            ACCESS[lang][access], note))
    return '<ol class="refs">' + "".join(out) + "</ol>"


def _logo(base, key):
    svg = (base / "static" / "img" / "marks" / (key + ".svg")).read_bytes()
    return '<img class="mod-logo" src="data:image/svg+xml;base64,{}" alt="">'.format(base64.b64encode(svg).decode("ascii"))


def toc(lang):
    return "".join('<li><a href="#m-{}">{}</a></li>'.format(m["key"], html.escape(m["name"])) for m in MODULES)


def sections(lang, base):
    w, out = WORDS[lang], []
    for m in MODULES:
        t = m[lang]
        steps = "".join("<li><b>{}</b>{}</li>".format(html.escape(a), html.escape(b)) for a, b in t["steps"])
        mvps = "".join("<tr><td>{}</td><td>{}</td></tr>".format(html.escape(a), html.escape(b)) for a, b in zip(MVPS[lang], t["mvps"]))
        parts = ""
        if m["parts"]:
            parts = "<h3>{}</h3>".format(w["parts"]) + "".join(
                '<h4>{}</h4><p>{}</p>{}'.format(html.escape(p["name"]), html.escape(p[lang]), _refs(p["refs"], lang)) for p in m["parts"])
        out.append(
            '  <section id="m-{key}" class="mod reveal" data-new="0.60.45-module-docs">\n'
            '    <h2>{logo}{name} <span class="depth">{depth}</span></h2>\n    <p class="lead">{role}</p>\n'
            '    <h3>{wwhy}</h3><p>{why}</p>\n    <h3>{wneed}</h3><p>{need}</p>\n'
            '    <h3>{wsteps}</h3><ol class="stepper">{steps}</ol>\n'
            '    <h3>{wmvp}</h3><table class="t"><tr><th>{loop}</th><th>{here}</th></tr>{mvps}</table><p class="mvpx">{mvpx}</p>\n'
            '    {parts}<h3>{wrefs}</h3>{refs}\n  </section>'.format(
                key=m["key"], logo=_logo(base, m["key"]), name=html.escape(m["name"]), depth=w["depth"].format("{:,}".format(m["depth"]).replace(",", "\u202f")),
                role=html.escape(t["role"]), wwhy=w["why"], why=html.escape(t["why"]), wneed=w["need"], need=html.escape(t["need"]),
                wsteps=w["steps"], steps=steps, wmvp=w["mvp"], loop=w["loop"], here=w["here"], mvps=mvps,
                mvpx=html.escape(MVP_X[lang]), parts=parts, wrefs=w["refs"], refs=_refs(m["refs"], lang)))
    return "\n".join(out)
