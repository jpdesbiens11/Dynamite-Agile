"""Diamond · « ↔ IA » (0.60.111, D-O-124): the prompt that carries the page (or all of Diamond) to an AI assistant.

Three modes, the same answer format (one ```json block, the sections complete):
  review     the assistant reads the artefacts and returns them corrected and completed, in one go;
  interview  one question at a time, in the order of the method; the document when the engineer writes « GÉNÈRE »;
  workshop   the blackboard: the engineer dictates the post-its of a session (moves, merges, new ideas, what goes away); the
             assistant keeps the document up to date and gives it back at each « GÉNÈRE ».
"""
import json

from core.terms import RULE_FR

from .rt import context, dump

MODES = {
    "review": "Révision : lisez ces artéfacts, corrigez ce qui ne tient pas (méthode, cohérence entre sections, formulation), "
              "complétez ce qui manque, retirez ce qui est en double ou hors sujet ; rendez le document complet en une fois, "
              "suivi d'une courte liste de ce que vous avez changé et pourquoi.",
    "interview": "Entrevue guidée : posez UNE question à la fois à l'ingénieur, dans l'ordre de la méthode, en partant de ce qui est "
                 "déjà là ; ne rendez le document que lorsqu'il écrit « GÉNÈRE ».",
    "workshop": ("Atelier (tableau blanc, brainstorm numérique) -- l'équipe pense, vous tenez le tableau. Déroulement : "
                 "(1) POST-IT : chaque message de l'équipe (tapé ou dicté) apporte un ou plusieurs post-it ; numérotez-les P1, "
                 "P2… dans l'ordre d'arrivée, sans juger ni trier, et répondez seulement par le tableau à jour ; ne proposez "
                 "pas vos propres post-it tant qu'on ne vous le demande pas (« TES IDÉES »), et marquez-les alors « (IA) ». "
                 "(2) « REGROUPE » : proposez des groupes nommés G1, G2… (3 à 8, un nom court, une phrase qui dit pourquoi), "
                 "chaque post-it dans un seul groupe, les doublons signalés ; l'équipe discute et corrige (« fusionne G2 et G4 », "
                 "« P7 va dans G1 », « renomme G3 », « retire P5 ») : appliquez et remontrez le tableau. "
                 "(3) Le TABLEAU GLOBAL, montré à chaque réponse et qui se peuple au fil de la séance : si votre interface sait "
                 "dessiner (Claude : UN seul artefact HTML « Tableau », mis à jour à chaque message plutôt que recréé ; ailleurs : "
                 "canvas ou HTML), dessinez des post-it carrés, légèrement inclinés, groupés en zones titrées G1, G2… (avant "
                 "« REGROUPE » : une seule zone « À trier »), avec leur numéro, ★ pour les étoiles que l'équipe donne, et un "
                 "contour épais sur ceux du dernier message ; sinon un tableau texte. COULEUR selon la nature du post-it, toujours "
                 "la même, légende en haut du tableau : jaune = idée / solution ; bleu = besoin / fonction (ce que le produit doit "
                 "faire) ; rouge = risque, problème, irritant ; violet = question ouverte ; gris = contrainte (norme, coût, délai, "
                 "masse) ; vert = décision ou acquis ; « (IA) » en pointillé. L'équipe peut corriger une couleur (« P4 est un "
                 "risque »). (4) « GÉNÈRE » seulement : traduisez les groupes retenus en artéfacts des sections envoyées (un "
                 "groupe devient le plus souvent une fonction, une brique, un risque ou une ligne de DFMEA ; un post-it, un détail "
                 "de cet élément ; la couleur guide : bleu → fonction, jaune → brique ou feuille de concept, rouge → risque ou "
                 "DFMEA, gris → contrainte) et rendez le document JSON selon les règles ci-dessous. Rien ne touche le Space avant "
                 "« GÉNÈRE » : l'équipe revoit ensuite chaque ajout, modification et retrait dans Diamond avant de l'appliquer."),
}


