"""Rover example: the project, the team, the needs and requirements (Goldmine) and the Test Base (Testing).
Needs BES-n come from the MVP 0 interviews; requirements REQ-n are derived from them (CdCF of phase B) and each one is
proven by a test ESSAI-n. Prices are indicative (2026, Canadian dollars) and to be checked by the team."""

PROJECT = {
    "key": "ROVER", "name": "Rover — véhicule autonome d'apprentissage",
    "description": "Petit véhicule autonome bâti sur le châssis d'une auto téléguidée tout-terrain au 1:16 : un Raspberry Pi lit "
                   "des capteurs abordables (ultrasons, temps de vol, centrale inertielle, encodeur de roue, pare-chocs), "
                   "ralentit à l'approche d'un obstacle et le contourne lentement. Une application web sur le téléphone le "
                   "démarre, l'arrête et affiche ce qu'il perçoit. Projet académique pour apprendre la mécanique, "
                   "l'électronique, le logiciel embarqué et la méthode de développement de produit, de MVP 0 à MVP 3.",
    "industry": "Éducation et robotique grand public", "product_type": "Robot mobile mécatronique avec liaison Wi-Fi",
    "weeks": 15, "markets": ["CA", "US"],
}

TEAM = [
    {"username": "nina", "display_name": "Nina", "study_profile": "Génie mécanique", "title": "Châssis, traction et direction",
     "role": "manager"},
    {"username": "lea", "display_name": "Léa", "study_profile": "Génie électrique", "title": "Alimentation, capteurs et câblage",
     "role": "editor"},
    {"username": "hugo", "display_name": "Hugo", "study_profile": "Design industriel", "title": "Carrosserie, ergonomie et application",
     "role": "editor"},
    {"username": "alexis", "display_name": "Alexis", "study_profile": "Génie informatique", "title": "Logiciel embarqué et évitement",
     "role": "editor"},
]


def _r(ref, kind, category, stakeholder, statement, rationale="", source="client", std=("", "", ""), method="", accept="",
       crit="", derived=(), lifecycle=""):
    item = {"ref": ref, "kind": kind, "category": category, "stakeholder": stakeholder, "statement": statement}
    for key, value in (("rationale", rationale), ("lifecycle", lifecycle), ("verification_method", method),
                       ("acceptance_criteria", accept), ("criticality", crit)):
        if value:
            item[key] = value
    if kind == "requirement":
        item["source"] = source
        if source == "standard":
            item["standard"], item["edition"], item["clause"] = std
    if derived:
        item["derived_from"] = list(derived)
    return item


NEEDS = [
    _r("BES-1", "need", "functional", "user", "L'étudiant veut un robot qui roule seul sans foncer dans les obstacles.",
       "Entrevues de MVP 0 : 9 étudiants sur 12 nomment « éviter les obstacles » comme premier projet de robotique."),
    _r("BES-2", "need", "functional", "user", "L'étudiant veut le piloter et le surveiller depuis son téléphone, sans installer d'application."),
    _r("BES-3", "need", "functional", "client", "L'enseignant veut un projet qui touche à la mécanique, à l'électronique et au logiciel.",
       "Le cours de conception de produit réunit des équipes multidisciplinaires."),
    _r("BES-4", "need", "performance", "client", "Le robot doit coûter moins de 250 $ en pièces, pour que chaque équipe en ait un."),
    _r("BES-5", "need", "safety", "safety", "Le robot ne doit blesser personne ni rien abîmer au laboratoire ou dans un corridor."),
    _r("BES-6", "need", "environmental", "user", "Le robot doit rouler dehors sur du gazon court, du gravier fin et des trottoirs."),
    _r("BES-7", "need", "functional", "user", "On veut comprendre ce que le robot « voit » et pourquoi il tourne."),
    _r("BES-8", "need", "regulatory", "authority", "Le robot doit pouvoir être vendu en kit au Canada et aux États-Unis.",
       "Hypothèse d'affaires du Lean Canvas : un kit pour les écoles après le cours."),
    _r("BES-9", "need", "functional", "repair", "Une pièce brisée doit se remplacer avec des pièces courantes, en moins de 30 minutes."),
]

