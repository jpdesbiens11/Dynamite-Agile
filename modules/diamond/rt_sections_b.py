"""Diamond · « ↔ IA » (0.60.111, D-O-124): the sections of « Concepts » and « Risque » -- Briques technologiques, Feuilles de
concept, Matrices de Pugh, Risques projet, DFMEA, Caractéristiques. See rt.py for the engine.

Codes: a brick is CB-<number>, a concept sheet CB-<brick>.<number>, a risk R-<number>, a characteristic C-<nn> (their numbers,
kept for ever); a Pugh matrix PM-<id>, a DFMEA row D-<id> (no number: their id, stable while the team keeps working -- never
the line, which moves).

A person (owner of a brick or of a risk, owner of a DFMEA action) is written by the display name of a member of the Space; a key
test by its code in the Space's Test Base (TST-…). What needs several fields or the record itself (a decided Pugh matrix is read
only, a scan needs its file) is checked in the create / update functions: the preview's rehearsal turns their ApiError into
« refused » with the message."""
from core.errors import ApiError

from . import actions as ACT
from . import char_spec as SP
from . import concept_sheets as CS
from . import concepts as CO
from . import risks as RI
from .rt import Field, Section


# ---------------------------------------------------------------- shared helpers

def _create(path, key="created"):
    """A create callable: POST to the page's route, the new id read from its answer."""
    def run(rt, body):
        return rt.call("POST", path, body)[key]
    return run


def _members(rt):
    if "_members" not in rt.temp:
        rt.temp["_members"] = ACT.members(rt.ctx.conn, rt.pid)
    return rt.temp["_members"]


def member(key, src, api, section, note):
    """A person of the Space by display name; empty: nobody. A name already on a record of the section stays accepted (a former
    member left untouched is not refused)."""
    def out(rt, rec):
        return rec.get(src) or ""

    def check(rt, value, temps):
        value = " ".join(str(value or "").split())
        if not value:
            return "", ""
        names = {m["display_name"].lower(): m["display_name"] for m in _members(rt)}
        names.update({str(r[src]).lower(): r[src] for r in rt.records(section) if r.get(src)})
        if value.lower() not in names:
            return None, "{} : « {} » n'est pas un membre du Space. Correctif : le nom affiché d'un membre ({}), ou vide.".format(
                key, value, ", ".join(m["display_name"] for m in _members(rt)[:12]))
        return names[value.lower()], ""

    def to_api(rt, value):
        if not value:
            return None
        return next((m["id"] for m in _members(rt) if m["display_name"].lower() == str(value).lower()), -1)
    return Field(key, src=src, api=api, out=out, check=check, to_api=to_api, note=note)


def _dfmea_payload(rt):
    if "_dfmea" not in rt.temp:
        rt.temp["_dfmea"] = rt.call("GET", "/dfmea")
    return rt.temp["_dfmea"]


def _tests(rt):
    return {t["code"].upper(): t for t in _dfmea_payload(rt)["tests"]}


def _test_check(rt, value, temps):
    value = str(value or "").strip().split(" ")[0].upper()
    if value and value not in _tests(rt):
        return None, "test : « {} » absent de la Test Base de ce Space. Correctif : un code TST-… de la Test Base, ou vide.".format(value)
    return (_tests(rt)[value]["code"] if value else ""), ""


def test_field():
    """The key test of a row, by its code in the Space's Test Base."""
    return Field("test", src="test_code", api="test_id", out=lambda rt, rec: rec.get("test_code") or "", check=_test_check,
                 to_api=lambda rt, value: _tests(rt)[value.upper()]["id"] if value else None,
                 note="l'essai clé : son code dans la Test Base du Space (TST-…), ou vide")


def _record(rt, key, item_id):
    return next(r for r in rt.records(key) if r["id"] == item_id)



# ---------------------------------------------------------------- concepts (briques technologiques)

