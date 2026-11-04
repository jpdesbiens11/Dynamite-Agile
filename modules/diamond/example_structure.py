"""Functional structure of the desk-lamp example (0.60.13, D-O-025): its inputs and outputs, the general flows between
the sub-systems and the detail flows between the tertiary functions -- every general flow is found again in the detail
view. Written for Dynamite | Agile (no third-party example, D-O-012). Functions are found by their text (tree of
example.py), so the example also applies to a tree loaded before 0.60.13.
"""
from core.errors import ApiError

from . import structure as S

PORTS = [("in", "Courant 12 V du bloc d'alimentation", "energy"), ("in", "Toucher de l'utilisateur", "information"),
         ("in", "Commande Bluetooth de l'application", "information"), ("in", "Force de la main", "energy"),
         ("out", "Lumière sur la surface de travail", "energy"), ("out", "Chaleur évacuée", "energy")]
# (src, dst, kind, label): an integer is a function number of the example, a string the start of a port label
GENERAL = [("Courant", 5, "energy", "12 V"), (5, 12, "energy", "courant"), (5, 8, "energy", "alimentation"),
           ("Toucher", 8, "information", "toucher"), ("Commande", 8, "information", "commande BLE"),
           (8, 12, "information", "consigne"), ("Force", 2, "energy", "force"), (2, 12, "material", "support de la tête"),
           (12, "Lumière", "energy", "lumière"), (12, 17, "energy", "chaleur des DEL"), (17, "Chaleur", "energy", "chaleur")]
DETAIL = [("Courant", 6, "energy", "12 V"), (6, 7, "energy", "12 V"), (7, 13, "energy", "courant des DEL"),
          (7, 9, "energy", "alimentation"), (7, 19, "energy", "parties sous tension"), ("Toucher", 9, "information", "toucher"),
          ("Commande", 10, "information", "commande BLE"), (9, 14, "information", "consigne"), (10, 14, "information", "consigne"),
          (10, 15, "information", "consigne de couleur"), (14, 11, "information", "réglage"), (11, 14, "information", "dernier réglage"),
          (14, 13, "information", "intensité"), (15, 13, "information", "couleur"), ("Force", 4, "energy", "force"),
          (3, 4, "material", "appui"), (3, 20, "material", "boîtier"), (4, 13, "material", "position de la tête"),
          (13, "Lumière", "energy", "lumière"), (13, 18, "energy", "chaleur"), (18, "Chaleur", "energy", "chaleur")]


def load(conn, pid, texts):
    """texts: {example number: function text}. Adds the ports and flows; refuses when the structure is not empty."""
    if conn.execute("SELECT 1 FROM diamond_ports WHERE project_id = ? UNION SELECT 1 FROM diamond_flows WHERE project_id = ?",
                    (pid, pid)).fetchone():
        raise ApiError(409, "La structure fonctionnelle de ce Space n'est pas vide. Correctif : chargez l'exemple dans un Space neuf.")
    by_text = {r["text"]: r["id"] for r in conn.execute("SELECT id, text FROM diamond_functions WHERE project_id = ? AND archived = 0", (pid,))}
    ids = {n: by_text.get(t) for n, t in texts.items()}
    if not all(ids.values()):
        raise ApiError(409, "L'arbre de ce Space n'est pas celui de l'exemple (lampe de bureau). Correctif : chargez l'exemple de "
                            "l'arbre dans un Space neuf, puis celui de la structure.")
    ports = {label: S.add_port(conn, pid, side, label, kind) for side, label, kind in PORTS}

    def end(x):
        if isinstance(x, int):
            return (ids[x], None)
        return (None, next(i for label, i in ports.items() if label.startswith(x)))
    for view, rows in (("general", GENERAL), ("detail", DETAIL)):
        for src, dst, kind, label in rows:
            S.add_flow(conn, pid, view, kind, label, end(src), end(dst))
    return len(PORTS), len(GENERAL) + len(DETAIL)
