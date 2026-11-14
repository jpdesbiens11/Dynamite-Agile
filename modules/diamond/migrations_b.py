"""Migrations of Diamond, 10 and after (0.60.101: classes CC / SC; 0.60.102: characteristics; 0.60.103: company PNs, assembly lines, PFMEA, control plans) (additive only: never a column renamed or dropped). The list is MIGRATIONS of __init__.py."""

MIGRATIONS = [
    (10, """
        -- 0.60.101 (D-O-108): the class CC / SC of a DFMEA row -- proposed by the rules, decided by a person (classes.py)
        ALTER TABLE diamond_dfmea ADD COLUMN class_code TEXT NOT NULL DEFAULT '';
        ALTER TABLE diamond_dfmea ADD COLUMN class_state TEXT NOT NULL DEFAULT '';
        ALTER TABLE diamond_dfmea ADD COLUMN class_by INTEGER REFERENCES users(id) ON DELETE SET NULL;
        ALTER TABLE diamond_dfmea ADD COLUMN class_at TEXT NOT NULL DEFAULT '';
        ALTER TABLE diamond_dfmea ADD COLUMN class_reason TEXT NOT NULL DEFAULT '';
        ALTER TABLE diamond_dfmea ADD COLUMN class_severity INTEGER;
        ALTER TABLE diamond_dfmea ADD COLUMN class_occurrence INTEGER;
        CREATE TABLE diamond_class_settings (
            project_id    INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
            customer      TEXT NOT NULL DEFAULT 'aiag',
            cc_severity   INTEGER NOT NULL DEFAULT 9,
            sc_severity   INTEGER NOT NULL DEFAULT 5,
            sc_occurrence INTEGER NOT NULL DEFAULT 4,
            updated_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at    TEXT NOT NULL
        );
        CREATE TABLE diamond_class_customers (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            code       TEXT NOT NULL,
            name       TEXT NOT NULL,
            cc_dfmea   TEXT NOT NULL DEFAULT '',
            sc_dfmea   TEXT NOT NULL DEFAULT '',
            cc_symbol  TEXT NOT NULL DEFAULT '',
            sc_symbol  TEXT NOT NULL DEFAULT '',
            cc_label   TEXT NOT NULL DEFAULT '',
            sc_label   TEXT NOT NULL DEFAULT '',
            source     TEXT NOT NULL DEFAULT '',
            updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (project_id, code)
        );
        CREATE TABLE diamond_class_decisions (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            dfmea_id   INTEGER NOT NULL REFERENCES diamond_dfmea(id) ON DELETE CASCADE,
            class_code TEXT NOT NULL DEFAULT '',
            state      TEXT NOT NULL,
            severity   INTEGER,
            occurrence INTEGER,
            reason     TEXT NOT NULL DEFAULT '',
            decided_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            decided_at TEXT NOT NULL
        );
        CREATE INDEX idx_diamond_class_customers_project ON diamond_class_customers(project_id);
        CREATE INDEX idx_diamond_class_decisions_row ON diamond_class_decisions(dfmea_id, decided_at);
    """),
    (11, """
        -- 0.60.102 (D-O-110): the characteristics C-n -- the exact dimension of the exact part that carries a class
        CREATE TABLE diamond_characteristics (
            id           INTEGER PRIMARY KEY,
            project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            number       INTEGER NOT NULL,
            dfmea_id     INTEGER REFERENCES diamond_dfmea(id) ON DELETE SET NULL,
            nature       TEXT NOT NULL DEFAULT 'product',
            label        TEXT NOT NULL,
            prefix       TEXT NOT NULL DEFAULT '',
            nominal      REAL,
            lsl          REAL,
            usl          REAL,
            decimals     INTEGER NOT NULL DEFAULT 1,
            unit         TEXT NOT NULL DEFAULT '',
            spec_text    TEXT NOT NULL DEFAULT '',
            part_id      INTEGER REFERENCES diamond_parts(id) ON DELETE SET NULL,
            part2_id     INTEGER REFERENCES diamond_parts(id) ON DELETE SET NULL,
            drawing      TEXT NOT NULL DEFAULT '',
            sheet        TEXT NOT NULL DEFAULT '',
            zone         TEXT NOT NULL DEFAULT '',
            datum        TEXT NOT NULL DEFAULT '',
            control      TEXT NOT NULL DEFAULT 'spc',
            cpk_required REAL,
            test_id      INTEGER REFERENCES testing_tests(id) ON DELETE SET NULL,
            notes        TEXT NOT NULL DEFAULT '',
            archived     INTEGER NOT NULL DEFAULT 0,
            created_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at   TEXT NOT NULL,
            updated_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at   TEXT NOT NULL,
            UNIQUE (project_id, number)
        );
        CREATE INDEX idx_diamond_characteristics_project ON diamond_characteristics(project_id, number);
        CREATE INDEX idx_diamond_characteristics_dfmea ON diamond_characteristics(dfmea_id);
        -- the Cpk a customer requires of a CC and of a SC (NULL: the start value, 1,67 and 1,33)
        ALTER TABLE diamond_class_customers ADD COLUMN cc_cpk REAL;
        ALTER TABLE diamond_class_customers ADD COLUMN sc_cpk REAL;
    """),
    (12, """
        -- 0.60.103 (D-O-112): the company part numbers (the BOM of the ERP) and which ones each Diamond part covers
        CREATE TABLE diamond_company_parts (
            id          INTEGER PRIMARY KEY,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            pn          TEXT NOT NULL,
            rev         TEXT NOT NULL DEFAULT '',
            designation TEXT NOT NULL DEFAULT '',
            supplier    TEXT NOT NULL DEFAULT '',
            material    TEXT NOT NULL DEFAULT '',
            created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at  TEXT NOT NULL,
            updated_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at  TEXT NOT NULL,
            UNIQUE (project_id, pn)
        );
        CREATE TABLE diamond_part_pns (
            id              INTEGER PRIMARY KEY,
            project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            part_id         INTEGER NOT NULL REFERENCES diamond_parts(id) ON DELETE CASCADE,
            company_part_id INTEGER NOT NULL REFERENCES diamond_company_parts(id) ON DELETE CASCADE,
            source          TEXT NOT NULL DEFAULT 'manual',
            confidence      REAL,
            reason          TEXT NOT NULL DEFAULT '',
            created_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at      TEXT NOT NULL,
            UNIQUE (part_id, company_part_id)
        );
        ALTER TABLE diamond_parts ADD COLUMN erp_todo INTEGER NOT NULL DEFAULT 0;
        CREATE INDEX idx_diamond_company_parts_project ON diamond_company_parts(project_id);
        CREATE INDEX idx_diamond_part_pns_part ON diamond_part_pns(part_id);
    """),
    (13, """
        -- 0.60.103 (D-O-113): « Procédés » -- the assembly line configurations, their operations, equipment and control
        -- points (each tied to the characteristic C-n it protects), and who may see them
        CREATE TABLE diamond_lines (
            id          INTEGER PRIMARY KEY,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            number      INTEGER NOT NULL,
            name        TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            archived    INTEGER NOT NULL DEFAULT 0,
            created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at  TEXT NOT NULL,
            updated_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at  TEXT NOT NULL,
            UNIQUE (project_id, number)
        );
        CREATE TABLE diamond_operations (
            id          INTEGER PRIMARY KEY,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            line_id     INTEGER NOT NULL REFERENCES diamond_lines(id) ON DELETE CASCADE,
            op          INTEGER NOT NULL,
            name        TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            equipment   TEXT NOT NULL DEFAULT '',
            traceability INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            UNIQUE (line_id, op)
        );
        CREATE TABLE diamond_control_points (
            id                INTEGER PRIMARY KEY,
            project_id        INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            operation_id      INTEGER NOT NULL REFERENCES diamond_operations(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES diamond_characteristics(id) ON DELETE SET NULL,
            label             TEXT NOT NULL DEFAULT '',
            method            TEXT NOT NULL DEFAULT '',
            frequency         TEXT NOT NULL DEFAULT '',
            position          INTEGER NOT NULL DEFAULT 0,
            created_at        TEXT NOT NULL
        );
        CREATE TABLE diamond_process_access (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            granted_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            granted_at TEXT NOT NULL,
            UNIQUE (project_id, user_id)
        );
        CREATE INDEX idx_diamond_lines_project ON diamond_lines(project_id);
        CREATE INDEX idx_diamond_operations_line ON diamond_operations(line_id, op);
        CREATE INDEX idx_diamond_control_points_op ON diamond_control_points(operation_id);
    """),
    (14, """
        -- 0.60.103 (D-O-114): the PFMEA, AIAG-VDA -- one row per process failure chain of an operation; S comes from the
        -- DFMEA through the characteristic C-n and is never lowered; an AI draft is reviewed row by row
        CREATE TABLE diamond_pfmea (
            id                INTEGER PRIMARY KEY,
            project_id        INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            operation_id      INTEGER REFERENCES diamond_operations(id) ON DELETE SET NULL,
            number            INTEGER NOT NULL DEFAULT 1,
            position          INTEGER NOT NULL DEFAULT 0,
            process_step      TEXT NOT NULL DEFAULT '',
            characteristic_id INTEGER REFERENCES diamond_characteristics(id) ON DELETE SET NULL,
            process_char      TEXT NOT NULL DEFAULT '',
            failure_mode      TEXT NOT NULL DEFAULT '',
            effect            TEXT NOT NULL DEFAULT '',
            severity          INTEGER,
            cause             TEXT NOT NULL DEFAULT '',
            cause_5m          TEXT NOT NULL DEFAULT '',
            prevention        TEXT NOT NULL DEFAULT '',
            occurrence        INTEGER,
            detection_ctrl    TEXT NOT NULL DEFAULT '',
            detection         INTEGER,
            action            TEXT NOT NULL DEFAULT '',
            action_owner_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            action_due        TEXT NOT NULL DEFAULT '',
            action_status     TEXT NOT NULL DEFAULT 'open',
            issue_id          INTEGER REFERENCES agile_issues(id) ON DELETE SET NULL,
            state             TEXT NOT NULL DEFAULT 'accepted',
            source            TEXT NOT NULL DEFAULT 'manual',
            created_by        INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at        TEXT NOT NULL,
            updated_by        INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at        TEXT NOT NULL
        );
        CREATE INDEX idx_diamond_pfmea_project ON diamond_pfmea(project_id, position);
    """),
    (15, """
        -- 0.60.103 (D-O-115): the control plans (several per Space: one per line configuration and phase, and the reception
        -- of the parts), the measurements and capability, the waves of the actions, the « à revoir » flags of an ECN
        CREATE TABLE diamond_control_plans (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            number     INTEGER NOT NULL,
            title      TEXT NOT NULL,
            scope      TEXT NOT NULL DEFAULT 'assembly',
            line_id    INTEGER REFERENCES diamond_lines(id) ON DELETE SET NULL,
            phase      TEXT NOT NULL DEFAULT 'prototype',
            revision   TEXT NOT NULL DEFAULT 'A',
            archived   INTEGER NOT NULL DEFAULT 0,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (project_id, number)
        );
        CREATE TABLE diamond_cp_items (
            id                INTEGER PRIMARY KEY,
            project_id        INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            plan_id           INTEGER NOT NULL REFERENCES diamond_control_plans(id) ON DELETE CASCADE,
            seq               INTEGER NOT NULL DEFAULT 1,
            position          INTEGER NOT NULL DEFAULT 0,
            operation_id      INTEGER REFERENCES diamond_operations(id) ON DELETE SET NULL,
            part_id           INTEGER REFERENCES diamond_parts(id) ON DELETE SET NULL,
            characteristic_id INTEGER REFERENCES diamond_characteristics(id) ON DELETE SET NULL,
            char_label        TEXT NOT NULL DEFAULT '',
            equipment         TEXT NOT NULL DEFAULT '',
            technique         TEXT NOT NULL DEFAULT '',
            sample            TEXT NOT NULL DEFAULT '',
            frequency         TEXT NOT NULL DEFAULT '',
            control_method    TEXT NOT NULL DEFAULT '',
            reaction_plan     TEXT NOT NULL DEFAULT '',
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL
        );
        CREATE TABLE diamond_measurements (
            id                INTEGER PRIMARY KEY,
            project_id        INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            characteristic_id INTEGER NOT NULL REFERENCES diamond_characteristics(id) ON DELETE CASCADE,
            value             REAL NOT NULL,
            taken_at          TEXT NOT NULL,
            sample            TEXT NOT NULL DEFAULT '',
            source            TEXT NOT NULL DEFAULT 'manual',
            entered_by        INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at        TEXT NOT NULL
        );
        CREATE TABLE diamond_waves (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            number     INTEGER NOT NULL,
            name       TEXT NOT NULL,
            due_date   TEXT NOT NULL DEFAULT '',
            UNIQUE (project_id, number)
        );
        ALTER TABLE diamond_dfmea ADD COLUMN wave_id INTEGER REFERENCES diamond_waves(id) ON DELETE SET NULL;
        ALTER TABLE diamond_pfmea ADD COLUMN wave_id INTEGER REFERENCES diamond_waves(id) ON DELETE SET NULL;
        CREATE TABLE diamond_review_flags (
            id                INTEGER PRIMARY KEY,
            project_id        INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            characteristic_id INTEGER NOT NULL REFERENCES diamond_characteristics(id) ON DELETE CASCADE,
            kind              TEXT NOT NULL,
            object_id         INTEGER,
            label             TEXT NOT NULL DEFAULT '',
            reason            TEXT NOT NULL DEFAULT '',
            raised_by         INTEGER REFERENCES users(id) ON DELETE SET NULL,
            raised_at         TEXT NOT NULL,
            reviewed_by       INTEGER REFERENCES users(id) ON DELETE SET NULL,
            reviewed_at       TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX idx_diamond_cp_items_plan ON diamond_cp_items(plan_id, position);
        CREATE INDEX idx_diamond_measurements_char ON diamond_measurements(characteristic_id, taken_at);
        CREATE INDEX idx_diamond_review_flags_char ON diamond_review_flags(characteristic_id, reviewed_at);
    """),
]