CONCEPTS = Section(
    "concepts", "Briques technologiques", ["concepts", "csheets"], order=40, table="diamond_concepts",
    items=lambda rt: rt.call("GET", "/concepts")["concepts"], code=lambda r: r["code"],
    fields=[Field("name", note="le nom de la brique, 120 caractères au plus (obligatoire)"),
            Field("initial_name", note="le concept initial, un nom qui parle (« Sandwich froid »), 80 caractères au plus"),
            Field("description", note="2000 caractères au plus"),
            Field("kind", kind="enum", values=list(CO.KINDS), note="existing : concept existant (catalogue, techno connue) ; to_define : à inventer"),
            Field("status", kind="enum", values=list(CO.STATUS)),
            Field("reference", note="la pièce du commerce, la techno ou le produit précédent d'une brique existing, 300 caractères au plus"),
            Field("pivot_note", note="ce qui a changé depuis le concept initial, et pourquoi, 1000 caractères au plus"),
            member("owner", "owner_name", "owner_id", "concepts", "qui porte la brique : le nom affiché d'un membre du Space, ou vide"),
            Field("functions", src="function_ids", api="function_ids", kind="refs", ref="functions",
                  note="les fonctions (F…) que la brique réalise ; une fonction appartient à une seule brique"),
            Field("selected_sheet", ro=True, out=lambda rt, rec: (rec.get("selected_sheet") or {}).get("code", ""),
                  note="la feuille retenue par une Pugh Matrix décidée"),
            Field("frozen", ro=True, out=lambda rt, rec: rec.get("frozen_text") or "" if rec.get("frozen") else "",
                  note="le concept retenu d'une brique figée (0.60.116) : la brique ne change plus, gardez-la telle quelle")],
    create=_create("/concepts"), update="/concepts/{id}", remove="/concepts/{id}/archive", removes="archive",
    guide="Les briques technologiques (CB-n) : le « avec quoi ? » des fonctions de l'arbre. Le nom d'une brique est une brique "
          "standard, définie très largement, qui existe déjà dans l'industrie pour couvrir la fonction (« Pack Li-ion avec BMS », "
          "« Capteur à ultrasons ») ; ses variantes inventives vont dans les feuilles de concept. Une brique porte une ou plusieurs "
          "fonctions, une fonction appartient à une seule brique (la nommer dans une autre brique l'y déplace). Une brique existing "
          "renvoie à un concept connu (reference) ; une brique to_define s'invente avec des feuilles de concept et des Pugh Matrices. "
          "Un retrait archive la brique : son numéro reste pris, ses feuilles et ses matrices restent.")


# ---------------------------------------------------------------- concept sheets

SHEET_KEYS = ("title", "kind", "principle", "description", "pros", "cons")
SCAN = "kind « scan » : réservé à une feuille papier déposée dans la page. Correctif : digital ou ai."


def _sheet_create(rt, body):
    cid, status = body.pop("concept_id", None), body.pop("status", None)
    if not cid:
        raise ApiError(400, "Feuille de concept sans brique. Correctif : « concept » : le code CB-n de sa brique.")
    if body.get("kind") == "scan" and not body.get("attachment_id"):
        raise ApiError(400, SCAN)
    sid = rt.call("POST", "/concepts/{}/sheets".format(cid), body)["created"]
    if status and status != "open":
        rt.call("PATCH", "/sheets/{}".format(sid), {"status": status})
    return sid


def _sheet_update(rt, sid, body):
    """A sheet does not change brick in place (its code CB-n.m names it): it is redrawn under the new brick, the old one archived."""
    rec = _record(rt, "sheets", sid)
    if "concept_id" in body and body["concept_id"] != rec["concept_id"]:
        full = dict({k: rec[k] for k in SHEET_KEYS}, status=rec["status"])
        full.update(body)
        if rec.get("attachment_id"):
            full["attachment_id"] = rec["attachment_id"]
        _sheet_create(rt, full)
        rt.call("POST", "/sheets/{}/archive".format(sid), {})
        return
    body.pop("concept_id", None)
    if body.get("kind") == "scan" and not rec.get("attachment_id"):
        raise ApiError(400, SCAN)
    if body:
        rt.call("PATCH", "/sheets/{}".format(sid), body)


