"""Generator catalogs and naming rules (D-B-021; product development process since 0.60.01).

Document types are the deliverables of the product development process (PDP) of a design course -- pre-study,
conceptual study, design, prototype and validation: MIP, RCS, CdCF, RC, RVE... -- plus general engineering. Each
reference is filed under one step of the PDP (« Étape », 01 to 21) and an optional subdivision, in the deliverables
folder of its type (columns codex_refs.pdp_step / pdp_sub).

Naming convention:
    reference  TYPE-DDDDD-TTTTT          Excel serial date-time, UTC
    file name  TYPE-DDDDD-TTTTT_REV_SYSTEM Title
    folder     Documents/<folder>/SS-UU_SYS/      folder of the type, SS = step of the PDP, UU = subdivision,
                                                  SYS = system code or label of the step
The serial is days since 1899-12-30 (Excel epoch): the integer part is the
date, the fraction x 100000 the time of day (resolution 0.864 s).
"""
import datetime as dt
import re

# (group, [(code, name, origin, folder), ...]) -- groups follow the four phases of the PDP, then general engineering.
DOC_GROUPS = [
    ("A. Pré-étude", [
        ("MIP", "Mémoire d'identification de projet", "PDP — A", "01_Pre-etude"),
        ("ETM", "Étude de marché", "PDP — A1", "01_Pre-etude"),
        ("SPP", "Spécifications préliminaires (client)", "PDP — A2", "01_Pre-etude"),
        ("ECH", "Échéancier et budget", "PDP — A4", "01_Pre-etude"),
        ("RSK", "Analyse des risques", "PDP — A6", "01_Pre-etude"),
    ]),
    ("B. Étude conceptuelle", [
        ("RCS", "Rapport de conception système", "PDP — B", "02_Etude-conceptuelle"),
        ("BES", "Analyse des besoins (diagramme des affinités)", "PDP — B8", "02_Etude-conceptuelle"),
        ("AF", "Analyse fonctionnelle (arbre, structure fonctionnelle)", "PDP — B9-B10", "02_Etude-conceptuelle"),
        ("CDCF", "Cahier des charges fonctionnel", "PDP — B11", "02_Etude-conceptuelle"),
        ("DFQ", "Matrice DFQ (déploiement de la fonction qualité)", "PDP — B12", "02_Etude-conceptuelle"),
        ("MMO", "Matrice morphologique", "PDP — B12", "02_Etude-conceptuelle"),
        ("PUGH", "Matrice de Pugh (sélection des concepts)", "PDP — B12", "02_Etude-conceptuelle"),
    ]),
    ("C. Conception", [
        ("RC", "Rapport de conception", "PDP — C", "03_Conception"),
        ("SSY", "Définition des sous-systèmes (configuration physique)", "PDP — C14", "03_Conception"),
        ("CALC", "Note de calcul et justification", "PDP — C15", "03_Conception"),
        ("AMDEC", "Analyse des modes de défaillance (AMDEC / FMEA)", "PDP — C15", "03_Conception"),
        ("DR", "Revue de conception (design review)", "PDP — C", "03_Conception"),
    ]),
    ("D. Fabrication et validation du prototype", [
        ("RVE", "Rapport de validation expérimentale", "PDP — D", "04_Validation"),
        ("PEX", "Protocole d'essai", "PDP — D21", "04_Validation"),
        ("REX", "Résultats d'essai", "PDP — D21", "04_Validation"),
        ("FAB", "Dossier de fabrication du prototype", "PDP — D", "04_Validation"),
    ]),
    ("Ingénierie générale", [
        ("DWG", "Mise en plan (dessin)", "Général", "05_Dessins"),
        ("SCH", "Schéma électrique", "Général", "05_Dessins"),
        ("BOM", "Nomenclature (Bill of Materials)", "Général", "05_Dessins"),
        ("REP", "Rapport", "Général", "06_Rapports"),
        ("PRO", "Procédure", "Général", "06_Rapports"),
        ("MOM", "Compte rendu de réunion", "Général", "06_Rapports"),
        ("TN", "Note technique", "Général", "06_Rapports"),
        ("PM", "Post-mortem de phase", "Général", "06_Rapports"),
        ("ECN", "Engineering Change Notice", "CM", "07_Changements"),
        ("ECR", "Engineering Change Request", "CM", "07_Changements"),
        ("MAN", "Manuel d'utilisation", "Général", "08_Admin"),
        ("LET", "Lettre", "Général", "08_Admin"),
        ("MEMO", "Mémo", "Général", "08_Admin"),
    ]),
]

# Codes no longer offered: a reference already issued keeps its code, name and folder in the registry, but a new
# reference uses the code that replaces it. (code, name, origin, folder, replaced_by)
RETIRED = []

