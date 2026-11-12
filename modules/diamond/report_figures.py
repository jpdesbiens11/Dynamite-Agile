"""The figures of each section of the Word report of Diamond (0.60.98, D-O-105): the Storyline scene by scene, the
functional tree (cut like the PowerPoint: whole while it stays readable, otherwise an overview then one figure per
branch), the two views of the functional structure, the risk map now and residual. Each figure has a lead-in sentence
and a numbered caption; the colours of a legend are said in the lead-in (a legend beside a diagram would halve its size
on the page). Pictures: figures.py (diagrams) and story_figure.py (scenes), in EMF (emf.py).
"""
from modules.testing import word_doc as WD

from . import export_data as X
from . import export_drawio as D
from . import figures, story_figure
from .docx_figures import scale
from .export_pptx import tree_pages

STORY_H = int(3.0 * 914400)   # two scenes per page with their text
MUTED_SIZE = 18


def _small(label, text):
    return WD.para([WD.run(label, bold=True, color=X.MUTED, size=MUTED_SIZE), WD.run(text, color=X.MUTED, size=MUTED_SIZE)], space_after=80)


def storyline(data, figs):
    scenes = data["story"]
    out = [WD.heading(1, "Storyline"),
           WD.para([WD.run("La Storyline raconte l'usage du produit, scène par scène : qui l'utilise, où, avec quoi, ce qui se passe et ce "
                           "qu'on ressent. C'est un exercice de divergence fait en équipe avant l'arbre fonctionnel : on imagine l'usage "
                           "réel sans chercher encore les fonctions, et il n'y a ni bonne ni mauvaise réponse. Chaque scène place des "
                           "pictogrammes — personnes, lieux, objets, environnement, sentiments — avec une étiquette ; les fonctions de "
                           "l'arbre, la structure et les risques en découlent ensuite.")], space_after=120)]
    if not scenes:
        return "".join(out) + WD.para([WD.run("Aucune scène : la Storyline de ce Space est vide.", italic=True, color=X.MUTED)])
    out.append(WD.para([WD.run("Ce Space compte {} scène(s), dans l'ordre de l'usage ; chacune est une figure, avec ce qui s'y passe "
                               "et les notes de l'équipe (idées, irritants, questions).".format(len(scenes)))], space_after=120))
    for k, scene in enumerate(scenes, 1):
        title = "Scène {} : {}".format(k, scene["title"] or "sans titre")
        lead = ("Scène {}.".format(k), scene["caption"] or "Ce qui se passe n'est pas encore écrit.")
        after = []
        notes = [n.strip() for n in (scene["notes"] or "").splitlines() if n.strip()]
        if notes:
            after.append(_small("Notes : ", " · ".join(notes)))
        out.append(figs.figure(story_figure.render(scene), title, lead, after, max_h=STORY_H))
    return "".join(out)


def _branch_count(data, f):
    kids = data["kids"].get(f["id"], [])
    return 1 + sum(_branch_count(data, k) for k in kids)


def tree(data, figs):
    pages = tree_pages(data)
    if not pages or not [f for f in data["tree"] if f["in_tree"]]:
        return ""
    colours = ("Couleurs : jaune pour la fonction primaire, orange pour les fonctions secondaires (sous-systèmes), cyan pour les "
               "tertiaires, gris pour les fonctions techniques ; le chemin critique est en rouge ; sous chaque fonction, les pièces "
               "P-n qui la réalisent.")
    if len(pages) == 1:
        return figs.figure(figures.render(pages[0], legend=False), "Arbre fonctionnel",
                           "La figure {} montre l'arbre entier, de la fonction primaire à gauche jusqu'aux fonctions techniques. {}".format(
                               figs.count + 1, colours))
    n = figs.count + 1
    out = [figs.figure(figures.render(pages[0], legend=False), "Arbre fonctionnel — vue d'ensemble",
                       "La figure {} montre l'arbre en vue d'ensemble : la fonction primaire et ses fonctions secondaires ; les figures "
                       "{} à {} détaillent ensuite chaque branche. {}".format(n, n + 1, n + len(pages) - 1, colours))]
    branches = [s for r in data["kids"].get(None, []) if r["in_tree"] for s in data["kids"].get(r["id"], []) if data["kids"].get(s["id"])]
    pictures = [figures.render(page, legend=False) for page in pages[1:]]
    k = min(scale(w, h) for _d, w, h in pictures)  # every branch at the size of the widest
    for pic, s in zip(pictures, branches):
        lead = "Branche {} « {} » : {} fonction(s), de la fonction secondaire à ses fonctions tertiaires et techniques.".format(
            X.code(s), s["text"], _branch_count(data, s))
        out.append(figs.figure(pic, "Branche {} {}".format(X.code(s), s["text"]), lead, k=k))
    return "".join(out)


def structure(data, figs):
    if not data["structure"]["ports"] and not data["structure"]["secondaries"]:
        return ""
    n = figs.count + 1
    general = figs.figure(figures.render(D.structure_page(data, "general"), legend=False), "Structure fonctionnelle — vue générale",
                          "La figure {} montre la vue générale : les entrées à gauche, la frontière du système en tirets avec ses "
                          "fonctions secondaires, les sorties à droite. Flux : énergie en orange, matière en noir épais, information "
                          "(signal) en bleu pointillé ; une fonction critique est cerclée de rouge ; P-n : les pièces.".format(n))
    detail = figs.figure(figures.render(D.structure_page(data, "detail"), legend=False), "Structure fonctionnelle — vue détaillée",
                         "La figure {} descend d'un niveau : chaque sous-système avec ses fonctions tertiaires et les flux entre elles. "
                         "La figure est vectorielle : dans Word ou dans le PDF, zoomez pour lire une vue dense.".format(n + 1))
    return general + detail


def risks(data, figs):
    """The map now; the residual map once at least one risk has its residual P and I (an empty map would say nothing)."""
    if not data["risks"]:
        return ""
    n = figs.count + 1
    colours = "Couleurs : rouge critique (15 à 25), orange élevé (10 à 14), jaune moyen (5 à 9), vert faible (1 à 4)."
    rated = [r for r in data["risks"] if r["residual_p"] and r["residual_i"]]
    if not rated:
        return figs.figure(figures.render(D.risk_page(data, "now"), legend=False), "Carte des risques — maintenant",
                           "La figure {} place chaque risque sur la carte probabilité × impact. {}".format(n, colours),
                           [WD.para([WD.run("Aucun risque n'a encore sa cotation résiduelle (P et I une fois l'action faite) : la carte "
                                            "résiduelle s'ajoutera au rapport dès qu'un risque sera coté.", italic=True, color=X.MUTED,
                                            size=MUTED_SIZE)], space_after=160)])
    lead = ("Les figures {} et {} placent chaque risque sur la carte probabilité × impact, maintenant puis après les actions "
            "(résiduel ; {} risque(s) sur {} cotés). {}".format(n, n + 1, len(rated), len(data["risks"]), colours))
    return (figs.figure(figures.render(D.risk_page(data, "now"), legend=False), "Carte des risques — maintenant", lead) +
            figs.figure(figures.render(D.risk_page(data, "residual"), legend=False), "Carte des risques — résiduelle (après les actions)"))
