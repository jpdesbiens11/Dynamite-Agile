"""Diamond -> Word (0.60.33, D-O-041): the report of the functional analysis, for a teacher, a jury or an investor.

The platform's template (modules/testing/templates/document.docx: cover page, table of contents, numbered headings,
header) and, in its footer, the mark « DynamiteAgile · Co-Intelligence WorkFlow™ ». Sections: synthesis, Storyline,
functional tree, functional structure, parts x functions, project risks, DFMEA, what a review would ask, the companion
files. Since 0.60.98 (D-O-105) the visuals are in the report as numbered figures (report_figures.py): the scenes of the
Storyline, the tree (overview then one figure per branch, as the PowerPoint), both views of the structure and the risk map
now and residual -- EMF pictures drawn from the same layout as draw.io and PowerPoint. The full tables (DFMEA prevention
controls, every column) are in the Excel workbook; Word -> Save as -> PDF gives the PDF.
"""
import io
import zipfile

from modules.testing import word_doc as WD

from . import export_data as X
from . import report_figures as RF
from .docx_figures import Figures

WIDTH = 9400  # dxa between the margins of the template (letter, 2.5 cm)
FOOTER_OLD = "Document généré par Dynamite | Agile."


def _p(text, bold=False, italic=False, color=None, size=None, align="left"):
    return WD.para([WD.run(text, bold=bold, italic=italic, color=color, size=size)], space_after=0, align=align)


def _cell(text, width, fill=None, bold=False, color=None, size=17, align="left"):
    tcpr = '<w:tcW w:w="{}" w:type="dxa"/>'.format(width) + ('<w:shd w:val="clear" w:color="auto" w:fill="{}"/>'.format(fill) if fill else "")
    return "<w:tc><w:tcPr>{}</w:tcPr>{}</w:tc>".format(tcpr, _p(text, bold=bold, color=color, size=size, align=align))


def table(header, rows, widths, fills=None, aligns=None, size=17):
    """Navy header row repeated on every page; fills(row) -> one fill per cell or None; aligns per column."""
    scale = WIDTH / float(sum(widths))
    widths = [int(w * scale) for w in widths]
    aligns = aligns or ["left"] * len(widths)
    grid = "".join('<w:gridCol w:w="{}"/>'.format(w) for w in widths)
    out = ['<w:tbl><w:tblPr><w:tblStyle w:val="Grilledutableau"/><w:tblW w:w="{}" w:type="dxa"/><w:tblBorders>'
           '<w:top w:val="single" w:sz="4" w:color="C9D1DB"/><w:left w:val="single" w:sz="4" w:color="C9D1DB"/>'
           '<w:bottom w:val="single" w:sz="4" w:color="C9D1DB"/><w:right w:val="single" w:sz="4" w:color="C9D1DB"/>'
           '<w:insideH w:val="single" w:sz="4" w:color="C9D1DB"/><w:insideV w:val="single" w:sz="4" w:color="C9D1DB"/></w:tblBorders>'
           '<w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="70" w:type="dxa"/><w:bottom w:w="40" w:type="dxa"/>'
           '<w:right w:w="70" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>{}</w:tblGrid>'.format(sum(widths), grid)]
    out.append("<w:tr><w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>{}</w:tr>".format(
        "".join(_cell(h, w, X.NAVY, bold=True, color="FFFFFF", size=size) for h, w in zip(header, widths))))
    for r in rows:
        f = fills(r) if fills else [None] * len(r)
        out.append("<w:tr><w:trPr><w:cantSplit/></w:trPr>{}</w:tr>".format("".join(
            _cell(str(c if c is not None else ""), w, fl, size=size, align=al) for c, w, fl, al in zip(r, widths, f, aligns))))
    out.append("</w:tbl>")
    return "".join(out) + WD.para("", space_after=120)


def _intro(text):
    return WD.para([WD.run(text)], space_after=120)


def _note(text):
    return WD.para([WD.run(text, italic=True, color=X.MUTED, size=18)], space_after=160)


