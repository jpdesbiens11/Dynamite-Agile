"""Website of Dynamite | Agile (D-O-015): site/index.html, site/installation.html, site/guide.html, in French, and the
same pages in English in site/en/ (D-O-017).

    python3 tools/build_site.py

A separate deliverable from the platform, published with GitHub Pages (.github/workflows/pages.yml). It reuses the
graphics and the look of the platform as they are (icons sprite, module logos, hero sketch, the CSS and the « day with
the team » of the vitrine, tools/build_vitrine.py), and adds the storyline of the landing page (the descent into the
mine), the installation procedure and the getting-started guide. Each page is one self-contained file: no external
resource, motion off with prefers-reduced-motion. The texts the two languages share are in tools/site_text.py.
"""
import base64
import html
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from tools import site_text as T  # noqa: E402

SRC = BASE / "tools" / "site"   # French templates; English ones in tools/site/en/
OUT = BASE / "site"
OWNER, NAME = "jpdesbiens11", "Dynamite-Agile"  # D-O-011: the public repository
REPO = "https://github.com/{}/{}".format(OWNER, NAME)
SITE_URL = "https://{}.github.io/{}".format(OWNER.lower(), NAME)  # GitHub Pages (or the domain of the site)
PAGES = ("index.html", "installation.html", "guide.html", "versions.html")  # 0.60.12: versions


def _between(text, start, end):
    i = text.index(start) + len(start)
    return text[i:text.index(end, i)]


def _section(page, section_id):
    match = re.search(r'<section id="{}"[^>]*>.*?</section>'.format(section_id), page, re.S)
    if not match:
        raise SystemExit("Section « {} » absente de la vitrine (tools/vitrine/template.html).".format(section_id))
    return "  " + match.group(0)


def _top(current, lang):
    links = "".join('<a href="{}"{}>{}</a>'.format(href, ' class="on" aria-current="page"' if href == current else "", label)
                    for href, label in zip(PAGES, T.NAV[lang]))
    label, title, other = T.SWITCH[lang]
    switch = ('<a class="lang" href="{}" hreflang="{}" lang="{}" title="{}">{}</a>'
              .format(("en/" if lang == "fr" else "../") + current, other, other, title, label))
    return ('<header class="top">\n  <a class="logo" href="index.html"><svg class="logo-mark" viewBox="0 0 32 32" aria-hidden="true">'
            '<rect x="3" y="3" width="26" height="26" rx="4" fill="#ffd23f" stroke="#26323f" stroke-width="2"/>'
            '<path d="M18 6 L11 17 H16 L14 26 L22 14 H17 Z" fill="none" stroke="#26323f" stroke-width="2" stroke-linejoin="round"/>'
            '</svg><span class="logo-word" role="img" aria-label="Dynamite Agile"><span class="lw-d">Dynamite</span><span class="lw-a">Agile</span></span></a>\n  <nav aria-label="Pages">{}</nav>\n  {}\n'
            '  <a class="btn btn-primary gh" href="{}">GitHub</a>\n</header>').format(links, switch, REPO)


def _alternates(name):
    """hreflang links in the <head> of both versions of a page."""
    return "".join('\n<link rel="alternate" hreflang="{}" href="{}/{}{}">'.format(lang, SITE_URL, "en/" if lang == "en" else "", name)
                   for lang in T.LANGS)


def _levels(lang):
    out = []
    for key, depth, name, text in T.MINE:
        mine, proj = text[lang]
        svg = (BASE / "static" / "img" / "marks" / (key + ".svg")).read_bytes()
        src = "data:image/svg+xml;base64," + base64.b64encode(svg).decode("ascii")
        out.append('        <article class="level" data-depth="{}"><img src="{}" alt="Logo {}">'
                   '<div><span class="m">{} m</span><h3>{}</h3><p class="mine">{}</p><p class="proj">{}</p></div></article>'
                   .format(depth, src, html.escape(name), depth, html.escape(name), html.escape(mine), proj))
    return "\n".join(out)


