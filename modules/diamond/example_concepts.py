"""Diamond · the bricks of the desk-lamp example (0.60.105, D-O-117): the « Concept / Brique technologique » column -- known
bricks the team refers to, and bricks to define, one of them with three concept sheets ready for a Pugh matrix."""
from . import concept_sheets as S
from . import concepts as C

# name, initial concept (a name that speaks), kind, reference, description, functions (texts of example.LAMP)
BRICKS = [
    ("Socle lesté moulé", "Presse-papier", "existing", "Base en zamak moulée sous pression (lampes d'architecte du marché)",
     "Le poids du socle tient la lampe stable.", ["Reposer sur une base lestée"]),
    ("Bras articulé à friction", "Bras d'architecte", "existing", "Rotules à friction réglables du commerce", "La tête reste où on la place.",
     ["Orienter la tête d'éclairage"]),
    ("Alimentation 12 V et distribution", "Prise unique", "existing", "Bloc secteur 12 V certifié et régulateur de la carte",
     "L'énergie arrive par un bloc externe et se répartit sur la carte.",
     ["Utiliser un bloc d'alimentation externe 12 V", "Distribuer l'énergie aux sous-systèmes"]),
    ("Interface de commande tactile et sans fil", "Un doigt, une appli", "to_define", "", "Toucher, application mobile et mémoire du réglage dans une "
     "seule carte de commande.", ["Détecter un toucher sur le bouton", "Recevoir les commandes de l'application mobile",
                                  "Mémoriser le dernier réglage"]),
    ("Module DEL blanc réglable", "Soleil de poche", "to_define", "", "Deux canaux de DEL (blanc chaud, blanc froid) pilotés en courant.",
     ["Convertir l'électricité en lumière", "Régler l'intensité", "Régler la température de couleur"]),
    ("Gestion thermique de la tête", "Tête-radiateur", "to_define", "", "Évacuer la chaleur des DEL sans ventilateur ni surface trop chaude.",
     ["Dissiper la chaleur des DEL"]),
    ("Enveloppe isolante", "Coquille fermée", "existing", "Boîtier en polycarbonate V-0 et passe-câble", "Isole et recouvre l'électronique.",
     ["Isoler les parties sous tension", "Recouvrir les composants internes"]),
]
SHEETS = {"Gestion thermique de la tête": [
    ("Dissipateur à ailettes en aluminium", "Des ailettes extrudées au dos de la tête évacuent la chaleur par convection.",
     "Simple et bon marché ; la tête grossit."),
    ("Tête en aluminium qui fait dissipateur", "Le corps moulé de la tête est le dissipateur.",
     "Allure épurée, une pièce de moins ; moule plus coûteux."),
    ("Caloduc vers le bras", "Un caloduc mène la chaleur dans le bras, qui la rayonne.", "Tête très fine ; caloduc fragile au pliage."),
]}


def load(conn, user_id, pid, texts):
    """texts: {function text: function id} of the example just loaded."""
    for name, initial, kind, reference, description, fns in BRICKS:
        cid = C.add(conn, user_id, pid, {"name": name, "initial_name": initial, "kind": kind, "reference": reference,
                                         "description": description},
                    [texts[t] for t in fns if t in texts])
        for title, principle, cons in SHEETS.get(name, []):
            S.add(conn, user_id, pid, cid, {"title": title, "principle": principle, "cons": cons})
