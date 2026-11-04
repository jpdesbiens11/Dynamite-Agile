"""Project risks of the desk-lamp example (0.60.14, D-O-026): a high-level register written for Dynamite | Agile
(D-O-012) -- every category, a few actions with their residual risk, two technical risks sent to the DFMEA.
Functions are found by their text (tree of example.py)."""
from core.errors import ApiError

from . import risks as R

# (title, cause, consequence, category, phase, P, I, response, action, residual P, residual I, function text, to DFMEA)
LAMP = [
    ("Surchauffe des DEL dans la tête", "le dissipateur est trop petit pour 10 W de DEL",
     "baisse du flux lumineux, durée de vie réduite, boîtier trop chaud au toucher", "technique", "C", 4, 4, "reduire",
     "Simulation thermique et prototype instrumenté (thermocouples) avant la CDR", 2, 3, "Dissiper la chaleur des DEL", 1),
    ("Bluetooth instable près d'un routeur Wi-Fi", "la bande 2,4 GHz est encombrée au bureau",
     "commandes de l'application perdues, avis négatifs", "technique", "C", 3, 3, "reduire",
     "Essai de coexistence dans un bureau réel ; reprise automatique de la connexion", 2, 2,
     "Recevoir les commandes de l'application mobile", 1),
    ("Retard du fournisseur de bloc d'alimentation", "un seul fournisseur homologué pour le 12 V",
     "prototype D en retard de 4 semaines", "fournisseurs", "C", 3, 4, "reduire",
     "Qualifier un deuxième bloc d'alimentation déjà certifié", 2, 3, "Utiliser un bloc d'alimentation externe 12 V", 0),
    ("Certification CSA / UL plus longue que prévu", "le laboratoire n'a pas de place avant le lancement",
     "mise en marché reportée", "normes", "D", 3, 5, "reduire",
     "Réserver le laboratoire dès la PDR ; pré-essais CEM chez nous", 2, 4, "", 0),
    ("Coût des pièces au-dessus de la cible", "le bras articulé en aluminium coûte plus cher qu'estimé",
     "prix de vente non compétitif", "couts", "C", 3, 3, "reduire",
     "Matrice de Pugh bras aluminium / bras plastique renforcé", 2, 2, "Orienter la tête d'éclairage", 0),
    ("Boucles du MVP plus longues que prévu", "le MVP 0 cherche à valider trop d'hypothèses à la fois",
     "Concept Review et PDR repoussées", "delais", "B", 3, 3, "reduire",
     "Limiter le MVP 0 aux trois hypothèses les plus risquées du Lean Canvas", 2, 2, "", 0),
    ("Charge de cours de l'équipe en fin de session", "les examens tombent pendant la phase D",
     "essais de validation bâclés", "equipe", "D", 4, 3, "eviter",
     "Avancer les essais de validation de deux semaines dans le plan (Exploration)", 2, 2, "", 0),
    ("Le client préfère une commande vocale", "les entrevues de Discovery ont été faites auprès de trop peu d'utilisateurs",
     "application mobile peu utilisée", "marche", "B", 2, 3, "accepter",
     "Garder le bouton tactile comme commande principale ; revoir au MVP 1", None, None, "", 0),
    ("Brûlure en touchant la tête", "la température de surface dépasse la limite de la norme",
     "blessure de l'utilisateur, rappel du produit", "securite", "C", 2, 5, "reduire",
     "Limite de température en conception ; essai d'échauffement selon IEC 62368-1", 1, 5, "Protéger l'utilisateur, les composants et le bureau", 0),
]


def load(conn, user_id, pid):
    if conn.execute("SELECT 1 FROM diamond_risks WHERE project_id = ?", (pid,)).fetchone():
        raise ApiError(409, "Le registre de risques de ce Space n'est pas vide. Correctif : chargez l'exemple dans un Space neuf.")
    by_text = {r["text"]: r["id"] for r in conn.execute("SELECT id, text FROM diamond_functions WHERE project_id = ? AND archived = 0", (pid,))}
    for title, cause, cons, cat, phase, p, i, resp, action, rp, ri, ftext, dfmea in LAMP:
        R.create(conn, user_id, pid, {"title": title, "cause": cause, "consequence": cons, "category": cat, "phase": phase,
                                      "probability": p, "impact": i, "response": resp, "action": action, "residual_p": rp,
                                      "residual_i": ri, "function_id": by_text.get(ftext), "to_dfmea": dfmea,
                                      "status": "in_progress" if action and rp else "open"})
    return len(LAMP)
