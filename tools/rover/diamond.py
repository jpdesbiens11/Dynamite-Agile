"""Rover example: Diamond -- the function tree (found with the methods of the course, see the page « Analyse fonctionnelle »),
the boundary diagram (inputs, flows, outputs), the parts on the functions, the project risks and the DFMEA (AIAG-VDA),
each action with its owner and due date."""


def _f(ref, text, parent, ftype="usage", kano="B", importance="indispensable", critical=False, notes=""):
    item = {"ref": ref, "text": text, "type": ftype, "parent": parent, "kano": kano, "importance": importance}
    if critical:
        item["critical"] = True
    if notes:
        item["notes"] = notes
    return item


FUNCTIONS = [
    _f("F1", "Se déplacer seul en évitant les obstacles", None, critical=True,
       notes="Fonction primaire, trouvée par la méthode intuitive puis vérifiée avec la bête à cornes : à qui rend-il service, sur quoi agit-il, dans quel but."),
    _f("F2", "Être prêt à rouler", "F1", notes="Première branche dans le temps (« quand ») : de la power-on au « Prêt »."),
    _f("F3", "Recevoir l'énergie de la battery", "F2"),
    _f("F4", "Démarrer le software et le point d'accès Wi-Fi", "F2"),
    _f("F5", "Se connecter au téléphone", "F2"),
    _f("F6", "Recevoir les consignes de l'utilisateur", "F1", notes="Trouvée par les interacteurs : l'utilisateur et son téléphone."),
    _f("F7", "Afficher l'application dans le navigateur du téléphone", "F6", kano="P", importance="importante"),
    _f("F8", "Transmettre démarrer, arrêter et vitesse maximale", "F6"),
    _f("F9", "Percevoir l'environnement", "F1", critical=True, notes="Trouvée par l'environnement (méthode SAFE) : obstacles, sol, lumière, eau."),
    _f("F10", "Mesurer les distances devant, à gauche et à droite", "F9", critical=True),
    _f("F15", "Convertir l'écho 5 V en 3,3 V", "F10", ftype="technique", kano="", importance="",
       notes="Fonction technique : elle n'existe qu'à cause du choix des ultrasonic sensors 5 V."),
    _f("F11", "Mesurer la distance dans l'axe à courte portée", "F9", critical=True),
    _f("F12", "Mesurer le cap et les rotations", "F9", kano="P", importance="importante"),
    _f("F13", "Mesurer la vitesse des roues", "F9"),
    _f("F14", "Sentir un contact avec un obstacle", "F9", notes="Dernier recours si la perception à distance échoue."),
    _f("F16", "Décider de la trajectoire", "F1", critical=True, notes="Le cœur du produit : ce que les étudiants viennent apprendre."),
    _f("F17", "Fusionner les mesures en une local map", "F16", critical=True),
    _f("F18", "Choisir la vitesse selon la distance de l'obstacle", "F16", critical=True,
       notes="Loi d'approche : 1,0 m/s au-delà de 1,2 m, 0,3 m/s jusqu'à 0,6 m, puis de 0,3 à 0,1 m/s jusqu'à l'arrêt à 0,30 m."),
    _f("F19", "Choisir le côté de contournement", "F16"),
    _f("F20", "Reprendre le cap initial", "F16", kano="P", importance="importante"),
    _f("F21", "Se propulser", "F1"),
    _f("F22", "Commander le drive motor", "F21"),
    _f("F23", "Transmettre le couple aux roues", "F21"),
    _f("F24", "Se diriger", "F1"),
    _f("F25", "Braquer les roues avant", "F24"),
    _f("F26", "Protéger les personnes et le robot", "F1", critical=True, notes="Trouvée par le produit de référence : toute RC car a une coupure."),
    _f("F27", "Couper la traction sur emergency stop", "F26", critical=True),
    _f("F28", "S'arrêter si la liaison est perdue", "F26", critical=True),
    _f("F29", "Surveiller la voltage de la battery", "F26"),
    _f("F30", "Supporter et protéger les composants", "F1"),
    _f("F31", "Porter les modules sur le chassis", "F30"),
    _f("F32", "Protéger l'électronique des éclaboussures et des chocs", "F30", kano="P", importance="importante"),
    _f("F33", "Rendre compte à l'utilisateur", "F1", kano="P", importance="importante"),
    _f("F34", "Envoyer la telemetry au téléphone", "F33", kano="P", importance="importante"),
    _f("F35", "Signaler l'état par une LED", "F33", kano="B", importance="interessante"),
    _f("F36", "Donner envie d'apprendre la technologie", "F1", ftype="estime", kano="I", importance="importante",
       notes="Fonction d'estime : le robot montre ses sensors et son wiring au lieu de les cacher."),
    _f("F37", "Montrer les sensors et le wiring", "F36", ftype="estime", kano="I", importance="interessante"),
    _f("F38", "Utiliser le chassis d'une RC car tout-terrain", "F1", ftype="contrainte", kano="C",
       notes="Contrainte du cours : traction et direction achetées, pour se concentrer sur la perception et la décision."),
    _f("F39", "Coûter moins de 250 $ en pièces", "F1", ftype="contrainte", kano="C"),
]
FUNCTIONS.sort(key=lambda f: int(f["ref"][1:]))  # Diamond numbers the functions in file order: F15 stays F15

