"""Diamond · « ↔ IA » (0.60.116, D-O-129): the competencies of each function line -- an AI assistant fills the whole grid at
once, the team reviews the preview and keeps what it wants; every cell stays editable by hand afterwards.

Code of a line: the code of its function (F12); only the functions that end with a brick have a line (a line is never created
nor removed here: give the function its brick first). Its « competencies »: a list « CODE:note » (« THERM:4 »), note 1 (almost
not involved) to 5 (at the heart of the development); a code left out leaves the line. The catalogue (code, name) goes along
as read-only context.
"""
import re

from core.errors import ApiError

from . import competencies as CP
from .rt import Field, Section

PAIR = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]{1,7})\s*[:=]\s*([0-5])\s*$")


def _lines(rt):
    return [dict(r, id=r["function_id"]) for r in rt.call("GET", "/competencies")["lines"]]


def _out(rt, rec):
    return sorted("{}:{}".format(k, v) for k, v in rec["ratings"].items())


def _check(rt, value, temps):
    if isinstance(value, dict):
        value = ["{}:{}".format(k, v) for k, v in value.items()]
    if isinstance(value, str):
        value = [x for x in re.split(r"[,;]", value) if x.strip()]
    if not isinstance(value, list):
        return None, "competencies : une liste « CODE:note » attendue (ex. [\"MECH:3\", \"THERM:4\"])."
    active = {c["code"] for c in CP.catalog(rt.ctx.conn, active_only=True)}
    out, bad = {}, []
    for item in value:
        m = PAIR.match(str(item))
        if not m or m.group(1).upper() not in active:
            bad.append(str(item)[:20])
            continue
        if int(m.group(2)):
            out[m.group(1).upper()] = int(m.group(2))
    if bad:
        return None, "competencies : « {} » refusé. Correctif : CODE:note avec un code du catalogue ({}) et une note de 1 à 5.".format(
            ", ".join(bad), ", ".join(sorted(active)))
    return sorted("{}:{}".format(k, v) for k, v in out.items()), ""


def _set(rt, fid, value):
    ratings = {k: int(v) for k, v in (x.split(":") for x in value)}
    rt.call("PUT", "/competencies/lines/{}".format(fid), {"ratings": ratings, "source": "ai"})


def _no_new(rt, body):
    raise ApiError(400, "Une ligne de compétences appartient à une fonction qui a sa brique (CB-n). Correctif : gardez le code F… d'une "
                        "ligne existante ; donnez d'abord sa brique à une nouvelle fonction (section « concepts »).")


CATALOG = Section(
    "competency_catalog", "Catalogue des compétences", [], order=47, table="diamond_competencies", listed=False,
    items=lambda rt: [dict(c, id=i + 1) for i, c in enumerate(CP.catalog(rt.ctx.conn, active_only=True))],
    code=lambda r: r["code"], fields=[Field("name", ro=True), Field("summary", ro=True)], create=_no_new)

COMPETENCIES = Section(
    "competencies", "Compétences par ligne", ["ftree", "competencies"], order=48, table="diamond_competency_ratings",
    items=_lines, code=lambda r: r["code"],
    fields=[Field("function", ro=True, out=lambda rt, rec: rec["text"], note="la fonction de la ligne"),
            Field("brick", ro=True, out=lambda rt, rec: "{} {}{}".format(rec["brick"]["code"], rec["brick"]["name"],
                                                                         " [figée : {}]".format(rec["brick"]["frozen_text"]) if rec["brick"]["frozen"] else ""),
                  note="la brique standard qui porte la fonction"),
            Field("competencies", kind="json", ref="competency_catalog", out=_out, check=_check, setter=_set,
                  note="les compétences nécessaires pour développer un concept de cette fonction, « CODE:note », note de 1 (presque pas "
                       "impliquée) à 5 (au cœur du développement) ; un code absent quitte la ligne")],
    create=_no_new,
    guide="Une ligne par fonction de l'arbre qui aboutit à une brique technologique. Pour chacune, notez les compétences du catalogue "
          "(_context.competency_catalog) qu'il faut pour développer un concept de cette fonction en général -- une hypothèse que "
          "l'équipe affinera : 5 au cœur du développement, 3 sollicitée régulièrement, 1 presque pas ; ne citez pas une compétence "
          "inutile. Pensez au produit entier : conception, analyse, sécurité (TR), fabrication, procédés spéciaux, essais, "
          "certification. Une ligne n'est jamais créée ni retirée ici.")

SECTIONS = [CATALOG, COMPETENCIES]
