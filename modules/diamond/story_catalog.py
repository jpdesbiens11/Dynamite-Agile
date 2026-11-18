"""Diamond · Storyline: the catalogue of the pictograms, for the AI (0.60.113, D-O-126).

The keys are drawn by tools/story_pictos.py; the palette (static/js/diamond/story_pictos.js) shows the same groups and names.
Here, for the prompts and the imports of an AI answer:
  CATALOG    groups of (key, French name, when to use it) -- written into the prompt of « ↔ IA » and of the Project Starter,
             so that the assistant draws every scene instead of leaving it empty;
  resolve()  a key, a French name or a usual English word -> the key (« battery », « Batterie », « soldier » -> batterie, soldat);
  ai_items() the pictograms of a scene written by an assistant: names resolved, an unknown one kept visible as a « question »
             pictogram with its word as label, missing positions laid out (people and objects on the ground line, the
             surroundings in the upper corners, ideas and irritants at the top) -- never an empty scene for a typo.
"""
import unicodedata

CATALOG = [
    ("Personnes", [
        ("adulte", "Adulte", "l'utilisateur, un client, une personne"),
        ("enfant", "Enfant", "un enfant, un jeune utilisateur"),
        ("aine", "Aîné", "une personne âgée, un usager fragile"),
        ("technicien", "Technicien", "opérateur, monteur, inspecteur, réparateur, personnel de maintenance"),
        ("groupe", "Groupe", "une équipe, du public, des personnes à proximité"),
        ("main", "Main", "un geste, une manipulation, un réglage à la main")]),
    ("Lieux", [
        ("maison", "Maison", "domicile, local, bâtiment, entrepôt"),
        ("cuisine", "Cuisine", "cuisine, salle de pause"),
        ("atelier", "Atelier", "fabricant, usine, poste de travail, banc d'assemblage, démontage"),
        ("bureau", "Bureau", "bureau, salle de contrôle, poste de supervision"),
        ("exterieur", "Extérieur", "dehors, site isolé, terrain, camp, base, nature"),
        ("route", "Route", "trajet, transport, livraison"),
        ("magasin", "Magasin", "point de vente, achat, distributeur")]),
    ("Objets", [
        ("produit", "Le produit", "LE produit de ce Space, à chaque scène où il paraît (taille 3 quand il est le sujet)"),
        ("telephone", "Téléphone", "téléphone, application, terminal portatif, télécommande"),
        ("ordinateur", "Ordinateur", "ordinateur, logiciel, diagnostic, banc de test, journal de données"),
        ("batterie", "Batterie", "batterie, cellule, pack, module d'énergie, niveau de charge"),
        ("prise", "Prise", "prise, chargeur, alimentation électrique, borne de recharge"),
        ("outil", "Outil", "outil, réparation, montage, maintenance"),
        ("colis", "Colis", "emballage, caisse, lot de pièces, expédition, stockage"),
        ("voiture", "Voiture", "voiture, camionnette, transport routier"),
        ("panier", "Panier", "achat, commande"),
        ("argent", "Argent", "prix, coût, budget, paiement"),
        ("horloge", "Temps", "durée, délai, attente, autonomie, fréquence"),
        ("notice", "Notice", "notice, procédure, manuel, étiquette, règlement")]),
    ("Environnement", [
        ("soleil", "Soleil, chaleur", "chaleur, été, température haute"),
        ("pluie", "Pluie", "pluie, humidité, intempéries"),
        ("froid", "Froid", "froid, gel, neige, soute froide, température basse"),
        ("nuit", "Nuit", "nuit, veille, mise en sommeil, stockage longue durée"),
        ("bruit", "Bruit", "bruit, alarme sonore, signal, vibrations"),
        ("eau", "Eau", "eau, liquide, fuite, immersion"),
        ("poussiere", "Poussière", "poussière, sable, saleté, contamination")]),
    ("Idées et ressentis", [
        ("idee", "Idée", "une idée de l'équipe"),
        ("question", "Question", "une question ouverte, un point à vérifier"),
        ("danger", "Danger", "risque, alarme, défaut, événement anormal"),
        ("content", "Content", "satisfaction, ce qui marche bien"),
        ("frustre", "Frustré", "irritant, frustration"),
        ("coeur", "J'aime", "ce que la personne apprécie"),
        ("mouvement", "Mouvement", "déplacement, flux, retour, étape suivante (entre deux pictogrammes)")]),
    ("Militaire et terrain", [
        ("soldat", "Soldat", "militaire, opérateur en mission, utilisateur de la défense"),
        ("blinde", "Véhicule blindé", "véhicule blindé, char, transport protégé"),
        ("camion", "Camion", "camion, logistique, convoi, ravitaillement"),
        ("helicoptere", "Hélicoptère", "hélicoptère, évacuation, transport par la voie des airs"),
        ("quadrirotor", "Quadrirotor", "engin télépiloté à rotors, quadricoptère, multirotor, plateforme sans équipage"),
        ("aile", "Voilure fixe", "engin télépiloté à ailes, plateforme sans équipage à voilure fixe, croisière, longue endurance"),
        ("tente", "Tente, bivouac", "camp, bivouac, abri de campagne"),
        ("drapeau", "Base, poste", "base, poste de commandement, point de rassemblement, objectif atteint"),
        ("radio", "Radio", "radio, liaison, transmission, communication"),
        ("generatrice", "Génératrice", "génératrice, groupe électrogène, carburant, énergie de campagne"),
        ("conteneur", "Conteneur", "conteneur, stockage au sol, armoire, abri technique"),
        ("carte", "Carte, GPS", "carte, position, navigation, itinéraire"),
        ("cible", "Objectif", "objectif, cible, zone de mission, précision"),
        ("jumelles", "Jumelles", "observation, surveillance, reconnaissance"),
        ("parachute", "Parachute", "largage, livraison par les airs"),
        ("bouclier", "Protection", "protection, sécurité, blindage, résistance"),
        ("montagne", "Montagne, terrain", "terrain accidenté, altitude, région isolée"),
        ("feu", "Feu", "feu, incendie, emballement thermique, surchauffe")]),
]
KEYS = tuple(key for _group, items in CATALOG for key, _name, _hint in items)
NAMES = {key: name for _group, items in CATALOG for key, name, _hint in items}
MOODS = {"idee", "question", "danger", "content", "frustre", "coeur"}
SKY = {"soleil", "pluie", "froid", "nuit"}
# usual words (French without accents, English) an assistant may write instead of the key
_ALIASES = {
    "adult": "adulte", "person": "adulte", "user": "adulte", "utilisateur": "adulte", "client": "adulte", "customer": "adulte",
    "child": "enfant", "kid": "enfant", "elder": "aine", "senior": "aine", "technician": "technicien", "operator": "technicien",
    "operateur": "technicien", "worker": "technicien", "group": "groupe", "team": "groupe", "equipe": "groupe", "people": "groupe",
    "hand": "main", "house": "maison", "home": "maison", "building": "maison", "kitchen": "cuisine", "workshop": "atelier",
    "factory": "atelier", "usine": "atelier", "fabricant": "atelier", "office": "bureau", "outdoor": "exterieur",
    "outside": "exterieur", "site": "exterieur", "tree": "exterieur", "arbre": "exterieur", "road": "route", "shop": "magasin",
    "store": "magasin", "product": "produit", "phone": "telephone", "smartphone": "telephone", "computer": "ordinateur",
    "laptop": "ordinateur", "pc": "ordinateur", "battery": "batterie", "cell": "batterie", "cellule": "batterie", "pack": "batterie",
    "plug": "prise", "charger": "prise", "chargeur": "prise", "tool": "outil", "wrench": "outil", "box": "colis", "package": "colis",
    "crate": "colis", "caisse": "colis", "car": "voiture", "van": "voiture", "cart": "panier", "basket": "panier", "money": "argent",
    "cost": "argent", "clock": "horloge", "time": "horloge", "temps": "horloge", "manual": "notice", "procedure": "notice",
    "sun": "soleil", "heat": "soleil", "chaleur": "soleil", "rain": "pluie", "cold": "froid", "snow": "froid", "neige": "froid",
    "night": "nuit", "moon": "nuit", "noise": "bruit", "sound": "bruit", "alarm": "bruit", "water": "eau", "dust": "poussiere",
    "sand": "poussiere", "idea": "idee", "ampoule": "idee", "warning": "danger", "risk": "danger", "risque": "danger",
    "alert": "danger", "happy": "content", "frustrated": "frustre", "angry": "frustre", "heart": "coeur", "love": "coeur",
    "arrow": "mouvement", "fleche": "mouvement", "movement": "mouvement", "motion": "mouvement",
    "soldier": "soldat", "militaire": "soldat", "military": "soldat", "tank": "blinde", "char": "blinde", "armored": "blinde",
    "armoured": "blinde", "truck": "camion", "lorry": "camion", "helicopter": "helicoptere", "quadcopter": "quadrirotor",
    "fixed-wing": "aile", "fixed wing": "aile", "fixedwing": "aile", "fixed_wing": "aile", "uav": "aile",
    "wing": "aile", "wings": "aile", "ailes": "aile", "aile fixe": "aile",
    "quadricoptere": "quadrirotor", "multirotor": "quadrirotor", "tent": "tente", "bivouac": "tente", "camp": "tente",
    "flag": "drapeau", "base": "drapeau", "talkie": "radio", "generator": "generatrice", "genset": "generatrice",
    "groupe electrogene": "generatrice", "container": "conteneur", "map": "carte", "gps": "carte", "target": "cible",
    "objectif": "cible", "binoculars": "jumelles", "shield": "bouclier", "protection": "bouclier", "mountain": "montagne",
    "terrain": "montagne", "fire": "feu", "flame": "feu", "incendie": "feu",
}


