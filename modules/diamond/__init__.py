"""« Diamond » 💎 (0.60.11, D-O-023): the functional analysis and the design risk of a Space's product, at 1 000 m in
the mine -- the deepest gallery, where the hardest stone is cut.

Sub-modules, one per iteration:
  0.60.11  Arbre fonctionnel (functions.py, example.py): primary, secondary, tertiary functions; how / why / when.
  0.60.13  Structure fonctionnelle (structure.py): boundary diagram -- inputs on the left, outputs on the right, the
           sub-systems (general view) or the tertiary functions (detail view), energy / material / information flows.
  0.60.14  Analyse de risque projet (risks.py): the high-level register, P x I on 5 x 5, response, owner, residual risk.
  0.60.15  DFMEA AIAG-VDA (dfmea.py, dfmea_ap.py): three levels, the functions of the tree, S / O / D, RPN and AP.
  0.60.20  Pièces (parts.py, example_parts.py): the parts tagged on the functions of the structure, the matrix parts x
           functions and what it says about the architecture (integrated parts, functions shared by several parts).
  0.60.16  Golden Nuggets (static/js/diamond/nuggets*.js): first-principles thinking and design rules, with examples.
  0.60.51  Storyline (story.py): the use of the product told scene by scene with pictograms, before the tree.
  0.60.52  Storyline → IA (story_ai.py): the prompt built from the scenes, and the AI's answer imported into the Space.
  0.60.61  Coûts et budget (costs.py, costs_budget.py): NRE, unit cost of each part in prototype and at three volumes,
           the project budget for investors and the department.
  0.60.101 Classes CC / SC du DFMEA (classes.py, classes_api.py): proposed by the rules of the Space, decided by a person,
           shown with the symbols of the Space's customer.
  0.60.102 Caractéristiques C-n (characteristics.py, char_spec.py, char_links.py, char_export.py): the exact dimension of
           the exact part, its drawing, its required Cpk, its test; the summary of the special characteristics.
Every table is tied to projects(id) (backup, restore, copy by the core); every write is journalled.
"""
from .search import search  # noqa: F401  (core search hook, 0.60.36)
from .bot import bot_summary  # noqa: F401  (Bob le mineur, core/bot.py, 0.60.36)
from .actions import dashboard  # noqa: F401  (core dashboard hook, 0.60.38)
from . import migrations_a, migrations_b  # noqa: E402
from . import ai_io, ai_prompts, ai_prompts_process, cp_io, dfmea_io, pfmea_io  # noqa: E402,F401 (0.60.104, D-O-116)
from . import actions, capability, char_export, characteristics, classes_api, company_pn, control_plans, impact, pfmea, pfmea_ai, pn_ai, prio, process, costs, costs_budget, costs_import, costs_prompt, dfmea, dfmea_complete, example, export_api, functions, parts, risks, story, story_ai, structure

SCHEMA = ""

# 0.60.103 (D-O-111): the parts of Diamond an administrator may turn off (core/features.py, ⚙ Admin → Modules et fonctions)
FEATURES = {
    "diamond_process": {"label": "Procédés (lignes d'assemblage)",
                        "help": "Les configurations de ligne, leurs opérations OP10…, équipements et points de contrôle ; accès réservé aux "
                                "membres choisis du Space.", "routes": [r"/api/diamond/p/\d+/process(/.*)?"]},
    "diamond_pfmea": {"label": "PFMEA", "requires": "diamond_process",
                      "help": "Le Process FMEA généré depuis le DFMEA final et la ligne d'assemblage, en brouillon puis validé.",
                      "routes": [r"/api/diamond/p/\d+/pfmea(/.*)?"]},
    "diamond_cplans": {"label": "Plans de contrôle", "requires": "diamond_process",
                       "help": "Un ou plusieurs Control Plans par configuration de ligne et à la réception, trois phases, mesures et Cpk.",
                       "routes": [r"/api/diamond/p/\d+/cplans(/.*)?"]},
}

MIGRATIONS = migrations_a.MIGRATIONS + migrations_b.MIGRATIONS  # 0.60.103: the SQL in two files (500-line rule)