# The steps of the PDP (« Étape »): (group, [(step, label, name, note), ...]) -- subdivision always "00" by default.
# Figure 1 of the course numbers 1 to 15 and 19 to 21; « Mise en plan et fabrication du prototype » has no number.
STEP_GROUPS = [
    ("A. Pré-étude", [
        ("01", "MKT", "Étude de marché", ""), ("02", "SPP", "Spécifications préliminaires avec le client", ""),
        ("03", "DEF", "Définition du projet", ""), ("04", "ECH", "Échéancier, budget et sources de financement", ""),
        ("05", "PRF", "Pré-faisabilité", ""), ("06", "RSK", "Analyse des risques et solutions potentielles", "→ MIP"),
    ]),
    ("B. Étude conceptuelle", [
        ("07", "MAJ", "Rappel et mise à jour de la pré-étude", ""), ("08", "BES", "Recherche des besoins du client", ""),
        ("09", "FCT", "Recherche des fonctions", "Analyse fonctionnelle"),
        ("10", "STF", "Définition de la structure fonctionnelle", "Analyse fonctionnelle"),
        ("11", "SPE", "Définition des spécifications d'ingénierie (CdCF)", ""),
        ("12", "CPT", "Recherche et sélection des concepts", "→ RCS"),
    ]),
    ("C. Conception", [
        ("13", "MAJ", "Rappel et mise à jour de l'étude conceptuelle", ""),
        ("14", "SSY", "Identification des sous-systèmes", ""), ("15", "CSS", "Conception des sous-systèmes", "→ RC"),
    ]),
    ("D. Fabrication et validation du prototype", [
        ("19", "MAJ", "Rappel et mise à jour de la phase de conception", ""),
        ("20", "VAQ", "Validation de certains aspects qualitatifs de la conception", ""),
        ("21", "TVS", "Tests de validation des spécifications par sous-système", "→ RVE"),
    ]),
]

DOC_TYPES = {code: {"code": code, "name": name, "standard": std, "folder": folder, "group": group}
             for group, items in DOC_GROUPS for code, name, std, folder in items}
RETIRED_TYPES = {code: {"code": code, "name": name, "standard": std, "folder": folder, "group": "Codes retirés",
                        "replaced_by": by, "retired": True} for code, name, std, folder, by in RETIRED}
ALL_TYPES = dict(RETIRED_TYPES, **DOC_TYPES)  # what the registry may show; DOC_TYPES: what a new reference may use
STEPS = {st: {"step": st, "label": label, "name": name, "note": note, "group": group}
         for group, items in STEP_GROUPS for st, label, name, note in items}

SYSTEM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,19}$")
FORBIDDEN_IN_FILENAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
EXCEL_EPOCH = dt.datetime(1899, 12, 30, tzinfo=dt.timezone.utc)
TIME_UNITS = 100000


def serial_parts(moment):
    """UTC datetime -> (date serial, time serial in 1/100000 day)."""
    days = (moment - EXCEL_EPOCH).total_seconds() / 86400
    date = int(days)
    time = round((days - date) * TIME_UNITS)
    if time >= TIME_UNITS:  # 23:59:59.6 and later rounds to the next day
        date, time = date + 1, 0
    return date, time


def next_slot(date, time):
    """The serial right after (date, time): used when a slot is already taken."""
    time += 1
    return (date + 1, 0) if time >= TIME_UNITS else (date, time)


def reference(doc_type, date, time):
    return "{}-{:05d}-{:05d}".format(doc_type, date, time)


def clean_title(title):
    """Title as it may appear in a Windows file name."""
    return re.sub(r"\s+", " ", FORBIDDEN_IN_FILENAME.sub("-", title)).strip(" .")


def file_name(ref, revision, system_code, title):
    name = "{}_{}".format(ref, revision)
    if system_code:
        name += "_" + system_code
    title = clean_title(title)
    if title:
        name += " " + title
    return name


def svn_path(folder, step, sub, system_code):
    """The folder of a reference: Documents/<folder of the type>/<step>-<subdivision>_<system or step label>/."""
    st = STEPS.get(step, {"label": step})  # a step no longer listed keeps its folder
    folder_sys = system_code if system_code and system_code != st["label"] else st["label"]
    return "Documents/{}/{}-{}_{}/".format(folder, step, sub, folder_sys)


def names(doc_type, date, time, step, sub, system_code, revision, title):
    """Every generated string of one reference."""
    ref = reference(doc_type, date, time)
    folder = ALL_TYPES[doc_type]["folder"]
    return {"reference": ref, "file_name": file_name(ref, revision, system_code, title),
            "svn_path": svn_path(folder, step, sub, system_code), "folder": folder}


def meta():
    """Catalogs for the browser (single source of truth)."""
    return {
        "doc_groups": [{"group": g, "types": [DOC_TYPES[c] for c, *_ in items]} for g, items in DOC_GROUPS],
        "step_groups": [{"group": g, "steps": [STEPS[c] for c, *_ in items]} for g, items in STEP_GROUPS],
        "retired_types": list(RETIRED_TYPES.values()),
        "folders": sorted({t["folder"] for t in DOC_TYPES.values()}),
    }
