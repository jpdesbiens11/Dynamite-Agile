"""The PFMEA proposed by an AI assistant (0.60.103, D-O-114): the prompt is assembled from two sources -- the final extract
of the DFMEA (the classified rows, their effects, severities and causes, with their characteristics C-n) and the assembly
line (operations, equipment, control points) -- and the answer comes back as DRAFT rows, never into the validated PFMEA:
a person accepts or rejects each one (pfmea.api_review). External loop only (copy, paste): nothing leaves the server.

GET …/pfmea/prompt?line=<n>; POST …/pfmea/ai {answer, line}: every proposal is checked (the operation exists on the line,
the C-n exists, the 5M class, O and D from 1 to 10) and written as a draft; a proposal that does not hold is listed with its
reason, never written.
"""
import json
import re

from core import audit
from core.errors import ApiError

from . import pfmea as PF
from . import process as PR

MAX_ANSWER = 600_000


def _line(conn, user, pid, number):
    lines = PR.payload(conn, user, pid)["lines"]
    if not lines:
        raise ApiError(400, "Aucune ligne d'assemblage. Correctif : décrivez d'abord la ligne dans Diamond → Procédés.")
    try:
        number = int(number) if number not in (None, "") else lines[0]["number"]
    except (TypeError, ValueError):
        number = -1
    line = next((x for x in lines if x["number"] == number), None)
    if line is None:
        raise ApiError(400, "Ligne L{} introuvable. Correctif : choisissez une configuration de ligne de la liste.".format(number))
    return line


def prompt(conn, user, pid, line):
    from . import characteristics as CH
    from . import dfmea as DF
    project = conn.execute("SELECT name, key FROM projects WHERE id = ?", (pid,)).fetchone()
    chars = CH.payload(conn, pid)["items"]
    by_row = {}
    for c in chars:
        if c["dfmea_id"]:
            by_row.setdefault(c["dfmea_id"], []).append(c)
    out = ["Tu prépares un PFMEA (Process FMEA, AIAG-VDA 2019) pour la ligne d'assemblage d'un produit.",
           "Produit : {} ({}). Ligne : {} · {}.".format(project["name"], project["key"], line["code"], line["name"]), "",
           "RÈGLES",
           "1. Une ligne par chaîne de défaillance de procédé : opération, étape, caractéristique produit (C-n) ou de procédé, mode, effet, "
           "cause, prévention, détection, O et D de 1 à 10.",
           "2. La sévérité vient du DFMEA (S de la ligne de la caractéristique) : ne la donne pas pour une C-n ; donne « s » seulement pour une "
           "caractéristique de procédé sans C-n.",
           "3. Classe chaque cause en 5M : main-d'œuvre, méthode, matière, machine, mesure.",
           "4. Commence par les caractéristiques spéciales (CC, SC) et par les causes de procédé que le DFMEA renvoie au PFMEA.",
           "5. N'invente ni opération ni C-n : utilise seulement celles données ci-dessous.", "",
           "RÉPONSE : uniquement un tableau JSON, sans texte autour :",
           '[{"op": "OP30", "step": "Poser le capteur à l\'entrefer", "char": "C-14", "process_char": "Hauteur de cale, serrage", '
           '"failure_mode": "Entrefer > 2,3 mm", "effect": "Impulsions manquées", "cause": "Cale oubliée", "cause_5m": "main-d\'œuvre", '
           '"prevention": "Instruction au poste", "detection": "Jauge go/no-go", "o": 5, "d": 6}]', "",
           "EXTRAIT FINAL DU DFMEA (lignes classées et causes de procédé ; L = ligne, S = sévérité)"]
    for r in DF.rows(conn, pid):
        linked = by_row.get(r["id"], [])
        if not (r["special"] or any(c["nature"] == "process" for c in linked)):
            continue
        out.append("L{} ; {} ; F{} {} ; mode : {} ; effet : {} ; S {} ; cause : {} ; caractéristiques : {}".format(
            r["line"], r["class_code"] or "procédé", r["function_number"] or "?", r["function_text"] or "", r["failure_mode"], r["effect"],
            r["severity"] or "—", r["cause"], ", ".join("{} {} ({}{})".format(c["code"], c["label"], c["spec"], ", procédé" if c["nature"] == "process" else "")
                                                         for c in linked) or "—"))
    out += ["", "LIGNE {} (opération ; nom ; équipements ; points de contrôle)".format(line["code"])]
    for o in line["operations"]:
        out.append("OP{} ; {} ; {} ; {}".format(o["op"], o["name"], ", ".join(o["equipment_list"]) or "—",
                                                " | ".join(PR.point_label(p) for p in o["points"]) or "—"))
    return "\n".join(out)


