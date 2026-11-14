"""Diamond -> Excel (0.60.33, D-O-041): every table of the functional analysis, one workbook ready to show.

Sheets: Synthèse (figures, what to review, the index), Arbre fonctionnel, Structure (inputs, outputs, flows),
Pièces × fonctions (the matrix), Risques projet (register and P x I map), DFMEA (AIAG-VDA, the three levels in colour,
S / O / D, RPN, AP). The mark « DynamiteAgile · Co-Intelligence WorkFlow™ » heads every printed page; the core adds
its revision sheet (core/stamp.py). Rows are sized to their text: Excel does not grow a wrapped row by itself.
"""
import math

from . import actions as ACT
from . import dfmea as DF
from . import export_data as X
from .xlsx_book import Book, col


class Kit:
    """The styles of the workbook, made once."""

    def __init__(self, book):
        s = book.style
        self.text, self.wrap = s(border=True), s(border=True, wrap=True)
        self.center = s(border=True, h="center", wrap=True)
        self.bold = s(border=True, bold=True, wrap=True)
        self.head = s(bold=True, color="FFFFFF", fill=X.NAVY, border=True, h="center", v="center", wrap=True)
        self.title = s(bold=True, size=16, color=X.NAVY, v="center")
        self.sub = s(italic=True, size=10, color=X.MUTED)
        self.section = s(bold=True, size=12, color=X.NAVY, v="center")
        self.label = s(color=X.MUTED, border=True)
        self.kpi = s(bold=True, size=12, color=X.NAVY, border=True, h="center")
        self.note = s(wrap=True, color=X.INK)
        self.mark_right = s(italic=True, size=9, color=X.MUTED, h="right", v="center")
        self.level = {lv: s(border=True, wrap=True, fill=fill) for lv, fill in X.LEVEL_FILL.items()}
        self.level_bold = {lv: s(border=True, wrap=True, bold=True, fill=fill) for lv, fill in X.LEVEL_FILL.items()}
        self.ap = {k: s(border=True, bold=True, h="center", fill=f, color=c) for k, (f, c) in X.AP_STYLE.items()}
        self.risk = {k: s(border=True, bold=True, h="center", fill=f, color=c, wrap=True) for k, (f, c) in X.RISK_STYLE.items()}
        self.group = {"higher": s(bold=True, fill="EEF1F5", border=True, h="center", v="center"),
                      "focus": s(bold=True, fill="D6E6FB", border=True, h="center", v="center"),
                      "lower": s(bold=True, fill="FCE2D2", border=True, h="center", v="center"),
                      "risk": s(bold=True, fill="E9E2F7", border=True, h="center", v="center"),
                      "special": s(bold=True, fill="FFE9A3", border=True, h="center", v="center")}  # 0.60.101
        self.cls = {"CC": s(border=True, bold=True, h="center", fill="FDE2E1", color="9B1C1C"),
                    "SC": s(border=True, bold=True, h="center", fill="FDEBD9", color="8A3B00")}
        self.rot = s(bold=True, color="FFFFFF", fill=X.NAVY, border=True, h="center", v="bottom", rotate=90)
        self.dot = s(border=True, h="center", v="center", bold=True, color=X.TEAL, size=12)
        self.empty = s(border=True)
        self.good = s(border=True, bold=True, h="center", fill="E2F4E7", color="1E6B3A")
        self.warn = s(border=True, bold=True, h="center", fill="FFF1C7", color="7A5B00")
        self.bad = s(border=True, bold=True, h="center", fill="FDE2E1", color="9B1C1C")


def _hf(text):
    return str(text).replace("&", "&&")


def _frame(sheet, data, title, widths, kit, tab):
    """Brand band, title, subtitle; header and footer of every printed page."""
    sheet.tab = tab
    for i, w in enumerate(widths):
        sheet.widths[i] = w
    last = max(len(widths) - 1, 1)
    r = sheet.line([[("Dynamite", {"bold": True, "size": 18, "color": X.ORANGE}), ("Agile", {"bold": True, "size": 18, "color": X.TEAL})]], height=30)
    sheet.put(r, last, X.WORKFLOW, kit.mark_right)
    r = sheet.line([title], kit.title, height=24)
    sheet.merge(r, 0, r, last)
    r = sheet.line(["{} · {} — Space {} · {} · DynamiteAgile v{}".format(data["project"]["name"], "Diamond", data["project"]["key"],
                                                                         data["date"], data["version"])], kit.sub)
    sheet.merge(r, 0, r, last)
    sheet.skip()
    sheet.header = '&L&"Segoe UI,Bold"&12&KE0602FDynamite&K0E9A9AAgile&R&"Segoe UI,Italic"&9&K5B6573{}'.format(_hf(X.WORKFLOW))
    sheet.footer = '&L&8{} · {}&C&8Page &P / &N&R&8{}'.format(_hf(data["project"]["key"]), _hf(sheet.name), _hf(X.MARK))


