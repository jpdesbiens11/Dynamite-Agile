"""Diamond · prompt templates for an AI assistant, process side (0.60.104, D-O-116): the PFMEA (interview, review; the
generation from the DFMEA and the line stays in pfmea_ai.py) and the control plans (interview, review). Same answer as the
DFMEA (ai_prompts.py): one ```json block, the keys being the headers of « Exporter (.csv) », read back by « Importer ».
"""
from . import actions as ACT
from . import ai_prompts as AIP
from . import control_plans as CPL
from . import pfmea as PF
from . import process as PR

PFMEA_KEYS = ["Code", "Ligne", "Opération", "Process Step", "Product Characteristic", "Process Characteristic", "Failure Mode", "Failure Effect",
              "Failure Cause", "Cause 5M", "Prevention Controls", "Detection Controls", "S", "O", "D", "Actions", "Responsable", "Échéance"]
CP_KEYS = ["Plan", "Code", "Opération", "Pièce", "Product Characteristic", "Process Characteristic", "Machine · Jig", "Measurement Technique",
           "Sample", "Frequency", "Control Method", "Reaction Plan"]


def _lines(conn, user, pid, only=None):
    out = []
    for line in PR.payload(conn, user, pid)["lines"]:
        if only and line["number"] != only:
            continue
        out.append("### {} · {}".format(line["code"], line["name"]))
        for o in line["operations"]:
            out.append("OP{} {} — équipements : {} — points de contrôle : {}{}".format(
                o["op"], o["name"], ", ".join(o["equipment_list"]) or "—", " | ".join(PR.point_label(p) for p in o["points"]) or "—",
                " — clôt la traçabilité des CC" if o["traceability"] else ""))
    return out or ["(aucune ligne : décrivez-la d'abord dans Diamond → Procédés)"]


def _characteristics(conn, pid):
    from . import characteristics as CH
    out = []
    for c in CH.payload(conn, pid)["items"]:
        s = c["dfmea"]["severity"] if c.get("dfmea") else None
        out.append("{} {} — {} — {} — {}{}".format(c["code"], c["class_code"] or ("procédé" if c["nature"] == "process" else "sans classe"), c["label"],
                                                   c["spec"] or "—", {"spc": "étude de capabilité", "test100": "essai 100 %", "design": "vérifiée en conception"}
                                                   .get(c["control"], c["control"]), " — S {} (DFMEA)".format(s) if s else ""))
    return out or ["(aucune caractéristique C-n)"]


def _pfmea_row(r):
    return {"Code": r["code"], "Ligne": "L{}".format(r["line_number"]) if r["line_number"] else "", "Opération": "OP{}".format(r["op"]) if r["op"] else "",
            "Process Step": r["process_step"], "Product Characteristic": r["char_code"], "Process Characteristic": r["process_char"],
            "Failure Mode": r["failure_mode"], "Failure Effect": r["effect"], "Failure Cause": r["cause"], "Cause 5M": PF.CAUSES_5M.get(r["cause_5m"], ""),
            "Prevention Controls": r["prevention"], "Detection Controls": r["detection_ctrl"], "S": r["severity"] or "", "O": r["occurrence"] or "",
            "D": r["detection"] or "", "Actions": r["action"], "Responsable": r["action_owner_name"] or "", "Échéance": r["action_due"] or "",
            "S héritée": r["inherited_s"] or "", "AP": {"H": "High", "M": "Medium", "L": "Low"}.get(r["ap"], ""), "État": PF.STATES.get(r["state"], "")}


def pfmea_prompt(conn, user, pid, mode, line=None):
    p = AIP.project(conn, pid)
    rows = [r for r in PF.rows(conn, pid) if r["state"] != "rejected" and (not line or r["line_number"] == line)]
    out = ["# PFMEA — {} ({}){}".format(p["name"], p["key"], " — ligne L{}".format(line) if line else ""), ""] + AIP.intro(
        p, "un ingénieur méthodes et qualité qui maîtrise l'AMDEC de procédé (PFMEA, AIAG-VDA 2019)", "module Diamond, onglet PFMEA")
    out += ["Une nouvelle ligne arrive en brouillon : l'équipe accepte ou rejette chaque ligne.", ""]
    out += AIP.protocol(mode, "opération par opération (OP10, OP20…) : l'étape, la caractéristique produit (C-n) ou de procédé qu'elle "
                              "touche, les modes de défaillance, leurs effets, les causes classées en 5M, la prévention, la détection et D, "
                              "puis les actions pour les AP High ; les caractéristiques spéciales (CC, SC) d'abord.")
    out += ["", "## Échelles"] + AIP.scales()
    out += ["S d'une ligne qui cite une C-n : héritée du DFMEA et verrouillée — laisse « S » vide (ou plus élevée, jamais plus basse). "
            "Donne « S » seulement pour une caractéristique de procédé sans C-n.",
            "Cause 5M, une de : " + ", ".join(PF.CAUSES_5M.values()) + "."]
    out += ["", "## Ligne(s) d'assemblage (opérations utilisables)"] + _lines(conn, user, pid, line)
    out += ["", "## Caractéristiques C-n (codes utilisables ; S de leur ligne du DFMEA)"] + _characteristics(conn, pid)
    out += ["", "## Membres du Space (pour « Responsable »)", ", ".join(m["display_name"] for m in ACT.members(conn, pid)) or "—"]
    out += ["", "## PFMEA actuel ({} lignes ; « S héritée », AP et État sont en lecture seule)".format(len(rows)),
            AIP.json_lines(_pfmea_row(r) for r in rows), ""]
    example = {"Code": "", "Ligne": "L1", "Opération": "OP30", "Process Step": "…", "Product Characteristic": "C-…", "Process Characteristic": "…",
               "Failure Mode": "…", "Failure Effect": "…", "Failure Cause": "…", "Cause 5M": "Méthode", "Prevention Controls": "…",
               "Detection Controls": "…", "S": "", "O": 4, "D": 5, "Actions": "", "Responsable": "", "Échéance": ""}
    out += AIP.answer_format(PFMEA_KEYS, [example], ["S héritée", "AP", "État", "Ticket Agile"], "Code",
                             ["- Une nouvelle ligne nomme sa « Ligne » (L1) et son « Opération » (OP30) ; elle arrive en brouillon."])
    return "\n".join(out)


