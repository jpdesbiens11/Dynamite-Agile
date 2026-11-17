"""The process side of the Rover in DEMO (0.60.103, D-O-113 to D-O-115), as on pages 12 to 16 of the presentation « Les
caractéristiques spéciales »: content only, demo_process.py applies it.

Two line configurations: the pilot line of the school workshop (OP10 to OP70, the one of the presentation) and the
prototype cell (one bench, prototypes P1 to P3). A characteristic is named by its number (14 = C-14), a part by its
Diamond number (21 = P-21), an account by its demo name (« nina »); dates are absolute, after the CDR of the Rover.
"""

# (number, name, description, [(op, name, description, equipment (one per line), traceability,
#   [(characteristic or None, label, method, frequency)])])
LINES = [
    (1, "Ligne pilote — kits Rover", "Montage des kits Rover à l'atelier de l'école : 7 postes, un robot à la fois, le n° de série posé à "
     "l'OP70 relie chaque robot aux résultats de ses CC.", [
         (10, "Réception des pièces", "Contrôle des lots avant mise en stock.", "Pied à coulisse\nJauge de rayon", 0, [
             (21, "", "Comparateur sur montage, carte X̄-R", "5 pièces par lot"),
             (20, "", "Jauge de rayon", "3 pièces par lot"),
             (None, "Certificat du lot INA219", "Revue du certificat du fabricant", "chaque lot")]),
         (20, "Chassis, transmission, bumper", "Transmission, roues, pinion motor, bumper et ses microswitches.",
          "Visseuse à couple contrôlé\nGabarit de course du bumper", 0, [
              (16, "", "Jauge de course", "100 %"),
              (17, "", "Visseuse bloquante, couple enregistré", "chaque vis")]),
         (30, "Sensor Hall et aimant", "Pose du support, de l'aimant sur l'arbre et réglage de l'entrefer.", "Gabarit d'entrefer G-30 avec cale de 2,0 mm",
          0, [(14, "", "Poka-yoke + carte X̄-R", "5 par heure")]),
         (40, "Enclosure, joint, Raspberry Pi", "Pose du joint, du Raspberry Pi et fermeture de l'enclosure.", "Outil de pose du joint", 0, [
             (None, "Sealing de l'enclosure", "Contrôle visuel du joint", "1 par heure")]),
         (50, "Wiring et coupure", "Wiring de l'emergency stop et de la coupure de traction.", "Cut-off bench B-50 avec oscilloscope", 0, [
             (8, "", "Essai de coupure", "100 %")]),
         (60, "Calibration, essai final", "Image du software, calibration du seuil de la battery, essai d'arrêt.",
          "Bench B-60 et alimentation de référence", 0, [
              (10, "", "Référence étalonnée, SPC", "100 % · Cpk 5 par jour"),
              (5, "", "Stop bench, temps de boucle", "100 %")]),
         (70, "Emballage, traceability", "Étiquette du n° de série, enregistrement des résultats, mise en boîte.", "Imprimante d'étiquettes", 1, [
             (None, "N° de série ↔ résultats CC", "Lecture du code, enregistrement", "100 %")]),
     ]),
    (2, "Cellule prototypes", "Les prototypes P1 à P3, montés sur un seul établi avant la ligne pilote : mêmes CC, moyens de laboratoire.", [
        (10, "Montage complet", "Mécanique et électronique sur le même établi.", "Établi ESD\nTournevis dynamométrique", 0, [
            (14, "", "Cale de 2,0 mm, réglage à la main", "chaque prototype")]),
        (20, "Calibration et essais", "Seuil de la battery, coupure, temps de boucle.", "Laboratory power supply\nCamera 240 images/s", 0, [
            (10, "", "Multimeter étalonné", "chaque prototype"),
            (8, "", "Vidéo de l'essai de coupure", "chaque prototype"),
            (5, "", "Journal du software", "chaque prototype")]),
        (30, "Identification", "N° de prototype et fiche de résultats.", "Étiquette manuscrite", 1, [
            (None, "N° de prototype ↔ fiche de résultats", "Fiche du prototype", "chaque prototype")]),
    ]),
]

# The accounts that see the process side (Diamond → Procédés → Accès); Alexis, on the software, does not need it.
ACCESS = ("nina", "lea", "hugo")