SHEETS = Section(
    "sheets", "Feuilles de concept", ["csheets", "concepts"], order=45, table="diamond_concept_sheets",
    items=lambda rt: rt.call("GET", "/sheets")["sheets"], code=lambda r: r["code"],
    fields=[Field("concept", src="concept_id", kind="ref", ref="concepts", note="la brique (CB-n) dont la feuille est une solution (obligatoire)"),
            Field("title", note="160 caractères au plus (obligatoire)"),
            Field("kind", kind="enum", values=list(CS.KINDS), note="digital : écrite dans la plateforme ; ai : rédigée avec l'IA ; scan : "
                  "feuille papier déposée dans la page (jamais pour une nouvelle feuille)"),
            Field("status", kind="enum", values=list(CS.STATUS), note="selected : retenue (d'ordinaire par une Pugh Matrix décidée)"),
            Field("principle", note="le principe en une phrase, 600 caractères au plus"), Field("description", note="4000 caractères au plus"),
            Field("pros", note="1500 caractères au plus"), Field("cons", note="1500 caractères au plus")],
    create=_sheet_create, update=_sheet_update, remove="/sheets/{id}/archive", removes="archive",
    guide="Les feuilles de concept (CB-n.m) : les solutions candidates d'une brique to_define, avant la Pugh Matrix. Changer la "
          "brique d'une feuille la recrée sous l'autre brique (nouveau code) et archive l'ancienne. Le scan d'une feuille papier se "
          "dépose dans la page, pas ici. Un retrait archive la feuille.")


# ---------------------------------------------------------------- Pugh matrices

def _pugh_columns(rt, mid):
    return {c["name"]: c["id"] for c in rt.call("GET", "/pugh/{}".format(mid))["concepts"]}


def _pugh_items(rt):
    try:
        matrices = rt.call("GET", "/pugh")["matrices"]
    except ApiError:  # Agile (Goldmine) not enabled on this Space: no matrix
        return []
    out = []
    for m in sorted(matrices, key=lambda m: m["id"]):
        data = rt.call("GET", "/pugh/{}".format(m["id"]))
        names = {c["id"]: c["name"] for c in data["concepts"]}
        out.append(dict(m, columns=[c["name"] for c in data["concepts"]], scope_ids=[s["id"] for s in data["scope"]],
                        datum=names.get(m["datum_id"], ""), decision=names.get(m["decision_concept_id"], "") if m["status"] == "decided" else ""))
    return out


def _columns_check(rt, value, temps):
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        return None, "columns : une liste de noms de colonnes attendue (ex. [\"CB-1.1 + CB-2.1\", \"CB-1.2\"])."
    names = [" ".join(v.split()) for v in value]
    if any(not n or len(n) > 80 for n in names) or len(set(names)) != len(names) or len(names) > 12:
        return None, "columns : 12 colonnes au plus, chacune nommée (80 caractères au plus), sans doublon."
    return names, ""


def _pugh_finish(rt, mid, body):
    """Title, bricks, datum, rationale, then the decision -- once the columns are in place."""
    cols = _pugh_columns(rt, mid)
    for key in ("datum", "decision"):
        if body.get(key) and body[key] not in cols:
            raise ApiError(400, "{} « {} » : ce n'est pas une colonne de PM-{}.".format(key, body[key], mid))
    patch = {k: body[k] for k in ("title", "description", "decision_note", "concept_ids") if k in body}
    if "datum" in body:
        patch["datum_id"] = cols.get(body["datum"]) if body["datum"] else None
    if patch:
        rt.call("PATCH", "/pugh/{}".format(mid), patch)
    if body.get("status") == "decided":
        rt.call("PATCH", "/pugh/{}".format(mid), {"status": "decided", "decision_concept_id": cols.get(body.get("decision") or "")})
    elif body.get("decision"):
        raise ApiError(400, "decision : une matrice n'a de colonne retenue que décidée. Correctif : status « decided ».")