PORTS = [
    {"ref": "E1", "side": "in", "label": "Charge de la battery (charger externe)", "kind": "energy"},
    {"ref": "E2", "side": "in", "label": "Consignes de l'utilisateur (téléphone)", "kind": "information"},
    {"ref": "E3", "side": "in", "label": "Échos et lumière réfléchie par les obstacles", "kind": "information"},
    {"ref": "E4", "side": "in", "label": "Contact avec un obstacle", "kind": "information"},
    {"ref": "E5", "side": "in", "label": "Eau, poussière et chocs du terrain", "kind": "material"},
    {"ref": "S1", "side": "out", "label": "Déplacement du robot", "kind": "energy"},
    {"ref": "S2", "side": "out", "label": "Telemetry vers le téléphone", "kind": "information"},
    {"ref": "S3", "side": "out", "label": "Chaleur du motor et du processor", "kind": "energy"},
    {"ref": "S4", "side": "out", "label": "Signal lumineux d'état", "kind": "information"},
]


def _flows(view, rows):
    return [{"view": view, "kind": kind, "label": label, "src": src, "dst": dst} for src, dst, kind, label in rows]


FLOWS = _flows("general", [
    ("E1", "F2", "energy", "7,4 V"), ("F2", "F9", "energy", "5 V"), ("F2", "F16", "energy", "5 V"), ("F2", "F21", "energy", "7,4 V"),
    ("F2", "F24", "energy", "6 V"), ("E2", "F6", "information", "Wi-Fi"), ("F6", "F16", "information", "setpoints"),
    ("F6", "F26", "information", "emergency stop"), ("E3", "F9", "information", "echoes"), ("E4", "F9", "information", "contact"),
    ("F9", "F16", "information", "distances, heading, vitesse"), ("F16", "F21", "information", "speed setpoint"),
    ("F16", "F24", "information", "steering angle"), ("F26", "F21", "information", "coupure"), ("F2", "F26", "information", "voltage"),
    ("F21", "S1", "energy", "mouvement"), ("F24", "S1", "energy", "steering"), ("F21", "S3", "energy", "chaleur"),
    ("F16", "F33", "information", "état et décision"), ("F33", "S2", "information", "telemetry"), ("F33", "S4", "information", "LED"),
    ("E5", "F30", "material", "eau, poussière"),
]) + _flows("detail", [
    ("E1", "F3", "energy", "7,4 V"), ("F3", "F4", "energy", "5 V"), ("F4", "F5", "information", "access point"),
    ("E2", "F7", "information", "web page"), ("F7", "F8", "information", "boutons"), ("F8", "F18", "information", "max speed"),
    ("F8", "F27", "information", "emergency stop"), ("E3", "F10", "information", "echo"), ("E3", "F11", "information", "lumière"),
    ("E4", "F14", "information", "contact"), ("F10", "F17", "information", "3 distances"), ("F11", "F17", "information", "distance axe"),
    ("F12", "F17", "information", "heading"), ("F13", "F18", "information", "vitesse"), ("F17", "F18", "information", "distance min"),
    ("F17", "F19", "information", "local map"), ("F12", "F20", "information", "heading"), ("F19", "F25", "information", "angle"),
    ("F20", "F25", "information", "correction"), ("F18", "F22", "information", "setpoint"), ("F14", "F27", "information", "choc"),
    ("F27", "F22", "information", "coupure"), ("F5", "F28", "information", "heartbeat 10 Hz"), ("F28", "F22", "information", "coupure"),
    ("F22", "F23", "energy", "torque"), ("F23", "S1", "energy", "mouvement"), ("F25", "S1", "energy", "steering"),
    ("F22", "S3", "energy", "chaleur"), ("F3", "F29", "information", "voltage"), ("F29", "F34", "information", "battery level"),
    ("F17", "F34", "information", "distances"), ("F34", "S2", "information", "telemetry"), ("F29", "F35", "information", "état"),
    ("F35", "S4", "information", "couleur"), ("E5", "F32", "material", "eau, poussière"),
    ("F3", "F10", "energy", "5 V"), ("F3", "F17", "energy", "5 V"), ("F3", "F22", "energy", "7,4 V"), ("F3", "F25", "energy", "6 V"),
    ("E5", "F31", "material", "chocs du terrain"),
])