def _mine_rows(lang):
    return "\n".join("    <tr><td><b>{}</b></td><td>{}</td><td>{}</td></tr>".format(html.escape(name), html.escape(text[lang][0]),
                                                                              text[lang][1]) for _k, _d, name, text in T.MINE)


def _tools_en():
    from tools import build_vitrine
    cards = "\n".join(
        '      <article class="tool reveal" style="--a: var({})"><svg class="ico"><use href="#i-{}"/></svg><h3>{}</h3><p>{}</p></article>'
        .format(accent, icon, html.escape(name), html.escape(T.TOOLS_EN[name])) for icon, accent, name, _fr in build_vitrine.TOOLS)
    return '  <section id="outils">\n{}\n    <div class="tools">\n{}\n    </div>\n  </section>'.format(T.TOOLS_HEAD_EN, cards)


def _news(lang):
    """0.60.34: the latest features under the tools grid (site_text.NEWS), same cards as the tools."""
    head, sub = T.NEWS_HEAD[lang]
    cards = "\n".join('      <article class="tool reveal" style="--a: var({})"><svg class="ico"><use href="#i-{}"/></svg><h3>{}</h3><p>{}</p></article>'
                      .format(accent, icon, html.escape(text[lang][0]), html.escape(text[lang][1])) for icon, accent, text in T.NEWS)
    return ('  <section id="nouveautes">\n    <h2 class="reveal">{}</h2>\n    <p class="sub reveal">{}</p>\n    <div class="tools">\n{}\n'
            '    </div>\n  </section>').format(head, html.escape(sub), cards)


def _latest(lang):
    """0.60.36 (D-O-045): the latest version and its date on the installation page, so a team decides whether to update."""
    found = []
    for path in (BASE / "docs" / "releases").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        found.append((tuple(int(x) for x in str(data["version"]).split(".")), data))
    if not found:
        return ""
    data = max(found, key=lambda item: item[0])[1]
    head, more, already = T.LATEST[lang]
    return ('  <p class="note ok latest" data-new="0.60.36-site-latest"><b>{} {}</b> · {} — {} '
            '<a href="versions.html">{}</a><br>{}</p>').format(
        head, html.escape(data["version"]), html.escape(data.get("date", "")),
        html.escape(data["summary"][lang] if isinstance(data.get("summary"), dict) else ""), more, already)


def _landing(vitrine, lang, src):
    hero = _between(vitrine, '<div class="hero-art">', "</div>\n  </div>").strip()
    script = _between(vitrine, "<script>", "</script>").strip()
    if lang == "en":
        hero = hero.replace(T.HERO_LABEL["fr"], T.HERO_LABEL["en"])
        script = script.replace(json.dumps(T.TYPED["fr"], ensure_ascii=False), json.dumps(T.TYPED["en"], ensure_ascii=False))
        if T.TYPED["en"] not in script:
            raise SystemExit("Texte tapé de la vitrine introuvable (tools/vitrine/template.html, tools/site_text.TYPED).")
    return {
        "HERO": hero,
        "LEVELS": _levels(lang),
        "JOURNEY": _section(vitrine, "journee") if lang == "fr" else "  " + (src / "journee.html").read_text(encoding="utf-8").strip(),
        "CHAIN": _section(vitrine, "chaine") if lang == "fr" else "  " + (src / "chaine.html").read_text(encoding="utf-8").strip(),
        "TOOLS": _section(vitrine, "outils") if lang == "fr" else _tools_en(),
        "NEWS": _news(lang),
        "TERM": html.escape(json.dumps(T.term(lang, SITE_URL), ensure_ascii=False), quote=True),
        "VITRINE_JS": script,
    }