def section_summary(data):
    sm, ps = data["summary"], data["part_stats"]
    lv = sm["by_level"]
    rows = [["Scènes de la Storyline", sm["scenes"], "l'usage raconté avant l'arbre"],
            ["Fonctions de l'arbre", sm["functions"], "{} primaire, {} secondaires, {} tertiaires, {} techniques".format(lv[1], lv[2], lv[3], lv[4])],
            ["Fonctions hors arbre (estime…)", sm["outside"], ""], ["Fonctions critiques", sm["critical"], "le chemin critique de l'arbre"],
            ["Entrées / sorties du système", "{} / {}".format(sm["inputs"], sm["outputs"]), "la frontière du produit"],
            ["Flux de la structure", sm["flows"], "énergie, matière, information"],
            ["Pièces", sm["parts"], "{} intégrée(s) · {} fonction(s) à plusieurs pièces".format(ps["integrated"], ps["shared"])],
            ["Risques projet", sm["risks"], "{} élevé(s) ou critique(s)".format(sm["risks_high"])],
            ["Lignes du DFMEA", sm["dfmea"], "AP High {} · Medium {} · Low {} · sans cotation {}".format(sm["ap"]["H"], sm["ap"]["M"], sm["ap"]["L"], sm["dfmea_unrated"])],
            ["Lignes avec essai clé", sm["dfmea_tested"], "Test Base du Space"]]
    primary = next((f for f in data["tree"] if f["level"] == 1 and f["in_tree"]), None)
    lead = ("Le produit « {} » a pour fonction primaire : {}. ".format(data["project"]["name"], primary["text"]) if primary else "") + \
        "Ce rapport rassemble l'analyse fonctionnelle de Diamond : la Storyline, l'arbre des fonctions, la structure fonctionnelle, " \
        "l'allocation des pièces, les risques du projet et le DFMEA ; les diagrammes y sont en figures numérotées."
    return WD.heading(1, "Synthèse") + _intro(lead) + table(["Indicateur", "Valeur", "Précision"], rows, [36, 12, 52], aligns=["left", "center", "left"])


def section_tree(data, figs):
    lab = data["labels"]
    rows, fills = [], {}
    for f in data["tree"]:
        lv = f["level"] if f["in_tree"] else 4
        rows.append([X.code(f), " " * (lv - 1 if f["in_tree"] else 0) + f["text"], X.label_of(f, data), lab["types"].get(f["ftype"], ""),
                     lab["kano"].get(f["kano"], ""), "Oui" if f["critical"] else "", X.part_codes(data, f["id"])])
        fills[X.code(f)] = X.LEVEL_FILL[lv]
    return (WD.heading(1, "Arbre fonctionnel") +
            _intro("Lecture : vers la droite, « Comment ? » (chaque fonction est réalisée par celles à sa droite) ; vers la gauche, "
                   "« Pourquoi ? » ; de haut en bas, « Quand ? », dans l'ordre de l'usage. Les couleurs suivent les niveaux : primaire, "
                   "secondaires (sous-systèmes), tertiaires, techniques et hors arbre.") +
            RF.tree(data, figs) +
            _intro("Le tableau donne chaque fonction avec son niveau, son type, sa catégorie Kano et ses pièces.") +
            table(["N°", "Fonction", "Niveau", "Type", "Kano", "Critique", "Pièces"], rows, [7, 43, 12, 10, 12, 8, 12],
                  fills=lambda r: [fills[r[0]]] * 7, aligns=["left", "left", "left", "left", "left", "center", "left"]) +
            _note("Le même diagramme, modifiable, est dans les fichiers draw.io et PowerPoint (page « Arbre fonctionnel »)."))


def section_structure(data, figs):
    st, lab = data["structure"], data["labels"]
    name = {("p", p["id"]): p["label"] for p in st["ports"]}
    name.update({("f", f["id"]): X.code(f) + " " + f["text"] for f in data["tree"]})
    out = [WD.heading(1, "Structure fonctionnelle"),
           _intro("La frontière du système (boundary diagram) : ce que le produit reçoit à gauche, ce qu'il rend à droite, et les flux "
                  "d'énergie, de matière et d'information entre ses fonctions."),
           RF.structure(data, figs),
           WD.heading(2, "Entrées et sorties"),
           table(["Côté", "Libellé", "Type de flux"], [[lab["sides"][p["side"]], p["label"], lab["kinds"].get(p["kind"], "")] for p in st["ports"]],
                 [30, 45, 25])]
    for view in ("general", "detail"):
        rows = [[fl["label"], lab["kinds"].get(fl["kind"], ""),
                 name.get(("p", fl["src_port_id"])) or name.get(("f", fl["src_function_id"]), ""),
                 name.get(("p", fl["dst_port_id"])) or name.get(("f", fl["dst_function_id"]), "")] for fl in st["flows"] if fl["view"] == view]
        if rows:
            out += [WD.heading(2, "Flux — " + lab["views"][view].lower()), table(["Flux", "Type", "De", "Vers"], rows, [20, 14, 33, 33])]
    out.append(_note("Les deux vues, modifiables, sont aussi dans les fichiers draw.io et PowerPoint (pages « Structure »)."))
    return "".join(out)