def _norm(text):
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.lower().replace("_", " ").replace("-", " ").split())


ALIASES = dict({_norm(name): key for key, name in NAMES.items()}, **{_norm(k): v for k, v in _ALIASES.items()},
               **{key: key for key in KEYS})


def resolve(word):
    """The key of a pictogram from its key, its French name or a usual word; None when unknown."""
    return ALIASES.get(_norm(word))


def prompt_text():
    """The catalogue and the way to compose a scene, for an assistant."""
    lines = ["PICTOGRAMMES DE LA STORYLINE -- chaque scène se dessine avec 3 à 8 pictogrammes de ce catalogue (la clé, pas un "
             "autre mot) ; une scène sans pictogramme reste vide à l'écran. Clé — nom : quand l'utiliser."]
    for group, items in CATALOG:
        lines.append("  {} : {}".format(group, " ; ".join("{} — {} : {}".format(k, n, h) for k, n, h in items)))
    lines.append("Composer une scène (items = [{p, x, y, s, f, t}]) : p = la clé ; t = une étiquette courte (40 caractères au plus) "
                 "qui dit ce que le pictogramme est DANS CETTE SCÈNE (« Lot de cellules », « Opérateur », « −40 °C ») ; x, y = le centre "
                 "en % de la scène 16:9 (x 10 à 90 de gauche à droite dans l'ordre de l'action, y 55 à 70 pour ce qui est au sol, "
                 "15 à 30 pour le ciel, la température et les idées, irritants, questions en haut à droite) ; s = 1 petit, 2 normal, "
                 "3 le sujet de la scène ; f = 1 pour retourner le pictogramme (une personne qui regarde vers la gauche). Pas deux "
                 "pictogrammes au même endroit : au moins 14 % d'écart en x sur une même ligne.")
    return "\n".join(lines)