# PFMEA of the pilot line, in the order of the operations: (op, characteristic or None, process step, process characteristic,
# failure mode, effect, cause, 5M, prevention, detection control, S (None: inherited from the DFMEA), O, D, action, owner, due,
# state, source). PF-30.1 to PF-60.3 came from the AI and were accepted after review; PF-70.1 waits in draft.
PFMEA = [
    (10, 21, "Contrôler la gorge de l'enclosure", "Échantillonnage du lot", "Lot hors tolérance accepté", "Eau sur le Raspberry Pi",
     "Comparateur non vérifié", "measurement", "Comparateur vérifié chaque semaine", "Carte X̄-R, 5 pièces par lot", None, 3, 4,
     "", None, "", "accepted", "manual"),
    (10, 20, "Contrôler le rayon des coins de la plaque", "Rayon des coins", "Coin vif non détecté", "Plaque fissurée",
     "Jauge de rayon non utilisée", "man", "Liste de contrôle de réception", "Jauge de rayon, 3 pièces par lot", None, 3, 5,
     "Étude de capabilité du rayon", "hugo", "2027-03-15", "accepted", "manual"),
    (20, None, "Monter la transmission", "Graissage du différentiel", "Transmission montée sans graisse", "Bruit, usure rapide",
     "Étape oubliée", "method", "Instruction au poste avec photo", "Rotation à la main, 100 %", 4, 3, 6, "", None, "", "accepted", "manual"),
    (20, None, "Monter les roues", "Serrage des écrous de roue", "Écrou de roue desserré", "Roue perdue en marche", "Clé non utilisée",
     "man", "Torque wrench au poste", "Liste de contrôle du poste", 5, 3, 5, "", None, "", "accepted", "manual"),
    (20, 16, "Monter le bumper et ses microswitches", "Position du microswitch", "Course hors 1,0 ± 0,2 mm", "Contact non détecté",
     "Microswitch mal positionné sur son support", "method", "Instruction au poste avec photo", "Essai au doigt, 100 %", None, 4, 6,
     "Gabarit de course du bumper", "nina", "2027-05-15", "accepted", "manual"),
    (20, 17, "Visser le pinion motor", "Couple 0,6 N·m ± 10 %", "Couple trop faible", "Pinion qui saute", "Visseuse déréglée", "machine",
     "Réglage au démarrage", "Couple enregistré", None, 4, 5, "", None, "", "accepted", "manual"),
    (30, 14, "Poser le sensor à l'entrefer", "Hauteur de cale, serrage", "Entrefer > 2,3 mm", "Impulsions manquées : vitesse et distance fausses",
     "Cale oubliée", "man", "Instruction au poste", "Jauge go/no-go", None, 5, 6, "Gabarit qui refuse la pose sans cale", "nina",
     "2026-12-18", "accepted", "ai"),
    (30, 14, "Régler l'entrefer", "Jeu du support sur sa semelle", "Entrefer dispersé : Cpk 1,21 pour 1,33 exigé",
     "Impulsions manquées : vitesse et distance fausses", "Tolérances empilées du support imprimé et de l'arbre", "material",
     "Cale de 2,0 mm", "Carte X̄-R, 5 par heure", None, 5, 4, "Support d'entrefer réglable, nouvelle étude de capabilité", "nina",
     "2027-02-15", "accepted", "ai"),
    (40, 21, "Poser le joint de l'enclosure", "Position du joint", "Joint vrillé, peu comprimé", "Eau sur le Raspberry Pi", "Pose sans guide",
     "method", "Aucune", "Visuel, 1 par heure", None, 4, 7, "Outil de pose du joint", "nina", "2027-03-01", "accepted", "ai"),
    (50, 8, "Câbler l'emergency stop", "Sens du connector", "Contacts NO / NC inversés", "La traction n'est pas coupée",
     "Connector non détrompé", "material", "Connector détrompé", "Cut-off bench, 100 %", None, 3, 2, "", None, "", "accepted", "ai"),
    (60, 10, "Étalonner la mesure de voltage", "Gain de calibration", "Seuil décalé de +0,05 V", "Décharge profonde de la battery",
     "Référence non étalonnée", "measurement", "Calibration annuel", "Essai à 3,40 V, 100 %", None, 4, 4,
     "Référence étalonnée, vérification quotidienne", "lea", "2027-04-30", "accepted", "ai"),
    (60, None, "Charger l'image du software", "Version RVR-SW-001", "Version périmée chargée", "Comportement d'arrêt non validé",
     "Image copiée d'une ancienne carte", "method", "Une seule image signée sur le serveur", "Version lue par le bench, 100 %", 8, 2, 2,
     "", None, "", "accepted", "manual"),
    (60, 5, "Essai final du temps de boucle", "Réglage du stop bench", "Temps de boucle > 50 ms non détecté", "Arrêt trop tardif",
     "Stop bench mal réglé", "machine", "Vérification du bench avec un robot étalon chaque matin", "Stop bench, 100 %, journalisé", None,
     2, 3, "", None, "", "accepted", "ai"),
    (70, None, "Étiqueter le robot et relier ses résultats", "Correspondance n° de série ↔ robot", "Étiquette collée sur le mauvais robot",
     "Rappel impossible jusqu'au dernier bon contrôle", "Deux robots au poste en même temps", "method", "Un seul robot au poste",
     "Lecture du code et comparaison au bench OP60", 8, 3, 3, "", None, "", "draft", "ai"),
]
# The PFMEA row whose action is followed in Agile (op, failure mode starts with): the Cpk of C-14 under the required one.
TRACKED = (30, "Entrefer dispersé")