def section_parts(data):
    if not data["parts"]:
        return WD.heading(1, "Pièces et fonctions") + _intro("Aucune pièce n'est encore allouée aux fonctions.")
    ps, detail = data["part_stats"], data["views"]["detail"]
    rows = [["P-{}".format(p["number"]), p["name"], data["labels"]["part_kinds"].get(p["kind"], ""),
             ", ".join(X.code(detail[f]) for f in p["functions"] if f in detail) or "—"] for p in data["parts"]]
    n = {r[0]: len(p["functions"]) for r, p in zip(rows, data["parts"])}
    out = [WD.heading(1, "Pièces et fonctions"),
           _intro("{} pièces réalisent {} des {} fonctions détaillées ; {} pièce(s) intégrée(s) assument deux fonctions ou plus, {} "
                  "fonction(s) demandent plusieurs pièces. En moyenne : {} fonction(s) par pièce.".format(
                      ps["parts"], ps["covered"], ps["functions"], ps["integrated"], ps["shared"], str(ps["ratio"]).replace(".", ","))),
           table(["Pièce", "Nom", "Type", "Fonctions réalisées"], rows, [9, 38, 13, 40],
                 fills=lambda r: [None, None, None, "E2F4E7" if n[r[0]] >= 2 else "FDE2E1" if n[r[0]] == 0 else None])]
    if data["part_checks"]:
        out += [WD.heading(2, "Ce que dit l'architecture"), WD.bullets(data["part_checks"])]
    out.append(_note("La matrice pièces × fonctions complète est dans le classeur Excel."))
    return "".join(out)


def section_risks(data, figs):
    lab = data["labels"]
    if not data["risks"]:
        return WD.heading(1, "Risques projet") + _intro("Aucun risque au registre.")
    rows = [["R-{}".format(r["number"]), r["title"], r["probability"], r["impact"], r["score"], r["level"]["label"],
             lab["responses"].get(r["response"], "") if r["response"] else "—", r["owner_name"] or "—"] for r in data["risks"]]
    lvl = {"R-{}".format(r["number"]): r["level"]["key"] for r in data["risks"]}
    out = [WD.heading(1, "Risques projet"),
           _intro("Probabilité (P) et impact (I) de 1 à 5 ; niveau selon P × I : faible 1 à 4, moyen 5 à 9, élevé 10 à 14, critique 15 à 25."),
           RF.risks(data, figs),
           table(["N°", "Risque", "P", "I", "P × I", "Niveau", "Stratégie", "Responsable"], rows, [7, 41, 5, 5, 7, 11, 11, 13],
                 fills=lambda r: [None] * 5 + [X.RISK_STYLE[lvl[r[0]]][0]] + [None, None],
                 aligns=["left", "left", "center", "center", "center", "center", "left", "left"])]
    actions = ["R-{} {} — {}".format(r["number"], r["title"], r["action"]) for r in data["risks"] if r["action"] and r["level"]["key"] in ("critique", "eleve")]
    if actions:
        out += [WD.heading(2, "Actions sur les risques élevés et critiques"), WD.bullets(actions)]
    out.append(_note("La carte P × I est aussi dans les fichiers draw.io et PowerPoint ; le registre complet, dans le classeur Excel."))
    return "".join(out)


def section_dfmea(data):
    rows_in = data["dfmea"]
    if not rows_in:
        return WD.heading(1, "DFMEA") + _intro("Le DFMEA est vide.")
    sm = data["summary"]
    rows = [[d["line"], "F{} {}".format(d["function_number"], d["function_text"]) if d["function_number"] else "", d["failure_mode"], d["effect"],
             d["severity"] or "", d["cause"], d["occurrence"] or "", d["detection"] or "", d["ap"] or "—",
             d["test_code"] or ""] for d in rows_in]
    out = [WD.heading(1, "DFMEA"),
           _intro("Design FMEA selon AIAG-VDA : {} lignes ; Action Priority High {}, Medium {}, Low {} ; {} ligne(s) encore à coter ; {} "
                  "ligne(s) reliée(s) à un essai clé de la Test Base.".format(sm["dfmea"], sm["ap"]["H"], sm["ap"]["M"], sm["ap"]["L"],
                                                                             sm["dfmea_unrated"], sm["dfmea_tested"])),
           table(["#", "Fonction", "Failure Mode", "Failure Effect", "S", "Failure Cause", "O", "D", "AP", "Essai clé"], rows,
                 [4, 15, 18, 15, 4, 18, 4, 4, 5, 10], size=15,
                 fills=lambda r: [None] * 8 + [X.AP_STYLE[r[8]][0] if r[8] in X.AP_STYLE else None, None],
                 aligns=["center", "left", "left", "left", "center", "left", "center", "center", "center", "left"]),
           _note("Les Prevention Controls (avec les bonnes pratiques de l'industrie), les Detection Controls et les actions sont dans le "
                 "classeur Excel, feuille DFMEA.")]
    return "".join(out + section_classes(data))


