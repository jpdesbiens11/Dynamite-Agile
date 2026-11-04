"""DFMEA of the desk-lamp example (0.60.15, D-O-027): seven failure chains on the functions of the tree, written for
Dynamite | Agile (D-O-012), with one AP High, one Medium and the rest Low, two of them coming from the project risks.
Functions and risks are found by their text (example.py, example_risks.py)."""
from core.errors import ApiError

from . import dfmea as DF

HIGHER = "Utilisateur et lampe de bureau"
# (focus, lower, function text, requirement, failure mode, effect, S, cause, prevention, O, detection, D, action, risk title)
LAMP = [
    ("Tête d'éclairage", "Dissipateur en aluminium", "Dissiper la chaleur des DEL", "Jonction des DEL ≤ 85 °C à 25 °C ambiant",
     "Chaleur mal dissipée", "Flux lumineux réduit, durée de vie raccourcie, tête chaude", 7, "Surface d'ailettes trop petite",
     "Calcul thermique, règle de conception de 1 cm² par watt", 5, "Prototype instrumenté (thermocouples), essai d'échauffement", 4,
     "Agrandir le dissipateur de 30 %, puis refaire l'essai", "Surchauffe des DEL dans la tête"),
    ("Tête d'éclairage", "Interface thermique", "Dissiper la chaleur des DEL", "Résistance thermique ≤ 1 K/W",
     "Contact thermique insuffisant", "Surchauffe locale des DEL, perte de flux", 7, "Pâte thermique mal appliquée au montage",
     "Instruction de montage", 4, "Inspection visuelle", 7, "Coussin thermique prédécoupé à la place de la pâte", ""),
    ("Carte de commande", "Pilote des DEL (MLI)", "Régler l'intensité", "Intensité de 5 à 100 % sans scintillement visible",
     "Scintillement à faible intensité", "Fatigue visuelle de l'utilisateur", 5, "Fréquence MLI trop basse (< 1 kHz)",
     "Pilote choisi à 20 kHz ou plus", 3, "Mesure à l'oscilloscope et à la caméra", 3, "", ""),
    ("Carte de commande", "Module Bluetooth", "Recevoir les commandes de l'application mobile", "Commande reçue en moins de 300 ms à 10 m",
     "Commande perdue", "L'application ne commande plus la lampe", 5, "Brouillage 2,4 GHz par le Wi-Fi du bureau",
     "Reprise automatique de la connexion", 5, "Essai de coexistence dans un bureau réel", 5, "", "Bluetooth instable près d'un routeur Wi-Fi"),
    ("Bloc d'alimentation", "Connecteur 12 V", "Utiliser un bloc d'alimentation externe 12 V", "Fiche bien tenue, 12 V ± 5 %",
     "Contact intermittent", "La lampe s'éteint en cours d'usage", 6, "Fiche à tolérance trop large",
     "Fiche normalisée 5,5 × 2,1 mm", 3, "Essai d'arrachement et de vibration", 4, "", ""),
    ("Boîtier", "Surface extérieure de la tête", "Protéger l'utilisateur, les composants et le bureau",
     "Température des surfaces accessibles sous la limite de la norme (IEC 62368-1)", "Surface trop chaude", "Brûlure de l'utilisateur",
     9, "Dissipateur exposé sans écran", "Écran isolant, distance minimale aux DEL", 3, "Essai d'échauffement selon IEC 62368-1", 3, "", ""),
    ("Base", "Lest en acier", "Reposer sur une base lestée", "Ne bascule pas, bras tendu, sur un plan incliné de 10°", "La lampe bascule",
     "Chute, tête abîmée", 6, "Masse du lest insuffisante", "Calcul du centre de gravité", 4, "Essai de stabilité sur plan incliné", 3, "", ""),
]


def load(conn, user_id, pid):
    if conn.execute("SELECT 1 FROM diamond_dfmea WHERE project_id = ?", (pid,)).fetchone():
        raise ApiError(409, "Le DFMEA de ce Space n'est pas vide. Correctif : chargez l'exemple dans un Space neuf.")
    fns = {r["text"]: r["id"] for r in conn.execute("SELECT id, text FROM diamond_functions WHERE project_id = ? AND archived = 0", (pid,))}
    if "Éclairer une surface de travail" not in fns:
        raise ApiError(409, "L'arbre de ce Space n'est pas celui de l'exemple (lampe de bureau). Correctif : chargez d'abord l'exemple de l'arbre.")
    risks = {r["title"]: r["id"] for r in conn.execute("SELECT id, title FROM diamond_risks WHERE project_id = ? AND archived = 0", (pid,))}
    for focus, lower, ftext, req, mode, effect, s, cause, prev, o, det, d, action, risk in LAMP:
        DF.insert(conn, user_id, pid, {"higher": HIGHER, "focus": focus, "lower": lower, "function_id": fns.get(ftext), "requirement": req,
                                       "failure_mode": mode, "effect": effect, "severity": s, "cause": cause, "prevention": prev,
                                       "occurrence": o, "detection_ctrl": det, "detection": d, "action": action, "risk_id": risks.get(risk)})
    return len(LAMP)
