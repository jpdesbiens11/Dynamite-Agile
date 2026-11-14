"""The characteristics C-n of the Rover in DEMO (0.60.102, D-O-110): the exact dimension, threshold or time behind the
rows of its DFMEA, as the team wrote them after the CDR -- 21 characteristics, the 7 whose row carries a confirmed class
being those of the presentation: C-05, C-08, C-10 (CC) and C-14, C-16, C-20, C-21 (SC). C-09 waits for the decision on
its proposed CC (F28); C-17 is a process characteristic (the torque of the pinion screw, for the PFMEA). Customer: generic
AIAG. Applied once per installation (journal « demo_characteristics_loaded »), after the classes of the CDR
(demo_classes); never on a Space whose team already wrote characteristics.
"""
from core import audit

from .demo_classes import LOADED as CLASSES_LOADED
from .demo_life import PREFIX
from .headlamp import project_id

LOADED = "demo_characteristics_loaded"
SW = "RVR-SW-001 v1.4 (spécification logicielle)"
SCH = "RVR-5000 rév. D (schéma électrique)"
# (number, function, start of the failure mode, nature, label, specification, part, second part, drawing, sheet, zone,
#  datum, control, note); specification: {nominal, tol | tol_plus / tol_minus, lsl, usl, unit, prefix, spec_text}
ITEMS = [
    (1, 10, "Obstacle non détecté", "product", "Portée de détection d'un obstacle de 10 cm", {"lsl": "0,05", "usl": "2,00", "unit": "m"},
     10, None, SW, "", "§ 2.1", "", "design", ""),
    (2, 10, "Distance fausse", "product", "Erreur de la distance mesurée", {"usl": "3", "unit": "cm"}, 10, None, SW, "", "§ 2.2", "", "design", ""),
    (3, 11, "Mesure saturée", "product", "Portée du capteur à temps de vol dans l'axe", {"lsl": "0,04", "usl": "2,00", "unit": "m"},
     12, None, SW, "", "§ 2.3", "", "design", ""),
    (4, 18, "Vitesse trop élevée", "product", "Vitesse à moins de 1,2 m d'un obstacle", {"usl": "0,3", "unit": "m/s"}, 5, None, SW, "", "§ 3.1", "",
     "design", ""),
    (5, 18, "Arrêt trop tardif", "product", "Temps de boucle de décision", {"usl": "50", "unit": "ms"}, 5, None, SW, "", "§ 3.2", "", "test100",
     "Mesuré sur chaque robot en fin de ligne (banc d'arrêt), journalisé avec le numéro de série."),
    (6, 3, "Chute de tension", "product", "Tension d'alimentation 5 V sous 3 A", {"nominal": "5,00", "tol": "0,25", "unit": "V"}, 8, None, SCH, "1",
     "B2", "", "design", ""),
    (7, 20, "Dérive du cap", "product", "Écart de cap à la reprise", {"usl": "15", "unit": "°"}, 5, None, SW, "", "§ 3.4", "", "design", ""),
    (8, 27, "La traction n'est pas coupée", "product", "Temps de coupure de la traction", {"usl": "0,20", "unit": "s"}, 18, 19, SCH, "2", "C4", "",
     "test100", "Essai de l'arrêt d'urgence sur chaque robot en fin de ligne, journalisé avec le numéro de série."),
    (9, 28, "Le robot continue", "product", "Temps d'arrêt sur perte de liaison", {"usl": "0,5", "unit": "s"}, 18, None, SW, "", "§ 4.1", "",
     "test100", "La CC proposée par la règle (S 9) attend sa décision."),
    (10, 29, "Décharge profonde", "product", "Seuil de coupure de la batterie", {"nominal": "3,40", "tol": "0,02", "unit": "V",
                                                                                 "spec_text": "par élément, lu par l'INA219"},
     9, None, SCH, "3", "A2", "", "spc", ""),
    (11, 2, "Démarrage trop long", "product", "Temps de démarrage", {"usl": "60", "unit": "s"}, 5, None, SW, "", "§ 1.2", "", "design", ""),
    (12, 6, "Consigne reçue en retard", "product", "Latence des consignes du téléphone", {"usl": "100", "unit": "ms"}, 5, None, SW, "", "§ 5.1", "",
     "design", ""),
    (13, 12, "Mesure du cap bruitée", "product", "Dérive du cap en 30 s", {"usl": "2", "unit": "°"}, 13, None, SW, "", "§ 2.5", "", "design", ""),
    (14, 13, "Impulsions manquées", "product", "Entrefer aimant–capteur", {"nominal": "2,0", "tol": "0,3", "unit": "mm"}, 14, 1, "RVR-3140-02 rév. C",
     "1", "B3", "A (semelle)", "spc", "La cote se porte sur le support du capteur ; l'arbre de roue (P-1) est cité."),
    (15, 9, "Angle mort", "product", "Couverture des capteurs", {"spec_text": "Aucun angle mort à ± 45° au-delà de 0,3 m"}, 10, None, SW, "", "§ 2.4", "",
     "design", ""),
    (16, 14, "Contact non détecté", "product", "Course d'enclenchement du pare-chocs", {"nominal": "1,0", "tol": "0,2", "unit": "mm"}, 16, 15,
     "RVR-3160-01 rév. A", "1", "C2", "B", "spc", ""),
    (17, 23, "Pignon qui saute", "process", "Couple de serrage de la vis du pignon", {"nominal": "0,8", "tol": "0,1", "unit": "N·m"}, 2, 1,
     "RVR-1010-01 (gamme de montage)", "", "OP20", "", "spc", "Caractéristique de procédé : elle ira au PFMEA."),
    (18, 25, "Angle différent", "product", "Écart d'angle de braquage", {"usl": "3", "unit": "°"}, 4, None, SW, "", "§ 3.3", "", "design", ""),
    (19, 34, "Télémétrie trop lente", "product", "Rafraîchissement de la télémétrie", {"lsl": "5", "unit": "Hz"}, 5, None, SW, "", "§ 5.2", "",
     "design", ""),
    (20, 31, "Plaque fissurée", "product", "Rayon des coins de la plaque", {"lsl": "3,0", "unit": "mm", "prefix": "R"}, 20, None, "RVR-2200-04 rév. A",
     "1", "A1", "A", "spc", ""),
    (21, 32, "Eau sur le Raspberry Pi", "product", "Profondeur de gorge du joint", {"nominal": "1,50", "tol": "0,05", "unit": "mm"}, 21, None,
     "RVR-2210-01 rév. B", "2", "B2", "A", "spc", ""),
]