def _fit(sheet, r, values, widths, minimum=1):
    """Row height from the longest wrapped cell (about 1.15 characters per width unit, 13.5 points per line)."""
    lines = minimum
    for v, w in zip(values, widths):
        text = str(v if v is not None else "")
        n = sum(max(1, math.ceil(len(part) / max(1.0, w * 1.15))) for part in text.split("\n")) if text else 1
        lines = max(lines, n)
    sheet.heights[r] = min(409, 14 * lines + 4)


def _table(sheet, kit, header, rows, widths, styles=None, filter_on=True):
    top = sheet.line(header, kit.head, height=32)
    for values in rows:
        st = styles(values) if styles else kit.wrap
        r = sheet.line(values, st)
        _fit(sheet, r, values, widths)
    if filter_on and rows:
        sheet.autofilter = "A{}:{}{}".format(top, col(len(header) - 1), sheet.row)
    sheet.freeze = sheet.freeze or "A{}".format(top + 1)
    sheet.print_rows = (top, top)
    return top


def synthese(book, kit, data):
    s, sm = book.sheet("Synthèse", landscape=False), data["summary"]
    _frame(s, data, "Diamond — synthèse de l'analyse fonctionnelle", [44, 16, 60], kit, X.NAVY)
    s.line(["Les chiffres", "", ""], kit.section, height=22)
    lv = sm["by_level"]
    figures = [("Fonctions de l'arbre", sm["functions"], "{} primaire, {} secondaires, {} tertiaires, {} techniques".format(lv[1], lv[2], lv[3], lv[4])),
               ("Fonctions hors arbre (estime…)", sm["outside"], ""), ("Fonctions critiques", sm["critical"], "le chemin critique de l'arbre"),
               ("Entrées / sorties du système", "{} / {}".format(sm["inputs"], sm["outputs"]), "frontière du produit (boundary diagram)"),
               ("Flux de la structure", sm["flows"], "énergie, matière, information"),
               ("Pièces", sm["parts"], "{} intégrée(s) · {} fonction(s) à plusieurs pièces".format(data["part_stats"]["integrated"], data["part_stats"]["shared"])),
               ("Risques projet", sm["risks"], "{} élevé(s) ou critique(s)".format(sm["risks_high"])),
               ("Lignes du DFMEA", sm["dfmea"], "AP High {} · Medium {} · Low {} · sans cotation {}".format(sm["ap"]["H"], sm["ap"]["M"], sm["ap"]["L"], sm["dfmea_unrated"])),
               ("Lignes avec essai clé (Test Base)", sm["dfmea_tested"], ""),
               ("Caractéristiques spéciales du DFMEA", "{} CC · {} SC".format(sm["classes"]["CC"], sm["classes"]["SC"]),  # 0.60.101
                "symboles : {} ; {} proposée(s) à décider, {} refusée(s)".format(data["classes"]["customer"]["name"], sm["class_proposed"],
                                                                              sm["class_refused"]))]
    for label, value, note in figures:
        s.line([label, value, note], [kit.label, kit.kpi, kit.wrap])
    s.skip()
    s.line(["Ce qu'une revue demanderait", "", ""], kit.section, height=22)
    names = {"tree": "Arbre fonctionnel", "structure": "Structure fonctionnelle", "risks": "Risques projet", "dfmea": "DFMEA"}
    any_check = False
    for key, name in names.items():
        for c in data["checks"][key] + (data["part_checks"] if key == "structure" else []):
            r = s.line([name, "", c], [kit.bold, kit.empty, kit.wrap])
            s.merge(r, 0, r, 1)
            _fit(s, r, ["", "", c], [44, 16, 60])
            any_check = True
    if not any_check:
        s.line(["Rien à signaler : chaque section est complète.", "", ""], kit.note)
    s.skip()
    s.line(["Les feuilles", "", ""], kit.section, height=22)
    for name, what in (("Arbre fonctionnel", "les fonctions par niveau, type, Kano, importance, pièces"),
                       ("Structure", "entrées, sorties et flux des deux vues"), ("Pièces × fonctions", "qui réalise quoi : intégration et simplification"),
                       ("Risques projet", "le registre et la carte P × I"), ("DFMEA", "AIAG-VDA : trois niveaux, S / O / D, RPN, AP, essai clé")):
        r = s.line([name, "", what], [kit.bold, kit.empty, kit.wrap])
        s.merge(r, 0, r, 1)
    s.skip()
    r = s.line(["Les diagrammes (arbre, structure, carte des risques) sont dans le fichier draw.io ; le rapport, dans le fichier Word.", "", ""], kit.sub)
    s.merge(r, 0, r, 2)


