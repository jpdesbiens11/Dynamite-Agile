"""« Diamond » 💎 (0.60.11, D-O-023): the functional analysis and the design risk of a Space's product, at 1 000 m in
the mine -- the deepest gallery, where the hardest stone is cut.

Sub-modules, one per iteration:
  0.60.11  Arbre fonctionnel (functions.py, example.py): primary, secondary, tertiary functions; how / why / when.
  0.60.13  Structure fonctionnelle (structure.py): boundary diagram -- inputs on the left, outputs on the right, the
           sub-systems (general view) or the tertiary functions (detail view), energy / material / information flows.
  next     Analyse de risque projet (high level, before the DFMEA), DFMEA AIAG-VDA (the same functions, RPN and AP),
           Golden Nuggets (first-principles thinking and design rules, with examples).
Every table is tied to projects(id) (backup, restore, copy by the core); every write is journalled.
"""
from . import example, functions, structure

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
]

P = r"/api/diamond/p/(?P<pid>\d+)"
FN = P + r"/functions/(?P<fid>\d+)"

ROUTES = [
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
]
