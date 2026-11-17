"""Diamond · « ↔ IA » (0.60.111, D-O-124): the sections of « Analyse fonctionnelle » -- Storyline, Arbre fonctionnel, Structure
fonctionnelle (inputs / outputs, flows, parts). See rt.py for the engine.

Codes: a function is F<number>; a part P-<number>; a scene S-<id>, an input or output IO-<id>, a flow FX-<id> (these have no
number: their id, stable while the team keeps working)."""
from . import functions as FN
from . import parts as PA
from . import story as ST
from . import structure as SR
from .rt import Field, Section


# ---------------------------------------------------------------- functions

def _functions(rt):
    return [f for f in rt.call("GET", "/functions")["functions"] if not f["archived"]]


def _function_update(rt, item_id, body):
    """« parent » moves the function (its own route); the other fields go to PATCH."""
    if "parent_id" in body:
        parent = body.pop("parent_id")
        rt.call("POST", "/functions/{}/move".format(item_id), {"parent_id": parent})
    if body:
        rt.call("PATCH", "/functions/{}".format(item_id), body)


FUNCTIONS = Section(
    "functions", "Arbre fonctionnel", ["ftree", "fstructure", "concepts", "dfmea"], order=10, table="diamond_functions",
    items=_functions, code=lambda r: "F{}".format(r["number"]),
    fields=[Field("text", note="la fonction : un verbe à l'infinitif et un complément, 160 caractères au plus"),
            Field("type", src="ftype", kind="enum", values=list(FN.TYPES), note="usage, estime, technique (niveau 4) ou contrainte"),
            Field("parent", src="parent_id", kind="ref", ref="functions", note="la fonction au-dessus (vide : primaire ou hors arbre)"),
            Field("kano", kind="enum", values=list(FN.KANO)), Field("importance", kind="enum", values=list(FN.IMPORTANCE)),
            Field("critical", kind="bool"), Field("notes"), Field("level", kind="int", ro=True, note="1 primaire … 4 technique")],
    create="/functions", update=_function_update, remove="/functions/{id}/archive", removes="archive",
    guide="L'arbre fonctionnel (FAST / APTE) : une primaire, des secondaires, des tertiaires, des techniques au niveau 4. "
          "Un retrait archive la fonction : ses sous-fonctions remontent sous son parent, son numéro reste pris.")


# ---------------------------------------------------------------- story

def _scenes(rt):
    return rt.call("GET", "/story")["scenes"]


def _scene_create(rt, body):
    created = rt.call("POST", "/story/scenes", {k: body[k] for k in ("title", "caption") if k in body})["created"]
    rest = {k: v for k, v in body.items() if k not in ("title", "caption")}
    if rest:
        rt.call("PATCH", "/story/scenes/{}".format(created), rest)
    return created


STORY = Section(
    "story", "Storyline", ["story"], order=5, table="diamond_story_scenes",
    items=_scenes, code=lambda r: "S-{}".format(r["id"]),
    fields=[Field("title", note="80 caractères au plus"), Field("caption", note="ce qui se passe, 600 caractères au plus"),
            Field("notes", note="questions, irritants, 2000 caractères au plus"),
            Field("items", kind="json", note="pictogrammes [{p, x, y, s, f, t}] : p parmi " + ", ".join(ST.PICTOS[:12]) + "…, "
                  "laisser tels quels si vous ne les changez pas")],
    create=_scene_create, update="/story/scenes/{id}", remove="/story/scenes/{id}/delete",
    guide="La Storyline : les scènes de l'usage du produit, dans l'ordre, celles d'où sortent les besoins et les fonctions.")


# ---------------------------------------------------------------- structure

def _structure(rt):
    if "_structure" not in rt.temp:
        rt.temp["_structure"] = rt.call("GET", "/structure")
    return rt.temp["_structure"]


def _end_out(side):
    def out(rt, rec):
        fid, port = rec.get(side + "_function_id"), rec.get(side + "_port_id")
        return rt.code_of("functions", fid) if fid else ("IO-{}".format(port) if port else "")
    return out


