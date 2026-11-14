"""Diamond · prompt templates for an AI assistant (0.60.104, D-O-116): the DFMEA here, the PFMEA and the control plans in
ai_prompts_process.py. Each prompt is built from what the Space holds, for Claude, Gemini or another LLM, in two modes:

  interview  « Entrevue guidée »: the assistant leads a FMEA session with the engineer -- one short question at a time, in the
             order of the method, a recap every few answers, never a fact it invented -- and gives the answer when the
             engineer writes « GÉNÈRE » (or confirms that everything is covered);
  review     « Révision »: it reads the current table and proposes corrections and missing rows at once.

The answer is always the same: ONE ```json block, an array of objects whose keys are the headers of « Exporter (.csv) » --
what « Importer » reads back (ai_io.py), preview first. The codes it may use are listed in the prompt (functions F-n, tests
TST-…, characteristics C-n, operations OP…, plans PC-n, parts P-n); a code it invents is refused at the import. External loop
only (copy, paste): the platform calls no AI service.
"""
import json

from core.errors import ApiError

from . import actions as ACT
from . import dfmea as DF
from . import dfmea_ap as AP
from . import functions as F

MODES = {"interview": "Entrevue guidée", "review": "Révision"}


def mode_of(ctx, allowed=MODES):
    mode = ctx.query.get("mode") or "interview"
    if mode not in allowed:
        raise ApiError(400, "Mode « {} » inconnu. Correctif : {}.".format(mode, ", ".join(allowed)))
    return mode


def project(conn, pid):
    return conn.execute("SELECT name, key, description FROM projects WHERE id = ?", (pid,)).fetchone()


def scales():
    names = {"severity": "S (sévérité)", "occurrence": "O (occurrence)", "detection": "D (détection)"}
    out = []
    for key, bands in AP.SCALES.items():
        out.append(names[key] + " : " + " · ".join("{}–{} {}".format(lo, hi, text) if lo != hi else "{} {}".format(lo, text) for (lo, hi), text in bands))
    out.append("AP (Action Priority, AIAG-VDA) : calculée par l'outil à partir de S, O et D — High demande une action, Medium une action ou "
               "une justification.")
    return out


def json_lines(items):
    """One object per line: short enough to read, exact keys to copy."""
    return "\n".join(json.dumps(item, ensure_ascii=False) for item in items) or "(aucune ligne pour l'instant)"


def protocol(mode, order):
    if mode == "interview":
        return ["## Déroulement : entrevue guidée",
                "Tu animes une séance de travail avec l'ingénieur·e responsable, comme un animateur d'AMDEC expérimenté.",
                "1. Pose **une seule question à la fois**, courte, et attends la réponse. Quand c'est possible, propose 2 à 4 réponses possibles.",
                "2. Commence par confirmer le périmètre et ce que la personne veut couvrir aujourd'hui, puis suis cet ordre : " + order,
                "3. Toutes les 3 ou 4 réponses, reformule en une ou deux phrases ce que tu as compris et fais corriger.",
                "4. N'invente aucun fait (valeur, essai, équipement, cote) : demande-le. Si la personne ne sait pas, écris « à vérifier » dans le texte.",
                "5. Propose les cotations S, O et D avec une phrase de justification tirée de l'échelle ; la personne tranche.",
                "6. Quand la personne écrit **GÉNÈRE** (ou confirme que tout est couvert), rends la réponse dans le format ci-dessous, "
                "puis une courte liste des points « à vérifier »."]
    return ["## Déroulement : révision",
            "Lis le tableau actuel et rends en une seule réponse : les corrections des lignes existantes (cotations incohérentes avec l'échelle, "
            "effet ou cause flous, contrôle de détection absent, action manquante pour une AP High) et les lignes qui manquent. Ordre suivi : " + order,
            "Sous le bloc, liste tes hypothèses et les questions à poser à l'équipe. N'invente aucun fait : écris « à vérifier » dans le texte."]


def answer_format(keys, example, readonly, code_key, extra_rules=()):
    return ["## Format de la réponse (obligatoire)",
            "Un **seul bloc ```json** : un tableau d'objets, un objet par ligne, avec exactement ces clés : " + ", ".join("« {} »".format(k) for k in keys) + ".",
            "- Ligne existante : garde son « {} » et ne donne que les clés que tu changes (une clé absente garde sa valeur).".format(code_key),
            "- Nouvelle ligne : « {} » vide (\"\") et toutes les clés.".format(code_key),
            "- Ne supprime rien : une ligne absente de ta réponse reste telle quelle dans l'outil.",
            "- N'utilise que les codes listés dans ce prompt ; un code inventé sera refusé à l'import.",
            "- Clés en lecture seule, ignorées à l'import : " + ", ".join(readonly) + "."] + list(extra_rules) + [
            "Exemple :", "```json", json.dumps(example, ensure_ascii=False, indent=1), "```"]


