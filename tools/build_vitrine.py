"""Showcase page of the platform (D-B-087): static/apps/vitrine/index.html, one self-contained file.

    python tools/build_vitrine.py

Built from tools/vitrine/template.html with the same hand-drawn assets as the platform (icons sprite and the sign-in
sketch, tools/make_sketch_assets.py), so the page and the application always look alike. No external resource: it
opens from the platform (/apps/vitrine/) or by double-click, on the team server or offline.
"""
import base64
import html
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

TOOLS = [  # (icon, accent, name, sentence)
    ("dashboard", "--b", "Dashboard", "Tout ce qui vous attend dans tous vos Spaces, avec vos @mentions et un statut changeable sur place."),
    ("goldmine", "--y", "Goldmine", "Needs et requirements : Need Status, fonctions F-XX, criticité, Test Procedure, Q&A client."),
    ("exploration", "--v", "Exploration", "Le plan du projet sur plusieurs mois : phases, prédécesseurs, jalons, Gantt et aller-retour Excel."),
    ("agile", "--b", "Agile", "Backlog, Sprints et Board ; Change Management avec PR, bugs et ECN approuvés au CCB."),
    ("dynamite", "--o", "Dynamite", "Le wiki : éditeur visuel, blocs ticket vivants, procédures, BDC, export Word et PDF."),
    ("testing", "--g", "Testing", "La Test Base d'un produit grand public (sécurité, CEM, IP, chute, vie), Test Plans et listes centrales."),
    ("tools", "--c", "Tools", "Idéation en brainwriting, Pugh Matrix, Kepner-Tregoe et Generator des livrables du PDP."),
    ("training", "--p", "Training", "Topics, plans de formation, tests corrigés sur le serveur, suivi par l'enseignant."),
    ("timesheet", "--t", "Timesheet", "Ma semaine par étape du PDP, approbation, export Excel et rapport Word."),
    ("help", "--y", "Help & HeadLamp", "Le guide pas à pas, la FAQ et un Space bac à sable pour apprendre sans risque."),
]


def build():
    from core import APP_VERSION
    template = (BASE / "tools" / "vitrine" / "template.html").read_text(encoding="utf-8")
    sprite = (BASE / "static" / "img" / "icons.svg").read_text(encoding="utf-8")
    hero = (BASE / "static" / "img" / "sketch" / "hero.svg").read_text(encoding="utf-8")
    hero = re.sub(r'role="img" aria-hidden="true"', 'role="img" aria-label="Un arbre de fonctions à trois niveaux, des engrenages et un crayon"', hero)
    cards = "\n".join(
        '      <article class="tool reveal" style="--a: var({})"><svg class="ico"><use href="#i-{}"/></svg><h3>{}</h3><p>{}</p></article>'
        .format(accent, icon, html.escape(name), html.escape(text)) for icon, accent, name, text in TOOLS)
    page = (template.replace("<!--SPRITE-->", sprite.strip()).replace("<!--HERO-->", hero.strip())
            .replace("<!--TOOLS-->", cards.strip()).replace("<!--VERSION-->", "version " + APP_VERSION)
            .replace("LOGO_FONT_DATA", "data:font/woff2;base64," + base64.b64encode(
                (BASE / "static" / "fonts" / "baloo2-logo.woff2").read_bytes()).decode("ascii")))  # 0.60.32 (D-O-040)
    out = BASE / "static" / "apps" / "vitrine" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out, len(page)


if __name__ == "__main__":
    path, size = build()
    print("{} ({} Ko)".format(path, size // 1024))