def build():
    from core import APP_VERSION
    from tools import build_vitrine
    vitrine_path, _size = build_vitrine.build()
    vitrine = vitrine_path.read_text(encoding="utf-8")
    css = _between(vitrine, "<style>", "</style>").strip() + "\n" + (SRC / "site.css").read_text(encoding="utf-8")
    common = {
        "FAVICON": re.search(r'<link rel="icon"[^>]*>', vitrine).group(0),
        "CSS": css,
        "SPRITE": (BASE / "static" / "img" / "icons.svg").read_text(encoding="utf-8").strip(),
        "SITE_JS": (SRC / "site.js").read_text(encoding="utf-8"),
        "REPO": REPO,
        "SITE_URL": SITE_URL,
    }
    written = []
    for lang in T.LANGS:
        src, out = (SRC, OUT) if lang == "fr" else (SRC / "en", OUT / "en")
        out.mkdir(parents=True, exist_ok=True)
        for name in PAGES:
            page = (src / name).read_text(encoding="utf-8")
            values = dict(common, TOP=_top(name, lang), MINE_ROWS=_mine_rows(lang), FOOTER=T.footer(lang, APP_VERSION, REPO))
            if name == "index.html":
                values.update(_landing(vitrine, lang, src))
            if name == "installation.html":
                values["LATEST"] = _latest(lang)
                values.update(TROUBLE=(src / "trouble.html").read_text(encoding="utf-8").rstrip(),
                              INSTALL_JS=(SRC / "install.js").read_text(encoding="utf-8"))
            if name == "versions.html":  # 0.60.12 (D-O-024): reads updates/versions.json, built by tools/build_release.py
                values["VERSIONS_JS"] = (SRC / "versions.js").read_text(encoding="utf-8")
            values["FAVICON"] += _alternates(name)
            for key, value in values.items():
                page = page.replace("{{" + key + "}}", value)
            left = re.findall(r"\{\{[A-Z_]+\}\}", page)
            if left:
                raise SystemExit("{}/{} : marqueurs non remplacés {}".format(lang, name, left))
            (out / name).write_text(page, encoding="utf-8")
            written.append((out / name, len(page)))
        # the guide an AI assistant reads next to the person, in the language of the page
        guide = (src / "installer.md").read_text(encoding="utf-8").replace("{{SITE_URL}}", SITE_URL).replace("{{REPO}}", REPO)
        (out / "installer.md").write_text(guide, encoding="utf-8")
        written.append((out / "installer.md", len(guide)))
        # 0.60.18 (D-O-019): the prompt of the Project Starter, the same text as « Commencer » serves in the tool
        from core import starter_prompt
        prompt = starter_prompt.render(lang, SITE_URL, REPO)
        (out / "starter.md").write_text(prompt, encoding="utf-8")
        written.append((out / "starter.md", len(prompt)))
    # the script the one-command installation fetches (one for both languages: DA_LANG=en for English messages)
    script = (BASE / "deploy" / "install.sh").read_text(encoding="utf-8")
    script = re.sub(r'REPO="\$\{DA_REPO:-[^}]*\}"', 'REPO="${{DA_REPO:-{}.git}}"'.format(REPO), script)
    (OUT / "install.sh").write_text(script, encoding="utf-8")
    written.append((OUT / "install.sh", len(script)))
    # 0.60.10 (D-O-022): the PowerShell script of the Windows team server -- kept byte for byte (its UTF-8 BOM lets
    # Windows PowerShell 5.1 read the accents), only the repository is filled in
    ps1 = (BASE / "deploy" / "install.ps1").read_bytes()
    ps1 = re.sub(rb'else \{ "https://github\.com/[^"]*" \}', 'else {{ "{}.git" }}'.format(REPO).encode("utf-8"), ps1)
    (OUT / "install.ps1").write_bytes(ps1)
    written.append((OUT / "install.ps1", len(ps1)))
    (OUT / ".nojekyll").write_text("", encoding="utf-8")  # GitHub Pages: serve the files as they are
    return written


if __name__ == "__main__":
    for path, size in build():
        print("{} ({} Ko)".format(path.relative_to(BASE), size // 1024))
