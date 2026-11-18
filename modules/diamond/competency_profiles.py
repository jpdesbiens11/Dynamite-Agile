"""Diamond · profiles of the competency grid (0.60.119, D-O-132): a team picks the set of columns its product needs in one go --
mechatronics, electronics and power, embedded software, mechanics and structure, battery and energy storage, regulated product,
industrialisation -- instead of adding them one by one with « + ». Applying a profile replaces the columns of the grid of the
Space: the ratings of the columns that leave are erased (the page asks first, with their number), the people planned for them
stay in the summary. Journalled like a column removed (the grid then counts as chosen by the team).
"""
from core import audit
from core.errors import ApiError

from . import competencies as CP
from . import functions as F

ACTION = "diamond_competency_profile"
# (key, name, what it is for, codes in the order of the grid) -- every code is in the default catalogue (data_competencies.py)
PROFILES = [
    ("mechatronics", "Mécatronique", "Un produit qui bouge, mesure et se pilote : la base d'une équipe d'ingénierie.",
     ("MECH", "PCB", "FW", "PWR", "TEST")),
    ("electronics", "Électronique et puissance", "Cartes, conversion d'énergie, faisceaux et leur thermique.",
     ("PCB", "PWR", "HARN", "THERM", "TEST")),
    ("software", "Logiciel embarqué", "Le produit est surtout du firmware et son architecture.",
     ("FW", "SYS", "PCB", "TEST")),
    ("mechanics", "Mécanique et structure", "Pièces, tenue mécanique, thermique et fabrication.",
     ("MECH", "FEA", "THERM", "MFG", "TEST")),
    ("energy", "Batterie et stockage d'énergie", "Cellules, modules, puissance et sécurité des personnes.",
     ("CELL", "PWR", "THERM", "SAFE", "TEST")),
    ("regulated", "Produit réglementé", "Un produit à certifier : sécurité (TR), conformité et qualité en plus de la base.",
     ("MECH", "PCB", "FW", "SAFE", "CERT", "QUAL", "TEST")),
    ("industrial", "Industrialisation", "Passer du prototype à la série : fabrication, procédés spéciaux, contrôle.",
     ("MECH", "MFG", "SPEC", "QUAL", "TEST")),
]
BY_KEY = {p[0]: p for p in PROFILES}


def profiles(conn, current):
    """[{key, name, summary, codes, current}] -- the codes still active in the catalogue; « current » when the grid is exactly it."""
    active = {c["code"] for c in CP.catalog(conn, active_only=True)}
    out = []
    for key, name, summary, codes in PROFILES:
        kept = [c for c in codes if c in active]
        out.append({"key": key, "name": name, "summary": summary, "codes": kept, "current": kept == list(current)})
    return out


def api_apply(ctx):
    """{profile}: the columns of the grid of this Space become those of the profile; the ratings of the others are erased."""
    pid = F.access(ctx, "editor")
    key = str(ctx.body.get("profile") or "").strip()
    if key not in BY_KEY:
        raise ApiError(400, "Profil « {} » inconnu. Correctif : {}.".format(key[:20], ", ".join(BY_KEY)))
    codes = next(p["codes"] for p in profiles(ctx.conn, []) if p["key"] == key)
    if not codes:
        raise ApiError(409, "Toutes les compétences du profil « {} » sont désactivées dans le catalogue. Correctif : un administrateur "
                            "les réactive, ou choisissez un autre profil.".format(BY_KEY[key][1]))
    marks = ", ".join("?" * len(codes))
    removed = ctx.conn.execute("DELETE FROM diamond_competency_ratings WHERE project_id = ? AND code NOT IN ({})".format(marks),
                               (pid, *codes)).rowcount
    CP.save_columns(ctx.conn, pid, codes)
    audit.log_action(ctx.conn, ctx.user["id"], ACTION, "project", pid, {"profile": key, "columns": codes, "ratings": removed}, ctx.ip)
    return CP.payload(ctx.conn, pid, ctx.user)