REQUIREMENTS = [
    _r("REQ-1", "requirement", "functional", "user", "Le robot doit détecter un obstacle de 10 cm de haut ou plus devant lui, de 0,05 m à 2 m.",
       "Trois ultrasons couvrent ± 45° ; un capteur à temps de vol couvre l'axe à courte distance.", method="T",
       accept="Détection dans 95 % des 200 essais (boîte, chaise, jambe, mur) à 0,1 / 0,5 / 1 / 2 m.", crit="A", derived=["BES-1"]),
    _r("REQ-2", "requirement", "safety", "safety", "Le robot doit s'arrêter avant de toucher un obstacle placé devant lui à n'importe quelle vitesse.",
       "Distance d'arrêt calculée : 0,35 m à 1 m/s ; zone d'arrêt réglée à 0,30 m à 0,3 m/s.", method="T",
       accept="0 contact sur 50 approches de face, à toutes les vitesses permises.", crit="A", derived=["BES-1", "BES-5"]),
    _r("REQ-3", "requirement", "performance", "user", "La vitesse doit diminuer avec la distance de l'obstacle : 1,0 m/s au plus à plus de 1,2 m, 0,3 m/s au plus sous 1,2 m.",
       "Le contournement « lent » est ce que les étudiants veulent observer (BES-7) et il réduit l'énergie d'un choc.",
       method="T", accept="Vitesse mesurée par l'encodeur ≤ consigne + 10 %.", crit="B", derived=["BES-1", "BES-5"]),
    _r("REQ-4", "requirement", "functional", "user", "Le robot doit contourner un obstacle isolé et reprendre son cap initial à ± 15°.",
       method="T", accept="Réussite dans 9 essais sur 10 sur le parcours d'essai B.", crit="B", derived=["BES-1"]),
    _r("REQ-5", "requirement", "interface", "user", "L'application doit s'ouvrir dans le navigateur du téléphone (iOS et Android) sans installation.",
       "Le Raspberry Pi crée son propre point d'accès Wi-Fi et sert une page web.", method="D",
       accept="Démarrage, arrêt et télémétrie sur 2 iPhone et 2 Android récents.", crit="B", derived=["BES-2"]),
    _r("REQ-6", "requirement", "safety", "safety", "Le robot doit s'arrêter en 0,5 s au plus si la liaison avec le téléphone est perdue.",
       "Chien de garde : sans message de l'application pendant 300 ms, les moteurs sont coupés.", method="T",
       accept="Arrêt complet ≤ 0,5 s après la coupure du Wi-Fi, 20 essais sur 20.", crit="A", derived=["BES-2", "BES-5"]),
    _r("REQ-7", "requirement", "safety", "safety", "Un bouton d'arrêt d'urgence doit couper la traction, sur le robot et dans l'application.",
       method="T", accept="Traction coupée ≤ 0,2 s, 20 essais sur 20 pour chacun des deux boutons.", crit="A", derived=["BES-5"]),
    _r("REQ-8", "requirement", "performance", "user", "L'autonomie doit être d'au moins 30 minutes de roulage continu.",
       "Bilan de puissance : 16 W moyens, batterie LiPo 2S de 2 200 mAh, 80 % utilisable : environ 48 minutes.",
       method="T", accept="≥ 30 min sur le parcours A jusqu'à la coupure basse tension.", crit="B", derived=["BES-1"]),
    _r("REQ-9", "requirement", "functional", "user", "L'application doit afficher, au moins 5 fois par seconde, les distances, la vitesse et la décision en cours.",
       method="D", accept="Rafraîchissement mesuré ≥ 5 Hz à 10 m du robot.", crit="C", derived=["BES-7"]),
    _r("REQ-10", "requirement", "environmental", "user", "Le robot doit rouler sur gazon court, gravier fin et trottoir, et franchir une marche de 3 cm.",
       method="T", accept="Parcours C réussi sans aide, 3 fois sur 3.", crit="C", derived=["BES-6"]),
    _r("REQ-11", "requirement", "environmental", "user", "L'électronique doit résister aux éclaboussures (IPX4).",
       source="standard", std=("IEC 60529", "1989+A2:2013", "14.2.4 (IPX4)"), method="T",
       accept="Fonctionnement normal après l'essai IPX4, aucune eau sur le Raspberry Pi.", crit="C", derived=["BES-6"]),
    _r("REQ-12", "requirement", "performance", "management", "Le coût des pièces doit rester sous 250 $ par robot (prix de 2026, sans taxes).",
       method="A", accept="Nomenclature chiffrée ≤ 250 $.", crit="B", derived=["BES-4"], lifecycle="cost"),
    _r("REQ-13", "requirement", "functional", "repair", "Les capteurs, la batterie et le Raspberry Pi doivent se remplacer avec un seul tournevis, sans soudure.",
       method="D", accept="Remplacement de chaque module en ≤ 10 min par un étudiant qui ne l'a jamais fait.", crit="C",
       derived=["BES-9"], lifecycle="maintenance"),
    _r("REQ-14", "requirement", "regulatory", "authority", "Les émissions radioélectriques non intentionnelles doivent respecter la classe B au Canada.",
       source="standard", std=("ICES-003", "Issue 7", "Limites de la classe B"), method="T",
       accept="Pré-balayage sous les limites de la classe B avec 6 dB de marge.", crit="B", derived=["BES-8"]),
    _r("REQ-15", "requirement", "regulatory", "authority", "Les émissions radioélectriques non intentionnelles doivent respecter la classe B aux États-Unis.",
       source="standard", std=("47 CFR Part 15", "Subpart B", "15.109"), method="T", accept="Même pré-balayage que REQ-14.",
       crit="B", derived=["BES-8"]),
    _r("REQ-16", "requirement", "regulatory", "authority", "La radio Wi-Fi doit être celle d'un module déjà certifié (IC et FCC ID), sans modification.",
       "Le Raspberry Pi porte ses certifications radio ; les refaire coûterait plus que le projet.", source="internal",
       method="I", accept="IC et FCC ID du module notés au dossier et sur l'étiquette du kit.", crit="B", derived=["BES-8"]),
    _r("REQ-17", "requirement", "safety", "safety", "La batterie lithium doit être conforme à la sécurité des accumulateurs portables.",
       source="standard", std=("IEC 62133-2", "2017", "7.3"), method="I",
       accept="Certificat du fournisseur au dossier ; batterie dans un sac ignifuge pendant la charge.", crit="A", derived=["BES-5", "BES-8"]),
    _r("REQ-18", "requirement", "regulatory", "logistics", "La batterie doit avoir passé les essais de transport des piles au lithium.",
       source="standard", std=("UN 38.3", "Rev. 7", "38.3.4"), method="I", accept="Résumé d'essai UN 38.3 du fournisseur au dossier.",
       crit="B", derived=["BES-8"], lifecycle="transport"),
    _r("REQ-19", "requirement", "safety", "safety", "La tension de la batterie doit être surveillée ; sous 3,4 V par élément, le robot rentre et s'arrête.",
       method="T", accept="Arrêt à 6,8 V ± 0,1 V, alerte dans l'application 2 min avant.", crit="A", derived=["BES-5"]),
    _r("REQ-20", "requirement", "personnel_safety", "safety", "Aucune pièce en mouvement ni arête vive ne doit être accessible au doigt d'essai.",
       method="I", accept="Inspection avec un doigt d'essai rigide : aucun contact avec engrenages ni roues motrices.", crit="B",
       derived=["BES-5"]),
    _r("REQ-21", "requirement", "regulatory", "authority", "Les matériaux doivent respecter les restrictions de substances dangereuses (RoHS).",
       source="standard", std=("Directive 2011/65/UE", "(UE) 2015/863", "Annexe II"), method="I",
       accept="Déclaration RoHS de chaque fournisseur au dossier.", crit="D", derived=["BES-8"]),
    _r("REQ-22", "requirement", "functional", "user", "Le robot doit être prêt à rouler 60 s au plus après la mise sous tension.",
       method="T", accept="Médiane de 10 démarrages ≤ 60 s jusqu'au « Prêt » dans l'application.", crit="C", derived=["BES-2"]),
    _r("REQ-23", "requirement", "performance", "user", "Le robot doit résister à une chute de 0,5 m sur le béton, roues en bas ou sur le côté.",
       method="T", accept="Fonctionne après 6 chutes ; aucune pièce détachée.", crit="C", derived=["BES-6", "BES-9"]),
    _r("REQ-24", "requirement", "functional", "user", "Le code et les schémas doivent être documentés pour qu'une nouvelle équipe les reprenne en une semaine.",
       method="D", accept="Une équipe d'une autre section refait le MVP 2 à partir du wiki seulement.", crit="D", derived=["BES-3"]),
]


