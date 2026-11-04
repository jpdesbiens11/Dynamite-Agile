"""Former French values of the Testing base (D-B-085), used once at start-up to rename in English what nobody
changed: the test statuses. EQUIPMENT_FR gives the French name of the default equipment (translation page)."""

STATUS_EN = {"Brouillon": "Draft", "En revue": "In Review", "Approuvé": "Approved", "Obsolète": "Obsolete"}
EQUIPMENT_FR = {
    "EQ-DAQ": "Acquisition de données (tension, courant, température)", "EQ-DMM": "Multimètre numérique (étalonné)",
    "EQ-SCOPE": "Oscilloscope", "EQ-PSU": "Alimentation de laboratoire",
    "EQ-WATT": "Analyseur de puissance (puissance absorbée, veille)", "EQ-MOHM": "Mégohmmètre (résistance d'isolement)",
    "EQ-HIPOT": "Testeur diélectrique (hipot)", "EQ-LEAK": "Testeur de courant de fuite / de contact",
    "EQ-GND": "Testeur de continuité de terre", "EQ-FINGER": "Doigt et calibres d'épreuve (IEC 61032)",
    "EQ-CLIM": "Enceinte climatique (température, humidité)", "EQ-TSHOCK": "Enceinte de chocs thermiques",
    "EQ-SALT": "Enceinte de brouillard salin", "EQ-DUST": "Enceinte de poussière (IP5X / IP6X)",
    "EQ-WATER": "Moyens d'essai eau (égouttement, aspersion, jet, immersion)", "EQ-VIB": "Pot vibrant (sinus, aléatoire)",
    "EQ-DROP": "Banc de chute", "EQ-IMPACT": "Marteau / bille d'impact", "EQ-FORCE": "Dynamomètre (poussée, traction, couple)",
    "EQ-CYCLE": "Banc d'endurance (boutons, charnières, mécanismes)", "EQ-IRCAM": "Caméra thermique",
    "EQ-TC": "Thermocouples et enregistreur", "EQ-EMC": "Laboratoire CEM (chambre, RSIL, générateurs)",
    "EQ-ESD": "Pistolet ESD (IEC 61000-4-2)", "EQ-XRF": "Analyseur XRF (dépistage RoHS)", "EQ-EOL": "Banc de fin de ligne",
}


def upgrade(conn):
    """Idempotent: statuses of every test still in French."""
    for fr, en in STATUS_EN.items():
        conn.execute("UPDATE testing_tests SET status = ? WHERE status = ?", (en, fr))