def section_classes(data):
    """0.60.101 (D-O-108): the classes CC / SC -- the decided and the proposed rows, with the symbols of the Space's customer."""
    from . import dfmea as DF
    info, sm = data["classes"], data["summary"]
    cust, r = info["customer"], info["rules"]
    rows_in = [d for d in data["dfmea"] if d["class_status"]]
    out = [WD.heading(2, "Caractéristiques spéciales (CC / SC)"),
           _intro("La plateforme propose une classe à partir de S et O (CC si S ≥ {} ; SC si S de {} à {} et O ≥ {}) ; une personne la "
                  "confirme ou la refuse avec sa justification. Confirmées : {} CC et {} SC ; {} proposée(s) à décider ; {} refusée(s). "
                  "Symboles du client : {}.".format(r["cc_severity"], r["sc_severity"], r["cc_severity"] - 1, r["sc_occurrence"], sm["classes"]["CC"],
                                                    sm["classes"]["SC"], sm["class_proposed"], sm["class_refused"], cust["name"]))]
    if rows_in:
        rows = [[d["line"], "F{} {}".format(d["function_number"], d["function_text"]) if d["function_number"] else "", d["failure_mode"],
                 d["severity"] or "", d["occurrence"] or ""] + DF.class_cells(d, cust) for d in rows_in]
        out.append(table(["#", "Fonction", "Failure Mode", "S", "O", "Class", "Status", "Décision", "Justification"], rows,
                         [4, 15, 15, 3, 3, 5, 9, 9, 22], size=15,
                         aligns=["center", "left", "left", "center", "center", "center", "left", "left", "left"]))
    return out


def section_chars(data):
    """0.60.102 (D-O-110): the summary of the special characteristics, after the DFMEA."""
    from . import char_export
    return char_export.section(data["characteristics"], 2)


def section_review(data):
    names = {"tree": "Arbre fonctionnel", "structure": "Structure fonctionnelle", "risks": "Risques projet", "dfmea": "DFMEA"}
    items = ["{} : {}".format(names[k], c) for k in names for c in data["checks"][k]]
    out = WD.heading(1, "Ce qu'une revue demanderait")
    return out + (WD.bullets(items) if items else _intro("Rien à signaler : chaque section est complète."))


def section_files(data):
    return (WD.heading(1, "Fichiers joints") + WD.bullets([
        "Classeur Excel « {} » : chaque tableau complet (arbre, structure, pièces × fonctions, risques, DFMEA).".format(X.safe_name(data, "Tableaux", "xlsx")),
        "Fichiers draw.io « {} » et PowerPoint « {} » : les diagrammes de ce rapport, modifiables (formes et flèches) ; draw.io "
        "exporte aussi en PNG ou SVG.".format(X.safe_name(data, "Diagrammes", "drawio"), X.safe_name(data, "Diagrammes", "pptx")),
        "Ce rapport en PDF : dans Word, Fichier → Enregistrer sous → PDF."]) +
        _note("{} · DynamiteAgile v{} · {}".format(X.MARK, data["version"], data["stamp"])))


def build(data, prepared, initials):
    figs = Figures()
    body = "".join([section_summary(data), RF.storyline(data, figs), section_tree(data, figs), section_structure(data, figs),
                    section_parts(data), section_risks(data, figs), section_dfmea(data), section_chars(data), section_review(data),
                    section_files(data)])
    meta = {"title": "Diamond — Analyse fonctionnelle", "subject": "{} ({})".format(data["project"]["name"], data["project"]["key"])[:80],
            "prepared": prepared[:80], "docno": "DIA-{}".format(data["project"]["key"])[:40], "rev": "A", "doctype": "Rapport", "lang": "fr"}
    raw = WD.build(meta, body, "Export de Diamond", initials)
    return figs.package(_mark(raw))


def _mark(raw):
    """The footer of the template carries the mark of the workflow."""
    buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith("word/footer") and item.filename.endswith(".xml"):
                data = data.decode("utf-8").replace(FOOTER_OLD, X.MARK + " — document généré par DynamiteAgile.").encode("utf-8")
            zout.writestr(item, data)
    return buf.getvalue()