def tree_sheet(book, kit, data):
    s = book.sheet("Arbre fonctionnel")
    widths = [8, 58, 12, 10, 12, 13, 14, 9, 16, 40]
    _frame(s, data, "Arbre fonctionnel", widths, kit, "F2C14E")
    lab = data["labels"]
    rows = []
    for f in data["tree"]:
        parent = data["by_id"].get(f["parent_id"])
        indent = "    " * (f["level"] - 1) if f["in_tree"] else ""
        rows.append([X.code(f), indent + f["text"], X.label_of(f, data), X.code(parent) if parent else "",
                     lab["types"].get(f["ftype"], f["ftype"]), lab["kano"].get(f["kano"], ""), lab["importance"].get(f["importance"], ""),
                     "Oui" if f["critical"] else "", X.part_codes(data, f["id"]), f["notes"]])
    level_of = {X.code(f): (f["level"] if f["in_tree"] else 4) for f in data["tree"]}

    def styles(v):
        lv = level_of[v[0]]
        return [kit.level_bold[lv], kit.level_bold[lv] if lv <= 2 else kit.level[lv]] + [kit.level[lv]] * 8
    _table(s, kit, ["N°", "Fonction (Comment ? → à droite · Pourquoi ? ← à gauche)", "Niveau", "Parent", "Type", "Kano",
                    "Importance", "Critique", "Pièces", "Notes"], rows, widths, styles)


def structure_sheet(book, kit, data):
    s = book.sheet("Structure")
    widths = [24, 34, 16, 30, 30]
    _frame(s, data, "Structure fonctionnelle — entrées, sorties et flux", widths, kit, "7FD1DD")
    st, lab = data["structure"], data["labels"]
    name = {("p", p["id"]): ("E" if p["side"] == "in" else "S") + " · " + p["label"] for p in st["ports"]}
    name.update({("f", f["id"]): X.code(f) + " " + f["text"] for f in data["tree"]})
    s.line(["Frontière du système", "", "", "", ""], kit.section, height=22)
    _table(s, kit, ["Côté", "Libellé", "Type de flux"],
           [[lab["sides"][p["side"]], p["label"], lab["kinds"].get(p["kind"], p["kind"])] for p in st["ports"]], widths, filter_on=False)
    s.skip()
    s.line(["Flux", "", "", "", ""], kit.section, height=22)
    rows = []
    for fl in sorted(st["flows"], key=lambda x: (x["view"] != "general", x["id"])):
        src = name.get(("p", fl["src_port_id"])) or name.get(("f", fl["src_function_id"]), "")
        dst = name.get(("p", fl["dst_port_id"])) or name.get(("f", fl["dst_function_id"]), "")
        rows.append([lab["views"][fl["view"]].split(" (")[0], fl["label"], lab["kinds"].get(fl["kind"], fl["kind"]), src, dst])
    top = s.line(["Vue", "Libellé", "Type de flux", "De", "Vers"], kit.head, height=28)
    for v in rows:
        r = s.line(v, kit.wrap)
        _fit(s, r, v, widths)
    if rows:
        s.autofilter = "A{}:E{}".format(top, s.row)


