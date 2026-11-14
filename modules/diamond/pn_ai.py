"""The company part numbers matched by an AI assistant (0.60.103, D-O-112) -- the external loop only, as for the Storyline and
the costs: « Copier le prompt pour l'IA », paste the answer back. Nothing leaves the server (FONDATIONS §2); a model
installed on the company's server (the internal loop) would be an exception to that rule: an open question (D-O-112).

The prompt gives the Diamond parts (code, name, kind, functions, notes) and the BOM of the ERP, with a strict rule: never
invent a PN, answer « aucun » when none fits, one reason per proposal. The answer is JSON, a list of
{part, pn, rev, confiance, raison}. POST …/pn/ai {answer, mode: preview | apply, pick: [index…], todo: [part…]}:
preview sorts every proposal -- « sûre » (confidence 0,8 or more, the PN exists), « à choisir » (lower), « à créer dans
l'ERP » (« aucun »), « refusée » (a PN absent from the BOM: invented, never written) --; apply writes the picked ones (by
default every « sûre ») and marks the « aucun » parts to create in the ERP, journalled.
"""
import json
import re

from core import audit
from core.errors import ApiError

from . import company_pn as PN
from . import functions as F

SURE = 0.8
MAX_ANSWER = 400_000


def prompt(conn, pid):
    project = conn.execute("SELECT name, key FROM projects WHERE id = ?", (pid,)).fetchone()
    data = PN.payload(conn, pid)
    fn = {}
    for r in conn.execute("SELECT pf.part_id, f.number, f.text FROM diamond_part_functions pf JOIN diamond_functions f ON f.id = pf.function_id "
                          "WHERE pf.project_id = ? AND f.archived = 0 ORDER BY f.number", (pid,)):
        fn.setdefault(r["part_id"], []).append("F{} {}".format(r["number"], r["text"]))
    lines = ["Tu relies les pièces d'un produit (Diamond) aux numéros de pièce de l'entreprise (la nomenclature de l'ERP).",
             "Produit : {} ({}).".format(project["name"], project["key"]), "",
             "RÈGLES STRICTES",
             "1. Ne jamais inventer un numéro : chaque « pn » de ta réponse est copié de la nomenclature ci-dessous, ou vaut « aucun ».",
             "2. Une pièce Diamond peut couvrir plusieurs PN (ex. un support et son aimant) : une proposition par PN.",
             "3. « aucun » quand rien ne convient : la pièce sera créée dans l'ERP.",
             "4. Une raison courte par proposition (désignation, matière, fournisseur, fonction).",
             "5. « confiance » de 0 à 1 : 0,8 ou plus seulement quand la désignation dit clairement la même pièce.", "",
             "RÉPONSE : uniquement un tableau JSON, sans texte autour :",
             '[{"part": "P-14", "pn": "RVR-3140-02", "rev": "C", "confiance": 0.9, "raison": "support du capteur à effet Hall"}]', "",
             "PIÈCES DIAMOND (code ; nom ; type ; fonctions ; notes)"]
    for p in data["parts"]:
        lines.append("{} ; {} ; {} ; {} ; {}".format(p["code"], p["name"], p["kind"], " | ".join(fn.get(p["id"], [])) or "—",
                                                     " ".join((p["notes"] or "").split())[:300] or "—"))
    lines += ["", "NOMENCLATURE DE L'ERP (PN ; révision ; désignation ; fournisseur ; matière)"]
    for b in data["bom"]:
        lines.append("{} ; {} ; {} ; {} ; {}".format(b["pn"], b["rev"] or "—", b["designation"] or "—", b["supplier"] or "—", b["material"] or "—"))
    return "\n".join(lines)


def api_prompt(ctx):
    pid = F.access(ctx)
    data = PN.payload(ctx.conn, pid)
    if not data["bom"]:
        raise ApiError(400, "La nomenclature de l'ERP est vide. Correctif : « Importer le BOM (.csv) » d'abord.")
    return {"prompt": prompt(ctx.conn, pid), "parts": len(data["parts"]), "bom": len(data["bom"])}