def _end_check(rt, value, temps):
    value = str(value or "").strip()
    known = set(rt.codes("functions")) | set(rt.codes("ports")) | temps.get("functions", set()) | temps.get("ports", set())
    if value not in known:
        return None, "Extrémité « {} » inconnue : une fonction (F…) ou une entrée / sortie (IO-…).".format(value)
    return value, ""


def _end_api(rt, value):
    if value in rt.codes("ports"):
        return {"type": "port", "id": rt.codes("ports")[value]}
    return {"type": "function", "id": rt.codes("functions")[value]}


def _flow_update(rt, item_id, body):
    if "src" in body or "dst" in body or "view" in body:  # the ends of a flow do not move: the flow is redrawn
        old = next(f for f in _structure(rt)["flows"] if f["id"] == item_id)
        full = {"view": old["view"], "kind": old["kind"], "label": old["label"],
                "src": {"type": "port", "id": old["src_port_id"]} if old["src_port_id"] else {"type": "function", "id": old["src_function_id"]},
                "dst": {"type": "port", "id": old["dst_port_id"]} if old["dst_port_id"] else {"type": "function", "id": old["dst_function_id"]}}
        full.update(body)
        rt.call("POST", "/structure/flows/{}/delete".format(item_id), {})
        rt.call("POST", "/structure/flows", full)
    else:
        rt.call("PATCH", "/structure/flows/{}".format(item_id), body)


PORTS = Section(
    "ports", "Entrées et sorties du système", ["fstructure"], order=20, table="diamond_ports",
    items=lambda rt: _structure(rt)["ports"], code=lambda r: "IO-{}".format(r["id"]),
    fields=[Field("label", note="80 caractères au plus"), Field("side", kind="enum", values=list(SR.SIDES), note="in : entrée, out : sortie"),
            Field("kind", kind="enum", values=list(SR.KINDS))],
    create="/structure/ports", update="/structure/ports/{id}", remove="/structure/ports/{id}/delete",
    guide="Ce qui entre dans le système et ce qui en sort (énergie, matière, information). Un retrait supprime aussi ses flux.")

FLOWS = Section(
    "flows", "Flux de la structure fonctionnelle", ["fstructure"], order=30, table="diamond_flows",
    items=lambda rt: _structure(rt)["flows"], code=lambda r: "FX-{}".format(r["id"]),
    fields=[Field("view", kind="enum", values=list(SR.VIEWS), note="general : entre secondaires ; detail : entre tertiaires"),
            Field("kind", kind="enum", values=list(SR.KINDS)), Field("label", note="60 caractères au plus"),
            Field("src", out=_end_out("src"), check=_end_check, to_api=_end_api, note="d'où part le flux : F… ou une entrée IO-…"),
            Field("dst", out=_end_out("dst"), check=_end_check, to_api=_end_api, note="où il arrive : F… ou une sortie IO-…")],
    create="/structure/flows", update=_flow_update, remove="/structure/flows/{id}/delete",
    guide="Les flux relient les fonctions entre elles et aux entrées / sorties ; un flux part d'une entrée et arrive à une sortie, "
          "jamais directement de l'une à l'autre.")


def _part_functions(rt, item_id, wanted):
    have = set(next((p["functions"] for p in rt.call("GET", "/structure")["parts"] if p["id"] == item_id), []))
    for fid in set(wanted) - have:
        rt.call("PUT", "/structure/parts/{}/functions".format(item_id), {"function_id": fid, "on": True})
    for fid in have - set(wanted):
        rt.call("PUT", "/structure/parts/{}/functions".format(item_id), {"function_id": fid, "on": False})


PARTS = Section(
    "parts", "Pièces", ["fstructure"], order=25, table="diamond_parts",
    items=lambda rt: _structure(rt)["parts"], code=lambda r: "P-{}".format(r["number"]),
    fields=[Field("name", note="80 caractères au plus"), Field("kind", kind="enum", values=list(PA.KINDS)), Field("notes"),
            Field("functions", kind="refs", ref="functions", setter=_part_functions, note="les fonctions que la pièce réalise (F…)")],
    create="/structure/parts", update="/structure/parts/{id}", remove="/structure/parts/{id}/delete",
    guide="Les pièces du produit et les fonctions que chacune réalise.")

SECTIONS = [STORY, FUNCTIONS, PORTS, PARTS, FLOWS]