def parts_sheet(book, kit, data):
    s = book.sheet("Pièces × fonctions")
    fns = sorted(data["views"]["detail"].values(), key=lambda f: f["number"])
    widths = [10, 34, 12, 11] + [5.5] * len(fns)
    _frame(s, data, "Pièces × fonctions — qui réalise quoi", widths[:max(6, len(widths))], kit, "9AD5A6")
    for i, w in enumerate(widths):
        s.widths[i] = w
    if not data["parts"]:
        s.line(["Aucune pièce encore : Diamond → Structure fonctionnelle → Pièces × fonctions."], kit.note)
        return
    head = s.line(["Pièce", "Nom", "Type", "Fonctions"] + [X.code(f) + " " + f["text"] for f in fns], [kit.head] * 4 + [kit.rot] * len(fns), height=150)
    per = {f["id"]: sum(1 for p in data["parts"] if f["id"] in p["functions"]) for f in fns}
    for p in data["parts"]:
        n = sum(1 for fid in p["functions"] if fid in per)
        st = kit.good if n >= 2 else kit.bad if n == 0 else kit.center
        s.line(["P-{}".format(p["number"]), p["name"], data["labels"]["part_kinds"].get(p["kind"], p["kind"]), n] +
               ["●" if f["id"] in p["functions"] else "" for f in fns], [kit.bold, kit.wrap, kit.text, st] + [kit.dot] * len(fns))
    s.line(["", "Pièces par fonction", "", ""] + [per[f["id"]] for f in fns],
           [kit.empty, kit.bold, kit.empty, kit.empty] + [kit.warn if per[f["id"]] >= 2 else kit.bad if per[f["id"]] == 0 else kit.center for f in fns])
    s.freeze = "E{}".format(head + 1)
    s.skip()
    r = s.line(["Vert : pièce intégrée (2 fonctions ou plus, bon pour le coût). Orange : fonction à plusieurs pièces (piste de "
                "simplification). Rouge : pièce sans fonction ou fonction sans pièce."], kit.sub)
    s.merge(r, 0, r, 3 + min(len(fns), 8))
    for c in data["part_checks"]:
        r = s.line([c], kit.note)
        s.merge(r, 0, r, 3 + min(len(fns), 8))
        _fit(s, r, [c], [sum(widths[:4 + min(len(fns), 8)])])


def risks_sheet(book, kit, data):
    s = book.sheet("Risques projet")
    widths = [7, 34, 30, 30, 15, 14, 5, 5, 7, 11, 12, 32, 16, 12, 12, 6, 6, 9, 11, 22, 12]
    _frame(s, data, "Risques projet — registre", widths, kit, "D64545")
    lab = data["labels"]
    rows = [["R-{}".format(r["number"]), r["title"], r["cause"], r["consequence"], lab["categories"].get(r["category"], r["category"]),
             lab["phases"].get(r["phase"], ""), r["probability"], r["impact"], r["score"], r["level"]["label"],
             lab["responses"].get(r["response"], "") if r["response"] else "", r["action"], r["owner_name"] or "", r["due_date"],
             lab["statuses"].get(r["status"], r["status"]), r["residual_p"] or "", r["residual_i"] or "", r["residual_score"] or "",
             r["residual_level"]["label"] if r["residual_score"] else "",
             "F{} {}".format(r["function_number"], r["function_text"]) if r["function_number"] else "",
             r["ticket"]["key"] if r["ticket"] else ""] for r in data["risks"]]  # 0.60.38: the Agile ticket of the action
    keys = {"R-{}".format(r["number"]): r for r in data["risks"]}

    def styles(v):
        r = keys[v[0]]
        out = [kit.bold] + [kit.wrap] * 5 + [kit.center] * 3 + [kit.risk[r["level"]["key"]]] + [kit.wrap] * 5 + [kit.center] * 3
        return out + [kit.risk[r["residual_level"]["key"]] if r["residual_score"] else kit.center, kit.wrap, kit.center]
    _table(s, kit, ["N°", "Risque", "Cause (si…)", "Conséquence (ce qui…)", "Catégorie", "Phase", "P", "I", "P × I", "Niveau",
                    "Stratégie", "Action", "Responsable", "Échéance", "Status", "P rés.", "I rés.", "Rés.", "Niveau rés.", "Fonction", "Ticket Agile"],
           rows, widths, styles)
    s.skip()
    s.line(["Carte P × I (maintenant)"], kit.section, height=22)
    s.line(["Impact ↓ / Probabilité →", "1", "2", "3", "4", "5"], [kit.head] * 6, height=22)
    for impact in range(5, 0, -1):
        cells = [str(impact)]
        styles_row = [kit.head]
        for p in range(1, 6):
            here = [k for k, r in keys.items() if r["probability"] == p and r["impact"] == impact]
            cells.append(", ".join(here))
            styles_row.append(kit.risk[X.R.level(p * impact)["key"]])
        r = s.line(cells, styles_row, height=34)


