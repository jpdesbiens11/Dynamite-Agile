"""The Rover's costs in DEMO (0.60.61, D-O-070): Diamond → « Coûts et budget » filled like a real student project
that wants to become a kit for schools -- each of the 23 parts priced in prototype and at 100 / 1 000 / 10 000 kits, the
NRE (moulds, EMC test, fixtures…), the hours of the team valued at 25 $/h. Applied once per installation (journal
« demo_costs_loaded »), on a new DEMO as on one filled before; never on a Space where the team already wrote costs.
"""
import json

from core import audit, db

from .demo_example import DONE
from .headlamp import project_id

LOADED = "demo_costs_loaded"
SETTINGS = {"currency": "CAD", "proto_qty": 4, "volumes": [100, 1000, 10000], "contingency": 15.0, "labour_rate": 25.0,
            "notes": "Prix de 2026, taxes en sus. Prototype : achat à l'unité chez un distributeur ; 100 kits : tarifs par lots ; "
                     "1 000 et 10 000 kits : soumissions de deux fournisseurs, boîtier et pare-chocs moulés par injection."}
# part name -> (quantity per robot, prototype, 100, 1 000, 10 000, supplier, basis)
PRICES = {
    "Châssis d'auto téléguidée tout-terrain 1:16": (1, 56, 49, 41, 35, "Distributeur de modélisme", "soumission"),
    "Moteur de traction à balais (type 390)": (1, 9, 7, 5.5, 4.5, "Distributeur de modélisme", "soumission"),
    "Variateur à balais 20 A": (1, 14, 11, 9, 7.5, "Distributeur de modélisme", "estimation"),
    "Servo de direction 9 kg·cm": (1, 12, 9, 7, 6, "Distributeur de modélisme", "estimation"),
    "Raspberry Pi 4 (2 Go)": (1, 62, 58, 55, 53, "Distributeur autorisé", "soumission"),
    "Carte microSD 32 Go": (1, 9, 6, 4.5, 3.5, "Distributeur", "estimation"),
    "Batterie LiPo 2S 2 200 mAh, connecteur XT60": (1, 22, 17, 14, 12, "Distributeur de modélisme", "soumission"),
    "Convertisseur abaisseur 5 V 5 A": (1, 7, 5, 3.5, 2.8, "Distributeur électronique", "estimation"),
    "Moniteur de tension et courant INA219": (1, 4, 3, 1.8, 1.2, "Distributeur électronique", "estimation"),
    "Capteurs à ultrasons HC-SR04 (× 3)": (3, 2.5, 1.8, 1.2, 0.9, "Distributeur électronique", "estimation"),
    "Diviseurs de tension de l'écho (× 3)": (3, 0.3, 0.2, 0.1, 0.08, "Distributeur électronique", "estimation"),
    "Capteur à temps de vol VL53L1X": (1, 9, 7, 5, 4, "Distributeur électronique", "soumission"),
    "Centrale inertielle ICM-20948": (1, 11, 8, 6, 5, "Distributeur électronique", "estimation"),
    "Capteur à effet Hall et aimant sur l'arbre": (1, 2, 1.5, 1, 0.8, "Distributeur électronique", "estimation"),
    "Microrupteurs de pare-chocs (× 2)": (2, 0.8, 0.5, 0.3, 0.25, "Distributeur électronique", "estimation"),
    "Pare-chocs avant en PETG": (1, 3, 2.5, 1.2, 0.6, "Impression 3D, puis moulage", "estimation"),
    "Carte PWM PCA9685": (1, 4, 3, 2.2, 1.8, "Distributeur électronique", "estimation"),
    "MOSFET de coupure de la traction": (1, 1.5, 1, 0.6, 0.5, "Distributeur électronique", "estimation"),
    "Bouton d'arrêt d'urgence à verrouillage 16 mm": (1, 4, 3, 2, 1.6, "Distributeur électronique", "soumission"),
    "Plaque porte-modules en acrylique": (1, 6, 4, 2.5, 1.5, "Découpe laser", "soumission"),
    "Boîtier électronique avec joint": (1, 12, 8, 3, 1.8, "Impression 3D, puis moulage", "estimation"),
    "DEL RGB d'état": (1, 0.5, 0.3, 0.15, 0.1, "Distributeur électronique", "estimation"),
    "Visserie M3 et entretoises": (1, 3, 2, 1.2, 0.9, "Quincaillerie industrielle", "estimation"),
}
FREE = [("Boîte du kit, calage et notice imprimée", 1, 9, 6, 3.5, 2.2, "Imprimeur et cartonnier", "estimation"),
        ("Assemblage et test d'un robot (main-d'œuvre)", 1, 0, 18, 12, 8, "Atelier partenaire", "estimation")]