def _answer(text):
    text = str(text or "").strip()
    if len(text.encode("utf-8")) > MAX_ANSWER:
        raise ApiError(413, "Réponse trop longue. Correctif : collez seulement le tableau JSON.")
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        raise ApiError(400, "Aucun tableau JSON dans la réponse. Correctif : demandez à l'IA « uniquement le tableau JSON ».")
    try:
        items = json.loads(text[start:end + 1])
    except ValueError as exc:
        raise ApiError(400, "JSON illisible ({}). Correctif : recopiez la réponse complète de l'IA.".format(exc))
    if not isinstance(items, list):
        raise ApiError(400, "Un tableau JSON est attendu.")
    return items


def _confidence(value):
    try:
        x = float(str(value).replace(",", ".").rstrip("%"))
    except (TypeError, ValueError):
        return 0.0
    return x / 100 if x > 1 else max(0.0, x)


def sort(conn, pid, items):
    """Each proposal with its verdict: sure | choose | todo | refused (and why)."""
    data = PN.payload(conn, pid)
    parts = {p["code"].upper(): p for p in data["parts"]}
    bom = {b["pn"].upper(): b for b in data["bom"]}
    out = []
    for i, it in enumerate(items):
        it = it if isinstance(it, dict) else {}
        code = str(it.get("part") or "").strip().upper().replace(" ", "")
        pn = str(it.get("pn") or "").strip()
        row = {"index": i, "part": code, "pn": pn, "rev": str(it.get("rev") or ""), "confidence": _confidence(it.get("confiance", it.get("confidence"))),
               "reason": str(it.get("raison") or it.get("reason") or "")[:300]}
        part = parts.get(code)
        if part is None:
            out.append(dict(row, verdict="refused", why="Pièce {} absente de Diamond.".format(code or "?")))
        elif pn.lower() in ("", "aucun", "none", "null", "—"):
            out.append(dict(row, verdict="todo", part_id=part["id"], why="Aucun PN ne convient : à créer dans l'ERP."))
        elif pn.upper() not in bom:
            out.append(dict(row, verdict="refused", part_id=part["id"], why="PN {} absent de la nomenclature : jamais écrit (inventé ?).".format(pn)))
        else:
            b = bom[pn.upper()]
            out.append(dict(row, part_id=part["id"], company_id=b["id"], designation=b["designation"], label=PN.label(b),
                            verdict="sure" if row["confidence"] >= SURE else "choose",
                            why="" if row["confidence"] >= SURE else "Confiance {:.0%} : à choisir à la main.".format(row["confidence"])))
    return out


def api_import(ctx):
    pid = F.access(ctx, "editor")
    rows = sort(ctx.conn, pid, _answer(ctx.body.get("answer")))
    counts = {k: sum(1 for r in rows if r["verdict"] == k) for k in ("sure", "choose", "todo", "refused")}
    if ctx.body.get("mode") != "apply":
        return {"mode": "preview", "rows": rows, "counts": counts}
    pick = ctx.body.get("pick")
    pick = {int(i) for i in pick} if isinstance(pick, list) else {r["index"] for r in rows if r["verdict"] == "sure"}
    todo = {str(c).upper() for c in ctx.body.get("todo", [r["part"] for r in rows if r["verdict"] == "todo"])}
    chosen = [r for r in rows if r["index"] in pick and r.get("company_id")]
    current = PN.links(ctx.conn, pid)
    by_part = {}
    for r in chosen:
        by_part.setdefault(r["part_id"], {})[r["company_id"]] = (r["confidence"], r["reason"])
    for part_id, detail in by_part.items():
        keep = [x["id"] for x in current.get(part_id, [])]
        PN.set_part(ctx.conn, ctx.user["id"], pid, part_id, sorted(set(keep) | set(detail)), "ai", detail)
    marked = [r["part_id"] for r in rows if r["verdict"] == "todo" and r["part"] in todo and r["part_id"] not in by_part]
    for part_id in marked:
        ctx.conn.execute("UPDATE diamond_parts SET erp_todo = 1 WHERE id = ?", (part_id,))
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_pn_ai_import", "project", pid,
                     {"linked": len(chosen), "erp_todo": len(marked), "refused": counts["refused"]}, ctx.ip)
    return dict(PN.payload(ctx.conn, pid), mode="apply", applied={"linked": len(chosen), "erp_todo": len(marked)})
