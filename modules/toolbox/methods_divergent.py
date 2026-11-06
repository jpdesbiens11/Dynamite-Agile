"""Explanation pages and FAQ of the divergent methods of « Tools » (D-B-065,
catalogue réduit en D-B-073 : brainstorming, brainwriting 6-3-5 (storytelling retiré en 0.60.52 : Diamond → Storyline),
mind map).

Each entry becomes, in the TOOLS space (Dynamite, editable as a wiki), a
method page and its FAQ sub-page. Keys: key, name, family, tagline, tool
(view of the interactive tool, or None), goal, when, steps, roles,
pitfalls, example, faq [(question, answer)].
"""
DIVERGENT = [
    {"key": "brainstorming", "name": "Brainstorming", "family": "divergent", "tool": "ideation",
     "tagline": "Produire vite beaucoup d'idées en groupe, sans jugement.",
     "goal": "Générer un grand nombre d'idées variées sur une question précise, en s'appuyant sur les idées des "
             "autres (règles d'Alex Osborn).",
     "when": "Après avoir formulé la question (« Comment pourrions-nous… ? »), avant toute évaluation.",
     "steps": ["Afficher la question et les 4 règles : pas de critique, la quantité d'abord, les idées folles sont "
               "bienvenues, rebondir sur les idées des autres.", "Réchauffement de 2 minutes sur un sujet léger.",
               "Période de production de 15 à 30 minutes : chaque idée est notée dans l'outil Idéation, une idée par "
               "carte.", "Regrouper par thèmes (labels), puis étoiler les meilleures (★).",
               "Envoyer les meilleures idées vers une Pugh matrix."],
     "roles": "4 à 10 participants, un animateur qui fait respecter les règles, un scribe (ou chacun saisit dans "
              "l'outil).",
     "pitfalls": ["Juger pendant la production (« ça ne passera jamais la certification »).",
                  "Laisser une ou deux voix dominer : préférer alors le brainwriting.",
                  "Question trop vague (« améliorer le produit ») : la reformuler."],
     "example": "« Comment pourrions-nous éviter que la colle chaude coule sur la table quand on dépose le pistolet ? » : "
                "pied rabattable, buse qui se referme, support aimanté, réservoir de récupération…",
     "faq": [("Combien d'idées viser ?", "Au moins 50 pour 30 minutes à 6 personnes : la quantité fait émerger la "
              "qualité."), ("Et si personne ne parle ?", "Passez au brainwriting 6-3-5, silencieux et écrit."),
             ("Faut-il garder les idées rejetées ?", "Oui : la séance reste dans l'outil, avec ses auteurs ; une idée "
              "écartée aujourd'hui peut servir au tour suivant.")]},
    {"key": "brainwriting", "name": "Brainwriting 6-3-5", "family": "divergent", "tool": "ideation",
     "tagline": "6 personnes, 3 idées, 5 minutes par tour : 108 idées en 30 minutes, en silence.",
     "goal": "Produire beaucoup d'idées sans effet de groupe : chacun écrit, puis enrichit les idées des autres. Dans "
             "l'outil, les participants connectés travaillent par paires qui changent à chaque tour : on voit en "
             "direct ce que son partenaire écrit, on rebondit dessus, et le tour suivant on change de partenaire.",
     "when": "Équipes avec des profils introvertis, sujets sensibles, ou quand le brainstorming oral tourne en rond.",
     "steps": ["L'animateur crée la séance (méthode Brainwriting 6-3-5) : question, durée d'un tour (5 min), nombre "
               "de tours, idées visées par tour (3).", "Chaque participant ouvre la séance et clique « Rejoindre ».",
               "L'animateur clique « Démarrer » : l'outil forme les paires du tour 1 et lance le minuteur.",
               "Pendant le tour, chacun écrit ses idées ; les idées de son partenaire apparaissent en direct à côté "
               "des siennes : « Rebondir » sur une idée la complète ou la contredit.",
               "À la fin du temps, le tour suivant démarre seul avec de nouvelles paires (rotation « toutes rondes » : "
               "chacun rencontre chacun) ; l'animateur peut passer au tour suivant plus tôt.",
               "Après le dernier tour, la séance passe en revue : tout le monde voit toutes les idées, les étiquette, "
               "leur donne des attributs (impact, faisabilité) et met des étoiles ★ aux meilleures ; le filtre « ★ » "
               "les fait ressortir du journal.", "Envoyer les idées retenues vers une Pugh matrix."],
     "roles": "3 à 12 participants connectés (6 idéalement), un animateur qui démarre et surveille le temps.",
     "pitfalls": ["Des idées trop courtes pour être comprises par le partenaire : une phrase complète.",
                  "Juger pendant les tours : on juge en revue, avec les étoiles.",
                  "Un nombre impair de participants : l'outil forme alors un trio à chaque tour, c'est normal."],
     "example": "Chargement des bâtonnets de colle : tour 1 « trappe à ressort », tour 2 (nouveau partenaire) « trappe "
                "détrompée par la forme », tour 3 « trappe qui guide aussi le bâtonnet vers la zone de chauffe »…",
     "faq": [("Peut-on le faire à distance ?", "Oui : chacun est connecté à la plateforme ; les paires et le minuteur "
              "sont gérés par le serveur, l'écran se met à jour seul toutes les quelques secondes."),
             ("Qui voit quoi pendant les tours ?", "Chacun voit ses idées et celles de son ou ses partenaires du tour "
              "(anciens et actuels). Tout le monde voit tout à la revue."),
             ("Comment les paires changent-elles ?", "Rotation « toutes rondes » (méthode du cercle) : avec n "
              "participants, chacun rencontre chacun en n − 1 tours ; au-delà, la rotation recommence."),
             ("Pourquoi 3 idées et 5 minutes ?", "C'est l'équilibre classique ; adaptez (2 idées, 7 minutes) si le "
              "sujet est technique.")]},
    {"key": "mindmap", "name": "Mind Map", "family": "divergent", "tool": "ideation",
     "tagline": "Explorer un sujet en branches autour d'un centre.",
     "goal": "Structurer la réflexion en réseau : le sujet au centre, des branches principales, des sous-branches, "
             "et des liens transversaux entre idées.",
     "when": "Pour explorer un sujet large, préparer une analyse (analyse fonctionnelle, AMDEC) ou un plan.",
     "steps": ["Créer la séance (méthode Mind Map) : la question devient le nœud central.",
               "Double-cliquer sur la surface pour poser une carte à cet endroit (ou « Ajouter une carte »).",
               "Glisser les cartes pour les disposer ; la position est enregistrée pour tous.",
               "« Lier » une carte puis cliquer sur une autre : une ligne les relie (branche) ; cliquer sur une ligne "
               "pour la retirer.", "Étiqueter et étoiler ★ les idées clés, puis converger (Pugh)."],
     "roles": "Seul ou en groupe (tous voient la carte se construire) ; 20 à 40 minutes.",
     "pitfalls": ["Trop de texte par carte : un mot-clé ou une courte phrase.",
                  "Tout relier au centre : créez des sous-branches."],
     "example": "Centre « Fin de vie du produit » : démontage, tri des matériaux, électronique, emballage, "
                "logistique inverse… reliés entre eux (électronique ↔ logistique inverse : collecte des DEEE).",
     "faq": [("L'outil dessine-t-il la carte ?", "Oui : cartes déplaçables sur une grande surface et lignes entre elles, "
              "enregistrées sur le serveur ; tout le monde voit la même carte."),
             ("Peut-on travailler à plusieurs ?", "Oui : l'écran se met à jour toutes les quelques secondes ; une carte "
              "en cours de déplacement n'est pas dérangée.")]},
]

# D-B-073: methods taken out of the catalogue; their generated wiki pages are removed at start-up.
RETIRED = ['Analyse morphologique', 'Storytelling', "Carte d'empathie", 'Comment pourrions-nous… (How Might We)', 'Crazy 8s', 'Design thinking et double diamant', 'Prototypage rapide', 'SCAMPER']
