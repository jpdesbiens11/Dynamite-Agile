"""Diamond · « ↔ IA » (0.60.111, D-O-124): the sections of « Industrialisation » -- Procédés (lines, operations and their
control points), PFMEA, Plans de contrôle -- and of « Projet » (Coûts et budget, in rt_sections_c2.py). See rt.py for the engine.

Codes: a line L<number>; an operation L<line>-OP<op> (OP10 exists on every line); a PFMEA row its code of the page PF-<op>.<n>,
L<line>-PF-<op>.<n> when two lines have the same OP; a control plan PC-<number>; a row of a plan PC-<plan>/CP-<op>.<seq>
(CP-R.<seq> at reception). The process side has its own access list and can be turned off (process.access, core/features.py):
an account without it, or a platform without it, sees these sections empty -- and the routes refuse any write.
"""
import datetime as dt

from core import features
from core.errors import ApiError

from . import actions as ACT
from . import control_plans as CPL
from . import pfmea as PF
from .rt import Field, Section
from .rt_sections_c2 import SECTIONS as COSTS, enum_or


def _get(rt, path, feature):
    """The payload of a process page, read once; None when the part is off or the account has no access to it."""
    key = "_c:" + path
    if key not in rt.temp:
        try:
            rt.temp[key] = rt.call("GET", path) if features.on(rt.ctx.conn, feature) else None
        except ApiError as e:
            if e.status not in (403, 404):
                raise
            rt.temp[key] = None
    return rt.temp[key]


def _unique(records, first, second):
    """r["_rt"] = first(r); when two records share it, second(r); still shared (an anomaly of the data): « #id » added."""
    groups = {}
    for r in records:
        groups.setdefault(first(r), []).append(r)
    for code, group in groups.items():
        for r in group:
            r["_rt"] = code if len(group) == 1 else second(r)
    count = {}
    for r in records:
        count[r["_rt"]] = count.get(r["_rt"], 0) + 1
    for r in records:
        if count[r["_rt"]] > 1:
            r["_rt"] = "{}#{}".format(r["_rt"], r["id"])
    return records


def _create_only(body, name, label):
    if name in body:
        raise ApiError(400, "{} ne change pas après la création. Correctif : gardez la valeur actuelle, ou retirez l'élément et "
                            "créez-en un nouveau.".format(label))


# ---------------------------------------------------------------- process lines and operations

def _lines(rt):
    data = _get(rt, "/process", "diamond_process")
    return [] if data is None else data["lines"]


def _ops(rt):
    numbers = {line["id"]: line["number"] for line in _lines(rt)}
    return [dict(o, _line=numbers[o["line_id"]]) for line in _lines(rt) for o in line["operations"]]


def _op_create(rt, body):
    line_id = body.pop("line_id", None)
    if not line_id:
        lines = _lines(rt)
        if len(lines) != 1:
            raise ApiError(400, "Une nouvelle opération nomme sa ligne (« line »: « L1 »). Correctif : ajoutez la ligne de l'opération.")
        line_id = lines[0]["id"]
    return rt.call("POST", "/process/lines/{}/ops".format(line_id), body)["created"]


def _op_update(rt, item_id, body):
    _create_only(body, "line_id", "La ligne d'une opération")
    rt.call("PATCH", "/process/ops/{}".format(item_id), body)


def _point(p):
    return {"char": p.get("code") or "", "label": "" if p.get("code") else p.get("label") or "", "method": p.get("method") or "",
            "frequency": p.get("frequency") or ""}


def _points_check(rt, value, temps):
    if value in (None, ""):
        value = []
    if not isinstance(value, list):
        return None, "points : une liste d'objets {char, label, method, frequency} est attendue."
    known = set(rt.codes("chars")) | temps.get("chars", set())
    out = []
    for p in value:
        if isinstance(p, str):
            p = {"char": p}
        if not isinstance(p, dict):
            return None, "points : chaque point est un objet {char, label, method, frequency}."
        clean = {k: " ".join(str(p.get(k) or "").split()) for k in ("char", "label", "method", "frequency")}
        if clean["char"] and clean["char"] not in known:
            return None, "points : « {} » n'existe pas dans les caractéristiques.".format(clean["char"])
        if clean["char"]:
            clean["label"] = ""
        elif not clean["label"]:
            return None, "points : un point protège une caractéristique C-n (char) ou nomme ce qu'il vérifie (label)."
        out.append(clean)
    return out, ""