NRE = [
    ("Pré-balayage CEM (laboratoire de l'école)", "essais", "D", 600, "paye", "Laboratoire de l'école"),
    ("Essai CEM au laboratoire reconnu (ICES-003, FCC partie 15)", "essais", "D", 4500, "soumission", "Laboratoire accrédité"),
    ("Dossier de conformité : radio, batterie, RoHS", "certification", "D", 1200, "estimation", ""),
    ("Moule d'injection du boîtier électronique", "outillage", "D", 14000, "soumission", "Mouliste"),
    ("Moule d'injection du pare-chocs", "outillage", "D", 6500, "estimation", "Mouliste"),
    ("Gabarit de montage et banc de test de fin de ligne", "equipement", "D", 1800, "estimation", "Atelier de l'école"),
    ("Filament, acrylique et pièces de prototypes", "prototypes", "C", 350, "paye", "Distributeurs"),
    ("Outils et instruments (multimètre, pinces, fer à souder)", "equipement", "B", 280, "engage", "Distributeur électronique"),
    ("Photos et vidéo de la notice de montage", "autre", "D", 600, "estimation", ""),
]


def ensure_costs(ctx):
    """Once: the Rover's costs in DEMO. Returns the counts, or None."""
    conn = ctx.conn
    pid = project_id(conn)
    if pid is None:
        return None
    logged = lambda action: conn.execute("SELECT 1 FROM audit_log WHERE action = ? AND object_id = ?", (action, str(pid))).fetchone()  # noqa: E731
    if not logged(DONE) or logged(LOADED):
        return None
    from modules.diamond import costs as C
    has = lambda table: conn.execute("SELECT 1 FROM {} WHERE project_id = ?".format(table), (pid,)).fetchone()  # noqa: E731
    counts = {"nre": 0, "lines": 0}
    if not (has("diamond_cost_nre") or has("diamond_cost_parts") or has("diamond_cost_settings")):
        uid = ctx.user["id"]
        now = db.utc_now()
        conn.execute("INSERT INTO diamond_cost_settings (project_id, currency, proto_qty, volumes, contingency, labour_rate, notes, updated_by, "
                     "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (pid, SETTINGS["currency"], SETTINGS["proto_qty"], json.dumps(SETTINGS["volumes"]),
                                                                        SETTINGS["contingency"], SETTINGS["labour_rate"], SETTINGS["notes"], uid, now))
        for title, cat, phase, amount, basis, supplier in NRE:
            C.add_nre(conn, uid, pid, {"title": title, "category": cat, "phase": phase, "amount": float(amount), "basis": basis, "supplier": supplier})
            counts["nre"] += 1
        for r in conn.execute("SELECT id, name FROM diamond_parts WHERE project_id = ? ORDER BY position, number", (pid,)).fetchall():
            price = PRICES.get(r["name"])
            if price:
                q, proto, p1, p2, p3, supplier, basis = price
                C.add_line(conn, uid, pid, r["id"], {"qty": q, "proto_unit": proto, "prod_1": p1, "prod_2": p2, "prod_3": p3,
                                                      "supplier": supplier, "basis": basis})
                counts["lines"] += 1
        for name, q, proto, p1, p2, p3, supplier, basis in FREE:
            C.add_line(conn, uid, pid, None, {"name": name, "qty": q, "proto_unit": proto, "prod_1": p1, "prod_2": p2, "prod_3": p3,
                                               "supplier": supplier, "basis": basis})
            counts["lines"] += 1
    audit.log_action(conn, ctx.user["id"], LOADED, "project", pid, counts, None)
    return counts