def _p(name, kind, functions, notes):
    return {"name": name, "kind": kind, "functions": functions, "notes": notes}


PARTS = [
    _p("Chassis de RC car tout-terrain 1:16", "bought", ["F31", "F23", "F25"], "4 × 4, suspensions ; environ 80 $ avec motor et servo."),
    _p("Drive motor à balais (type 390)", "bought", ["F23"], "Fourni avec le chassis ; réduction par pinions."),
    _p("Brushed ESC 20 A", "bought", ["F22"], "Commandé par un signal PWM de 50 Hz comme un servo."),
    _p("Servo de direction 9 kg·cm", "bought", ["F25"], "Fourni avec le chassis ; ± 30° de braquage."),
    _p("Raspberry Pi 4 (2 Go)", "bought", ["F4", "F5", "F17", "F18", "F19", "F20", "F34"],
       "Wi-Fi intégré déjà certifié (IC / FCC ID) ; environ 60 $."),
    _p("MicroSD card 32 Go", "bought", ["F4"], "Image du système préparée et copiée pour chaque robot."),
    _p("Battery LiPo 2S 2 200 mAh, connector XT60", "bought", ["F3"], "Certifiée IEC 62133-2 et UN 38.3 ; environ 30 $."),
    _p("Buck converter 5 V 5 A", "bought", ["F3"], "Alimente le Pi et les sensors ; le motor reste sur 7,4 V."),
    _p("Voltage and current monitor INA219", "bought", ["F29"], "Bus I2C ; mesure la voltage de la battery."),
    _p("Ultrasonic sensors HC-SR04 (× 3)", "bought", ["F10"], "Gauche, centre, droite à ± 45° ; environ 4 $ chacun."),
    _p("Voltage dividers de l'écho (× 3)", "standard", ["F10"], "Deux résistances : 5 V → 3,3 V pour les entrées du Pi (fonction technique F15)."),
    _p("Sensor à temps de vol VL53L1X", "bought", ["F11"], "Axe avant, 4 cm à 4 m ; voit les obstacles mous que les ultrasons ratent."),
    _p("IMU ICM-20948", "bought", ["F12"], "Gyroscope pour le cap pendant le contournement."),
    _p("Sensor à effet Hall et aimant sur l'arbre", "bought", ["F13"], "Une impulsion par tour d'arbre : la vitesse des roues."),
    _p("Microswitches de bumper (× 2)", "standard", ["F14"], "Contact franc, câblés en série avec l'emergency stop."),
    _p("Bumper avant en PETG", "designed", ["F14", "F32"], "Imprimé en 3D, pivote sur deux tiges et appuie sur les microswitches."),
    _p("PWM board PCA9685", "bought", ["F22", "F25"], "16 canaux en I2C : ESC et servo sans charger le processor."),
    _p("MOSFET de coupure de la traction", "bought", ["F27", "F28"], "Coupe le signal et l'alimentation de l'ESC ; ouvert par défaut."),
    _p("Emergency stop button à verrouillage 16 mm", "standard", ["F27"], "Rouge sur fond jaune, sur le dessus du robot."),
    _p("Plaque porte-modules en acrylic", "designed", ["F31", "F37"], "Découpée au laser, transparente : on voit le wiring (fonction d'estime)."),
    _p("Electronics enclosure avec joint", "designed", ["F32"], "Imprimé en PETG ; joint en mousse ; ouvert vers le bas pour l'air."),
    _p("LED RGB d'état", "standard", ["F35"], "Vert : prêt ; bleu : roule ; ambre : contourne ; rouge : arrêt ou battery basse."),
    _p("Fasteners M3 et standoffs", "standard", ["F31"], "Un seul tournevis cruciforme no 1 pour tout le robot."),
]


