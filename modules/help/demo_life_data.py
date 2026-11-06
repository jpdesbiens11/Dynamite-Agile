"""The Rover in DEMO, at week 15 of 15 (0.60.54, D-O-063): the facts that make the example a project in motion -- who did
what, when, in which sprint, what was said, what changed, what was tested and how many hours it took. Content only;
demo_life.py applies it. Weeks count from 1 (the first week of the project); days from 0 (Monday) to 4 (Friday).
"""

# The team of rover.json, as inactive accounts: they carry the work and the hours, nobody can sign in with them.
TEAM = ("nina", "lea", "hugo", "alexis")
LEAD = "nina"
WEEKS = 15
NOW_WEEK = 15

# (name, goal, first week, last week, refs of the backlog of rover.json); the last one is the active sprint
SPRINTS = [
    ("Sprint 1", "MVP 0 : entrevues, Lean Canvas, kits de référence", 1, 2, ("S1", "S2", "S3", "S4")),
    ("Sprint 2", "MVP 0 : magicien d'Oz et bilan ; début de l'analyse fonctionnelle", 3, 4, ("S5", "T1", "S6", "S7")),
    ("Sprint 3", "MVP 1 : concepts, Pugh et Kepner-Tregoe ; Pi en point d'accès", 5, 6, ("S8", "S9", "S10", "S11")),
    ("Sprint 4", "MVP 1 démontré ; MVP 2 : plaque, alimentation, PDR", 7, 8, ("S12", "T2", "S13", "S14", "T3")),
    ("Sprint 5", "MVP 2 : capteurs, carte locale, approche lente, arrêts", 9, 10, ("S15", "S16", "S17", "B1", "S18")),
    ("Sprint 6", "MVP 2 complet : télémétrie, boîtier, DFMEA, CDR", 11, 12, ("S19", "S20", "S21", "B2", "T4", "S26")),
    ("Sprint 7", "MVP 3 : validation, pré-conformité, notice, décision de lancement", 13, 15, ("S22", "S23", "S24", "S25", "B3", "T5")),
]
# versions: (name, week of release, released)
VERSIONS = [("MVP0", 3, True), ("MVP1", 7, True), ("MVP2", 12, True), ("MVP3", 15, False)]
# where the tickets of the active sprint stand today (the others of a closed sprint are Done)
OPEN = {"S23": "In Review", "S25": "In Progress", "T5": "In Progress"}
EPICS_OPEN = ("E3",)

