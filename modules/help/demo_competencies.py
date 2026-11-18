"""The Rover's bricks and competencies in DEMO (0.60.116, D-O-129): the « Concept / Brique technologique » column filled with
standard bricks (the concept the industry already knows for the function -- a LiPo pack with its 5 V regulator, a single-board
computer, ultrasonic sensors…), two of them frozen at the PDR, and the grid of the competencies of every line rated as the
team of the Rover would: a student project where the embedded software and the mechanics carry most of the work, with the
five starter columns only (0.60.118, D-O-131). Applied once per installation (journal « demo_competencies_loaded »), only on a DEMO without any brick nor
rating -- never over what a team wrote.
"""
from core import audit, db

from .demo_example import DONE
from .headlamp import project_id

LOADED = "demo_competencies_loaded"
TRIMMED = "demo_competencies_trimmed"
# (name, kind, reference, functions by number, frozen text or "")
BRICKS = [
    ("Pack LiPo 2S avec régulateur 5 V", "existing", "Battery LiPo 2S 2 200 mAh, XT60 ; buck converter 5 V 5 A", [3, 29],
     "Pack LiPo 2S 2 200 mAh (XT60) et buck converter 5 V 5 A du commerce ; voltage surveillée par INA219. Retenu au PDR."),
    ("Ordinateur monocarte (SBC) Linux", "existing", "Raspberry Pi 4 (2 Go), Raspberry Pi OS Lite", [4, 7, 17, 18, 19, 20],
     "Raspberry Pi 4 (2 Go) sous Raspberry Pi OS Lite, Python 3 ; le software complet tourne sur la carte. Retenu au PDR."),
    ("Point d'accès Wi-Fi et application web", "existing", "Wi-Fi de la carte en mode point d'accès, page web servie par la carte", [5, 8, 28, 34], ""),
    ("Ultrasonic sensors de distance", "existing", "HC-SR04 × 3, diviseurs de tension de l'écho", [10, 15], ""),
    ("Sensor de distance ToF", "existing", "VL53L1X", [11], ""),
    ("IMU 9 axes", "existing", "ICM-20948", [12], ""),
    ("Encodeur de roue à effet Hall", "existing", "Sensor à effet Hall et aimant sur l'arbre", [13], ""),
    ("Bumper à microswitches", "to_define", "", [14], ""),
    ("Groupe moto-propulseur de RC car", "existing", "Drive motor à balais type 390, brushed ESC 20 A", [22, 23], ""),
    ("Direction par servomoteur", "existing", "Servo de direction 9 kg·cm", [25], ""),
    ("Chaîne d'emergency stop", "to_define", "Bouton à verrouillage et MOSFET de coupure", [27], ""),
    ("Chassis de RC car et plaque porte-modules", "existing", "Chassis 1:16 tout-terrain, plaque acrylic découpée au laser", [31], ""),
    ("Electronics enclosure IP54", "to_define", "", [32], ""),
    ("LED d'état RGB", "existing", "LED RGB pilotée par la carte", [35], ""),
]
# 0.60.118 (D-O-131): only the base of mechatronics (the starter columns MECH, PCB, FW, PWR, TEST) -- a student team of
# engineers, not a safety or certification department; « + » adds the others when the product needs them.
RATINGS = {
    3: {"PWR": 3, "TEST": 2}, 29: {"PCB": 2, "FW": 3}, 4: {"FW": 4}, 7: {"FW": 4}, 17: {"FW": 5, "TEST": 2},
    18: {"FW": 4, "TEST": 3}, 19: {"FW": 4, "TEST": 2}, 20: {"FW": 3}, 5: {"FW": 3, "TEST": 2}, 8: {"FW": 3}, 34: {"FW": 3},
    28: {"FW": 3, "TEST": 3}, 10: {"PCB": 2, "FW": 3, "MECH": 2, "TEST": 2}, 15: {"PCB": 3}, 11: {"PCB": 2, "FW": 3},
    12: {"FW": 3, "PCB": 2, "MECH": 1}, 13: {"PCB": 2, "FW": 2, "MECH": 2}, 14: {"MECH": 4, "PCB": 1, "TEST": 3},
    22: {"PWR": 3, "FW": 3}, 23: {"MECH": 4, "TEST": 2}, 25: {"MECH": 3, "FW": 2}, 27: {"PWR": 3, "TEST": 4}, 31: {"MECH": 5},
    32: {"MECH": 4, "TEST": 3}, 35: {"PCB": 1, "FW": 1},
}
STAFF = {"FW": (1, "Interne : un étudiant en génie logiciel à temps plein"), "MECH": (1, "Interne"),
         "TEST": (0.5, "Stage d'été")}


