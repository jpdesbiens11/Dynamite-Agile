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
    "Peer design review (PDR, CDR) avec cette ligne du DFMEA sous les yeux",
    "Lessons learned : DFMEA et field returns d'un produit semblable ou précédent",
    "Proven design ou COTS part qualifiée plutôt qu'une technologie nouvelle, sauf raison chiffrée",
    "Requirement chiffrée et vérifiable dans le CdCF (Goldmine) pour cette fonction, avec sa tolerance",
]

THEMES = {
    "elec": {"label": "Electrical Safety", "subjects": ("elec", "ver"),
             "words": ("isol", "sous tension", "secteur", "electri", "tension", "courant", "fusib", "terre", "choc electr",
                       "alimentation", "bloc d alim", "insulat", "live", "mains", "voltage", "current", "earth", "shock"),
             "practices": [
                 "Clearances (air) et surface distances selon IEC 62368-1 ou IEC 60335-1, pour la working voltage et le pollution degree",
                 "Double insulation ou reinforced insulation entre le mains et les parties accessibles (Class II), ou protective earthing vérifié (Class I)",
                 "External power supply certifié CSA / UL (Class 2, ES1 / PS2) plutôt qu'une mains power supply intégrée",
                 "Overcurrent protection (fuse, PTC) dimensionnée sur le fault current",
                 "Derating des components : voltage ≤ 80 %, current ≤ 70-80 %, power ≤ 50-60 % du rating",
                 "Liste des safety-critical components, chacun certifié et figé (aucun remplacement sans review)",
                 "Single fault analysis : un component en short circuit ou open circuit ne rend pas le produit dangereux"]},
    "power": {"label": "Energy and Battery", "subjects": ("elec", "func", "env"),
              "words": ("energ", "distribu", "batter", "pile", "accumul", "lithium", "charg", "power", "supply"),
              "practices": [
                  "Power budget avec une margin d'au moins 20 % sur chaque power rail",
                  "Reverse polarity protection et overvoltage protection (diode, TVS) à chaque power input",
                  "Connectors avec poka-yoke (keyed), dimensionnés pour le current et le nombre de mating cycles prévus",
                  "Lithium battery : cells IEC 62133-2, battery protection circuit (overcharge, deep discharge, short circuit, temperature), transport UN 38.3",
                  "Decoupling et filtering au plus près de chaque IC"]},
    "therm": {"label": "Thermal", "subjects": ("therm", "elec", "env"),
              "words": ("chaleur", "therm", "temperat", "dissip", "refroid", "chauff", "ventil", "heat", "cool", "hot"),
              "practices": [
                  "Thermal budget calculé ou simulé, junction temperature au moins 20 °C sous le maximum du component",
                  "Touch temperature des surfaces selon IEC 62368-1 (TS1) ou IEC 60335-1, avec margin",
                  "Materials choisis selon leur Relative Thermal Index (RTI, UL 746B) au-delà de la température atteinte",
                  "Thermal protection (thermistor, thermal cut-off) qui met le produit en safe state",
                  "Thermal contact assuré et reproductible : thermal paste ou thermal pad spécifié, tightening torque, flatness",
                  "Temperature derating des components (derating curve du fabricant)"]},
    "emc": {"label": "EMC and Radio", "subjects": ("emc", "sw"),
            "words": ("commun", "radio", "sans fil", "bluetooth", "wifi", "antenn", "signal", "mli", "pwm", "horlog",
                      "wireless", "emission", "parasit", "interfer"),
            "practices": [
                "Ground plane continu, current loops courtes, layout rules (placement et routing) écrites",
                "Filtering au power input (ferrite, X / Y capacitors) et sur chaque cable qui sort de l'enclosure",
                "ESD protection (TVS) sur toute surface touchée et tout connector accessible (IEC 61000-4-2)",
                "Radio module pre-certified ISED / FCC avec l'antenna et le placement de son integration guide",
                "Switching frequency hors des bandes sensibles, slew rate limité ou spread spectrum"]},
    "sw": {"label": "Electronics and Software", "subjects": ("sw", "func"),
           "words": ("logiciel", "micrologiciel", "firmware", "software", "memor", "programm", "command", "regul", "calcul",
                     "detect", "capteur", "mesur", "application", "connexion", "donnee", "sensor", "control", "data"),
           "practices": [
               "Watchdog et safe state défini au démarrage, en défaut et à la perte de power",
               "IEC 60730-1 annexe H (Class B) si le software assure une safety function",
               "Coding rules (ex. MISRA C), code review et static analysis avant chaque version",
               "Unit tests et integration tests automatisés, rejoués à chaque modification",
               "Input validation, timeouts et retry automatique des communications",
               "Non-volatile memory protégée par CRC, écritures limitées à la write endurance de la memory",
               "Signed firmware update avec rollback possible à la version précédente",
               "Sensors : filtering et debounce, thresholds avec hysteresis, plausibility check de la mesure"]},
    "mech": {"label": "Structure and Mechanics", "subjects": ("mech", "ver", "life"),
             "words": ("poser", "tenir", "stab", "support", "structur", "base", "boitier", "fix", "assembl", "rigid", "porter",
                       "resist", "choc", "chute", "lest", "bascul", "enclos", "hold", "mount", "drop", "load"),
             "practices": [
                 "Safety factor d'au moins 2 sur les structural parts (3 pour un plastic chargé longtemps : creep)",
                 "Calcul ou FEA (finite element analysis) des pièces chargées, drop et shock compris",
                 "Tolerance stack-up (worst case ou RSS) sur chaque fit critique",
                 "Fillets, pas de sharp corner ni de notch dans une zone chargée (stress concentration)",
                 "Molded parts : wall thickness uniforme, ribs, draft angles, material choisi avec sa datasheet",
                 "Fasteners : torque spécifié, threadlocker ou washer, metal inserts dans le plastic",
                 "Stability : center of gravity bas, tip-over test sur un plan incliné selon la norme du produit"]},
    "life": {"label": "Moving Parts and Service Life", "subjects": ("life", "mech", "usab"),
             "words": ("orient", "tourn", "pivot", "articul", "charnier", "bouton", "glisser", "ressort", "moteur", "mouv",
                       "deplac", "usure", "cycle", "hinge", "button", "motor", "move", "wear"),
             "practices": [
                 "Service life spécifiée en cycles, avec une margin d'au moins 2 fois l'usage prévu",
                 "Materials appariés contre la wear (plastic sur metal, lubricant spécifié), pas deux plastics identiques en friction",
                 "Switches et buttons choisis pour un nombre de cycles connu (datasheet), avec debounce",
                 "Friction ou clamping réglable, wear compensation prévue",
                 "Pas de pinch point ni de shear point pour les doigts sur les moving parts (IEC 60335-1, art. 20)"]},
    "ingress": {"label": "Water, Dust and Environment", "subjects": ("ingress", "env"),
                "words": ("eau", "humid", "poussier", "etanch", "exterieur", "recouvr", "envelop", "joint", "proteg", "water",
                          "dust", "seal", "cover", "outdoor"),
                "practices": [
                    "IP rating visé dès le concept (IEC 60529) : gaskets, labyrinths et drainage paths dessinés",
                    "Conformal coating des PCB exposés à l'humidité",
                    "Materials stables aux UV, à l'humidité et aux produits ménagers",
                    "Membrane vent contre la condensation dans une enclosure fermée",
                    "Environmental tests IEC 60068 planifiés tôt (damp heat, cold, transport vibration)"]},
    "light": {"label": "Light and Optics", "subjects": ("func", "therm"),
              "words": ("lumi", "eclair", "del", "led", "optiq", "intensit", "temperature de couleur", "light"),
              "practices": [
                  "LED classées selon IEC 62471 (photobiological safety, risk group Exempt ou RG1)",
                  "Constant-current driver ; dimming sans flicker visible (IEEE 1789 : PWM frequency élevée)",
                  "Binning des LED pour une couleur constante d'un produit à l'autre",
                  "Lumen maintenance connue (L70, données LM-80 et projection TM-21) à la température réelle des LED"]},
    "mat": {"label": "Materials, Appearance and Compliance", "subjects": ("mat", "usab", "ver"),
            "words": ("plair", "allure", "aspect", "esthet", "couleur", "finition", "materi", "plastiq", "epure",
                      "look", "appearance", "finish", "material"),
            "practices": [
                "Materials conformes RoHS et REACH dès le choix, avec les supplier declarations",
                "Plastics UL 94 V-0 près des sources de chaleur et d'énergie, flammability class exigée par la norme ailleurs",
                "Color, gloss et texture fixés par des master samples et des appearance tolerances",
                "Scratch resistance, UV resistance et yellowing vérifiés sur le material retenu"]},
    "usab": {"label": "Usability and Ergonomics", "subjects": ("usab", "func"),
             "words": ("utilis", "user", "interface", "afficher", "indiqu", "regler", "ergonom", "prise en main", "toucher",
                       "touch", "display", "adjust"),
             "practices": [
                 "Usability engineering (IEC 62366-1, même hors médical) : use scenarios et use errors prévisibles",
                 "Poka-yoke : un seul sens possible pour brancher, poser ou assembler",
                 "Un user feedback (son, lumière, mouvement) pour chaque commande",
                 "Usability tests avec de vrais utilisateurs dès le premier prototype, puis à chaque itération",
                 "User manual clair et standard symbols (IEC 60417, ISO 7000)"]},
    "prod": {"label": "Manufacturing and Assembly", "subjects": ("prod", "ver"),
             "words": ("assembl", "fabri", "product", "montag", "manufact"),
             "practices": [
                 "DFM / DFA (méthode Boothroyd-Dewhurst) : moins de pièces, pièces symétriques ou avec poka-yoke",
                 "Poka-yoke à l'assembly : impossible de monter une pièce à l'envers",
                 "Special characteristics (CC / SC) reportées au Control Plan et au PFMEA",
                 "End-of-line test sur chaque produit"]},
}
PART_KINDS = {
    "bought": "Purchased part : datasheet lue en entier, supplier qualifié, second source identifiée",
    "standard": "Standard part (ISO, DIN) avec sa property class ou tolerance class spécifiée au drawing",
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
