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
Every table is tied to projects(id) (backup, restore, copy by the core); every write is journalled.
"""
from .search import search  # noqa: F401  (core search hook, 0.60.36)
from .bot import bot_summary  # noqa: F401  (Bob le mineur, core/bot.py, 0.60.36)
from .actions import dashboard  # noqa: F401  (core dashboard hook, 0.60.38)
from . import actions, dfmea, dfmea_complete, example, export_api, functions, parts, risks, story, story_ai, structure

SCHEMA = ""

MIGRATIONS = [
    (1, """
        CREATE TABLE diamond_functions (
            id          INTEGER PRIMARY KEY,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            number      INTEGER NOT NULL,
            text        TEXT NOT NULL,
            ftype       TEXT NOT NULL DEFAULT 'usage',
            kano        TEXT NOT NULL DEFAULT '',
            importance  TEXT NOT NULL DEFAULT '',
            notes       TEXT NOT NULL DEFAULT '',
            parent_id   INTEGER REFERENCES diamond_functions(id) ON DELETE SET NULL,
            position    INTEGER NOT NULL DEFAULT 0,
            is_primary  INTEGER NOT NULL DEFAULT 0,
            critical    INTEGER NOT NULL DEFAULT 0,
            feedback_to INTEGER REFERENCES diamond_functions(id) ON DELETE SET NULL,
            archived    INTEGER NOT NULL DEFAULT 0,
            created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at  TEXT NOT NULL,
            updated_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at  TEXT NOT NULL,
            UNIQUE (project_id, number)
        );
        CREATE INDEX idx_diamond_functions_project ON diamond_functions(project_id);
    """),
    (2, """
        -- 0.60.13 (D-O-025): the functional structure (boundary diagram)
        CREATE TABLE diamond_ports (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            side       TEXT NOT NULL CHECK (side IN ('in', 'out')),
            label      TEXT NOT NULL,
            kind       TEXT NOT NULL DEFAULT 'energy',
            position   INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE diamond_flows (
            id              INTEGER PRIMARY KEY,
            project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            view            TEXT NOT NULL CHECK (view IN ('general', 'detail')),
            kind            TEXT NOT NULL CHECK (kind IN ('energy', 'material', 'information')),
            label           TEXT NOT NULL DEFAULT '',
            src_function_id INTEGER REFERENCES diamond_functions(id) ON DELETE CASCADE,
            src_port_id     INTEGER REFERENCES diamond_ports(id) ON DELETE CASCADE,
            dst_function_id INTEGER REFERENCES diamond_functions(id) ON DELETE CASCADE,
            dst_port_id     INTEGER REFERENCES diamond_ports(id) ON DELETE CASCADE,
            created_at      TEXT NOT NULL
        );
        CREATE TABLE diamond_positions (
            id          INTEGER PRIMARY KEY,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            view        TEXT NOT NULL,
            function_id INTEGER REFERENCES diamond_functions(id) ON DELETE CASCADE,
            port_id     INTEGER REFERENCES diamond_ports(id) ON DELETE CASCADE,
            x           REAL NOT NULL,
            y           REAL NOT NULL
        );
        CREATE INDEX idx_diamond_ports_project ON diamond_ports(project_id);
        CREATE INDEX idx_diamond_flows_project ON diamond_flows(project_id);
        CREATE INDEX idx_diamond_positions_project ON diamond_positions(project_id);
    """),
    (3, """
        -- 0.60.14 (D-O-026): the project risk register
        CREATE TABLE diamond_risks (
            id          INTEGER PRIMARY KEY,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            number      INTEGER NOT NULL,
            title       TEXT NOT NULL,
            cause       TEXT NOT NULL DEFAULT '',
            consequence TEXT NOT NULL DEFAULT '',
            category    TEXT NOT NULL DEFAULT 'technique',
            phase       TEXT NOT NULL DEFAULT '',
            probability INTEGER NOT NULL DEFAULT 3,
            impact      INTEGER NOT NULL DEFAULT 3,
            response    TEXT NOT NULL DEFAULT '',
            action      TEXT NOT NULL DEFAULT '',
            owner_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
            due_date    TEXT NOT NULL DEFAULT '',
            status      TEXT NOT NULL DEFAULT 'open',
            residual_p  INTEGER,
            residual_i  INTEGER,
            function_id INTEGER REFERENCES diamond_functions(id) ON DELETE SET NULL,
            to_dfmea    INTEGER NOT NULL DEFAULT 0,
            notes       TEXT NOT NULL DEFAULT '',
            archived    INTEGER NOT NULL DEFAULT 0,
            created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at  TEXT NOT NULL,
            updated_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at  TEXT NOT NULL,
            UNIQUE (project_id, number)
        );
        CREATE INDEX idx_diamond_risks_project ON diamond_risks(project_id);
    """),
    (4, """
        -- 0.60.15 (D-O-027): the DFMEA, one row per failure chain
        CREATE TABLE diamond_dfmea (
            id             INTEGER PRIMARY KEY,
            project_id     INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            position       INTEGER NOT NULL DEFAULT 0,
            higher         TEXT NOT NULL DEFAULT '',
            focus          TEXT NOT NULL DEFAULT '',
            lower          TEXT NOT NULL DEFAULT '',
            function_id    INTEGER REFERENCES diamond_functions(id) ON DELETE SET NULL,
            requirement    TEXT NOT NULL DEFAULT '',
            failure_mode   TEXT NOT NULL DEFAULT '',
            effect         TEXT NOT NULL DEFAULT '',
            severity       INTEGER,
            cause          TEXT NOT NULL DEFAULT '',
            prevention     TEXT NOT NULL DEFAULT '',
            occurrence     INTEGER,
            detection_ctrl TEXT NOT NULL DEFAULT '',
            detection      INTEGER,
            action         TEXT NOT NULL DEFAULT '',
            risk_id        INTEGER REFERENCES diamond_risks(id) ON DELETE SET NULL,
            created_by     INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at     TEXT NOT NULL,
            updated_by     INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at     TEXT NOT NULL
        );
        CREATE INDEX idx_diamond_dfmea_project ON diamond_dfmea(project_id, position);
    """),
    (5, """
        -- 0.60.20 (D-O-031): the parts and the functions each one carries out
        CREATE TABLE diamond_parts (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            number     INTEGER NOT NULL,
            name       TEXT NOT NULL,
            kind       TEXT NOT NULL DEFAULT 'designed',
            notes      TEXT NOT NULL DEFAULT '',
            position   INTEGER NOT NULL DEFAULT 0,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (project_id, number)
        );
        CREATE TABLE diamond_part_functions (
            id          INTEGER PRIMARY KEY,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            part_id     INTEGER NOT NULL REFERENCES diamond_parts(id) ON DELETE CASCADE,
            function_id INTEGER NOT NULL REFERENCES diamond_functions(id) ON DELETE CASCADE,
            UNIQUE (part_id, function_id)
        );
        CREATE INDEX idx_diamond_parts_project ON diamond_parts(project_id);
        CREATE INDEX idx_diamond_part_functions_project ON diamond_part_functions(project_id);
    """),
    (6, """
        -- 0.60.24 (D-O-033): the key test of the Test Base that detects the failure, in « Detection Controls »
        ALTER TABLE diamond_dfmea ADD COLUMN test_id INTEGER REFERENCES testing_tests(id) ON DELETE SET NULL;
    """),
    (7, """
        -- 0.60.38 (D-O-047): who carries the action, by when, where it stands, and the Agile ticket that follows it
        ALTER TABLE diamond_dfmea ADD COLUMN action_owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
        ALTER TABLE diamond_dfmea ADD COLUMN action_due TEXT NOT NULL DEFAULT '';
        ALTER TABLE diamond_dfmea ADD COLUMN action_status TEXT NOT NULL DEFAULT 'open';
        ALTER TABLE diamond_dfmea ADD COLUMN issue_id INTEGER REFERENCES agile_issues(id) ON DELETE SET NULL;
        ALTER TABLE diamond_risks ADD COLUMN issue_id INTEGER REFERENCES agile_issues(id) ON DELETE SET NULL;
    """),
    (8, """
        -- 0.60.51 (D-O-060): the Storyline, scene by scene, pictograms as JSON (key, x, y in %, size, mirror, label)
        CREATE TABLE diamond_story_scenes (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            position   REAL NOT NULL DEFAULT 0,
            title      TEXT NOT NULL DEFAULT '',
            caption    TEXT NOT NULL DEFAULT '',
            notes      TEXT NOT NULL DEFAULT '',
            items      TEXT NOT NULL DEFAULT '[]',
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX idx_diamond_story_project ON diamond_story_scenes(project_id, position);
    """),
]

P = r"/api/diamond/p/(?P<pid>\d+)"
FN = P + r"/functions/(?P<fid>\d+)"

SC = P + r"/story/scenes/(?P<sid>\d+)"

ROUTES = [
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
    ("GET", P + r"/dfmea", dfmea.api_list, "user"),
    ("POST", P + r"/dfmea/rows", dfmea.api_create, "user"),
    ("GET", P + r"/dfmea/export\.csv", dfmea.api_export, "user"),
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