def dfmea_sheet(book, kit, data):
    s = book.sheet("DFMEA")
    widths = [6, 20, 24, 20, 30, 28, 32, 30, 5, 32, 62, 5, 30, 26, 5, 7, 8, 34, 18, 11, 10, 11, 9, 8, 16, 14, 40]
    _frame(s, data, "DFMEA — Design FMEA (AIAG-VDA)", widths, kit, "7E57C2")
    groups = [("higher", 0, 1, "Structure : Higher-Level"), ("focus", 2, 7, "Focus Element : fonction, requirement, défaillance, effet"),
              ("lower", 8, 14, "Lower-Level : cause, prévention, détection"), ("risk", 15, 22, "Risque, actions et suivi"),
              ("special", 23, 26, "Classe CC / SC")]  # 0.60.101 (D-O-108)
    r = s.line([""] * len(widths), kit.empty, height=22)
    for key, a, b, label in groups:
        s.put(r, a, label, kit.group[key])
        for c in range(a + 1, b + 1):
            s.put(r, c, "", kit.group[key])
        s.merge(r, a, r, b)
    header = ["Ligne", "Higher-Level Element", "Focus Element", "Lower-Level Element", "Function of Focus Element",
              "Requirement / Characteristic", "Failure Mode", "Failure Effect", "S", "Failure Cause", "Prevention Controls", "O",
              "Detection Controls", "Essai clé (Test Base)", "D", "RPN", "AP", "Actions", "Responsable", "Échéance", "Status",
              "Ticket Agile", "Risque projet", "Class", "Class Status", "Décision", "Justification de la classe"]
    cust = data["classes"]["customer"]
    rows = [[d["line"], d["higher"], d["focus"], d["lower"], "F{} {}".format(d["function_number"], d["function_text"]) if d["function_number"] else "",
             d["requirement"], d["failure_mode"], d["effect"], d["severity"] or "", d["cause"], d["prevention"], d["occurrence"] or "",
             d["detection_ctrl"], "{} {}".format(d["test_code"], d["test_title"]) if d["test_code"] else "", d["detection"] or "",
             d["rpn"] or "", d["ap"] or "", d["action"], d["action_owner_name"] or "", d["action_due"],
             ACT.DFMEA_STATUSES.get(d["action_status"], "") if d["action"].strip() else "", d["ticket"]["key"] if d["ticket"] else "",
             "R-{}".format(d["risk_number"]) if d["risk_number"] else ""] + DF.class_cells(d, cust) for d in data["dfmea"]]
    special = {DF.class_cells(d, cust)[0]: d["class_code"] for d in data["dfmea"] if d["class_status"] == "confirmed"}

    def styles(v):
        ap = kit.ap.get(v[16], kit.center)
        return [kit.bold] + [kit.wrap] * 7 + [kit.center, kit.wrap, kit.wrap, kit.center, kit.wrap, kit.wrap, kit.center, kit.center, ap,
                                               kit.wrap, kit.wrap, kit.center, kit.center, kit.center, kit.center,
                                               kit.cls.get(special.get(v[23]), kit.center), kit.center, kit.center, kit.wrap]
    top = _table(s, kit, header, rows, widths, styles)
    s.freeze = "E{}".format(top + 1)
    s.print_rows = (top - 1, top)
    s.skip()
    r = s.line(["S, O, D : de 1 à 10. RPN = S × O × D. AP (Action Priority, AIAG-VDA) : H = action requise, M = action "
                "recommandée, L = action possible. La légende complète est dans Diamond → DFMEA → Légende AP."], kit.sub)
    s.merge(r, 0, r, 10)
    r = s.line([class_note(data["classes"])], kit.sub)  # 0.60.101 (D-O-108)
    s.merge(r, 0, r, 10)


def class_note(info):
    r, c = info["rules"], info["customer"]
    return ("Class : symboles du client « {} » ({} / {} au DFMEA). Proposée par la règle du Space (CC si S ≥ {} ; SC si S de {} à {} et "
            "O ≥ {}), confirmée ou refusée par une personne ; « ? » = proposée, pas encore décidée.").format(
        c["name"], c["cc_dfmea"], c["sc_dfmea"], r["cc_severity"], r["sc_severity"], r["cc_severity"] - 1, r["sc_occurrence"])


def build(data, only=None):
    """only: "tree" or "structure" -- the table of one screen (0.60.50, D-O-059); None: the whole workbook."""
    book = Book()
    kit = Kit(book)
    if only == "tree":
        tree_sheet(book, kit, data)
    elif only == "structure":
        structure_sheet(book, kit, data)
        if data["parts"]:
            parts_sheet(book, kit, data)
    else:
        synthese(book, kit, data)
        tree_sheet(book, kit, data)
        structure_sheet(book, kit, data)
        parts_sheet(book, kit, data)
        risks_sheet(book, kit, data)
        dfmea_sheet(book, kit, data)
        from . import char_export  # 0.60.102 (D-O-110): the summary of the special characteristics
        char_export.sheet(book, kit, data["characteristics"], data)
    return book.bytes(title="Diamond — {} ({})".format(data["project"]["name"], data["project"]["key"]))
