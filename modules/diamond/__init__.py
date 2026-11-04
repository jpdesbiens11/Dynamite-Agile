"""« Diamond » 💎 (0.60.11, D-O-023): the functional analysis and the design risk of a Space's product, at 1 000 m in
the mine -- the deepest gallery, where the hardest stone is cut.

Sub-modules, one per iteration:
  0.60.11  Arbre fonctionnel (functions.py, example.py): primary, secondary, tertiary functions; how / why / when.
  next     Structure fonctionnelle (boundary diagram: In on the left, Out on the right, flows between the functions),
           Analyse de risque projet (high level, before the DFMEA), DFMEA AIAG-VDA (the same functions, RPN and AP),
           Golden Nuggets (first-principles thinking and design rules, with examples).
Every table is tied to projects(id) (backup, restore, copy by the core); every write is journalled.
"""
from . import example, functions

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
]