def _points_api(rt, value):
    return [dict(p, characteristic_id=rt.codes("chars").get(p["char"]) if p["char"] else None) for p in value]


def _points_set(rt, item_id, wanted):
    """No update route for a point: the points after the first difference are removed and created again, in the order given."""
    rec = next((o for o in rt.records("process_ops") if o["id"] == item_id), None)
    have = [dict(_point(p), id=p["id"]) for p in (rec or {}).get("points") or []]
    keys = ("char", "label", "method", "frequency")
    same = 0
    while same < min(len(have), len(wanted)) and all(have[same][k] == wanted[same][k] for k in keys):
        same += 1
    for p in have[same:]:
        rt.call("POST", "/process/points/{}/delete".format(p["id"]), {})
    for p in wanted[same:]:
        rt.call("POST", "/process/ops/{}/points".format(item_id), {"characteristic_id": p["characteristic_id"], "label": p["label"],
                                                                  "method": p["method"], "frequency": p["frequency"]})


PROCESS_LINES = Section(
    "process_lines", "Procédés · lignes d'assemblage", ["process"], order=80, table="diamond_lines",
    items=_lines, code=lambda r: "L{}".format(r["number"]),
    fields=[Field("name", note="120 caractères au plus"), Field("description", note="1000 caractères au plus")],
    create=lambda rt, body: rt.call("POST", "/process/lines", body)["created"], update="/process/lines/{id}", remove=None,
    guide="Les configurations de la ligne d'assemblage (ligne pilote, cellule prototypes chez un partenaire…). Une ligne ne se "
          "retire pas d'ici : une ligne absente de la réponse reste dans le Space.")

PROCESS_OPS = Section(
    "process_ops", "Procédés · opérations", ["process"], order=82, table="diamond_operations",
    items=_ops, code=lambda r: "L{}-OP{}".format(r["_line"], r["op"]),
    fields=[Field("line", src="line_id", kind="ref", ref="process_lines", create_only=True, note="la ligne (L1…) ; fixée à la création"),
            Field("op", kind="int", note="le numéro d'opération, de 1 à 9990 (10, 20, 30…), unique sur la ligne ; vide : le suivant"),
            Field("name", note="120 caractères au plus"), Field("description", note="1000 caractères au plus"),
            Field("equipment", note="équipements et gabarits, un par ligne de texte, 600 caractères au plus"),
            Field("traceability", kind="bool", note="true : l'opération ferme la traceability des CC (n° de série ↔ résultats)"),
            Field("points", kind="json", out=lambda rt, rec: [_point(p) for p in rec.get("points") or []], check=_points_check,
                  to_api=_points_api, setter=_points_set,
                  note="les points de contrôle, dans l'ordre : [{char: « C-14 » ou vide, label: le contrôle quand il n'y a pas de C-n, "
                       "method, frequency}]")],
    create=_op_create, update=_op_update, remove="/process/ops/{id}/delete",
    guide="Les opérations de chaque ligne, dans l'ordre (OP10, OP20…), leurs équipements et leurs points de contrôle : chacun "
          "protège une caractéristique C-n ou nomme un contrôle de procédé. Une opération qui a des lignes de PFMEA ne se retire pas : "
          "déplacez d'abord ces lignes vers une autre opération.")


# ---------------------------------------------------------------- PFMEA

def _pfmea_data(rt):
    return _get(rt, "/pfmea", "diamond_pfmea")


def _pfmea(rt):
    data = _pfmea_data(rt)
    rows = [] if data is None else [dict(r) for r in data["rows"]]
    return _unique(rows, lambda r: r["code"], lambda r: "L{}-{}".format(r["line_number"], r["code"]) if r["line_number"] else r["code"])


def _owners(rt):
    """{display name (lower case): id} of the members who may own an action, and of the owners already named in the PFMEA."""
    data = _pfmea_data(rt) or {"members": [], "rows": []}
    out = {r["action_owner_name"].lower(): r["action_owner_id"] for r in data["rows"] if r.get("action_owner_name")}
    out.update({m["display_name"].lower(): m["id"] for m in data["members"]})
    return out