def _risk(title, cause, consequence, category, phase, p, i, response, action, owner, due, function=None):
    item = {"title": title, "cause": cause, "consequence": consequence, "category": category, "phase": phase, "probability": p,
            "impact": i, "response": response, "action": action, "owner": owner, "due": due}
    if function:
        item["function"] = function
    return item


RISKS = [
    _risk("Les ultrasons ratent les obstacles mous ou en biais", "le son est absorbé ou réfléchi ailleurs", "collision avec une jambe ou un sac",
          "technique", "B", 4, 4, "reduire", "Ajouter un sensor à temps de vol dans l'axe et des bumper ; essai de couverture sur grille",
          "lea", "2026-12-04", "F10"),
    _risk("Interférence entre les trois ultrasons", "un sensor entend l'écho d'un autre", "fausses distances, arrêts inutiles",
          "technique", "C", 3, 3, "reduire", "Déclencher les sensors à tour de rôle, 25 ms d'écart", "alexis", "2026-12-18", "F10"),
    _risk("Distance d'arrêt trop longue à pleine vitesse", "inertie, latency de 100 ms de la boucle", "contact avec l'obstacle",
          "securite", "C", 3, 5, "reduire", "Loi d'approche lente sous 1,2 m ; calcul de la distance d'arrêt à la PDR", "alexis", "2026-12-11", "F18"),
    _risk("Battery LiPo endommagée ou trop déchargée", "chute, perforation, décharge sous 3,0 V par élément", "incendie, battery perdue",
          "securite", "C", 2, 5, "reduire", "Coupure à 3,4 V par élément, sac ignifuge, consignes de charge affichées au labo", "lea", "2026-12-04", "F29"),
    _risk("Wi-Fi coupé dans un corridor achalandé", "réseau 2,4 GHz encombré", "commandes perdues, robot hors contrôle",
          "technique", "C", 3, 4, "reduire", "Watchdog de 300 ms ; canal Wi-Fi choisi au démarrage", "alexis", "2026-12-18", "F28"),
    _risk("Rupture de stock du Raspberry Pi", "pénurie chez les distributeurs", "équipes sans contrôleur", "fournisseurs", "B", 2, 4,
          "transferer", "Commander les 12 cartes au début de la phase B ; code compatible Pi 4 et Pi 5", "nina", "2026-11-27"),
    _risk("Dépassement du budget de 250 $", "pièces de remplacement, frais de port", "kit trop cher pour les écoles", "couts", "C", 3, 3,
          "reduire", "BOM chiffrée à chaque revue ; achats groupés", "nina", "2027-01-15", "F39"),
    _risk("Équipe en retard sur le software d'évitement", "un seul informaticien dans l'équipe", "MVP 2 incomplet à la CDR", "equipe", "C",
          3, 4, "reduire", "Binôme Alexis–Léa sur le software ; simulation sur ordinateur avant le robot", "alexis", "2027-01-08", "F16"),
    _risk("Le kit est considéré comme un jouet", "vendu à des jeunes de moins de 14 ans", "normes de jouets à respecter, coût d'essais",
          "normes", "D", 2, 3, "eviter", "Kit destiné aux 14 ans et plus, mention sur la boîte et dans la notice", "hugo", "2027-02-05"),
    _risk("Les étudiants trouvent le robot ennuyeux", "il ne montre pas ce qu'il « pense »", "peu d'intérêt pour le kit", "marche", "A",
          2, 3, "reduire", "Telemetry et local map dans l'application ; plaque transparente", "hugo", "2026-11-20", "F36"),
]