def _fields(sec):
    out = []
    for f in sec.fields:
        what = {"ref": "code de " + str(f.ref), "refs": "liste de codes de " + str(f.ref), "bool": "true / false", "int": "entier",
                "num": "nombre", "json": "liste JSON", "enum": "une de : " + ", ".join(repr(v) for v in (f.values or []) if v != "") + (" ou \"\"" if "" in (f.values or []) else "")
                }.get(f.kind, "texte")
        out.append("    - {}{} ({}){}".format(f.key, " [lecture seule]" if f.ro else "", what, " : " + f.note if f.note else ""))
    return "\n".join(out)


def build(rt, keys, mode, goal="", board=None):
    project = rt.ctx.conn.execute("SELECT key, name FROM projects WHERE id = ?", (rt.pid,)).fetchone()
    doc = dump(rt, keys)
    ctx = context(rt, keys)
    parts = [
        "Vous êtes l'ingénieur méthodes de l'équipe du Space {} — {}, dans Diamond (analyse fonctionnelle, briques, risques, "
        "DFMEA, industrialisation). {}".format(project["key"], project["name"], MODES[mode]),
        "Objectif de la séance : " + goal.strip() if goal and goal.strip() else "",
        RULE_FR,
        "SECTIONS ENVOYÉES",
    ]
    for key in keys:
        sec = rt.sections[key]
        parts.append("« {} » ({} élément(s)). {}\n  Champs :\n{}".format(key, len(doc[key]), sec.guide, _fields(sec)))
    parts += [
        "RÈGLES DU DOCUMENT RENDU",
        "1. Un seul bloc ```json contenant un objet {\"section\": [éléments]}, avec chaque section que vous rendez COMPLÈTE : "
        "un élément existant absent d'une section rendue est retiré du Space. Ne rendez pas une section que vous ne voulez pas toucher.",
        "2. Gardez le « code » de chaque élément existant, tel quel. Un nouvel élément n'a pas de code, ou un code temporaire qui "
        "commence par « + » (\"+F1\", \"+CB1\") si d'autres éléments doivent le pointer.",
        "3. Les liens s'écrivent avec les codes (\"parent\": \"F2\", \"functions\": [\"F3\", \"+F1\"]). Un lien vers un code qui "
        "n'existe ni dans le Space ni dans votre réponse est refusé.",
        "4. Un champ omis garde sa valeur ; une valeur vide l'efface. Les champs [lecture seule] sont ignorés.",
        "5. Les valeurs à choix : exactement une des valeurs données. Pas de champ inventé.",
        "6. Après le bloc, une courte liste de ce que vous avez changé et pourquoi (pour la revue de l'équipe).",
        "L'équipe colle votre réponse dans Diamond (« ↔ IA » → « Importer la réponse ») : elle voit chaque ajout, modification et "
        "retrait, décoche ce qu'elle refuse, puis applique — une sauvegarde du Space est prise avant.",
        "DOCUMENT ACTUEL",
        "```json\n" + json.dumps(doc, ensure_ascii=False, indent=1) + "\n```",
    ]
    if board:
        parts += ["POST-IT DE LA SÉANCE D'IDÉATION « {} » (matière première, par groupe ; I… = un post-it, ★ = étoiles de "
                  "l'équipe)".format(board["title"]),
                  "Partez de ces post-it : les groupes retenus deviennent des éléments des sections envoyées, les post-it leurs "
                  "détails ; les post-it les plus étoilés passent en premier. Ne recopiez pas ce bloc dans le JSON.",
                  board["text"]]
    if ctx:
        parts += ["CONTEXTE (lecture seule, pour les liens ; ne pas rendre)",
                  "```json\n" + json.dumps(ctx, ensure_ascii=False, indent=1) + "\n```"]
    return "\n\n".join(p for p in parts if p)