def _t(ref, title, subject, method, objective, accept, means, verifies, category="custom", standard="", section="", level="Product"):
    item = {"ref": ref, "title": title, "subject": subject, "category": category, "level": level, "method": method,
            "objective": objective, "acceptance": accept, "means": means, "verifies": list(verifies)}
    if standard:
        item["standard"], item["section"] = standard, section
    return item


TESTS = [
    _t("ESSAI-1", "Détection des obstacles — 200 essais", "func", "T", "Mesurer le taux de détection et la distance lue par obstacle.",
       "≥ 95 % de détection de 0,05 à 2 m.", "Boîte, chaise, jambe en mousse, mur ; ruban gradué ; journal des capteurs.", ["REQ-1"]),
    _t("ESSAI-2", "Arrêt avant contact — 50 approches", "func", "T", "Vérifier qu'aucune approche de face ne touche l'obstacle.",
       "0 contact.", "Obstacle en mousse sur une balance (détecte le contact) ; caméra du téléphone au ralenti.", ["REQ-2"]),
    _t("ESSAI-3", "Vitesse selon la distance", "func", "T", "Comparer la vitesse de l'encodeur à la consigne de la loi d'approche.",
       "Écart ≤ 10 % sur toute la plage.", "Encodeur de roue, journal à 50 Hz, couloir de 10 m.", ["REQ-3"]),
    _t("ESSAI-4", "Contournement sur le parcours B", "func", "T", "Mesurer le taux de réussite et l'écart de cap après contournement.",
       "9 réussites sur 10 ; cap à ± 15°.", "Parcours B (un obstacle de 40 cm), centrale inertielle, rapporteur au sol.", ["REQ-4"]),
    _t("ESSAI-5", "Application sur quatre téléphones", "usab", "D", "Démarrer, arrêter, lire la télémétrie sur iOS et Android.",
       "Toutes les fonctions sur les 4 téléphones ; ≥ 5 Hz.", "2 iPhone, 2 Android ; chronomètre ; 3 étudiants qui ne connaissent pas le projet.",
       ["REQ-5", "REQ-9"], level="Product in Use"),
    _t("ESSAI-6", "Perte de liaison — chien de garde", "sw", "T", "Couper le Wi-Fi en roulant et mesurer le temps d'arrêt.",
       "Arrêt ≤ 0,5 s, 20 sur 20.", "Wi-Fi du téléphone coupé ; vidéo à 240 images/s.", ["REQ-6"]),
    _t("ESSAI-7", "Arrêts d'urgence", "func", "T", "Mesurer le temps de coupure de la traction par chaque bouton.",
       "≤ 0,2 s, 20 sur 20 par bouton.", "Oscilloscope sur la commande du variateur ; vidéo.", ["REQ-7"]),
    _t("ESSAI-8", "Autonomie sur le parcours A", "elec", "T", "Rouler en continu jusqu'à la coupure basse tension.",
       "≥ 30 min ; coupure à 6,8 V ± 0,1 V ; alerte 2 min avant.", "Parcours A en boucle, wattmètre, multimètre, chronomètre.",
       ["REQ-8", "REQ-19"]),
    _t("ESSAI-9", "Terrain : gazon, gravier, trottoir, marche", "env", "T", "Réussir le parcours C sans aide.",
       "3 réussites sur 3, marche de 3 cm franchie.", "Parcours C à l'extérieur, par temps sec.", ["REQ-10"], level="Product in Use"),
    _t("ESSAI-10", "Éclaboussures IPX4", "ingress", "T", "Arroser selon IPX4, puis faire rouler.",
       "Aucune eau sur le Raspberry Pi ; fonctionnement normal.", "Tube oscillant ou pomme d'arrosoir selon la norme ; essuie-tout témoin.",
       ["REQ-11"], category="standard", standard="IEC 60529", section="14.2.4"),
    _t("ESSAI-11", "Pré-balayage des émissions rayonnées", "emc", "T", "Mesurer les émissions en pré-conformité avant un laboratoire reconnu.",
       "Sous les limites de la classe B avec 6 dB de marge.", "Analyseur de spectre, antenne, chambre du laboratoire de l'école.",
       ["REQ-14", "REQ-15"], category="standard", standard="ICES-003 / 47 CFR 15.109", section="Classe B"),
    _t("ESSAI-12", "Dossier radio, batterie et RoHS", "ver", "I", "Vérifier les certificats des modules achetés.",
       "IC / FCC ID, IEC 62133-2, UN 38.3 et RoHS au dossier.", "Liste de contrôle du dossier technique.",
       ["REQ-16", "REQ-17", "REQ-18", "REQ-21"], category="industry", level="Component"),
    _t("ESSAI-13", "Doigt d'essai sur les pièces mobiles", "mech", "I", "Chercher un contact possible avec engrenages et roues motrices.",
       "Aucun contact.", "Doigt d'essai rigide imprimé en 3D, lampe de poche.", ["REQ-20"]),
    _t("ESSAI-14", "Coût de la nomenclature", "prod", "A", "Chiffrer chaque pièce chez deux fournisseurs.",
       "≤ 250 $ par robot.", "Nomenclature dans Diamond (pièces), tableur des prix.", ["REQ-12"], level="Product"),
    _t("ESSAI-15", "Remplacement des modules", "usab", "D", "Faire remplacer chaque module par un étudiant novice.",
       "≤ 10 min par module, un seul tournevis.", "Chronomètre, tournevis cruciforme no 1.", ["REQ-13"]),
    _t("ESSAI-16", "Démarrage jusqu'à « Prêt »", "sw", "T", "Mesurer le temps entre la mise sous tension et « Prêt ».",
       "Médiane ≤ 60 s.", "Chronomètre, 10 démarrages à froid.", ["REQ-22"]),
    _t("ESSAI-17", "Chutes de 0,5 m", "mech", "T", "Laisser tomber le robot sur le béton dans six orientations.",
       "Fonctionne ; aucune pièce détachée.", "Gabarit de 0,5 m, dalle de béton.", ["REQ-23"]),
    _t("ESSAI-18", "Reprise par une autre équipe", "ver", "D", "Une équipe d'une autre section refait le MVP 2 à partir du wiki.",
       "MVP 2 refait en une semaine.", "Wiki Dynamite, dépôt du code, une équipe volontaire.", ["REQ-24"], level="Product in Use"),
    _t("ESSAI-19", "Couverture des capteurs (banc)", "func", "T", "Cartographier le cône de chaque capteur sur une grille au sol.",
       "Pas d'angle mort entre ± 45° à 0,3 m et plus.", "Grille de 10 cm au sol, cylindre de 5 cm, journal des capteurs.",
       ["REQ-1"], level="Subsystem"),
    _t("ESSAI-20", "Échauffement du boîtier électronique", "therm", "T", "Mesurer la température du processeur après 30 min au soleil.",
       "Processeur < 80 °C, sans baisse de fréquence.", "Journal de température du Pi, thermomètre, 30 °C à l'ombre.", ["REQ-8"],
       level="Subsystem"),
]
