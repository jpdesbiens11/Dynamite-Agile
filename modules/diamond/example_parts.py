"""Parts of the desk-lamp example (0.60.20, D-O-031): who carries out which function of the structure. The allocation
shows each case the analysis looks for: an integrated part (the aluminium head is the housing and the heat sink), a
function shared by several parts (covering the internal components: three parts), a part that carries no function of
the tree (the screws: candidates to remove with snap fits) and a function carried by two cards (setting the intensity).
Written for Dynamite | Agile (no third-party example, D-O-012). Functions are found by their text (tree of example.py).
"""
from core.errors import ApiError

from . import parts as P

# (name, kind, notes, example function numbers)
PARTS = [
    ("Base lestée en zamak", "designed", "Moulée sous pression ; son poids tient la lampe stable.", [3]),
    ("Bras articulé à friction", "designed", "Deux rotules à friction : la tête reste où on la place.", [4]),
    ("Tête en aluminium extrudé", "designed", "Boîtier de la tête et radiateur des DEL en une seule pièce.", [18, 20, 4]),
    ("Carte DEL et pilote MLI", "designed", "DEL blanc chaud et blanc froid, pilote de courant.", [13, 14, 15]),
    ("Carte de commande BLE", "designed", "Microcontrôleur avec radio Bluetooth Low Energy, mémoire du réglage.", [10, 11, 14]),
    ("Électrode tactile", "designed", "Zone cuivrée sous la base : bouton capacitif sans pièce mobile.", [9]),
    ("Bloc d'alimentation 12 V", "bought", "Homologué (acheté) : la lampe ne touche jamais au 120 V.", [6]),
    ("Câble et connecteur", "bought", "Du jack 12 V aux cartes, par le bras.", [7]),
    ("Diffuseur en polycarbonate", "designed", "Adoucit la lumière, ferme la tête.", [20]),
    ("Couvercle isolant de la base", "designed", "Isole la carte de commande ; ferme la base.", [19, 20]),
    ("Vis M3 (× 8)", "standard", "Fixent couvercles et cartes : des clips les remplaceraient.", []),
]


def load(conn, user_id, pid, texts):
    """texts: {example number: function text}. Refuses when the Space already has parts."""
    if conn.execute("SELECT 1 FROM diamond_parts WHERE project_id = ?", (pid,)).fetchone():
        raise ApiError(409, "Ce Space a déjà des pièces. Correctif : chargez l'exemple dans un Space neuf.")
    by_text = {r["text"]: r["id"] for r in conn.execute("SELECT id, text FROM diamond_functions WHERE project_id = ? AND archived = 0", (pid,))}
    ids = {n: by_text.get(t) for n, t in texts.items()}
    if not all(ids.get(n) for _name, _kind, _notes, fns in PARTS for n in fns):
        raise ApiError(409, "L'arbre de ce Space n'est pas celui de l'exemple (lampe de bureau). Correctif : chargez l'exemple "
                            "dans un Space neuf.")
    for name, kind, notes, fns in PARTS:
        oid = P.add_part(conn, user_id, pid, name, kind, notes)
        for n in fns:
            P.tag(conn, pid, oid, ids[n])
    return len(PARTS)
