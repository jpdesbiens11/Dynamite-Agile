"""Diamond · « Coûts et budget » → « Copier le prompt pour l'IA » (0.60.66, D-O-075).

GET …/costs/prompt builds, from what Diamond already holds, the complete instructions for an AI assistant (Claude or
another LLM) that estimates the budget: the product and its Storyline, the function tree, the parts (with the functions
each one carries), the project risks and the DFMEA tests (certification, essais), the assumptions of the page and the
current CSV. The assistant answers with the same CSV, which « Importer » (costs_import.py) reads back: a dry run first,
then « Appliquer ». The prompt is in French (the content of the Space is), the CSV headers are those of the export.
"""
from . import costs as C
from . import costs_budget as B
from . import functions as F
from . import parts as P
from . import story
from . import story_ai

GUIDE = """Tu es un ingénieur en développement de produit et en estimation de coûts. Tu prépares le budget du projet « {name} »{description}, à partir de son analyse fonctionnelle faite dans Dynamite | Agile (module Diamond).

## Ce que tu dois rendre
Un seul bloc ```csv, séparateur « ; », exactement dans le format ci-dessous (celui de l'export de la page « Coûts et budget »), et rien d'autre dans le bloc. Ensuite, sous le bloc, une courte liste de tes hypothèses et des points à faire confirmer par l'équipe.

Deux tableaux, chacun précédé de sa ligne d'en-tête exacte, séparés par une ligne vide :
1. `NRE;Intitulé;Catégorie;Phase;Montant;Base;Fournisseur;Notes` — les coûts uniques : ingénierie, outillage et moules, prototypes, essais et certification, gabarits, logiciel, etc.
   - code : garde « NRE-n » pour corriger une ligne existante ; laisse vide pour une nouvelle ligne.
   - Catégorie, une de : {categories}.
   - Phase, une de : {phases} (vide si aucune).
2. `Pièce;Désignation;Quantité;Prix prototype;Prix à {v1};Prix à {v2};Prix à {v3};Fournisseur;Base;Notes` — le coût de chaque pièce par produit.
   - code : « P-n » pour une pièce de Diamond (liste plus bas, n'invente aucun numéro) ; vide pour une ligne libre (emballage, assemblage, notice, quincaillerie…).
   - Quantité : nombre de cette pièce dans un produit. Prix : prix unitaire en {currency}, sans symbole, point ou virgule décimale.
   - « Prix à {v1} » etc. : le prix unitaire attendu quand on achète pour {v1}, {v2} et {v3} produits (tarifs par lots, puis soumissions, moulage par injection…).
Base, une de : {bases}. Une valeur estimée par toi est « Estimation » ; dis d'où vient le chiffre dans Notes (prix catalogue d'un distributeur, ordre de grandeur, analogie…).

## Règles
- Couvre chaque pièce de Diamond et chaque fonction : une fonction sans pièce coûteuse peut demander une ligne libre (assemblage, câblage, logiciel).
- Pense aux essais et à la certification qu'exigent les essais clés et les risques ci-dessous (laboratoire accrédité, CEM, sécurité électrique, transport des piles…).
- Pas de taxes. Prix de l'année en cours. Reste réaliste pour une équipe de {team} personne(s) et {proto_qty} prototype(s).
- Ne recopie pas le tableau de synthèse : la page calcule seule le budget, le coût par unité et la contingence ({contingency} %).

## Le produit, raconté (Storyline, {count} scènes)
{scenes}

## L'arbre fonctionnel
{tree}

## Les pièces (Diamond → Structure) et les fonctions qu'elles portent
{parts}

## Risques projet
{risks}

## Essais clés (DFMEA → Detection Controls)
{tests}

## Hypothèses de la page
Devise : {currency}. Prototypes : {proto_qty}. Volumes : {v1}, {v2}, {v3}. Taux horaire de l'équipe : {rate} {currency}. Heures déjà inscrites au Timesheet : {hours}. Notes : {notes}

## Le fichier actuel (à compléter ou corriger ; garde les codes existants)
```csv
{current}
```
"""