# Control plans: (title, scope, line number or None, phase, revision, [(op or part number, characteristic or None, label,
#   equipment, technique, sample, frequency, control method, reaction plan)])
PLANS = [
    ("Pièces à la réception", "reception", None, "prelaunch", "B", [
        (7, None, "Conformité du lot — essais de transport UN 38.3", "", "Revue du certificat", "1", "par lot", "Registre de réception",
         "Lot en attente du certificat"),
        (9, None, "Conformité du lot — certificat du fabricant", "", "Revue du certificat", "1", "par lot", "Registre de réception",
         "Lot en attente du certificat"),
        (19, None, "Verrouillage du bouton d'arrêt", "", "Essai manuel", "5 pièces", "par lot", "Liste de contrôle",
         "Lot bloqué, retour au fournisseur"),
        (21, 21, "", "Comparateur sur montage", "Comparateur", "5 pièces", "par lot", "Carte X̄-R", "Lot bloqué, tri 100 %, avis au fournisseur"),
        (20, 20, "", "", "Jauge de rayon", "3 pièces", "par lot", "Liste de contrôle", "Lot bloqué, retour au fournisseur"),
    ]),
    ("Ligne pilote — étapes d'assembly", "assembly", 1, "prelaunch", "B", [
        (20, None, "Jeu de la transmission", "", "Rotation à la main", "100 %", "chaque robot", "Liste de contrôle du poste", "Démonter, regraisser"),
        (20, None, "Serrage des écrous de roue", "Torque wrench", "Clé à déclic", "100 %", "chaque roue", "Liste de contrôle du poste",
         "Resserrer, signaler au chef d'équipe"),
        (20, 16, "", "Gabarit de course", "Jauge de course", "100 %", "chaque robot", "Jauge go/no-go", "Régler le microswitch, contrôler à nouveau"),
        (20, 17, "", "Visseuse à couple contrôlé", "Sensor de la visseuse", "100 %", "chaque vis", "Visseuse bloquante", "Desserrer, revisser, signaler"),
        (30, 14, "", "Gabarit G-30, cale 2,0", "Jauge go/no-go, cale", "100 %", "5 par heure", "Poka-yoke + X̄-R",
         "Arrêt du poste, revoir les 5 dernières poses"),
        (40, None, "Position du joint", "Outil de pose du joint", "Contrôle visuel", "1", "par heure", "Liste de contrôle du poste",
         "Reposer le joint, revoir les robots depuis le dernier contrôle"),
        (50, 8, "", "Bench B-50", "Oscilloscope du bench", "100 %", "chaque robot", "Essai automatique lié au n° de série",
         "Rebut, 8D, quarantaine du lot"),
        (60, None, "Version du software", "Bench B-60", "Lecture par le bench", "100 %", "chaque robot", "Bench bloquant", "Recharger l'image signée"),
        (60, 10, "", "Bench B-60, référence", "Référence étalonnée", "100 % · Cpk", "5 par jour", "SPC + enregistrement",
         "Arrêt, ré-étalonner, rappel depuis le dernier bon contrôle"),
        (60, 5, "", "Stop bench", "Stop bench chronométré", "100 %", "chaque robot", "Essai automatique lié au n° de série",
         "Rebut, analyse du journal, rappel depuis le dernier bon contrôle"),
        (70, None, "N° de série ↔ résultats CC", "Imprimante d'étiquettes", "Lecture du code", "100 %", "chaque robot", "Enregistrement automatique",
         "Robot bloqué jusqu'à la correspondance"),
    ]),
    ("Cellule prototypes", "assembly", 2, "prototype", "A", [
        (10, 14, "", "Établi, cale 2,0 mm", "Cale d'épaisseur", "100 %", "chaque prototype", "Fiche du prototype", "Régler, noter la valeur"),
        (20, 10, "", "Laboratory power supply", "Multimeter étalonné", "100 %", "chaque prototype", "Fiche du prototype",
         "Ré-étalonner, refaire l'essai, noter"),
        (20, 8, "", "Camera 240 images/s", "Vidéo de l'essai", "100 %", "chaque prototype", "Fiche du prototype",
         "Prototype arrêté, analyse avant tout autre essai"),
        (20, 5, "", "Stop bench du labo", "Journal du software", "100 %", "chaque prototype", "Fiche du prototype",
         "Prototype arrêté, analyse du journal"),
    ]),
]

