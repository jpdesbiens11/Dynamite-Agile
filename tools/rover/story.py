"""Rover example: the Storyline of Diamond (0.60.52, D-O-061) -- the use of the Rover told scene by scene, from the box
to the shelf, the way the team told it at MVP 0 before drawing the functional tree. Pictogram keys: modules/diamond/story.PICTOS."""


def _i(p, x, y, s=2, t="", f=0):
    item = {"p": p, "x": x, "y": y, "s": s}
    if t:
        item["t"] = t
    if f:
        item["f"] = 1
    return item


STORY = [
    {"title": "La découverte", "caption": "Sam, en première année, reçoit le kit du Rover au laboratoire et ouvre la boîte avec la "
     "chargée de lab.", "notes": "Par où commencer ? Une feuille « Commencez ici » sur le dessus. Combien de pièces ? Est-ce que "
     "tout est là ?", "items": [_i("atelier", 82, 45, 3), _i("adulte", 22, 55, 3, "Sam"), _i("technicien", 40, 55, 3, "Chargée de lab", 1),
                                _i("colis", 62, 70, 2, "Le kit"), _i("question", 30, 18, 1)]},
    {"title": "L'assemblage", "caption": "Sam monte le Raspberry Pi, les capteurs et la batterie sur le châssis en suivant la notice, "
     "en deux soirées.", "notes": "Les vis se perdent. Le câblage doit être impossible à inverser. Combien de temps ? Viser moins de "
     "4 heures.", "items": [_i("adulte", 15, 55, 3, "Sam"), _i("outil", 35, 60, 2), _i("notice", 55, 65, 2, "Notice"),
                            _i("produit", 75, 62, 2, "Châssis"), _i("batterie", 88, 75, 1), _i("horloge", 82, 20, 1, "2 soirées")]},
    {"title": "La première connexion", "caption": "Sam allume le Rover et ouvre l'application sur son téléphone : il faut trouver "
     "le réseau du Rover et le démarrer.", "notes": "Le téléphone ne trouve pas le Rover tout de suite. Un voyant qui dit « prêt » ? "
     "Pas de compte à créer.", "items": [_i("adulte", 18, 55, 3, "Sam"), _i("telephone", 38, 50, 2, "Application"),
                                         _i("produit", 72, 62, 2, "Rover"), _i("frustre", 30, 18, 1), _i("idee", 58, 22, 1, "Voyant")]},
    {"title": "Le premier parcours", "caption": "Dans le corridor, le Rover roule lentement, ralentit devant le mur et tourne. "
     "Les autres étudiants regardent.", "notes": "Il faut qu'il soit lent et prévisible. Voir sur le téléphone ce qu'il « voit ». "
     "Bouton d'arrêt toujours visible.", "items": [_i("groupe", 15, 55, 3, "Étudiants"), _i("produit", 45, 62, 2, "Rover"),
                                                   _i("mouvement", 65, 62, 2), _i("telephone", 30, 30, 1), _i("content", 50, 20, 1)]},
    {"title": "L'obstacle", "caption": "Une chaise et une marche : le Rover s'arrête, recule un peu et contourne lentement par la "
     "droite.", "notes": "Et s'il ne voit pas une patte de chaise mince ? Pare-chocs en dernier recours. La marche : il ne doit "
     "jamais tomber. Poussière sur les capteurs.", "items": [_i("produit", 30, 62, 2, "Rover"), _i("danger", 62, 55, 2, "Marche"),
                                                             _i("bureau", 82, 55, 2, "Chaise"), _i("poussiere", 45, 82, 1),
                                                             _i("question", 22, 20, 1)]},
    {"title": "La pile faible", "caption": "Après 40 minutes, le Rover ralentit ; l'application avertit que la batterie est faible "
     "et Sam le recharge.", "notes": "Prévenir avant qu'il s'arrête au milieu du corridor. Recharge simple, sans retirer la batterie ? "
     "Ne jamais charger sans surveillance.", "items": [_i("batterie", 30, 55, 3, "Batterie faible"), _i("horloge", 55, 25, 1, "40 min"),
                                                       _i("telephone", 55, 60, 2), _i("prise", 80, 60, 2), _i("frustre", 15, 20, 1)]},
    {"title": "La démo et le rangement", "caption": "Le jour de la démo, l'équipe montre le parcours à la classe, puis range le Rover "
     "dans sa boîte pour la cohorte suivante.", "notes": "Fier de le montrer : une coque soignée. Rangement sans démonter. La "
     "cohorte suivante doit pouvoir le reprendre.", "items": [_i("groupe", 18, 55, 3, "Équipe"), _i("produit", 45, 62, 2, "Rover"),
                                                               _i("coeur", 32, 18, 1), _i("colis", 75, 65, 2, "Boîte"),
                                                               _i("mouvement", 60, 62, 1)]},
]
