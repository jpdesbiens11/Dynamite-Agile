"""The company part numbers of the Rover in DEMO (0.60.103, D-O-112): the BOM of its (fictitious) ERP, RVR-xxxx as in the
presentation, and the links the team kept from the answer of an AI assistant -- P-14 covers the bracket and the magnet,
P-5 the board and its software, P-21 the enclosure and its gasket; P-11 (the echo dividers, a small board made by the team)
is « à créer dans l'ERP ». Applied once per installation (journal « demo_pn_loaded »), after the characteristics; never on
a Space that already has a BOM.
"""
from core import audit, db

from .demo_characteristics import LOADED as CHARS_LOADED
from .demo_life import PREFIX
from .headlamp import project_id

LOADED = "demo_pn_loaded"
# (PN, rev, designation, supplier, material)
BOM = [
    ("RVR-1010-01", "", "Châssis 1:16 tout-terrain, transmission et roues", "Distributeur de modélisme", "PA66 chargé verre, acier"),
    ("RVR-1020-01", "", "Moteur à balais type 390", "Distributeur de modélisme", "—"),
    ("RVR-1040-02", "", "Servo de direction 9 kg·cm", "Distributeur de modélisme", "—"),
    ("RVR-1230-01", "", "Kit visserie M3 et entretoises", "Quincaillerie industrielle", "Acier zingué, laiton"),
    ("RVR-2200-04", "A", "Plaque porte-modules découpée laser", "Découpe laser", "PMMA 4 mm"),
    ("RVR-2210-01", "B", "Boîtier électronique", "Impression 3D puis moulage", "PETG, puis PC/ABS"),
    ("RVR-2211-01", "", "Cordon de joint du boîtier", "Distributeur", "EPDM 2 mm"),
    ("RVR-3100-01", "", "Capteur à ultrasons HC-SR04", "Distributeur électronique", "—"),
    ("RVR-3120-01", "", "Capteur ToF VL53L1X sur carte", "Distributeur électronique", "—"),
    ("RVR-3130-01", "", "Centrale inertielle ICM-20948 sur carte", "Distributeur électronique", "—"),
    ("RVR-3140-02", "C", "Support du capteur à effet Hall", "Impression 3D", "PETG"),
    ("RVR-3141-01", "", "Aimant néodyme Ø6 × 3 mm", "Distributeur", "NdFeB N42"),
    ("RVR-3150-02", "", "Microrupteur à levier", "Distributeur électronique", "—"),
    ("RVR-3160-01", "", "Pare-chocs avant", "Impression 3D puis moulage", "PETG, puis TPU"),
    ("RVR-5030-01", "", "Variateur à balais 20 A", "Distributeur de modélisme", "—"),
    ("RVR-5050-01", "", "Raspberry Pi 4 modèle B 2 Go", "Distributeur autorisé", "—"),
    ("RVR-SW-001", "v1.4", "Logiciel de navigation et d'évitement", "Équipe Rover", "—"),
    ("RVR-5060-01", "", "Carte microSD 32 Go avec image du logiciel", "Distributeur", "—"),
    ("RVR-5070-01", "", "Batterie LiPo 2S 2 200 mAh XT60", "Distributeur de modélisme", "—"),
    ("RVR-5080-01", "", "Convertisseur abaisseur 5 V 5 A", "Distributeur électronique", "—"),
    ("RVR-5090-02", "", "Moniteur de tension et courant INA219", "Distributeur électronique", "—"),
    ("RVR-5170-01", "", "Carte PWM PCA9685", "Distributeur électronique", "—"),
    ("RVR-5180-01", "", "MOSFET de coupure de traction sur carte", "Distributeur électronique", "—"),
    ("RVR-5190-03", "", "Bouton d'arrêt d'urgence à verrouillage 16 mm", "Distributeur électronique", "—"),
    ("RVR-5220-01", "", "DEL RGB d'état", "Distributeur électronique", "—"),
    ("RVR-9010-01", "", "Boîte du kit et calage", "Imprimeur et cartonnier", "Carton"),
    ("RVR-9020-01", "", "Notice de montage imprimée", "Imprimeur", "Papier"),
]
# Diamond part number -> [(PN, confidence, reason)]
LINKS = {
    1: [("RVR-1010-01", .95, "Même châssis 1:16, transmission et roues comprises")], 2: [("RVR-1020-01", .95, "Moteur type 390")],
    3: [("RVR-5030-01", .9, "Variateur à balais 20 A")], 4: [("RVR-1040-02", .95, "Servo 9 kg·cm")],
    5: [("RVR-5050-01", .95, "Raspberry Pi 4, 2 Go"), ("RVR-SW-001", .85, "Le logiciel embarqué tourne sur cette carte")],
    6: [("RVR-5060-01", .9, "Carte microSD 32 Go")], 7: [("RVR-5070-01", .95, "LiPo 2S 2 200 mAh XT60")],
    8: [("RVR-5080-01", .95, "Convertisseur 5 V 5 A")], 9: [("RVR-5090-02", .95, "INA219")], 10: [("RVR-3100-01", .9, "HC-SR04 (× 3 au montage)")],
    12: [("RVR-3120-01", .95, "VL53L1X")], 13: [("RVR-3130-01", .95, "ICM-20948")],
    14: [("RVR-3140-02", .9, "Support du capteur à effet Hall"), ("RVR-3141-01", .85, "L'aimant sur l'arbre fait partie de P-14")],
    15: [("RVR-3150-02", .9, "Microrupteur à levier (× 2 au montage)")], 16: [("RVR-3160-01", .95, "Pare-chocs avant")],
    17: [("RVR-5170-01", .95, "PCA9685")], 18: [("RVR-5180-01", .95, "MOSFET de coupure")], 19: [("RVR-5190-03", .95, "Bouton d'arrêt d'urgence 16 mm")],
    20: [("RVR-2200-04", .95, "Plaque porte-modules en acrylique")],
    21: [("RVR-2210-01", .95, "Boîtier électronique"), ("RVR-2211-01", .8, "Le joint du boîtier fait partie de P-21")],
    22: [("RVR-5220-01", .95, "DEL RGB")], 23: [("RVR-1230-01", .9, "Visserie M3 et entretoises")],
}
TODO = (11,)  # the echo dividers: a small board the team makes, not yet in the ERP