# (ref, author, week, day, text); a comment answers the previous one of the same ticket when it starts with « ↳ »
COMMENTS = [
    ("S1", "hugo", 1, 3, "12 entrevues faites : 9 étudiants sur 12 parlent d'abord d'« éviter les obstacles ». Notes dans le wiki (A. Discovery)."),
    ("S3", "lea", 2, 1, "Les kits du commerce coûtent 180 à 420 $ ; aucun n'a de temps de vol ni d'arrêt si le Wi-Fi tombe. Tableau comparatif dans le wiki."),
    ("S5", "alexis", 3, 2, "Magicien d'Oz : les gens trouvent « lent » sous 0,4 m/s et « trop près » sous 25 cm. On garde 30 cm pour l'arrêt."),
    ("T1", "nina", 3, 4, "Décision : on persévère. Le problème existe, le prix cible est crédible. Hypothèse suivante : le concept plaît-il ?"),
    ("S9", "nina", 5, 3, "Pugh : le concept C (3 ultrasons + temps de vol) gagne de 4 points. Kepner-Tregoe confirme contre B, risque soleil noté."),
    ("S10", "alexis", 6, 1, "Point d'accès « ROVER-01 » et page Avancer / Arrêter : 180 ms de latence au pire sur 4 téléphones."),
    ("S10", "hugo", 6, 2, "↳ Le bouton Arrêter doit rester visible même quand on fait défiler la page, c'est ce que les testeurs ont demandé."),
    ("S12", "hugo", 7, 3, "Démo à 10 étudiants : 8 voudraient le monter eux-mêmes. Concept Review passée, deux remarques sur le coût."),
    ("S14", "lea", 8, 2, "INA219 en place ; la coupure de traction s'ouvre en 6 ms sur l'arrêt d'urgence matériel."),
    ("B1", "lea", 9, 1, "Reproduit : le 5 V tombe à 4,4 V au démarrage du moteur, le Pi redémarre. Voir le PR et l'ECN dans Change Management."),
    ("B1", "nina", 9, 2, "↳ OK pour la rampe de 0,5 s et le condensateur de 1 000 µF ; Léa met à jour le schéma et la nomenclature."),
    ("S16", "alexis", 10, 3, "Loi d'approche : 1,0 m/s au-delà de 1,5 m, 0,3 m/s sous 0,5 m, arrêt à 0,30 m. Courbe dans le wiki."),
    ("B2", "alexis", 11, 2, "Hystérésis de 10 cm et côté gardé 2 s : plus d'oscillation sur 20 approches du mur."),
    ("T4", "nina", 12, 4, "CDR passée : design figé, nomenclature à 212 $, plan d'essais TP de validation prêt."),
    ("B3", "lea", 13, 2, "Le temps de vol sature au soleil sur le parcours C (2 essais sur 3). Mode courte portée + filtre de plausibilité : 3 / 3."),
    ("S23", "lea", 14, 3, "Pré-balayage : 4 dB de marge à 120 MHz au lieu de 6. Ferrite sur le câble moteur ; à confirmer au laboratoire."),
    ("S25", "alexis", 14, 4, "L'équipe 3 a remonté le MVP 2 avec le wiki en 3 h 40. Deux étapes de la notice à clarifier (photos)."),
    ("T5", "nina", 15, 1, "Validation Report en relecture. Décision proposée : lancer le kit, action ouverte sur la CEM."),
]
# (source ref, target, link type); a target « REQ-n » is the requirement of Goldmine with that external id
LINKS = [("S16", "S17", "blocks"), ("S11", "S16", "relates"), ("B1", "S14", "relates"), ("B2", "S17", "relates"),
         ("B3", "S22", "relates"), ("S11", "REQ-2", "implements"), ("S16", "REQ-3", "implements"), ("S17", "REQ-4", "implements"),
         ("S18", "REQ-6", "implements"), ("S18", "REQ-7", "implements"), ("S14", "REQ-19", "implements"),
         ("S19", "REQ-9", "implements"), ("S10", "REQ-5", "implements"), ("S26", "REQ-12", "implements")]

# Change Management: problem reports derived into ECNs. week = when the PR was opened.
CHANGES = [
    {"pr": {"title": "Le Pi redémarre au démarrage du moteur (chute du 5 V)", "week": 9, "by": "lea", "status": "Derived to ECN",
            "fields": {"severity": "majeure", "detected_in": "essai", "item_ref": "Carte d'alimentation", "found_version": "MVP2",
                       "containment": "Démarrer le moteur seulement par l'application, rampe logicielle de 0,5 s en attendant le correctif.",
                       "root_cause": "Appel de courant du moteur au démarrage : le régulateur 5 V décroche sous 4,6 V."}, "relates": "B1"},
     "ecn": {"title": "Rampe moteur de 0,5 s et condensateur de 1 000 µF sur le 5 V", "week": 9, "by": "lea", "status": "Closed",
             "fields": {"change_class": "mineur", "reason": "correctif", "impact_fff": 0, "impact_safety": 1,
                        "impact_notes": "Le Pi ne redémarre plus ; l'arrêt d'urgence reste matériel.", "effectivity": "Tous les robots dès le MVP 2"},
             "items": [("plan", "SCH-ALIM", "Schéma de l'alimentation", "A", "B", "na"),
                       ("piece", "C-1000UF", "Condensateur 1 000 µF 16 V", "", "A", "na"),
                       ("logiciel", "rover-drive", "Pilote de traction (rampe)", "0.3", "0.4", "na")],
             "tasks": [("Modifier le schéma et la nomenclature", "lea", "Done"), ("Rampe de 0,5 s dans le pilote de traction", "alexis", "Done"),
                       ("Refaire l'essai des arrêts d'urgence", "lea", "Done")]}},
    {"pr": {"title": "Marge CEM de 4 dB à 120 MHz au pré-balayage", "week": 14, "by": "lea", "status": "Derived to ECN",
            "fields": {"severity": "mineure", "detected_in": "essai", "item_ref": "Câble moteur", "found_version": "MVP3",
                       "containment": "Pas de vente avant l'essai au laboratoire reconnu.",
                       "root_cause": "Le câble du moteur rayonne les commutations du variateur."}, "relates": "S23"},
     "ecn": {"title": "Ferrite sur le câble moteur", "week": 14, "by": "lea", "status": "In Implementation",
             "fields": {"change_class": "mineur", "reason": "securite", "impact_fff": 0, "impact_certification": 1,
                        "impact_notes": "À confirmer par l'essai CEM au laboratoire reconnu.", "effectivity": "Kits pour les écoles"},
             "items": [("piece", "FER-7MM", "Ferrite à clipser 7 mm", "", "A", "na"),
                       ("document", "NOTICE", "Notice de montage, étape 4", "A", "B", "na")],
             "tasks": [("Ajouter la ferrite à la nomenclature", "nina", "Done"), ("Photo de la ferrite dans la notice", "hugo", "In Progress"),
                       ("Essai CEM au laboratoire reconnu", "lea", "To Do")]}},
]