def _pugh_create(rt, body):
    data = rt.call("POST", "/pugh", {"title": body.get("title", ""), "description": body.get("description", ""), "fill": True,
                                     "concepts": body.get("columns") or [], "concept_ids": body.get("concept_ids") or []})
    mid = data["matrix"]["id"]
    rest = {k: v for k, v in body.items() if k in ("datum", "decision", "decision_note", "status")}
    if rest:
        _pugh_finish(rt, mid, rest)
    return mid


def _pugh_update(rt, mid, body):
    if _record(rt, "pugh", mid)["status"] == "decided":
        if body.get("status") != "draft":
            raise ApiError(409, "PM-{} est décidée : lecture seule. Correctif : status « draft » pour la rouvrir.".format(mid))
        rt.call("PATCH", "/pugh/{}".format(mid), {"status": "draft"})
        body.pop("status")
    if "columns" in body:
        cols, wanted = _pugh_columns(rt, mid), body.pop("columns")
        for name, cid in cols.items():
            if name not in wanted:  # its scores leave with it
                rt.call("PATCH", "/pugh/{}/concepts/{}".format(mid, cid), {"delete": True})
        for name in wanted:
            if name not in cols:
                rt.call("POST", "/pugh/{}/concepts".format(mid), {"name": name})
    _pugh_finish(rt, mid, body)


PUGH = Section(
    "pugh", "Matrices de Pugh", ["pugh", "concepts"], order=48, table="goldmine_pugh",
    items=_pugh_items, code=lambda r: "PM-{}".format(r["id"]),
    fields=[Field("title", note="200 caractères au plus (obligatoire)"), Field("description", note="4000 caractères au plus"),
            Field("bricks", src="scope_ids", api="concept_ids", kind="refs", ref="concepts", note="les briques jugées (CB-n)"),
            Field("columns", out=lambda rt, rec: rec["columns"], check=_columns_check, note="les options comparées, 12 au plus, "
                  "souvent des combinaisons de feuilles « CB-1.2 + CB-3.1 » ; retirer ou renommer une colonne efface ses notes"),
            Field("datum", note="la colonne de référence : son nom exact, parmi columns"),
            Field("status", kind="enum", values=["draft", "decided"], note="decided : la matrice est tranchée, en lecture seule"),
            Field("decision", note="la colonne retenue (son nom exact) ; seulement avec status decided"),
            Field("decision_note", note="le rationale de la décision, 4000 caractères au plus"),
            Field("round", kind="int", ro=True, note="le tour de la matrice")],
    create=_pugh_create, update=_pugh_update, remove=lambda rt, mid: rt.call("DELETE", "/pugh/{}".format(mid)),
    guide="Les Pugh Matrices (PM-n) : des colonnes (options, souvent des combinaisons de feuilles de concept) jugées + / S / - "
          "contre une colonne de référence (datum), sur les besoins, les fonctions et les requirements. Ici : le titre, les briques "
          "jugées, les colonnes, le datum, la décision. Les critères et les notes + / S / - restent dans la page. Décider sélectionne "
          "les feuilles de la colonne retenue ; une matrice décidée ne change plus sans revenir à status draft. Un retrait supprime "
          "la matrice (admin du Space).")


# ---------------------------------------------------------------- project risks