def api_prompt(ctx):
    pid = PR.access(ctx)
    line = _line(ctx.conn, ctx.user, pid, ctx.query.get("line"))
    return {"prompt": prompt(ctx.conn, ctx.user, pid, line), "line": line["code"], "operations": len(line["operations"])}


def _items(text):
    text = str(text or "").strip()
    if len(text.encode("utf-8")) > MAX_ANSWER:
        raise ApiError(413, "Réponse trop longue. Correctif : collez seulement le tableau JSON.")
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    text = fence.group(1).strip() if fence else text
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        raise ApiError(400, "Aucun tableau JSON dans la réponse. Correctif : demandez à l'IA « uniquement le tableau JSON ».")
    try:
        items = json.loads(text[start:end + 1])
    except ValueError as exc:
        raise ApiError(400, "JSON illisible ({}). Correctif : recopiez la réponse complète.".format(exc))
    if not isinstance(items, list):
        raise ApiError(400, "Un tableau JSON est attendu.")
    return items


def api_import(ctx):
    """The answer of the AI, every valid proposal written as a DRAFT row; the others listed with their reason."""
    pid = PR.access(ctx, "editor")
    line = _line(ctx.conn, ctx.user, pid, ctx.body.get("line"))
    ops = {o["op"]: o for o in line["operations"]}
    chars = {c["code"].upper(): c for c in PR.payload(ctx.conn, ctx.user, pid)["characteristics"]}
    made, refused = 0, []
    for i, it in enumerate(_items(ctx.body.get("answer")), start=1):
        it = it if isinstance(it, dict) else {}
        try:
            op = int(str(it.get("op") or "").upper().replace("OP", "").strip() or -1)
        except ValueError:
            op = -1
        if op not in ops:
            raw = str(it.get("op") or "?").strip()
            refused.append("Proposition {} : {} absente de {}.".format(i, raw if raw.upper().startswith("OP") else "OP" + raw, line["code"]))
            continue
        code = str(it.get("char") or "").strip().upper()
        if code and code not in chars:
            refused.append("Proposition {} : {} n'existe pas (inventée ?).".format(i, code))
            continue
        body = {"operation_id": ops[op]["id"], "characteristic_id": chars[code]["id"] if code else None, "process_step": it.get("step", ""),
                "process_char": it.get("process_char", ""), "failure_mode": it.get("failure_mode", ""), "effect": it.get("effect", ""),
                "cause": it.get("cause", ""), "cause_5m": it.get("cause_5m", ""), "prevention": it.get("prevention", ""),
                "detection_ctrl": it.get("detection", ""), "occurrence": it.get("o"), "detection": it.get("d"),
                "severity": None if code else it.get("s")}
        try:
            values = PF.fields(ctx.conn, pid, body, {})
        except ApiError as exc:
            refused.append("Proposition {} : {}".format(i, exc.message))
            continue
        PF.insert(ctx.conn, ctx.user["id"], pid, values, state="draft", source="ai")
        made += 1
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_pfmea_ai_import", "project", pid, {"line": line["code"], "drafts": made, "refused": len(refused)}, ctx.ip)
    return dict(PF.payload(ctx.conn, ctx.user, pid), drafts=made, refused=refused)
