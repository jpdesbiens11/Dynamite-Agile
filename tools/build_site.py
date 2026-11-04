"""Website of Dynamite | Agile (D-O-015): site/index.html, site/installation.html, site/guide.html.

    python3 tools/build_site.py

A separate deliverable from the platform, published with GitHub Pages (.github/workflows/pages.yml). It reuses the
graphics and the look of the platform as they are (icons sprite, module logos, hero sketch, the CSS and the « day with
the team » of the vitrine, tools/build_vitrine.py), and adds the storyline of the landing page (the descent into the
mine), the installation procedure and the getting-started guide. Each page is one self-contained file: no external
resource, motion off with prefers-reduced-motion.
"""
import base64
import html
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

SRC = BASE / "tools" / "site"
OUT = BASE / "site"
OWNER = "OWNER"  # D-O-011: the GitHub account of the repository, to set when it is created
REPO = "https://github.com/{}/dynamite-agile".format(OWNER)
SITE_URL = "https://{}.github.io/dynamite-agile".format(OWNER.lower())  # GitHub Pages (or the domain of the site)
PAGES = (("index.html", "Accueil"), ("installation.html", "Installation"), ("guide.html", "Guide"))

# (logo, depth in m, name, in the mine, in the project) -- the descent of the landing page and the guide (D-O-014)
MINE = [
    ("exploration", 40, "Exploration", "La prospection : on étudie le terrain et on décide où creuser, dans quel ordre.",
     "Le <b>plan du projet</b> : phases du PDP, jalons, prédécesseurs, Gantt."),
    ("dynamite", 90, "Dynamite", "La charge qui fait sauter la roche : on dynamite le savoir brut pour le dégager.",
     "Le <b>wiki</b> de l'équipe : notes, comptes rendus, procédures, décisions."),
    ("goldmine", 150, "Goldmine", "Le filon d'or : ce qu'on est venu chercher, trié pépite par pépite.",
     "Les <b>besoins et requirements</b>, tracés du client jusqu'à leur essai."),
    ("agile", 210, "Agile", "Les équipes de forage, par quarts : chacune sait quel front attaquer.",
     "<b>Backlog, sprints et Board</b> ; Change Management quand la galerie dévie."),
    ("testing", 270, "Testing", "L'essai du minerai : on mesure la teneur avant de déclarer le filon rentable.",
     "La <b>Test Base</b>, les procédures et les plans qui prouvent chaque requirement."),
    ("tools", 330, "Tools & Generator", "La boîte à outils et le poinçon des lots : chaque wagon reçoit son numéro.",
     "Les <b>méthodes de conception</b> (Pugh, Kepner-Tregoe) et le nom de chaque document."),
    ("timesheet", 390, "Timesheet", "Le carnet de quart : qui a travaillé à quel front, combien d'heures.",
     "Les <b>heures par étape du PDP</b>, les vacances, les réclamations de financement."),
    ("training", 450, "Training & HeadLamp", "L'école de la mine et la lampe frontale qui éclaire la galerie.",
     "La <b>formation</b>, le tour guidé et un bac à sable pour s'exercer sans risque."),
]
TERM = ["$ ssh root@203.0.113.10",
        "root@serveur:~# curl -fsSL {}/install.sh | sudo bash -s -- atelier.mon-domaine.ca moi@exemple.ca".format(SITE_URL),
        "== 1/7 Paquets du système … == 6/7 Service « dynamite-agile »",
        "== 7/7 C'est installé",
        "✓ Ouvrez https://atelier.mon-domaine.ca — compte admin, mot de passe affiché ci-dessus"]


def _between(text, start, end):
    i = text.index(start) + len(start)
    return text[i:text.index(end, i)]


def _section(page, section_id):
    match = re.search(r'<section id="{}"[^>]*>.*?</section>'.format(section_id), page, re.S)
    if not match:
        raise SystemExit("Section « {} » absente de la vitrine (tools/vitrine/template.html).".format(section_id))
    return "  " + match.group(0)