# Measurements: characteristic -> (who, source, first date, values per day, sample label « {n} », values). Cpk (σ = MR̄ / 1,128):
# C-10 1,82 (capable, 1,67 required), C-14 1,21 (under 1,33: PF-30.2 and its ticket), C-21 1,47 (capable).
MEASURES = {
    10: ("lea", "csv", "2026-11-02", 6, "INA219 board n° {}", [
        3.404, 3.397, 3.401, 3.393, 3.4, 3.405, 3.406, 3.396, 3.398, 3.399, 3.391, 3.406, 3.402, 3.402, 3.403, 3.399, 3.401, 3.403, 3.402,
        3.398, 3.396, 3.402, 3.401, 3.396, 3.404, 3.402, 3.401, 3.4, 3.402, 3.405]),
    14: ("nina", "manual", "2026-11-09", 10, "Montage d'essai G-30, pose {}", [
        2.07, 2.03, 2.28, 2.08, 2.05, 2.07, 2.0, 1.99, 2.08, 2.01, 2.1, 2.03, 1.92, 1.95, 1.98, 1.9, 2.03, 2.02, 2.1, 1.98, 2.02, 2.08, 2.09,
        1.97, 2.15, 2.0, 2.12, 2.02, 2.01, 1.95]),
    21: ("nina", "manual", "2026-10-27", 30, "Lot 1 des enclosures, pièce {}", [
        1.508, 1.504, 1.494, 1.512, 1.507, 1.507, 1.506, 1.519, 1.513, 1.516, 1.501, 1.5, 1.495, 1.502, 1.479, 1.519, 1.505, 1.505, 1.512,
        1.501, 1.507, 1.512, 1.489, 1.521, 1.506, 1.51, 1.494, 1.498, 1.52, 1.499]),
}

# Waves tied to the milestones, and the actions placed in them: ("dfmea", characteristic of the row) or ("pfmea", op, failure mode
# starts with). PF-60.1 (AP High) sits in wave 3 on purpose: page 16 of the presentation -- the « AP High » filter shows the
# planning error, one drag brings it back to wave 1 and its date follows.
WAVES = [
    ("Vague 1 — avant le prototype", "2026-12-18", [("dfmea", 8), ("dfmea", 14), ("pfmea", 30, "Entrefer > 2,3")]),
    ("Vague 2 — avant la pré-série", "2027-03-31", [("dfmea", 10), ("pfmea", 30, "Entrefer dispersé"), ("pfmea", 40, "Joint vrillé"),
                                                    ("pfmea", 10, "Coin vif")]),
    ("Vague 3 — avant la production", "2027-06-30", [("pfmea", 60, "Seuil décalé"), ("pfmea", 20, "Course hors")]),
]