# Goldmine: where each requirement stands (external id -> status); the others are « Implemented »
REQ_STATUS = {"REQ-1": "Verified", "REQ-2": "Verified", "REQ-3": "Verified", "REQ-4": "Verified", "REQ-6": "Verified",
              "REQ-7": "Verified", "REQ-8": "Verified", "REQ-10": "Verified", "REQ-12": "Verified", "REQ-19": "Verified",
              "REQ-14": "In Verification", "REQ-15": "In Verification", "REQ-24": "In Verification", "REQ-18": "Allocated"}
REQ_DEFAULT = "Implemented"
NEED_STATUS = {"BES-1": "confirmed", "BES-2": "confirmed", "BES-3": "confirmed", "BES-4": "contractual", "BES-5": "contractual",
               "BES-8": "contractual"}
# Q&R with the client (the teacher): (requirement, asked by, week, question, answer or "", week answered, status, owner, blocking)
QA = [
    ("REQ-12", "nina", 2, "Le 250 $ comprend-il la batterie et le chargeur ?", "Oui : tout ce qui est dans la boîte, sans le téléphone.", 2, "closed", "", 0),
    ("REQ-10", "alexis", 6, "Quelle hauteur de marche le robot doit-il franchir dehors ?", "3 cm, la bordure du trottoir devant l'atelier.", 7, "closed", "", 0),
    ("REQ-8", "lea", 8, "Les 30 minutes se mesurent-elles sur le parcours A ou en ligne droite ?", "Sur le parcours A, à vitesse normale.", 8, "closed", "", 0),
    ("REQ-14", "lea", 14, "Quel laboratoire CEM l'école accepte-t-elle pour l'essai final ?", "", None, "open", "lea", 1),
]

# Testing: (title, location, test titles, status, week sent, week of results)
PLANS = [
    ("Rover — banc et sécurité (MVP 2)", "LAB",
     ("Couverture des capteurs (banc)", "Détection des obstacles — 200 essais", "Arrêt avant contact — 50 approches",
      "Arrêts d'urgence", "Perte de liaison — chien de garde", "Démarrage jusqu'à « Prêt »"), "closed", 11, 12),
    ("Rover — parcours A, B, C et robustesse (MVP 3)", "ATELIER",
     ("Vitesse selon la distance", "Contournement sur le parcours B", "Autonomie sur le parcours A", "Terrain : gazon, gravier, trottoir, marche",
      "Application sur quatre téléphones", "Chutes de 0,5 m", "Éclaboussures IPX4", "Échauffement du boîtier électronique",
      "Doigt d'essai sur les pièces mobiles", "Remplacement des modules", "Reprise par une autre équipe", "Coût de la nomenclature"),
     "results", 13, 14),
    ("Rover — pré-conformité CEM et dossier", "EXT", ("Pré-balayage des émissions rayonnées", "Dossier radio, batterie et RoHS"), "sent", 14, None),
]
# results printed in the PDF of a plan: test title -> (result, verdict)
RESULTS = {
    "Couverture des capteurs (banc)": ("Aucune zone aveugle de 0,05 à 2 m devant", "Réussi"),
    "Détection des obstacles — 200 essais": ("97 % (194 / 200)", "Réussi"),
    "Arrêt avant contact — 50 approches": ("0 contact sur 50", "Réussi"),
    "Arrêts d'urgence": ("0,06 s au pire", "Réussi"),
    "Perte de liaison — chien de garde": ("0,34 s au pire", "Réussi"),
    "Démarrage jusqu'à « Prêt »": ("41 s", "Réussi"),
    "Vitesse selon la distance": ("écart de 6 % au pire", "Réussi"),
    "Contournement sur le parcours B": ("9 / 10, 11° au pire", "Réussi"),
    "Autonomie sur le parcours A": ("41 min, coupure à 6,81 V", "Réussi"),
    "Terrain : gazon, gravier, trottoir, marche": ("2 / 3, puis 3 / 3 après le correctif du temps de vol", "Réussi"),
    "Application sur quatre téléphones": ("4 / 4", "Réussi"),
    "Chutes de 0,5 m": ("6 chutes, aucun dommage", "Réussi"),
    "Éclaboussures IPX4": ("Aucune trace d'eau dans le boîtier", "Réussi"),
    "Échauffement du boîtier électronique": ("+18 °C après 40 min", "Réussi"),
    "Doigt d'essai sur les pièces mobiles": ("Aucune pièce en mouvement accessible", "Réussi"),
    "Remplacement des modules": ("Capteur remplacé en 6 min", "Réussi"),
    "Reprise par une autre équipe": ("MVP 2 remonté en 3 h 40", "Réussi"),
    "Coût de la nomenclature": ("212 $", "Réussi"),
}