def _cp_row(plan, r):
    return {"Plan": plan["code"], "Code": r["code"], "Opération": "OP{}".format(r["op"]) if r["op"] else "", "Pièce": (r["part"] or "").split(" ")[0],
            "Product Characteristic": r["char_code"], "Process Characteristic": "" if r["char_code"] else r["characteristic"],
            "Machine · Jig": r["equipment"], "Measurement Technique": r["technique"], "Sample": r["sample"], "Frequency": r["frequency"],
            "Control Method": r["control_method"], "Reaction Plan": r["reaction_plan"], "Class": r["class_code"], "Spec / Tolerance": r["spec"]}


def cp_prompt(conn, user, pid, mode, only=None):
    p = AIP.project(conn, pid)
    d = CPL.payload(conn, user, pid)
    plans = [x for x in d["plans"] if not only or x["number"] == only]
    out = ["# Plans de contrôle — {} ({})".format(p["name"], p["key"]), ""] + AIP.intro(
        p, "un ingénieur qualité qui maîtrise le plan de contrôle AIAG (APQP, IATF 16949)", "module Diamond, onglet Plans de contrôle")
    out += AIP.protocol(mode, "plan par plan, puis opération par opération (ou pièce par pièce à la réception) : la caractéristique contrôlée "
                              "(C-n, ou de procédé), la machine ou le gabarit, la technique de mesure, l'échantillon et la fréquence, la "
                              "méthode de contrôle et le plan de réaction — toutes les caractéristiques spéciales (CC, SC) d'abord, et pour "
                              "une CC un plan de réaction qui remonte jusqu'au dernier bon contrôle (traçabilité par n° de série).")
    out += ["", "## Plans existants (codes utilisables pour « Plan » ; un nouveau plan se crée dans l'outil)"]
    out += ["{} · {} · {} · {} · {} · rév. {}".format(x["code"], x["title"], d["labels"]["scopes"][x["scope"]], x["line"] or "—",
                                                      d["labels"]["phases"][x["phase"]], x["revision"]) for x in plans] or ["(aucun plan)"]
    out += ["", "## Ligne(s) d'assemblage (opérations utilisables ; une ligne d'un plan d'assemblage est sur la ligne de son plan)"]
    out += _lines(conn, user, pid)
    out += ["", "## Caractéristiques C-n (codes utilisables ; classe et spécification lues par l'outil)"] + _characteristics(conn, pid)
    out += ["", "## Pièces Diamond (codes utilisables pour « Pièce », plans de réception)"]
    out += ["P-{} {}".format(x["number"], x["name"]) for x in d["parts"]] or ["(aucune pièce)"]
    rows = [_cp_row(x, r) for x in plans for r in x["items"]]
    out += ["", "## Lignes actuelles ({} ; « Class » et « Spec / Tolerance » en lecture seule)".format(len(rows)), AIP.json_lines(rows), ""]
    example = {"Plan": plans[0]["code"] if plans else "PC-1", "Code": "", "Opération": "OP30", "Pièce": "", "Product Characteristic": "C-…",
               "Process Characteristic": "", "Machine · Jig": "…", "Measurement Technique": "…", "Sample": "5", "Frequency": "par heure",
               "Control Method": "…", "Reaction Plan": "…"}
    out += AIP.answer_format(CP_KEYS, [example], ["Class", "Spec / Tolerance", "Phase", "Révision"], "Code",
                             ["- Plan d'assemblage : « Opération » de sa ligne, « Pièce » vide. Plan de réception : « Pièce » (P-21), « Opération » vide.",
                              "- Une ligne contrôle une C-n (« Product Characteristic ») ou nomme une caractéristique de procédé."])
    return "\n".join(out)


def api_cp_prompt(ctx):
    from . import ai_io as IO
    pid = PR.access(ctx)
    mode = AIP.mode_of(ctx)
    only = IO.number(ctx.query.get("plan"), "PC") if ctx.query.get("plan") else None
    return {"prompt": cp_prompt(ctx.conn, ctx.user, pid, mode, only), "mode": mode, "mode_label": AIP.MODES[mode]}
