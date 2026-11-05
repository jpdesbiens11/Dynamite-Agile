"""Industry good practices of the DFMEA (0.60.28, D-O-037): the prevention controls a team should consider for a function,
listed in the « Prevention Controls » column -- to train young engineers and to keep the memory of the older ones.

Each theme says which words of a function (its text, its flows, its parts) call it, which subjects of the Test Base
verify it (in order of preference, see modules/testing/data_tests.SUBJECTS) and the design practices that prevent its
failure causes (AIAG-VDA: a prevention control acts on the occurrence of the cause, before the part exists). The words
are accent-free stems matched at the start of a word, French and English. GENERAL applies to every row.
"""
import re
import unicodedata

MARK = "Bonnes pratiques (industrie) :"
GENERAL = [
    "Revue de conception par des pairs (PDR, CDR) avec cette ligne du DFMEA sous les yeux",
    "Leçons apprises : DFMEA et retours terrain d'un produit semblable ou précédent",
    "Solution éprouvée ou pièce du commerce qualifiée plutôt qu'une technologie nouvelle, sauf raison chiffrée",
    "Exigence chiffrée et vérifiable dans le CdCF (Goldmine) pour cette fonction, avec sa tolérance",
]

THEMES = {
    "elec": {"label": "Sécurité électrique", "subjects": ("elec", "ver"),
             "words": ("isol", "sous tension", "secteur", "electri", "tension", "courant", "fusib", "terre", "choc electr",
                       "alimentation", "bloc d alim", "insulat", "live", "mains", "voltage", "current", "earth", "shock"),
             "practices": [
                 "Distances d'isolement dans l'air et lignes de fuite sur les surfaces selon IEC 62368-1 ou IEC 60335-1, pour la tension de service et le degré de pollution",
                 "Isolation double ou renforcée entre le secteur et les parties accessibles (classe II), ou mise à la terre vérifiée (classe I)",
                 "Bloc d'alimentation externe certifié CSA / UL (classe 2, ES1 / PS2) plutôt qu'une alimentation secteur intégrée",
                 "Protection contre les surintensités (fusible, PTC) dimensionnée sur le courant de défaut",
                 "Derating des composants : tension ≤ 80 %, courant ≤ 70-80 %, puissance ≤ 50-60 % de la valeur nominale",
                 "Liste des composants critiques de sécurité, chacun certifié et figé (aucun remplacement sans revue)",
                 "Analyse de défaut unique (single fault) : un composant en court-circuit ou ouvert ne rend pas le produit dangereux"]},
    "power": {"label": "Énergie et batterie", "subjects": ("elec", "func", "env"),
              "words": ("energ", "distribu", "batter", "pile", "accumul", "lithium", "charg", "power", "supply"),
              "practices": [
                  "Bilan de puissance avec une marge d'au moins 20 % sur chaque rail d'alimentation",
                  "Protection contre l'inversion de polarité et les surtensions (diode, TVS) à chaque entrée d'énergie",
                  "Connecteurs détrompés, dimensionnés pour le courant et le nombre de branchements prévus",
                  "Batterie lithium : cellules IEC 62133-2, circuit de gestion de la batterie (surcharge, décharge profonde, court-circuit, température), transport UN 38.3",
                  "Découplage et filtrage au plus près de chaque circuit intégré"]},
    "therm": {"label": "Thermique", "subjects": ("therm", "elec", "env"),
              "words": ("chaleur", "therm", "temperat", "dissip", "refroid", "chauff", "ventil", "heat", "cool", "hot"),
              "practices": [
                  "Bilan thermique calculé ou simulé, température de jonction au moins 20 °C sous le maximum du composant",
                  "Température des surfaces touchées selon IEC 62368-1 (TS1) ou IEC 60335-1, avec marge",
                  "Matériaux choisis selon leur indice thermique (RTI, UL 746B) au-delà de la température atteinte",
                  "Protection thermique (thermistance, coupe-circuit thermique) qui met le produit en état sûr",
                  "Contact thermique assuré et reproductible : pâte ou tampon spécifié, couple de serrage, planéité",
                  "Derating des composants en température (courbe du fabricant)"]},
    "emc": {"label": "CEM et radio", "subjects": ("emc", "sw"),
            "words": ("commun", "radio", "sans fil", "bluetooth", "wifi", "antenn", "signal", "mli", "pwm", "horlog",
                      "wireless", "emission", "parasit", "interfer"),
            "practices": [
                "Plan de masse continu, boucles de courant courtes, règles de placement et de routage écrites",
                "Filtrage à l'entrée d'alimentation (ferrite, condensateurs X / Y) et sur chaque câble qui sort du boîtier",
                "Protection ESD (TVS) sur toute surface touchée et tout connecteur accessible (IEC 61000-4-2)",
                "Module radio précertifié ISED / FCC avec l'antenne et le placement de sa fiche d'intégration",
                "Fréquence de commutation hors des bandes sensibles, fronts adoucis ou étalement de spectre"]},
    "sw": {"label": "Électronique et logiciel", "subjects": ("sw", "func"),
           "words": ("logiciel", "micrologiciel", "firmware", "software", "memor", "programm", "command", "regul", "calcul",
                     "detect", "capteur", "mesur", "application", "connexion", "donnee", "sensor", "control", "data"),
           "practices": [
               "Chien de garde (watchdog) et état sûr défini au démarrage, en défaut et à la perte d'alimentation",
               "IEC 60730-1 annexe H (classe B) si le logiciel assure une fonction de sécurité",
               "Règles de codage (ex. MISRA C), revue de code et analyse statique avant chaque version",
               "Tests unitaires et d'intégration automatisés, rejoués à chaque modification",
               "Validation des entrées, délais d'attente (timeouts) et reprise automatique des communications",
               "Mémoire non volatile protégée par CRC, écritures limitées à l'endurance de la mémoire",
               "Mise à jour signée avec retour possible à la version précédente",
               "Capteurs : filtrage et anti-rebond, seuils avec hystérésis, plausibilité de la mesure"]},
    "mech": {"label": "Structure et mécanique", "subjects": ("mech", "ver", "life"),
             "words": ("poser", "tenir", "stab", "support", "structur", "base", "boitier", "fix", "assembl", "rigid", "porter",
                       "resist", "choc", "chute", "lest", "bascul", "enclos", "hold", "mount", "drop", "load"),
             "practices": [
                 "Facteur de sécurité d'au moins 2 sur les pièces structurelles (3 pour un plastique chargé longtemps : fluage)",
                 "Calcul ou simulation par éléments finis des pièces chargées, cas de chute et de choc compris",
                 "Analyse de tolérances (pire cas ou RSS) sur chaque ajustement critique",
                 "Congés de raccordement, pas d'angle vif ni d'entaille dans une zone chargée (concentration de contraintes)",
                 "Pièces moulées : épaisseur de paroi uniforme, nervures, dépouilles, matière choisie avec sa fiche technique",
                 "Fixations : couple spécifié, frein-filet ou rondelle, inserts métalliques dans le plastique",
                 "Stabilité : centre de gravité bas, essai de basculement sur un plan incliné selon la norme du produit"]},
    "life": {"label": "Pièces en mouvement et durée de vie", "subjects": ("life", "mech", "usab"),
             "words": ("orient", "tourn", "pivot", "articul", "charnier", "bouton", "glisser", "ressort", "moteur", "mouv",
                       "deplac", "usure", "cycle", "hinge", "button", "motor", "move", "wear"),
             "practices": [
                 "Durée de vie spécifiée en cycles, avec une marge d'au moins 2 fois l'usage prévu",
                 "Matériaux appariés contre l'usure (plastique sur métal, lubrifiant spécifié), pas deux plastiques identiques en frottement",
                 "Interrupteurs et boutons choisis pour un nombre de cycles connu (fiche technique), avec anti-rebond",
                 "Friction ou serrage réglable, rattrapage d'usure prévu",
                 "Pas de pincement ni de cisaillement des doigts par les pièces en mouvement (IEC 60335-1, art. 20)"]},
    "ingress": {"label": "Eau, poussière et environnement", "subjects": ("ingress", "env"),
                "words": ("eau", "humid", "poussier", "etanch", "exterieur", "recouvr", "envelop", "joint", "proteg", "water",
                          "dust", "seal", "cover", "outdoor"),
                "practices": [
                    "Indice IP visé dès le concept (IEC 60529) : joints, chicanes et chemins de drainage dessinés",
                    "Vernis de tropicalisation (conformal coating) des cartes exposées à l'humidité",
                    "Matériaux stables aux UV, à l'humidité et aux produits ménagers",
                    "Évent à membrane contre la condensation dans un boîtier fermé",
                    "Essais d'environnement IEC 60068 planifiés tôt (chaleur humide, froid, vibration de transport)"]},
    "light": {"label": "Lumière et optique", "subjects": ("func", "therm"),
              "words": ("lumi", "eclair", "del", "led", "optiq", "intensit", "temperature de couleur", "light"),
              "practices": [
                  "DEL classées selon IEC 62471 (sécurité photobiologique, groupe de risque exempt ou 1)",
                  "Pilote à courant constant ; gradation sans scintillement visible (IEEE 1789 : fréquence MLI élevée)",
                  "Tri (binning) des DEL pour une couleur constante d'un produit à l'autre",
                  "Maintien du flux connu (L70, données LM-80 et projection TM-21) à la température réelle des DEL"]},
    "mat": {"label": "Matériaux, aspect et conformité", "subjects": ("mat", "usab", "ver"),
            "words": ("plair", "allure", "aspect", "esthet", "couleur", "finition", "materi", "plastiq", "epure",
                      "look", "appearance", "finish", "material"),
            "practices": [
                "Matériaux conformes RoHS et REACH dès le choix, avec les déclarations des fournisseurs",
                "Plastiques UL 94 V-0 près des sources de chaleur et d'énergie, classe exigée par la norme ailleurs",
                "Teinte, brillance et texture fixées par des échantillons maîtres (master samples) et des tolérances d'aspect",
                "Résistance aux rayures, aux UV et au jaunissement vérifiée sur la matière retenue"]},
    "usab": {"label": "Utilisation et ergonomie", "subjects": ("usab", "func"),
             "words": ("utilis", "user", "interface", "afficher", "indiqu", "regler", "ergonom", "prise en main", "toucher",
                       "touch", "display", "adjust"),
             "practices": [
                 "Ingénierie de l'aptitude à l'utilisation (IEC 62366-1, même hors médical) : scénarios d'usage et erreurs prévisibles",
                 "Détrompage (poka-yoke) : un seul sens possible pour brancher, poser ou assembler",
                 "Un retour à l'utilisateur (son, lumière, mouvement) pour chaque commande",
                 "Essais avec de vrais utilisateurs dès le premier prototype, puis à chaque itération",
                 "Notice claire et symboles normalisés (IEC 60417, ISO 7000)"]},
    "prod": {"label": "Fabrication et assemblage", "subjects": ("prod", "ver"),
             "words": ("assembl", "fabri", "product", "montag", "manufact"),
             "practices": [
                 "DFM / DFA (méthode Boothroyd-Dewhurst) : moins de pièces, pièces symétriques ou détrompées",
                 "Détrompage (poka-yoke) à l'assemblage : impossible de monter une pièce à l'envers",
                 "Caractéristiques spéciales (CC / SC) reportées au plan de contrôle et au PFMEA",
                 "Test de fin de ligne sur chaque produit"]},
}
PART_KINDS = {
    "bought": "Pièce achetée : fiche technique lue en entier, fournisseur qualifié, deuxième source identifiée",
    "standard": "Pièce normalisée (ISO, DIN) avec sa classe de résistance ou de précision spécifiée au plan",
}
STOP = {"les", "des", "une", "aux", "pour", "par", "dans", "avec", "sur", "sous", "son", "ses", "leur", "cette", "est",
        "the", "and", "for", "with", "from", "into", "realise", "fonction", "function", "essai", "test", "preciser"}