def ensure_competencies(ctx):
    """Once: the Rover's bricks, two frozen, and the ratings of its lines. Returns the counts, or None."""
    conn = ctx.conn
    pid = project_id(conn)
    if pid is None:
        return None
    logged = lambda action: conn.execute("SELECT 1 FROM audit_log WHERE action = ? AND object_id = ?", (action, str(pid))).fetchone()  # noqa: E731
    if not logged(DONE) or logged(LOADED):
        return None
    from modules.diamond import competencies as CP
    from modules.diamond import concepts as CO
    counts = {"bricks": 0, "lines": 0}
    has = lambda table: conn.execute("SELECT 1 FROM {} WHERE project_id = ?".format(table), (pid,)).fetchone()  # noqa: E731
    if not (has("diamond_concepts") or has("diamond_competency_ratings")):
        uid, now = ctx.user["id"], db.utc_now()
        ids = {r["number"]: r["id"] for r in conn.execute("SELECT id, number FROM diamond_functions WHERE project_id = ? AND archived = 0", (pid,))}
        for name, kind, ref, numbers, frozen in BRICKS:
            fids = [ids[n] for n in numbers if n in ids]
            if not fids:
                continue
            cid = CO.add(conn, uid, pid, {"name": name, "kind": kind, "reference": ref, "status": "selected" if frozen else "exploring"}, fids)
            if frozen:
                conn.execute("UPDATE diamond_concepts SET frozen = 1, frozen_text = ?, frozen_by = ?, frozen_at = ? WHERE id = ?",
                             (frozen, uid, now, cid))
            counts["bricks"] += 1
        for number, ratings in RATINGS.items():
            if number in ids:
                CP.write_line(conn, uid, pid, ids[number], ratings)
                counts["lines"] += 1
        for code, (people, note) in STAFF.items():
            conn.execute("INSERT OR IGNORE INTO diamond_competency_staff (project_id, code, people, note, updated_by, updated_at) "
                         "VALUES (?, ?, ?, ?, ?, ?)", (pid, code, people, note, uid, now))
    audit.log_action(conn, ctx.user["id"], LOADED, "project", pid, counts, None)
    return counts


def trim_competencies(ctx):
    """Once (0.60.118, D-O-131): a DEMO loaded with the 14 columns of 0.60.116 keeps only the starter columns -- the ratings and
    the people of the other competencies leave the Rover --, unless someone already chose its columns. Returns the counts, or None."""
    conn = ctx.conn
    pid = project_id(conn)
    if pid is None:
        return None
    logged = lambda action: conn.execute("SELECT 1 FROM audit_log WHERE action = ? AND object_id = ?", (action, str(pid))).fetchone()  # noqa: E731
    if not logged(LOADED) or logged(TRIMMED):
        return None
    from modules.diamond import competencies as CP
    counts = {"ratings": 0, "staff": 0, "skipped": CP.customized(conn, pid)}
    keep = CP.starters(conn)
    if keep and not counts["skipped"]:
        marks = ", ".join("?" * len(keep))
        for table, key in (("diamond_competency_ratings", "ratings"), ("diamond_competency_staff", "staff")):
            counts[key] = conn.execute("DELETE FROM {} WHERE project_id = ? AND code NOT IN ({})".format(table, marks),
                                       (pid, *keep)).rowcount
    audit.log_action(conn, ctx.user["id"], TRIMMED, "project", pid, counts, None)
    return counts
