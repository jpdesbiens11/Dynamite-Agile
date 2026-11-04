"""Original example of the functional tree (0.60.11, D-O-023): the connected desk lamp of the Project Starter examples
(deploy/starter_exemples/lampe_bureau.json). Loaded on demand in an empty tree, to see the method at work: secondaries
in the order of the first use (out of the box, set on the desk, plugged in, switched on, adjusted), the protection
branch last, one technique function at level 4, a critical path, a feedback loop and an « estime » function left
outside the tree. Content written for Dynamite | Agile (no third-party example, D-O-012).
"""
from core import audit
from core.errors import ApiError

from . import example_risks, example_structure, functions as F

# (key, parent key | None, text, ftype, kano, importance, critical); the first one is the primary function
LAMP = [
    ("f1", None, "Éclairer une surface de travail", "usage", "B", "indispensable", 1),
    ("f2", "f1", "Se poser et tenir stable sur le bureau", "usage", "B", "indispensable", 0),
    ("f3", "f2", "Reposer sur une base lestée", "usage", "B", "indispensable", 0),
    ("f4", "f2", "Orienter la tête d'éclairage", "usage", "P", "importante", 0),
    ("f5", "f1", "Recevoir l'énergie électrique", "usage", "B", "indispensable", 0),
    ("f6", "f5", "Utiliser un bloc d'alimentation externe 12 V", "contrainte", "C", "indispensable", 0),
    ("f7", "f5", "Distribuer l'énergie aux sous-systèmes", "usage", "B", "indispensable", 0),
    ("f8", "f1", "Commander la lampe", "usage", "B", "indispensable", 0),
    ("f9", "f8", "Détecter un toucher sur le bouton", "usage", "B", "indispensable", 0),
    ("f10", "f8", "Recevoir les commandes de l'application mobile", "usage", "I", "interessante", 0),
    ("f11", "f8", "Mémoriser le dernier réglage", "usage", "P", "importante", 0),
    ("f12", "f1", "Produire une lumière réglable", "usage", "B", "indispensable", 1),
    ("f13", "f12", "Convertir l'électricité en lumière", "usage", "B", "indispensable", 1),
    ("f14", "f12", "Régler l'intensité", "usage", "P", "importante", 0),
    ("f15", "f12", "Régler la température de couleur", "usage", "I", "interessante", 0),
    ("f16", "f14", "Piloter le courant des DEL par MLI", "technique", "", "", 0),
    ("f17", "f1", "Protéger l'utilisateur, les composants et le bureau", "usage", "B", "indispensable", 0),
    ("f18", "f17", "Dissiper la chaleur des DEL", "usage", "B", "indispensable", 0),
    ("f19", "f17", "Isoler les parties sous tension", "usage", "B", "indispensable", 0),
    ("f20", "f17", "Recouvrir les composants internes", "usage", "B", "indispensable", 0),
    ("f21", None, "Plaire par une allure épurée", "estime", "P", "interessante", 0),
]
FEEDBACK = [("f9", "f14"), ("f10", "f14")]  # control functions, linked like a feedback loop (dotted arrows)
NOTES = {"f1": "Fonction primaire : ce que le produit réalise, le plus simplement possible.",
         "f2": "Première branche : ce qui se passe en premier, au sortir de la boîte.",
         "f17": "Dernière branche : les fonctions de protection, communes à tous les produits.",
         "f21": "Fonction d'estime : au CdCF, hors de l'arbre proprement dit."}
EXAMPLES = {"lampe": ("Lampe de bureau connectée", LAMP)}


def api_example(ctx):
    pid = F.access(ctx, "editor")
    name = str(ctx.body.get("name") or "lampe")
    if name not in EXAMPLES:
        raise ApiError(400, "Exemple « {} » inconnu. Correctif : {}.".format(name, ", ".join(EXAMPLES)))
    if F.rows(ctx.conn, pid):
        raise ApiError(409, "L'arbre de ce Space contient déjà des fonctions. Correctif : chargez l'exemple dans un Space "
                            "neuf (ex. un Space d'essai).")
    title, items = EXAMPLES[name]
    ids = {}
    for key, parent, text, ftype, kano, importance, critical in items:
        fields = {"text": text, "ftype": ftype, "kano": kano, "importance": importance, "critical": critical,
                  "notes": NOTES.get(key, "")}
        primary = parent is None and key == items[0][0]
        ids[key] = F.create(ctx.conn, ctx.user["id"], pid, fields, ids.get(parent), None, primary)
    for src, dst in FEEDBACK:
        ctx.conn.execute("UPDATE diamond_functions SET feedback_to = ? WHERE id = ?", (ids[dst], ids[src]))
    example_structure.load(ctx.conn, pid, _texts(items))  # 0.60.13: its functional structure too
    if not ctx.conn.execute("SELECT 1 FROM diamond_risks WHERE project_id = ?", (pid,)).fetchone():
        example_risks.load(ctx.conn, ctx.user["id"], pid)  # 0.60.14: and its project risks
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_example", "projects", pid, {"example": name, "functions": len(items)}, ctx.ip)
    return F.payload(ctx.conn, pid)


def _texts(items):
    """{function number in the example: text} -- F1 for the first line, F2 for the second…"""
    return {n: row[2] for n, row in enumerate(items, start=1)}


def api_structure_example(ctx):
    """0.60.13: the structure of the example for a tree loaded before (the lamp tree must be there, the structure empty)."""
    pid = F.access(ctx, "editor")
    ports, flows = example_structure.load(ctx.conn, pid, _texts(LAMP))
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_structure_example", "projects", pid, {"ports": ports, "flows": flows}, ctx.ip)
    from . import structure
    return structure.payload(ctx.conn, pid)


def api_risks_example(ctx):
    """0.60.14: the project risks of the example (for a register still empty)."""
    pid = F.access(ctx, "editor")
    n = example_risks.load(ctx.conn, ctx.user["id"], pid)
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_risks_example", "projects", pid, {"risks": n}, ctx.ip)
    from . import risks
    return risks.payload(ctx.conn, pid)