def norm(text):
    text = unicodedata.normalize("NFKD", str(text or "").lower())
    return " " + re.sub(r"[^a-z0-9]+", " ", "".join(c for c in text if not unicodedata.combining(c))).strip() + " "


def words(text):
    """The stems of a text, for matching a row with a test (5 letters, accents and small words left out)."""
    return {w[:5] for w in norm(text).split() if len(w) >= 4 and w not in STOP}


def themes(text):
    """The themes called by a text, best first (number of distinct words that match)."""
    t = norm(text)
    scored = []
    for key, th in THEMES.items():
        n = sum(1 for w in th["words"] if (" " + w) in t)
        if n:
            scored.append((-n, list(THEMES).index(key), key))
    return [k for _n, _i, k in sorted(scored)]


RAS = "Rien à signaler (RAS)"
RAS_WORDS = (" ras ", " rien a signaler ", " n a ", " na ", " none ", " nothing to report ")


def ras(text):
    """« Rien à signaler » in any usual spelling -> the one expression; officially every function can fail, so a RAS row
    stays an explicit choice of the team, justified in Failure Effect."""
    return RAS if norm(text) in RAS_WORDS else text


def block(keys, part_kinds=()):
    """The text added to « Prevention Controls », one practice per line, grouped by theme."""
    lines = [MARK]
    for key in keys:
        lines.append(THEMES[key]["label"] + " :")
        lines += ["• " + p for p in THEMES[key]["practices"]]
    extra = [PART_KINDS[k] for k in ("bought", "standard") if k in part_kinds]
    lines.append("Pour toute fonction :")
    lines += ["• " + p for p in extra + GENERAL]
    return "\n".join(lines)
