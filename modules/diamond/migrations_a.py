"""Migrations of Diamond, 1 to 9 (0.60.11 to 0.60.61) (additive only: never a column renamed or dropped). The list is MIGRATIONS of __init__.py."""

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
    (9, """
        -- 0.60.61 (D-O-070): « Coûts et budget »
        CREATE TABLE diamond_cost_settings (
            project_id  INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
            currency    TEXT NOT NULL DEFAULT 'CAD',
            proto_qty   INTEGER NOT NULL DEFAULT 3,
            volumes     TEXT NOT NULL DEFAULT '[100, 1000, 10000]',
            contingency REAL NOT NULL DEFAULT 15,
            labour_rate REAL NOT NULL DEFAULT 0,
            notes       TEXT NOT NULL DEFAULT '',
            updated_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at  TEXT NOT NULL
        );
        CREATE TABLE diamond_cost_nre (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            number     INTEGER NOT NULL,
            position   INTEGER NOT NULL DEFAULT 0,
            title      TEXT NOT NULL,
            category   TEXT NOT NULL DEFAULT 'ingenierie',
            phase      TEXT NOT NULL DEFAULT '',
            amount     REAL NOT NULL DEFAULT 0,
            basis      TEXT NOT NULL DEFAULT 'estimation',
            supplier   TEXT NOT NULL DEFAULT '',
            notes      TEXT NOT NULL DEFAULT '',
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (project_id, number)
        );
        CREATE TABLE diamond_cost_parts (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            part_id    INTEGER UNIQUE REFERENCES diamond_parts(id) ON DELETE CASCADE,
            position   INTEGER NOT NULL DEFAULT 0,
            name       TEXT NOT NULL DEFAULT '',
            qty        REAL NOT NULL DEFAULT 1,
            proto_unit REAL,
            prod_1     REAL,
            prod_2     REAL,
            prod_3     REAL,
            supplier   TEXT NOT NULL DEFAULT '',
            basis      TEXT NOT NULL DEFAULT 'estimation',
            notes      TEXT NOT NULL DEFAULT '',
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX idx_diamond_cost_nre_project ON diamond_cost_nre(project_id, position);
        CREATE INDEX idx_diamond_cost_parts_project ON diamond_cost_parts(project_id, position);
    """),
]