# --------------------------------------------------------------------------- DFMEA

DFMEA_KEYS = ["Ligne", "Function of Focus Element", "Requirement / Characteristic", "Failure Mode", "Failure Effect", "S", "Failure Cause",
              "Prevention Controls", "O", "Detection Controls", "Essai clé (Test Base)", "D", "Actions", "Responsable", "Échéance", "Status de l'action"]


def dfmea_row(r):
    return {"Ligne": "L{}".format(r["line"]), "Function of Focus Element": "F{} {}".format(r["function_number"], r["function_text"]) if r["function_number"] else "",
            "Requirement / Characteristic": r["requirement"], "Failure Mode": r["failure_mode"], "Failure Effect": r["effect"], "S": r["severity"] or "",
            "Failure Cause": r["cause"], "Prevention Controls": r["prevention"], "O": r["occurrence"] or "", "Detection Controls": r["detection_ctrl"],
            "Essai clé (Test Base)": r["test_code"] or "", "D": r["detection"] or "", "Actions": r["action"], "Responsable": r["action_owner_name"] or "",
            "Échéance": r["action_due"] or "", "Status de l'action": ACT.DFMEA_STATUSES.get(r["action_status"], ""),
            "AP": {"H": "High", "M": "Medium", "L": "Low"}.get(r["ap"], ""), "Class": r["class_code"] if r.get("special") else ""}


def dfmea_prompt(conn, pid, mode):
    p = project(conn, pid)
    rows = DF.rows(conn, pid)
    functions = F.rows(conn, pid)
    tests = DF.tests(conn, pid)
    out = ["# DFMEA — {} ({})".format(p["name"], p["key"]), "",
           "Tu es un ingénieur fiabilité qui maîtrise l'AMDEC de conception (DFMEA, AIAG-VDA 2019). Tu travailles avec l'équipe du produit "
           "« {} »{} dans l'outil Dynamite | Agile (module Diamond). Ce que tu rends est relu par l'équipe, puis importé.".format(
               p["name"], " : " + p["description"] if p["description"] else ""), ""]
    out += protocol(mode, "fonction par fonction (de l'arbre ci-dessous, les fonctions principales d'abord) : l'exigence, les modes de "
                          "défaillance (perte, partielle, intermittente, non voulue), leurs effets et S, les causes et O, la prévention, la "
                          "détection et D, l'essai clé de la Test Base, puis les actions pour les AP High.")
    out += ["", "## Échelles"] + scales()
    out += ["", "## Fonctions de l'arbre (codes utilisables)"] + ["F{} {}".format(f["number"], f["text"]) for f in functions]
    out += ["", "## Essais de la Test Base (codes utilisables pour « Essai clé (Test Base) »)"]
    out += ["{} {}".format(t["code"], t["title"]) for t in tests[:150]] or ["(aucun essai)"]
    out += ["", "## Membres du Space (pour « Responsable »)", ", ".join(m["display_name"] for m in ACT.members(conn, pid)) or "—"]
    out += ["", "## DFMEA actuel ({} lignes ; AP et Class sont calculées ou décidées dans l'outil)".format(len(rows)), json_lines(dfmea_row(r) for r in rows), ""]
    example = {"Ligne": "", "Function of Focus Element": "F{} {}".format(functions[0]["number"], functions[0]["text"]) if functions else "F1 …",
               "Requirement / Characteristic": "…", "Failure Mode": "…", "Failure Effect": "…", "S": 7, "Failure Cause": "…",
               "Prevention Controls": "…", "O": 4, "Detection Controls": "…", "Essai clé (Test Base)": tests[0]["code"] if tests else "",
               "D": 3, "Actions": "", "Responsable": "", "Échéance": "", "Status de l'action": ""}
    out += answer_format(DFMEA_KEYS, [example], ["AP", "Class", "RPN", "Ticket Agile"], "Ligne",
                         ["- « Status de l'action » : " + ", ".join(ACT.DFMEA_STATUSES.values()) + " ; « Échéance » au format AAAA-MM-JJ.",
                          "- Les classes CC / SC se décident dans l'outil, à partir de S et O : ne les écris pas."])
    return "\n".join(out)


def api_dfmea_prompt(ctx):
    pid = F.access(ctx)
    mode = mode_of(ctx)
    text = dfmea_prompt(ctx.conn, pid, mode)
    return {"prompt": text, "mode": mode, "mode_label": MODES[mode], "rows": len(DF.rows(ctx.conn, pid))}