def _tree(conn, pid):
    rows = [dict(r) for r in conn.execute("SELECT id, number, text, parent_id, ftype FROM diamond_functions WHERE project_id = ? "
                                          "AND archived = 0 ORDER BY position, number", (pid,))]
    kids = {}
    for r in rows:
        kids.setdefault(r["parent_id"], []).append(r)
    out = []

    def walk(parent, depth):
        for r in kids.get(parent, []):
            out.append("{}- F{} {}{}".format("  " * depth, r["number"], r["text"], " ({})".format(r["ftype"]) if r["ftype"] not in ("usage", "") else ""))
            walk(r["id"], depth + 1)
    walk(None, 0)
    known = {r["id"] for r in rows}
    out += ["- F{} {}".format(r["number"], r["text"]) for r in rows if r["parent_id"] and r["parent_id"] not in known]
    return "\n".join(out) or "(arbre vide : décris les pièces probables à partir de la Storyline)"


def _parts(conn, pid):
    serves = {}
    for r in conn.execute("SELECT pf.part_id, f.number FROM diamond_part_functions pf JOIN diamond_functions f ON f.id = pf.function_id "
                          "WHERE pf.project_id = ? ORDER BY f.number", (pid,)):
        serves.setdefault(r["part_id"], []).append("F{}".format(r["number"]))
    lines = []
    for p in conn.execute("SELECT id, number, name, kind, notes FROM diamond_parts WHERE project_id = ? ORDER BY position, number", (pid,)):
        extra = " — " + " ".join(p["notes"].split())[:160] if p["notes"] else ""
        lines.append("- P-{} {} ({}){}{}".format(p["number"], p["name"], P.KINDS.get(p["kind"], p["kind"]),
                                              " → " + ", ".join(serves[p["id"]]) if p["id"] in serves else "", extra))
    return "\n".join(lines) or "(aucune pièce : utilise des lignes libres, code vide)"


def _risks(conn, pid):
    return "\n".join("- R-{} {} (P {} × I {})".format(r["number"], r["title"], r["probability"], r["impact"])
                     for r in conn.execute("SELECT number, title, probability, impact FROM diamond_risks WHERE project_id = ? "
                                           "ORDER BY number", (pid,))) or "(aucun)"


def _tests(conn, pid):
    try:
        rows = conn.execute("SELECT DISTINCT t.test_id AS code, t.title FROM diamond_dfmea d JOIN testing_tests t ON t.id = d.test_id "
                            "WHERE d.project_id = ? ORDER BY t.code", (pid,)).fetchall()
    except Exception:  # Testing absent from this installation
        rows = []
    return "\n".join("- {} {}".format(r["code"], r["title"]) for r in rows) or "(aucun essai relié au DFMEA)"


def prompt(conn, pid):
    project = conn.execute("SELECT name, description FROM projects WHERE id = ?", (pid,)).fetchone()
    s = C.settings(conn, pid)
    scenes = story.rows(conn, pid)
    team = conn.execute("SELECT COUNT(*) FROM memberships m JOIN users u ON u.id = m.user_id WHERE m.project_id = ? "
                        "AND u.username NOT IN ('admin', 'invite')", (pid,)).fetchone()[0]
    v1, v2, v3 = s["volumes"]
    return GUIDE.format(
        name=project["name"], description=" — " + " ".join(project["description"].split()).rstrip(".") if project["description"] else "",
        categories=", ".join(C.CATEGORIES.values()), phases=", ".join(v for k, v in C.PHASES.items() if k),
        bases=", ".join(C.BASES.values()), currency=s["currency"], v1=v1, v2=v2, v3=v3, team=team or "quelques",
        proto_qty=s["proto_qty"], contingency=s["contingency"], rate=s["labour_rate"], hours=C.labour_hours(conn, pid),
        notes=" ".join((s["notes"] or "—").split()), count=len(scenes),
        scenes="\n\n".join(story_ai._scene_text(i, sc) for i, sc in enumerate(scenes)) or "(aucune scène)",
        tree=_tree(conn, pid), parts=_parts(conn, pid), risks=_risks(conn, pid), tests=_tests(conn, pid),
        current=B.csv_text(conn, pid).strip())


def api_prompt(ctx):
    pid = F.access(ctx)
    text = prompt(ctx.conn, pid)
    return {"prompt": text, "parts": ctx.conn.execute("SELECT COUNT(*) FROM diamond_parts WHERE project_id = ?", (pid,)).fetchone()[0]}