def ensure_pn(ctx):
    conn = ctx.conn
    pid = project_id(conn)
    if pid is None:
        return None
    logged = lambda action: conn.execute("SELECT 1 FROM audit_log WHERE action = ? AND object_id = ?", (action, str(pid))).fetchone()  # noqa: E731
    if not logged(CHARS_LOADED) or logged(LOADED):
        return None
    counts = {"bom": 0, "links": 0}
    if not conn.execute("SELECT 1 FROM diamond_company_parts WHERE project_id = ?", (pid,)).fetchone():
        lead = conn.execute("SELECT id FROM users WHERE username = ?", (PREFIX + "lea",)).fetchone()
        uid, now = (lead["id"] if lead else ctx.user["id"]), db.utc_now()
        ids = {}
        for pn, rev, designation, supplier, material in BOM:
            ids[pn] = conn.execute("INSERT INTO diamond_company_parts (project_id, pn, rev, designation, supplier, material, created_by, created_at, "
                                   "updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                   (pid, pn, rev, designation, supplier, material, uid, now, uid, now)).lastrowid
            counts["bom"] += 1
        parts = {r["number"]: r["id"] for r in conn.execute("SELECT id, number FROM diamond_parts WHERE project_id = ?", (pid,))}
        for number, links in LINKS.items():
            for pn, conf, reason in links:
                if number in parts:
                    conn.execute("INSERT INTO diamond_part_pns (project_id, part_id, company_part_id, source, confidence, reason, created_by, created_at) "
                                 "VALUES (?, ?, ?, 'ai', ?, ?, ?, ?)", (pid, parts[number], ids[pn], conf, reason, uid, now))
                    counts["links"] += 1
        for number in TODO:
            if number in parts:
                conn.execute("UPDATE diamond_parts SET erp_todo = 1 WHERE id = ?", (parts[number],))
    audit.log_action(conn, ctx.user["id"], LOADED, "project", pid, counts, None)
    return counts
