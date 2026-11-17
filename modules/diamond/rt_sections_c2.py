"""Diamond · « ↔ IA » (0.60.111, D-O-124): the sections of « Projet » -- Coûts et budget (NRE, cost lines). Exported through
rt_sections_c.SECTIONS; see rt.py for the engine.

Codes: an NRE line NRE-<number>; the cost line of a part its part's code P-<number> (every part has one on the page, priced or
not, as on the screen); a free line (packaging, assembly, notice…) CL-<id>. The hypotheses (currency, volumes, contingency) are
one record, not a list: they stay on the page.
"""
from core.errors import ApiError

from . import costs as CO
from .rt import Field, Section


def _costs(rt):
    if "_c:/costs" not in rt.temp:
        rt.temp["_c:/costs"] = rt.call("GET", "/costs")
    return rt.temp["_c:/costs"]


def enum_or(name, values, default):
    """check of an enum whose empty value means its default (the page's own default): shown as such in the preview."""
    def check(rt, value, temps):
        value = default if value in (None, "") else str(value).strip()
        if value not in values:
            return None, "{} : « {} » n'est pas une valeur permise ({}).".format(name, value, ", ".join(values))
        return value, ""
    return check


NRE = Section(
    "costs_nre", "Coûts · NRE", ["costs"], order=95, table="diamond_cost_nre",
    items=lambda rt: _costs(rt)["nre"], code=lambda r: "NRE-{}".format(r["number"]),
    fields=[Field("title", note="l'intitulé, obligatoire, 160 caractères au plus"),
            Field("category", kind="enum", values=list(CO.CATEGORIES), check=enum_or("category", list(CO.CATEGORIES), "ingenierie"),
                  note=", ".join("{} ({})".format(k, v) for k, v in CO.CATEGORIES.items())),
            Field("phase", kind="enum", values=list(CO.PHASES), note="la phase du PDP : A, B, C, D, ou vide"),
            Field("amount", kind="num", note="le montant dans la devise du Space, de 0 à 1 000 000 000"),
            Field("basis", kind="enum", values=list(CO.BASES), check=enum_or("basis", list(CO.BASES), "estimation"),
                  note="estimation, soumission, engage ou paye : à quel point le montant est sûr"),
            Field("supplier", note="120 caractères au plus"), Field("notes", note="2000 caractères au plus")],
    create="/costs/nre", update="/costs/nre/{id}", remove="/costs/nre/{id}/delete",
    guide="Les coûts non récurrents (NRE) du projet : ingénierie, outillage et moules, prototypes, essais, certification, logiciels, "
          "équipement… chacun avec sa phase du PDP et la base de son montant (estimation, soumission, engagé, payé).")


def _lines(rt):
    """The page's lines: a part without a priced line yet has the id « part:<part id> » (its line is created when it is written)."""
    return [dict(ln, id=ln["id"] if ln["id"] else "part:{}".format(ln["part_id"])) for ln in _costs(rt)["lines"]]


def _line_code(r):
    return r["code"] if r["part_id"] else "CL-{}".format(r["id"])


def _line_create(rt, body):
    if not body.get("part_id"):
        body.pop("part_id", None)
    return rt.call("POST", "/costs/lines", body)["created"]


def _line_update(rt, item_id, body):
    if "part_id" in body:
        raise ApiError(400, "La pièce d'une ligne de coût ne change pas. Correctif : gardez la pièce, ou retirez la ligne et créez-en une "
                            "autre.")
    rec = next(r for r in rt.records("costs_lines") if r["id"] == item_id)
    if rec["part_id"]:
        body.pop("name", None)  # the name of a part is the part's (Pièces), not written here
    if not body:
        return
    if isinstance(item_id, str):  # a part not priced yet: its line is created, as on the page
        rt.call("POST", "/costs/lines", dict(body, part_id=rec["part_id"]))
    else:
        rt.call("PATCH", "/costs/lines/{}".format(item_id), body)


def _line_remove(rt, item_id):
    if not isinstance(item_id, str):  # a part not priced yet: nothing to clear
        rt.call("POST", "/costs/lines/{}/delete".format(item_id), {})


LINES = Section(
    "costs_lines", "Coûts · pièces et lignes", ["costs"], order=96, table="diamond_cost_parts",
    items=_lines, code=_line_code,
    fields=[Field("part", src="part_id", kind="ref", ref="parts", create_only=True, note="la pièce (P-n) ; vide : une ligne libre ; fixée à la création"),
            Field("name", note="la désignation d'une ligne libre (160 caractères au plus) ; pour une pièce, son nom, lu dans Pièces"),
            Field("qty", kind="num", note="quantité par produit (1 par défaut)"),
            Field("proto_unit", kind="num", note="prix unitaire en prototype, ou vide"),
            Field("prod_1", kind="num", note="prix unitaire au 1er volume de production, ou vide"),
            Field("prod_2", kind="num", note="prix unitaire au 2e volume, ou vide"),
            Field("prod_3", kind="num", note="prix unitaire au 3e volume, ou vide"),
            Field("supplier", note="120 caractères au plus"),
            Field("basis", kind="enum", values=list(CO.BASES), check=enum_or("basis", list(CO.BASES), "estimation"),
                  note="estimation, soumission, engage ou paye"),
            Field("notes", note="1000 caractères au plus")],
    create=_line_create, update=_line_update, remove=_line_remove,
    removable=lambda rec: not isinstance(rec["id"], str),  # a part not priced yet has nothing to clear
    guide="Le coût unitaire du produit : une ligne par pièce de Diamond (P-n, toujours présente, avec ou sans prix) et des lignes "
          "libres (CL-…: emballage, assemblage, notice). Quantité par produit, prix en prototype et aux trois volumes de production. "
          "Retirer la ligne d'une pièce efface ses prix (la pièce reste) ; retirer une ligne libre la supprime.")

SECTIONS = [NRE, LINES]