def ensure_characteristics(ctx):
    """Once: the 21 characteristics of the Rover. Returns the counts, or None (no DEMO, classes not loaded, already done)."""
    conn = ctx.conn
    pid = project_id(conn)
    if pid is None:
        return None
    logged = lambda action: conn.execute("SELECT 1 FROM audit_log WHERE action = ? AND object_id = ?", (action, str(pid))).fetchone()  # noqa: E731
    if not logged(CLASSES_LOADED) or logged(LOADED):
        return None
    from modules.diamond import char_spec as SP, characteristics as CH
    counts = {"made": 0, "skipped": 0}
    if not conn.execute("SELECT 1 FROM diamond_characteristics WHERE project_id = ?", (pid,)).fetchone():
        lead = conn.execute("SELECT id FROM users WHERE username = ?", (PREFIX + "nina",)).fetchone()
        uid = lead["id"] if lead else ctx.user["id"]
        rows = [dict(r) for r in conn.execute("SELECT d.id, d.failure_mode, d.test_id, f.number AS fn FROM diamond_dfmea d "
                                              "JOIN diamond_functions f ON f.id = d.function_id WHERE d.project_id = ?", (pid,))]
        parts = {r["number"]: r["id"] for r in conn.execute("SELECT id, number FROM diamond_parts WHERE project_id = ?", (pid,))}
        for number, fn, mode, nature, label, spec, part, part2, drawing, sheet, zone, datum, control, notes in ITEMS:
            row = next((r for r in rows if r["fn"] == fn and r["failure_mode"].startswith(mode)), None)
            if row is None or part not in parts:
                counts["skipped"] += 1
                continue
            fields = dict(SP.limits({k: v for k, v in spec.items() if k not in ("unit", "prefix", "spec_text")}, {}) or {},
                          number=number, dfmea_id=row["id"], nature=nature, label=label, unit=spec.get("unit", ""), prefix=spec.get("prefix", ""),
                          spec_text=spec.get("spec_text", ""), part_id=parts[part], part2_id=parts.get(part2), drawing=drawing, sheet=sheet,
                          zone=zone, datum=datum, control=control, test_id=row["test_id"], notes=notes)
            CH.insert(conn, uid, pid, fields)
            counts["made"] += 1
    audit.log_action(conn, ctx.user["id"], LOADED, "project", pid, counts, None)
    return counts