def _owner_check(rt, value, temps):
    value = " ".join(str(value or "").split())
    if value and value.lower() not in _owners(rt):
        names = ", ".join(m["display_name"] for m in (_pfmea_data(rt) or {"members": []})["members"])
        return None, "owner : « {} » n'est pas un membre du Space ({}).".format(value, names)
    return value, ""


def _date_check(rt, value, temps):
    value = str(value or "").strip()
    if value:
        try:
            dt.date.fromisoformat(value)
        except ValueError:
            return None, "action_due : « {} » n'est pas une date AAAA-MM-JJ.".format(value)
    return value, ""


def _pfmea_create(rt, body):
    """A row written by the AI arrives as a draft (D-O-114): a person accepts it on the page, row by row."""
    created = rt.call("POST", "/pfmea/rows", body)["created"]
    rt.call("POST", "/pfmea/rows/{}/review".format(created), {"state": "draft"})
    return created


PFMEA = Section(
    "pfmea", "PFMEA", ["pfmea"], order=85, table="diamond_pfmea",
    items=_pfmea, code=lambda r: r["_rt"],
    fields=[Field("operation", src="operation_id", kind="ref", ref="process_ops", note="l'opération (L1-OP30) ; changer d'opération "
                  "renumérote la ligne"),
            Field("process_step", note="Process Step, 200 caractères au plus"),
            Field("characteristic", src="characteristic_id", kind="ref", ref="chars", note="la caractéristique produit C-n, ou vide"),
            Field("process_char", note="Process Characteristic, 200 caractères au plus"),
            Field("failure_mode", note="Failure Mode, 400 caractères au plus"), Field("effect", note="Failure Effect, 400 caractères au plus"),
            Field("cause", note="Failure Cause, 400 caractères au plus"),
            Field("cause_5m", kind="enum", values=list(PF.CAUSES_5M), note="5M : man, method, material, machine, measurement, ou vide"),
            Field("prevention", note="Prevention Controls, 1000 caractères au plus"),
            Field("detection_ctrl", note="Detection Controls, 400 caractères au plus"),
            Field("severity", kind="int", note="S de 1 à 10, ou vide : la S héritée du DFMEA ; jamais plus basse que inherited_s"),
            Field("occurrence", kind="int", note="O de 1 à 10, ou vide"), Field("detection", kind="int", note="D de 1 à 10, ou vide"),
            Field("action", note="Actions, 600 caractères au plus"),
            Field("owner", src="action_owner_name", api="action_owner_id", check=_owner_check,
                  to_api=lambda rt, v: _owners(rt).get(v.lower()) if v else None, note="le responsable : le nom d'un membre du Space, ou vide"),
            Field("action_due", check=_date_check, note="échéance AAAA-MM-JJ, ou vide"),
            Field("action_status", kind="enum", values=list(ACT.DFMEA_STATUSES),
                  check=enum_or("action_status", list(ACT.DFMEA_STATUSES), "open"),
                  note="open, in_progress ou done"),
            Field("inherited_s", kind="int", ro=True, note="la S de la ligne du DFMEA de la C-n"),
            Field("ap", ro=True, note="Action Priority H, M, L, calculée"),
            Field("state", ro=True, note="draft (proposée, à accepter sur la page), accepted, rejected")],
    create=_pfmea_create, update="/pfmea/rows/{id}", remove=None,
    guide="Le Process FMEA (AIAG-VDA) : une ligne par chaîne de défaillance d'une opération (Failure Mode, Effect, Cause en 5M, "
          "Prevention, Detection, S, O, D, AP). La S d'une C-n vient du DFMEA et ne peut pas baisser. Une nouvelle ligne arrive en "
          "brouillon (draft) : une personne l'accepte sur la page PFMEA. Aucune ligne ne se retire d'ici : rejetez-la sur la page.")


# ---------------------------------------------------------------- control plans

def _plans(rt):
    data = _get(rt, "/cplans", "diamond_cplans")
    return [] if data is None else data["plans"]


def _plan_update(rt, item_id, body):
    _create_only(body, "scope", "La portée d'un plan de contrôle")
    rt.call("PATCH", "/cplans/plans/{}".format(item_id), body)