RISKS = Section(
    "risks", "Risques projet", ["prisk"], order=50, table="diamond_risks",
    items=lambda rt: rt.call("GET", "/risks")["risks"], code=lambda r: "R-{}".format(r["number"]),
    fields=[Field("title", note="« Si <cause>, alors <événement> », 200 caractères au plus (obligatoire)"),
            Field("cause", note="400 caractères au plus"), Field("consequence", note="400 caractères au plus"),
            Field("category", kind="enum", values=list(RI.CATEGORIES)),
            Field("phase", kind="enum", values=[k for k in RI.PHASES if k], note="A Discovery, B Concept, C Design, D Validation ; vide : aucune"),
            Field("probability", kind="int", note="de 1 (rare) à 5 (presque certain)"),
            Field("impact", kind="int", note="de 1 (faible) à 5 (majeur)"),
            Field("response", kind="enum", values=[k for k in RI.RESPONSES if k], note="la stratégie ; vide : à choisir"),
            Field("action", note="600 caractères au plus"),
            member("owner", "owner_name", "owner_id", "risks", "le nom affiché d'un membre du Space, ou vide"),
            Field("due_date", note="AAAA-MM-JJ, ou vide"),
            Field("status", kind="enum", values=list(RI.STATUSES), note="un risque suivi dans Agile prend le status de son ticket"),
            Field("residual_p", kind="int", note="probabilité une fois l'action faite, 1 à 5, ou vide"),
            Field("residual_i", kind="int", note="impact une fois l'action faite, 1 à 5, ou vide"),
            Field("function", src="function_id", kind="ref", ref="functions", note="la fonction de l'arbre en cause (F…), ou vide"),
            Field("to_dfmea", kind="bool", note="true : à détailler dans le DFMEA"), Field("notes", note="2000 caractères au plus"),
            Field("score", kind="int", ro=True, note="probability x impact"),
            Field("level", ro=True, out=lambda rt, rec: rec["level"]["label"]),
            Field("ticket", ro=True, out=lambda rt, rec: (rec.get("ticket") or {}).get("key", ""), note="le ticket Agile qui suit le risque")],
    create=_create("/risks"), update="/risks/{id}", remove="/risks/{id}/archive", removes="archive",
    guide="Le registre des risques du projet (R-n), avant le DFMEA : « Si <cause>, alors <événement>, ce qui <conséquence> », "
          "probabilité et impact de 1 à 5 (score P x I), une stratégie, une action, un responsable, une échéance, le risque résiduel. "
          "Un risque technique peut pointer une fonction de l'arbre et être marqué to_dfmea. Un retrait archive le risque : son "
          "numéro reste pris.")


# ---------------------------------------------------------------- DFMEA

def _rating(key, note):
    return Field(key, kind="int", note=note + ", de 1 à 10, ou vide")


DFMEA = Section(
    "dfmea", "DFMEA", ["dfmea"], order=60, table="diamond_dfmea",
    items=lambda rt: _dfmea_payload(rt)["rows"], code=lambda r: "D-{}".format(r["id"]),
    fields=[Field("function", src="function_id", kind="ref", ref="functions", note="la fonction du Focus Element (F…)"),
            Field("failure_mode", note="Failure Mode, 400 caractères au plus ; « Rien à signaler » se justifie dans effect"),
            Field("higher", note="Higher-Level Element : où l'effet arrive (l'utilisateur, le produit, le système), 160 caractères au plus"),
            Field("focus", note="Focus Element : l'ensemble ou le composant analysé, 160 caractères au plus"),
            Field("lower", note="Lower-Level Element : le sous-composant ou la caractéristique en cause, 160 caractères au plus"),
            Field("requirement", note="Requirement / Characteristic, 400 caractères au plus"),
            Field("effect", note="Failure Effect, 400 caractères au plus"), _rating("severity", "Severity (S)"),
            Field("cause", note="Failure Cause, 400 caractères au plus"),
            Field("prevention", note="Prevention Controls, 4000 caractères au plus"), _rating("occurrence", "Occurrence (O)"),
            Field("detection_ctrl", note="Detection Controls, 400 caractères au plus"),
            test_field(), _rating("detection", "Detection (D)"),
            Field("action", note="Actions, 600 caractères au plus"),
            member("action_owner", "action_owner_name", "action_owner_id", "dfmea", "qui porte l'action : un membre du Space, ou vide"),
            Field("action_due", note="AAAA-MM-JJ, ou vide"),
            Field("action_status", kind="enum", values=list(ACT.DFMEA_STATUSES), note="suivie dans Agile : le status de son ticket"),
            Field("rpn", kind="int", ro=True, note="S x O x D"), Field("ap", ro=True, note="Action Priority : H, M, L"),
            Field("risk", src="risk_id", kind="ref", ref="risks", ro=True, note="le risque projet d'où vient la ligne"),
            Field("class", ro=True, out=lambda rt, rec: rec.get("class_code") or "", note="CC / SC, décidée dans la page")],
    create=_create("/dfmea/rows"), update="/dfmea/rows/{id}", remove="/dfmea/rows/{id}/delete",
    guide="Le DFMEA AIAG-VDA : une ligne (D-n) par chaîne de défaillance -- Higher-Level Element (Failure Effect, Severity), "
          "Focus Element (Function, Requirement, Failure Mode), Lower-Level Element (Failure Cause, Prevention Controls et "
          "Occurrence, Detection Controls et Detection). RPN = S x O x D et l'Action Priority sont calculés. Toute fonction de "
          "l'arbre peut faillir : chacune a au moins une ligne. Une nouvelle ligne va à la fin du tableau ; un retrait supprime la "
          "ligne. La classe CC / SC se décide dans la page.")


