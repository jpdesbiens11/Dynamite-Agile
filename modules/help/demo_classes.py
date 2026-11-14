"""The classes CC / SC of the Rover in DEMO (0.60.101, D-O-108): what the team decided at the CDR (sprint 6, week 12) on the
proposals of the rule -- three CC (the stop before contact, the emergency stop, the battery cut-off), four SC (the gasket
groove, the corners of the plate, the air gap of the Hall sensor, the travel of the bumper) and five refusals with their
reason (a refusal is kept). Three CC proposals are left to decide (F28, F1, F26): the « CC proposées » filter shows them,
on purpose -- the tool shows its gaps. Customer: generic AIAG (a student kit, no OEM).
Applied once per installation (journal « demo_classes_loaded »), after the Rover in motion (demo_life, its accounts);
a row a person already decided is never touched.
"""
from core import audit

from .demo_life import LIFE_DONE, PREFIX, Clock
from .headlamp import project_id

LOADED = "demo_classes_loaded"
# (function number, start of the failure mode, decision CC | SC | refused, who, day of week 12, reason)
DECISIONS = [
    (18, "Arrêt trop tardif", "CC", "alexis", 1, "Peut blesser une personne : l'arrêt avant le contact est la fonction de sécurité du robot (REQ-2)."),
    (27, "La traction n'est pas coupée", "CC", "lea", 1, "Sécurité des personnes : l'arrêt d'urgence doit couper la traction en 0,2 s au plus (REQ-7)."),
    (29, "Décharge profonde", "CC", "lea", 1, "Batterie LiPo gonflée, risque d'incendie : la coupure à 3,4 V par élément est une exigence de sécurité (REQ-19)."),
    (32, "Eau sur le Raspberry Pi", "SC", "hugo", 1, "Fonction IPX4 (REQ-11) : la gorge du joint du boîtier est une cote à tenir en fabrication."),
    (31, "Plaque fissurée", "SC", "nina", 1, "Tenue à la chute de 0,5 m (REQ-23) : le rayon des coins de la plaque se tient à la découpe."),
    (13, "Impulsions manquées", "SC", "lea", 2, "Fonction de vitesse : l'entrefer entre l'aimant et le capteur à effet Hall décide si les impulsions sont lues."),
    (14, "Contact non détecté", "SC", "hugo", 2, "Le pare-chocs est la dernière protection avant un contact : sa course d'enclenchement se règle au montage."),
    (10, "Obstacle non détecté", "refused", "alexis", 2, "La détection dépend de la surface de l'obstacle, pas d'une cote qu'on fabrique : couverte par l'arrêt "
     "avant le contact (F18, CC) et par le pare-chocs (F14, SC)."),
    (10, "Distance fausse", "refused", "alexis", 2, "Cause logicielle (deux capteurs émettent en même temps), corrigée par le séquencement des mesures : "
     "rien à contrôler en fabrication."),
    (11, "Mesure saturée", "refused", "lea", 2, "Limite d'environnement du capteur à temps de vol, couverte par les ultrasons : aucune caractéristique "
     "de produit à tenir."),
    (3, "Chute de tension", "refused", "lea", 2, "Corrigé en conception (rampe de 0,5 s, condensateur de 1 000 µF, ECN du sprint 5) et vérifié par essai : "
     "aucune cote qui varie en production."),
    (6, "Consigne reçue en retard", "refused", "alexis", 2, "Dépend de l'encombrement Wi-Fi du lieu, pas d'une caractéristique du produit ; l'arrêt sur "
     "perte de liaison (F28) protège."),
]


def _rows(conn, pid):
    return [dict(r) for r in conn.execute(
        "SELECT d.id, d.failure_mode, d.severity, d.occurrence, d.class_state, f.number AS fn FROM diamond_dfmea d "
        "JOIN diamond_functions f ON f.id = d.function_id WHERE d.project_id = ? ORDER BY d.position, d.id", (pid,))]


def ensure_classes(ctx, today=None):
    """Once: the class decisions of the Rover's CDR. Returns the counts, or None (no DEMO, no Rover in motion, already done)."""
    conn = ctx.conn
    pid = project_id(conn)
    if pid is None:
        return None
    logged = lambda action: conn.execute("SELECT 1 FROM audit_log WHERE action = ? AND object_id = ?", (action, str(pid))).fetchone()  # noqa: E731
    if not logged(LIFE_DONE) or logged(LOADED):
        return None
    from modules.diamond import classes as CL
    clock, rules = Clock(today), CL.rules(conn, pid)
    people = {r["username"][len(PREFIX):]: r["id"] for r in conn.execute("SELECT id, username FROM users WHERE username LIKE ?", (PREFIX + "%",))}
    rows = _rows(conn, pid)
    counts = {"confirmed": 0, "refused": 0, "kept": 0}
    for number, mode, decision, who, day, reason in DECISIONS:
        row = next((r for r in rows if r["fn"] == number and r["failure_mode"].startswith(mode)), None)
        if row is None:
            continue
        if row["class_state"]:
            counts["kept"] += 1  # a person decided already: never replaced
            continue
        code = CL.propose(row["severity"], row["occurrence"], rules) if decision == "refused" else decision
        if not code:
            continue
        state = "refused" if decision == "refused" else "confirmed"
        uid, at = people.get(who) or ctx.user["id"], clock.iso(12, day, 14)
        conn.execute("UPDATE diamond_dfmea SET class_code = ?, class_state = ?, class_by = ?, class_at = ?, class_reason = ?, "
                     "class_severity = ?, class_occurrence = ? WHERE id = ?",
                     (code, state, uid, at, reason, row["severity"], row["occurrence"], row["id"]))
        conn.execute("INSERT INTO diamond_class_decisions (project_id, dfmea_id, class_code, state, severity, occurrence, reason, "
                     "decided_by, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (pid, row["id"], code, state, row["severity"], row["occurrence"], reason, uid, at))
        counts[state] += 1
    audit.log_action(conn, ctx.user["id"], LOADED, "project", pid, counts, None)
    return counts