def _d(focus, lower, function, requirement, mode, effect, s, cause, prevention, o, detection_ctrl, d, action, test, owner, due):
    return {"higher": "Rover et son utilisateur", "focus": focus, "lower": lower, "function": function, "requirement": requirement,
            "failure_mode": mode, "effect": effect, "severity": s, "cause": cause, "prevention": prevention, "occurrence": o,
            "detection_ctrl": detection_ctrl, "detection": d, "action": action, "test": test, "owner": owner, "due": due}


DFMEA = [
    _d("Perception", "Ultrasons HC-SR04", "F10", "Détecter un obstacle de 10 cm de 0,05 à 2 m (REQ-1)", "Obstacle non détecté",
       "Collision", 8, "Surface molle ou en biais qui absorbe l'écho", "Trois sensors à ± 45°, temps de vol dans l'axe", 5,
       "Essai de couverture sur grille, 200 essais de détection", 3, "Ajouter le temps de vol et vérifier la couverture", "ESSAI-19", "lea", "2026-12-04"),
    _d("Perception", "Ultrasons HC-SR04", "F10", "Distance juste à ± 3 cm", "Distance fausse (écho croisé)", "Arrêts inutiles, contournement raté",
       5, "Deux sensors émettent en même temps", "Déclenchement à tour de rôle", 4, "Journal des distances sur le bench", 4,
       "Séquenceur de 25 ms dans le pilote", "ESSAI-1", "alexis", "2026-12-18"),
    _d("Perception", "Sensor à temps de vol", "F11", "Distance dans l'axe de 0,04 à 2 m", "Mesure saturée au soleil", "Obstacle vu trop tard",
       7, "Lumière infrarouge du soleil", "Mode courte portée, filtre de plausibilité avec les ultrasons", 4, "Essai dehors au soleil (parcours C)",
       4, "Fusion : la plus courte distance plausible l'emporte", "ESSAI-9", "lea", "2027-01-15"),
    _d("Décision", "Loi d'approche", "F18", "Vitesse ≤ 0,3 m/s sous 1,2 m (REQ-3)", "Vitesse trop élevée près de l'obstacle",
       "Contact, robot ou obstacle abîmé", 8, "Encoder qui manque des impulsions", "Comparer encoder et consigne ; limite logicielle", 3,
       "Essai de vitesse selon la distance", 3, "Limiter la commande de l'ESC à 30 % sous 1,2 m", "ESSAI-3", "alexis", "2026-12-18"),
    _d("Décision", "Arrêt avant contact", "F18", "S'arrêter avant de toucher (REQ-2)", "Arrêt trop tardif", "Collision avec une personne",
       9, "Latency de la boucle de 100 ms", "Boucle à 20 Hz, calcul de la distance d'arrêt", 3, "50 approches de face", 2,
       "Zone d'arrêt à 0,30 m, revue du calcul à la CDR", "ESSAI-2", "alexis", "2027-01-08"),
    _d("Décision", "Choix du côté", "F19", "Contourner et reprendre le cap (REQ-4)", "Oscillation gauche-droite devant l'obstacle",
       "Robot bloqué, battery gaspillée", 4, "Distances gauche et droite presque égales", "Hysteresis de 10 cm et côté gardé 2 s", 5,
       "Parcours B, 10 essais", 4, "Ajouter la hysteresis au choix du côté", "ESSAI-4", "alexis", "2027-01-15"),
    _d("Décision", "Reprise du cap", "F20", "Cap initial à ± 15° (REQ-4)", "Dérive du cap", "Robot perdu, ne revient pas", 4,
       "Dérive du gyroscope", "Calibration à l'arrêt au démarrage", 4, "Parcours B avec rapporteur au sol", 4, "Calibration de 2 s au « Prêt »",
       "ESSAI-4", "alexis", "2027-01-15"),
    _d("Sécurité", "Emergency stop", "F27", "Couper la traction en ≤ 0,2 s (REQ-7)", "La traction n'est pas coupée", "Blessure, chute du robot",
       10, "MOSFET en short circuit", "Coupure matérielle en série, MOSFET ouvert par défaut", 2, "Essai à l'oscilloscope des deux boutons", 2,
       "Vérifier la coupure à chaque démarrage (self-test)", "ESSAI-7", "lea", "2026-12-11"),
    _d("Sécurité", "Watchdog", "F28", "Arrêt en ≤ 0,5 s sans liaison (REQ-6)", "Le robot continue sans liaison", "Robot hors contrôle",
       9, "Fil d'exécution du watchdog bloqué", "Watchdog matériel du Pi en plus du software", 3, "Coupure du Wi-Fi en roulant, 20 essais",
       2, "Activer le watchdog matériel", "ESSAI-6", "alexis", "2026-12-18"),
    _d("Énergie", "Battery LiPo", "F29", "Arrêt à 3,4 V par élément (REQ-19)", "Décharge profonde", "Battery gonflée, risque d'incendie",
       9, "Lecture de voltage absente ou fausse", "INA219 étalonné, seuil software et alarme de l'ESC", 3, "Essai d'autonomie jusqu'à la coupure",
       3, "Double seuil : alerte à 3,6 V, arrêt à 3,4 V", "ESSAI-8", "lea", "2027-01-15"),
    _d("Énergie", "Converter 5 V", "F3", "5 V stable sous 3 A", "Voltage drop au démarrage du motor", "Redémarrage du Pi en roulant",
       6, "Current peak du motor sur la même battery", "Capacitor de 1 000 µF, cables séparés", 4, "Oscilloscope sur le 5 V au démarrage",
       4, "Soft start du motor (rampe de 0,5 s)", "ESSAI-8", "lea", "2026-12-18"),
    _d("Structure", "Electronics enclosure", "F32", "IPX4 (REQ-11)", "Eau sur le Raspberry Pi", "Short circuit, robot arrêté", 6,
       "Joint mal posé, ouverture de cables vers le haut", "Passe-câbles par le bas, joint en mousse", 4, "Essai IPX4", 3,
       "Revoir les passe-câbles après le premier essai", "ESSAI-10", "hugo", "2027-01-22"),
    _d("Structure", "Plaque porte-modules", "F31", "Résister à une chute de 0,5 m (REQ-23)", "Plaque fissurée, sensor décroché",
       "Perception perdue d'un côté", 6, "Acrylic cassant aux coins", "Rayons de 3 mm aux coins, rondelles en caoutchouc", 4,
       "Six chutes de 0,5 m", 3, "Essayer le PETG si l'acrylic casse", "ESSAI-17", "nina", "2027-01-22"),
    _d("Propulsion", "ESC et motor", "F22", "Vitesse commandée à ± 10 %", "Le robot démarre seul", "Robot qui part sans consigne", 8,
       "Signal PWM flottant au démarrage du Pi", "Résistance de rappel, MOSFET ouvert tant que le software n'est pas prêt", 3,
       "Démarrages à froid, 10 essais", 3, "Self-test au démarrage avant d'ouvrir la coupure", "ESSAI-16", "lea", "2026-12-11"),
]