# ---------------------------------------------------------------- characteristics

CHARS = Section(
    "chars", "Caractéristiques", ["chars"], order=70, table="diamond_characteristics",
    items=lambda rt: rt.call("GET", "/characteristics")["items"], code=lambda r: r["code"],
    fields=[Field("label", note="la cote, le seuil ou le temps (ex. « Entrefer aimant–capteur »), 160 caractères au plus"),
            Field("dfmea", src="dfmea_id", kind="ref", ref="dfmea", note="la ligne du DFMEA (D-n) d'où vient la caractéristique : sa classe en vient"),
            Field("nature", kind="enum", values=list(SP.NATURES)),
            Field("prefix", note="R (rayon), Ø (diamètre)…, 4 caractères au plus"),
            Field("nominal", kind="num", note="un nombre (point décimal), ou vide"), Field("lsl", kind="num", note="LSL, ou vide"),
            Field("usl", kind="num", note="USL, ou vide ; LSL < nominal < USL"), Field("unit", note="16 caractères au plus"),
            Field("spec_text", note="la spécification sans nombre (« aucune fuite à 0,5 bar »), 400 caractères au plus"),
            Field("part", src="part_id", kind="ref", ref="parts", note="la pièce qui porte la cote (P-n)"),
            Field("part2", src="part2_id", kind="ref", ref="parts", note="la seconde pièce d'une interface (P-n), ou vide"),
            Field("drawing", note="le plan, 80 caractères au plus"), Field("sheet", note="16 caractères au plus"),
            Field("zone", note="16 caractères au plus"), Field("datum", note="40 caractères au plus"),
            Field("control", kind="enum", values=list(SP.CONTROLS), note="spc : capability study (Cpk) ; test100 : essai 100 % ; design : vérifiée en conception"),
            Field("cpk_required", kind="num", note="de 0.5 à 5, ou vide pour la valeur du client selon la classe"),
            test_field(), Field("notes", note="2000 caractères au plus"),
            Field("spec", ro=True, note="la spécification écrite comme sur le plan"), Field("class", ro=True, out=lambda rt, rec: rec.get("class_code") or ""),
            Field("status", ro=True, out=lambda rt, rec: rec.get("status_label") or "")],
    create=_create("/characteristics", "created_id"), update="/characteristics/{id}", remove="/characteristics/{id}/archive",
    removes="archive",
    guide="Les caractéristiques spéciales (C-nn) : la cote exacte de la pièce exacte, venue d'une ligne du DFMEA dont la classe CC / "
          "SC est confirmée. Leur spécification (nominal, LSL, USL, unité, ou un texte), la pièce, le plan, le contrôle, le Cpk exigé, "
          "l'essai clé. Un retrait archive la caractéristique : son numéro n'est jamais redonné.")

SECTIONS = [CONCEPTS, SHEETS, PUGH, RISKS, DFMEA, CHARS]