def _items(rt):
    rows = [dict(i, _plan=p["code"]) for p in _plans(rt) for i in p["items"]]
    return _unique(rows, lambda r: "{}/{}".format(r["_plan"], r["code"]), lambda r: "{}/{}".format(r["_plan"], r["code"]))


def _item_create(rt, body):
    plan_id = body.pop("plan_id", None)
    if not plan_id:
        raise ApiError(400, "Une nouvelle ligne de plan de contrôle nomme son plan (« plan »: « PC-2 »). Correctif : ajoutez le plan.")
    rt.call("POST", "/cplans/plans/{}/items".format(plan_id), body)  # the route gives back the page, not the new id
    return rt.ctx.conn.execute("SELECT MAX(id) FROM diamond_cp_items WHERE project_id = ? AND plan_id = ?", (rt.pid, plan_id)).fetchone()[0]


def _item_update(rt, item_id, body):
    _create_only(body, "plan_id", "Le plan d'une ligne")
    rt.call("PATCH", "/cplans/items/{}".format(item_id), body)


CPLANS = Section(
    "cplans", "Plans de contrôle", ["cplans"], order=90, table="diamond_control_plans",
    items=_plans, code=lambda r: r["code"],
    fields=[Field("title", note="160 caractères au plus"),
            Field("scope", kind="enum", values=list(CPL.SCOPES), create_only=True, note="assembly (étapes d'une ligne) ou reception (pièces) ; fixée à la "
                  "création"),
            Field("line", src="line_id", kind="ref", ref="process_lines", note="la ligne suivie (L1…) ; obligatoire pour assembly, vide pour "
                  "reception"),
            Field("phase", kind="enum", values=list(CPL.PHASES), note="prototype, prelaunch ou production"),
            Field("revision", note="12 caractères au plus (A, B…)")],
    create=lambda rt, body: rt.call("POST", "/cplans/plans", body)["created"], update=_plan_update, remove=None,
    guide="Les Control Plans AIAG du Space : un plan par configuration de ligne (assembly) ou pour la réception des pièces "
          "(reception), avec sa phase APQP (prototype, prelaunch, production) et sa révision. Un plan ne se retire pas d'ici.")

CPLAN_ITEMS = Section(
    "cplan_items", "Plans de contrôle · lignes", ["cplans"], order=92, table="diamond_cp_items",
    items=_items, code=lambda r: r["_rt"],
    fields=[Field("plan", src="plan_id", kind="ref", ref="cplans", create_only=True, note="le plan (PC-2) ; fixé à la création"),
            Field("operation", src="operation_id", kind="ref", ref="process_ops", note="l'opération (L1-OP30), sur la ligne du plan ; "
                  "vide à la réception"),
            Field("part", src="part_id", kind="ref", ref="parts", note="la pièce (P-21) d'une ligne de réception, ou vide"),
            Field("characteristic", src="characteristic_id", kind="ref", ref="chars", note="la caractéristique produit C-n, ou vide"),
            Field("char_label", note="Process Characteristic en mots, quand il n'y a pas de C-n (160 caractères au plus)"),
            Field("equipment", note="Machine · Jig, 200 caractères au plus"),
            Field("technique", note="Measurement Technique, 200 caractères au plus"),
            Field("sample", note="Sample, 80 caractères au plus"), Field("frequency", note="Frequency, 80 caractères au plus"),
            Field("control_method", note="Control Method, 300 caractères au plus"),
            Field("reaction_plan", note="Reaction Plan, 600 caractères au plus ; attendu pour toute CC"),
            Field("class_code", ro=True, note="classe de la C-n (CC, SC), lue du DFMEA"),
            Field("spec", ro=True, note="spécification de la C-n, lue de la caractéristique")],
    create=_item_create, update=_item_update,
    remove=lambda rt, item_id: rt.call("PATCH", "/cplans/items/{}".format(item_id), {"delete": True}),
    guide="Les lignes de chaque Control Plan : l'opération ou la pièce, la caractéristique (une C-n, dont la classe et la "
          "spécification sont lues, ou une caractéristique de procédé en mots), la Measurement Technique, le Sample, la Frequency, "
          "la Control Method et le Reaction Plan. Une CC sans Reaction Plan reste signalée sur la page.")

SECTIONS = [PROCESS_LINES, PROCESS_OPS, PFMEA, CPLANS, CPLAN_ITEMS] + COSTS