P = r"/api/diamond/p/(?P<pid>\d+)"
FN = P + r"/functions/(?P<fid>\d+)"

SC = P + r"/story/scenes/(?P<sid>\d+)"
CUST = r"/dfmea/classes/customers/(?P<code>[a-z0-9-]{1,40})"

ROUTES = [
    ("GET", P + r"/costs", costs.api_get, "user"),  # 0.60.61 (D-O-070): « Coûts et budget »
    ("GET", P + r"/costs/export\.csv", costs_budget.api_export, "user"),
    ("POST", P + r"/costs/import", costs_import.api_import, "user"),  # 0.60.66 (D-O-075): the CSV of the export, back in
    ("GET", P + r"/costs/prompt", costs_prompt.api_prompt, "user"),  # 0.60.66 (D-O-075): instructions for an AI assistant
    ("PATCH", P + r"/costs/settings", costs.api_settings, "user"),
    ("POST", P + r"/costs/nre", costs.api_nre_create, "user"),
    ("PATCH", P + r"/costs/nre/(?P<oid>\d+)", costs.api_nre_update, "user"),
    ("POST", P + r"/costs/nre/(?P<oid>\d+)/delete", costs.api_nre_delete, "user"),
    ("POST", P + r"/costs/lines", costs.api_line_create, "user"),
    ("PATCH", P + r"/costs/lines/(?P<oid>\d+)", costs.api_line_update, "user"),
    ("POST", P + r"/costs/lines/(?P<oid>\d+)/delete", costs.api_line_delete, "user"),
    ("GET", P + r"/story", story.api_list, "user"),  # 0.60.51 (D-O-060): the Storyline
    ("POST", P + r"/story/scenes", story.api_create, "user"),
    ("PATCH", SC, story.api_update, "user"),
    ("POST", SC + r"/move", story.api_move, "user"),
    ("POST", SC + r"/duplicate", story.api_duplicate, "user"),
    ("POST", SC + r"/delete", story.api_delete, "user"),
    ("GET", P + r"/story/prompt", story_ai.api_prompt, "user"),  # 0.60.52 (D-O-061): « Copier pour l'IA »
    ("POST", P + r"/import", story_ai.api_import, "user"),  # 0.60.52: the AI's answer applied to this Space
    ("GET", P + r"/functions", functions.api_list, "user"),
    ("POST", P + r"/functions", functions.api_create, "user"),
    ("PATCH", FN, functions.api_update, "user"),
    ("POST", FN + r"/move", functions.api_move, "user"),
    ("POST", FN + r"/archive", functions.api_archive, "user"),
    ("POST", P + r"/example", example.api_example, "user"),
    ("GET", P + r"/structure", structure.api_get, "user"),
    ("POST", P + r"/structure/ports", structure.api_port_create, "user"),
    ("PATCH", P + r"/structure/ports/(?P<oid>\d+)", structure.api_port_update, "user"),
    ("POST", P + r"/structure/ports/(?P<oid>\d+)/delete", structure.api_port_delete, "user"),
    ("POST", P + r"/structure/flows", structure.api_flow_create, "user"),
    ("PATCH", P + r"/structure/flows/(?P<oid>\d+)", structure.api_flow_update, "user"),
    ("POST", P + r"/structure/flows/(?P<oid>\d+)/delete", structure.api_flow_delete, "user"),
    ("PUT", P + r"/structure/position", structure.api_position, "user"),
    ("POST", P + r"/structure/layout/reset", structure.api_reset_layout, "user"),
    ("POST", P + r"/structure/example", example.api_structure_example, "user"),
    ("POST", P + r"/structure/parts", parts.api_create, "user"),
    ("POST", P + r"/structure/parts/example", example.api_parts_example, "user"),
    ("PATCH", P + r"/structure/parts/(?P<oid>\d+)", parts.api_update, "user"),
    ("PUT", P + r"/structure/parts/(?P<oid>\d+)/functions", parts.api_tag, "user"),
    ("POST", P + r"/structure/parts/(?P<oid>\d+)/delete", parts.api_delete, "user"),
    ("GET", P + r"/risks", risks.api_list, "user"),
    ("POST", P + r"/risks", risks.api_create, "user"),
    ("GET", P + r"/risks/export\.csv", risks.api_export, "user"),
    ("POST", P + r"/risks/example", example.api_risks_example, "user"),
    ("PATCH", P + r"/risks/(?P<rid>\d+)", risks.api_update, "user"),
    ("POST", P + r"/risks/(?P<rid>\d+)/duplicate", risks.api_duplicate, "user"),
    ("POST", P + r"/risks/(?P<rid>\d+)/archive", risks.api_archive, "user"),
    ("POST", P + r"/actions/(?P<kind>risk|dfmea)/(?P<oid>\d+)/track", actions.api_track, "user"),  # 0.60.38 (D-O-047)
    ("POST", P + r"/pfmea/rows/(?P<oid>\d+)/track", actions.api_track_pfmea, "user"),  # 0.60.103 (D-O-114): behind the « PFMEA » switch
    ("GET", P + r"/dfmea", dfmea.api_list, "user"),
    ("GET", P + r"/cplans", control_plans.api_get, "user"),  # 0.60.103 (D-O-115): control plans, measurements, capability
    ("POST", P + r"/cplans/plans", control_plans.api_plan_create, "user"),
    ("PATCH", P + r"/cplans/plans/(?P<planid>\d+)", control_plans.api_plan_update, "user"),
    ("POST", P + r"/cplans/plans/(?P<planid>\d+)/items", control_plans.api_item_create, "user"),
    ("PATCH", P + r"/cplans/items/(?P<iid>\d+)", control_plans.api_item_update, "user"),
    ("POST", P + r"/cplans/measures", capability.api_measures, "user"),
    ("GET", P + r"/cplans/measures/(?P<cid>\d+)", capability.api_get, "user"),
    ("GET", P + r"/cplans/export\.csv", cp_io.api_export, "user"),  # 0.60.104 (D-O-116): spreadsheet and AI assistant, both ways
    ("GET", P + r"/cplans/prompt", ai_prompts_process.api_cp_prompt, "user"),
    ("POST", P + r"/cplans/import", cp_io.api_import, "user"),
    ("POST", P + r"/characteristics/(?P<cid>\d+)/reviewed", impact.api_reviewed, "user"),
    ("GET", P + r"/prio", prio.api_get, "user"),  # 0.60.103 (D-O-115): « Prioriser », waves of the actions
    ("POST", P + r"/prio/waves/init", prio.api_waves_init, "user"),
    ("PATCH", P + r"/prio/waves/(?P<wid>\d+)", prio.api_wave_update, "user"),
    ("POST", P + r"/prio/move", prio.api_move, "user"),
    ("GET", P + r"/pfmea", pfmea.api_list, "user"),  # 0.60.103 (D-O-114): the PFMEA, AI drafts reviewed row by row
    ("POST", P + r"/pfmea/rows", pfmea.api_create, "user"),
    ("PATCH", P + r"/pfmea/rows/(?P<rid>\d+)", pfmea.api_update, "user"),
    ("POST", P + r"/pfmea/rows/(?P<rid>\d+)/review", pfmea.api_review, "user"),
    ("POST", P + r"/pfmea/accept-all", pfmea.api_accept_all, "user"),
    ("GET", P + r"/pfmea/prompt", pfmea_ai.api_prompt, "user"),
    ("POST", P + r"/pfmea/ai", pfmea_ai.api_import, "user"),
    ("GET", P + r"/pfmea/export\.csv", pfmea_io.api_export, "user"),  # 0.60.104 (D-O-116)
    ("POST", P + r"/pfmea/import", pfmea_io.api_import, "user"),
    ("GET", P + r"/process", process.api_get, "user"),  # 0.60.103 (D-O-113): « Procédés », the assembly lines
    ("POST", P + r"/process/lines", process.api_line_create, "user"),
    ("PATCH", P + r"/process/lines/(?P<lid>\d+)", process.api_line_update, "user"),
    ("POST", P + r"/process/lines/(?P<lid>\d+)/ops", process.api_op_create, "user"),
    ("PATCH", P + r"/process/ops/(?P<oid>\d+)", process.api_op_update, "user"),
    ("POST", P + r"/process/ops/(?P<oid>\d+)/delete", process.api_op_delete, "user"),
    ("POST", P + r"/process/ops/(?P<oid>\d+)/points", process.api_point_create, "user"),
    ("POST", P + r"/process/points/(?P<cpid>\d+)/delete", process.api_point_delete, "user"),
    ("PUT", P + r"/process/access", process.api_access, "user"),
    ("GET", P + r"/pn", company_pn.api_get, "user"),  # 0.60.103 (D-O-112): company part numbers, BOM of the ERP, AI matching
    ("POST", P + r"/pn/bom", company_pn.api_bom, "user"),
    ("PUT", P + r"/pn/parts/(?P<oid>\d+)", company_pn.api_part, "user"),
    ("GET", P + r"/pn/prompt", pn_ai.api_prompt, "user"),
    ("POST", P + r"/pn/ai", pn_ai.api_import, "user"),
    ("GET", P + r"/characteristics", characteristics.api_list, "user"),  # 0.60.102 (D-O-110): « Caractéristiques » C-n
    ("POST", P + r"/characteristics", characteristics.api_create, "user"),
    ("GET", P + r"/characteristics/summary\.xlsx", char_export.api_xlsx, "user"),
    ("GET", P + r"/characteristics/summary\.docx", char_export.api_docx, "user"),
    ("PATCH", P + r"/characteristics/(?P<cid>\d+)", characteristics.api_update, "user"),
    ("POST", P + r"/characteristics/(?P<cid>\d+)/archive", characteristics.api_archive, "user"),
    ("GET", P + r"/dfmea/classes", classes_api.api_get, "user"),  # 0.60.101 (D-O-108): classes CC / SC, rules and symbols
    ("PATCH", P + r"/dfmea/classes", classes_api.api_settings, "user"),
    ("POST", P + r"/dfmea/classes/customers", classes_api.api_customer_create, "user"),
    ("PATCH", P + CUST, classes_api.api_customer_update, "user"),
    ("POST", P + CUST + r"/delete", classes_api.api_customer_delete, "user"),
    ("GET", P + r"/dfmea/rows/(?P<did>\d+)/class", classes_api.api_history, "user"),
    ("POST", P + r"/dfmea/rows/(?P<did>\d+)/class", classes_api.api_decide, "user"),
    ("POST", P + r"/dfmea/rows", dfmea.api_create, "user"),
    ("GET", P + r"/dfmea/export\.csv", dfmea.api_export, "user"),
    ("GET", P + r"/dfmea/prompt", ai_prompts.api_dfmea_prompt, "user"),  # 0.60.104 (D-O-116): interview / review for an AI assistant
    ("POST", P + r"/dfmea/import", dfmea_io.api_import, "user"),
    ("POST", P + r"/dfmea/from-tree", dfmea.api_from_tree, "user"),
    ("POST", P + r"/dfmea/from-risks", dfmea.api_from_risks, "user"),
    ("POST", P + r"/dfmea/complete", dfmea_complete.api_complete, "user"),
    ("GET", P + r"/export\.xlsx", export_api.api_xlsx, "user"),  # 0.60.33 (D-O-041): every table, every diagram, the report
    ("GET", P + r"/export\.docx", export_api.api_docx, "user"),
    ("GET", P + r"/export\.drawio", export_api.api_drawio, "user"),
    ("GET", P + r"/export\.pptx", export_api.api_pptx, "user"),  # 0.60.50 (D-O-059): the diagrams as PowerPoint shapes
    ("POST", P + r"/dfmea/example", example.api_dfmea_example, "user"),
    ("PATCH", P + r"/dfmea/rows/(?P<did>\d+)", dfmea.api_update, "user"),
    ("POST", P + r"/dfmea/rows/(?P<did>\d+)/duplicate", dfmea.api_duplicate, "user"),
    ("POST", P + r"/dfmea/rows/(?P<did>\d+)/move", dfmea.api_move, "user"),
    ("POST", P + r"/dfmea/rows/(?P<did>\d+)/delete", dfmea.api_delete, "user"),
]