def _spot(i, n, row):
    """A free place for the i-th of n pictograms without a position, on its row."""
    if row == "sky":
        return [14, 86, 30, 70][i % 4], 18
    if row == "mood":
        return 86 - 14 * (i % 4), 20 if i < 4 else 36
    xs = [50] if n == 1 else [round(12 + 76 * k / (n - 1), 1) for k in range(n)]
    return xs[i], [50, 68][i % 2]


def ai_items(items):
    """(items, unknown words) of a scene written by an assistant: keys resolved, positions laid out where missing."""
    if not isinstance(items, list):
        return [], []
    out, unknown = [], []
    for item in items:
        item = dict(item) if isinstance(item, dict) else {"p": item}
        word = item.get("p") or item.get("key") or item.get("picto") or ""
        key = resolve(word)
        if key is None:
            unknown.append(str(word)[:30])
            key, item["t"] = "question", str(item.get("t") or word)[:40]
        item["p"] = key
        item["t"] = " ".join(str(item.get("t") or "").split())[:40]
        out.append(item)
    rows = {"sky": [], "mood": [], "ground": []}
    for item in out:
        if not _placed(item):
            rows["sky" if item["p"] in SKY else "mood" if item["p"] in MOODS else "ground"].append(item)
    for row, group in rows.items():
        for i, item in enumerate(group):
            item["x"], item["y"] = _spot(i, len(group), row)
    return out, unknown


def _placed(item):
    try:
        float(item.get("x"))
        float(item.get("y"))
        return True
    except (TypeError, ValueError):
        return False