def _top(current):
    links = "".join('<a href="{}"{}>{}</a>'.format(href, ' class="on" aria-current="page"' if href == current else "", label)
                    for href, label in PAGES)
    return ('<header class="top">\n  <a class="logo" href="index.html"><svg class="logo-mark" viewBox="0 0 32 32" aria-hidden="true">'
            '<rect x="3" y="3" width="26" height="26" rx="4" fill="#ffd23f" stroke="#26323f" stroke-width="2"/>'
            '<path d="M18 6 L11 17 H16 L14 26 L22 14 H17 Z" fill="none" stroke="#26323f" stroke-width="2" stroke-linejoin="round"/>'
            '</svg>Dynamite | Agile</a>\n  <nav aria-label="Pages">{}</nav>\n'
            '  <a class="btn btn-primary gh" href="{}">GitHub</a>\n</header>').format(links, REPO)


def _levels():
    out = []
    for key, depth, name, mine, proj in MINE:
        svg = (BASE / "static" / "img" / "marks" / (key + ".svg")).read_bytes()
        src = "data:image/svg+xml;base64," + base64.b64encode(svg).decode("ascii")
        out.append('        <article class="level" data-depth="{}"><img src="{}" alt="Logo {}">'
                   '<div><span class="m">{} m</span><h3>{}</h3><p class="mine">{}</p><p class="proj">{}</p></div></article>'
                   .format(depth, src, html.escape(name), depth, html.escape(name), html.escape(mine), proj))
    return "\n".join(out)


def _mine_rows():
    return "\n".join("    <tr><td><b>{}</b></td><td>{}</td><td>{}</td></tr>".format(html.escape(name), html.escape(mine), proj)
                     for _key, _d, name, mine, proj in MINE)


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
        "FOOTER": ('<footer>Dynamite | Agile · logiciel libre sous licence MIT · version {} · '
                   'Jean-Philippe Desbiens · <a href="{}">GitHub</a></footer>').format(APP_VERSION, REPO),
    }
    landing = {
        "HERO": _between(vitrine, '<div class="hero-art">', "</div>\n  </div>").strip(),
        "LEVELS": _levels(),
        "JOURNEY": _section(vitrine, "journee"),
        "CHAIN": _section(vitrine, "chaine"),
        "TOOLS": _section(vitrine, "outils"),
        "TERM": html.escape(json.dumps(TERM, ensure_ascii=False), quote=True),
        "VITRINE_JS": _between(vitrine, "<script>", "</script>").strip(),
    }
    OUT.mkdir(exist_ok=True)
    written = []
    for name, _label in PAGES:
        page = (SRC / name).read_text(encoding="utf-8")
        values = dict(common, TOP=_top(name), MINE_ROWS=_mine_rows(), **(landing if name == "index.html" else {}))
        if name == "installation.html":
            values.update(TROUBLE=(SRC / "trouble.html").read_text(encoding="utf-8").rstrip(),
                          INSTALL_JS=(SRC / "install.js").read_text(encoding="utf-8"))
        for key, value in values.items():
            page = page.replace("{{" + key + "}}", value)
        left = re.findall(r"\{\{[A-Z_]+\}\}", page)
        if left:
            raise SystemExit("{} : marqueurs non remplacés {}".format(name, left))
        (OUT / name).write_text(page, encoding="utf-8")
        written.append((OUT / name, len(page)))
    # the script the one-command installation fetches, and the guide an AI assistant reads next to the person
    script = (BASE / "deploy" / "install.sh").read_text(encoding="utf-8")
    script = re.sub(r'REPO="\$\{DA_REPO:-[^}]*\}"', 'REPO="${{DA_REPO:-{}.git}}"'.format(REPO), script)
    (OUT / "install.sh").write_text(script, encoding="utf-8")
    guide = (SRC / "installer.md").read_text(encoding="utf-8").replace("{{SITE_URL}}", SITE_URL).replace("{{REPO}}", REPO)
    (OUT / "installer.md").write_text(guide, encoding="utf-8")
    written += [(OUT / "install.sh", len(script)), (OUT / "installer.md", len(guide))]
    (OUT / ".nojekyll").write_text("", encoding="utf-8")  # GitHub Pages: serve the files as they are
    return written


if __name__ == "__main__":
    for path, size in build():
        print("{} ({} Ko)".format(path.relative_to(BASE), size // 1024))