# Exploration: where the Rover's plan stands (code -> (status, progress)); the steps before D-20 are done
PLAN_OPEN = {"D-20": ("doing", 80), "D-21": ("doing", 60), "VVR": ("todo", 0)}

# Timesheet: (person, first week, last week, [(code, hours, day, what)])
HOURS = [
    ("nina", 1, 3, [("A-03", 4, 1, "Lean Canvas et hypothèses"), ("A-06", 3, 3, "Hypothèses risquées et registre des risques")]),
    ("lea", 1, 3, [("A-01", 3, 1, "Étude des kits de référence"), ("A-05", 4, 3, "Pré-faisabilité : alimentation et capteurs")]),
    ("hugo", 1, 3, [("A-01", 4, 1, "Entrevues étudiants et enseignants"), ("A-05", 3, 3, "Maquette papier de l'application")]),
    ("alexis", 1, 3, [("A-05", 4, 1, "Magicien d'Oz : préparation et essais"), ("A-01", 2, 3, "Synthèse des entrevues")]),
    ("nina", 4, 7, [("B-09", 4, 1, "Arbre fonctionnel (Diamond)"), ("B-12", 4, 3, "Pugh et Kepner-Tregoe")]),
    ("lea", 4, 7, [("B-11", 4, 1, "CdCF : requirements et niveaux (Goldmine)"), ("B-12", 3, 3, "Un ultrason : arrêt sous 30 cm")]),
    ("hugo", 4, 7, [("B-08", 3, 1, "Besoins des étudiants"), ("B-12", 4, 3, "Idéation et matrice morphologique")]),
    ("alexis", 4, 7, [("B-10", 3, 1, "Structure fonctionnelle"), ("B-12", 5, 3, "Pi en point d'accès et page web")]),
    ("nina", 8, 12, [("C-14", 3, 1, "PDR : architecture et calculs"), ("C-15", 5, 3, "Plaque porte-modules, DFMEA")]),
    ("lea", 8, 12, [("C-14", 3, 1, "Alimentation et coupure de traction"), ("C-15", 5, 3, "Chien de garde et arrêt d'urgence")]),
    ("hugo", 8, 12, [("C-15", 5, 1, "Boîtier et pare-chocs imprimés"), ("C-15", 3, 3, "Télémétrie et vue radar")]),
    ("alexis", 8, 12, [("C-15", 5, 1, "Pilotes des capteurs et carte locale"), ("C-15", 4, 3, "Approche lente et contournement")]),
    ("nina", 13, 15, [("D-19", 2, 0, "Bilan du MVP 2"), ("D-21", 5, 2, "Validation Report et décision")]),
    ("lea", 13, 15, [("D-21", 5, 1, "Essais de validation du Test Plan"), ("D-20", 3, 3, "Pré-balayage CEM et dossier")]),
    ("hugo", 13, 15, [("D-FAB", 4, 1, "Fabrication des boîtiers du kit"), ("D-20", 3, 3, "Notice de montage")]),
    ("alexis", 13, 15, [("D-21", 4, 1, "Parcours A, B et C"), ("D-20", 3, 3, "Reprise par une autre équipe")]),
]
APPROVED_UNTIL = 13  # weeks 1-13 approved, 14 submitted, 15 in draft (this week)
