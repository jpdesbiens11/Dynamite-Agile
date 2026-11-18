"""Where an audited Diamond object lives, for « Changements » (core lot v0.39, 0.60.120, D-O-133): the page of its table
and the code the pages show (F12, R-3, C-04, CB-2, L1, P-5, NRE-2…). The pointer (?focus=) finds the code on the page."""

PAGES = [  # table prefix -> page of Diamond (longest prefix first)
    ("diamond_concept_sheets", "csheets"), ("diamond_concept", "concepts"), ("diamond_competenc", "competencies"),
    ("diamond_functions", "ftree"), ("diamond_review_flags", "ftree"), ("diamond_ports", "fstructure"),
    ("diamond_flows", "fstructure"), ("diamond_part", "fstructure"), ("diamond_company_parts", "fstructure"),
    ("diamond_pugh", "pugh"), ("diamond_risks", "prisk"), ("diamond_dfmea", "dfmea"), ("diamond_class", "dfmea"),
    ("diamond_characteristics", "chars"), ("diamond_measurements", "chars"), ("diamond_pfmea", "pfmea"),
    ("diamond_control", "cplans"), ("diamond_cp_items", "cplans"), ("diamond_lines", "process"),
    ("diamond_operations", "process"), ("diamond_positions", "process"), ("diamond_process", "process"),
    ("diamond_waves", "prio"), ("diamond_cost", "costs"), ("diamond_story", "story"),
]
CODES = {"diamond_functions": "F{}", "diamond_risks": "R-{}", "diamond_characteristics": "C-{:02d}", "diamond_concepts": "CB-{}",
         "diamond_lines": "L{}", "diamond_parts": "P-{}", "diamond_cost_nre": "NRE-{}", "diamond_control_plans": "PC-{}"}
BY_ID = {"diamond_dfmea": "D-{}", "diamond_story_scenes": "S-{}", "diamond_ports": "IO-{}", "diamond_flows": "FX-{}"}  # codes of ↔ IA


def page_of(name):
    for prefix, page in PAGES:
        if name.startswith(prefix):
            return page
    return None


def change_link(conn, entry, row, key):
    object_type, object_id = entry["object_type"], entry["object_id"]
    if not object_type.startswith("diamond_") or not key:
        return None
    table = object_type if object_type.endswith("s") or object_type.endswith("ea") else object_type + "s"
    page = page_of(table) or page_of(object_type)
    if not page:
        return None
    code = ""
    fmt = CODES.get(table) or CODES.get(object_type)
    if fmt and row and row.get("number") is not None:
        code = fmt.format(row["number"])
    elif (BY_ID.get(table) or BY_ID.get(object_type)) and row:
        code = (BY_ID.get(table) or BY_ID.get(object_type)).format(row["id"])
    href = "#/diamond/{}/{}".format(key, page)
    if page == "chars" and code:
        href += "/" + code
    elif code:
        href = "/?focus={}#/diamond/{}/{}".format(code, key, page)
    return {"tab": "diamond", "code": code, "href": href}
