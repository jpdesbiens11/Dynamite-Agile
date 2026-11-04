"""SQL schema of the Agile module (tickets, workflows, labels, sprints).

Top-level tables reference projects(id); child tables reach the project
through their parent (workflow, issue), always with ON DELETE CASCADE.
"""


SCHEMA = """
CREATE TABLE IF NOT EXISTS agile_settings (
    project_id INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    enabled_at TEXT NOT NULL,
    enabled_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS agile_workflows (
    id         INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0,
    UNIQUE (project_id, name)
);

CREATE TABLE IF NOT EXISTS agile_statuses (
    id          INTEGER PRIMARY KEY,
    workflow_id INTEGER NOT NULL REFERENCES agile_workflows(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL CHECK (category IN ('todo', 'in_progress', 'done')),
    position    INTEGER NOT NULL DEFAULT 0,
    is_initial  INTEGER NOT NULL DEFAULT 0,
    UNIQUE (workflow_id, name)
);

CREATE TABLE IF NOT EXISTS agile_transitions (
    id             INTEGER PRIMARY KEY,
    workflow_id    INTEGER NOT NULL REFERENCES agile_workflows(id) ON DELETE CASCADE,
    from_status_id INTEGER REFERENCES agile_statuses(id) ON DELETE CASCADE,
    to_status_id   INTEGER NOT NULL REFERENCES agile_statuses(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    min_role       TEXT NOT NULL DEFAULT 'editor' CHECK (min_role IN ('editor', 'admin'))
);

CREATE TABLE IF NOT EXISTS agile_issue_types (
    id          INTEGER PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    icon_key    TEXT NOT NULL DEFAULT 'task',
    workflow_id INTEGER NOT NULL REFERENCES agile_workflows(id),
    is_subtask  INTEGER NOT NULL DEFAULT 0,
    position    INTEGER NOT NULL DEFAULT 0,
    UNIQUE (project_id, name)
);

CREATE TABLE IF NOT EXISTS agile_sprints (
    id         INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    goal       TEXT NOT NULL DEFAULT '',
    state      TEXT NOT NULL DEFAULT 'future' CHECK (state IN ('future', 'active', 'closed')),
    start_date TEXT,
    end_date   TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agile_versions (
    id           INTEGER PRIMARY KEY,
    project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    release_date TEXT,
    is_released  INTEGER NOT NULL DEFAULT 0,
    UNIQUE (project_id, name)
);

CREATE TABLE IF NOT EXISTS agile_issues (
    id           INTEGER PRIMARY KEY,
    project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    number       INTEGER NOT NULL,
    type_id      INTEGER NOT NULL REFERENCES agile_issue_types(id),
    status_id    INTEGER NOT NULL REFERENCES agile_statuses(id),
    parent_id    INTEGER REFERENCES agile_issues(id) ON DELETE SET NULL,
    title        TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    priority     TEXT NOT NULL DEFAULT 'medium'
                 CHECK (priority IN ('blocker', 'high', 'medium', 'low', 'trivial')),
    assignee_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reporter_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    story_points REAL,
    due_date     TEXT,
    sprint_id    INTEGER REFERENCES agile_sprints(id) ON DELETE SET NULL,
    version_id   INTEGER REFERENCES agile_versions(id) ON DELETE SET NULL,
    rank         REAL NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    resolved_at  TEXT,
    UNIQUE (project_id, number)
);
CREATE INDEX IF NOT EXISTS idx_agile_issues_status ON agile_issues(project_id, status_id);
CREATE INDEX IF NOT EXISTS idx_agile_issues_sprint ON agile_issues(sprint_id);
CREATE INDEX IF NOT EXISTS idx_agile_issues_parent ON agile_issues(parent_id);
CREATE INDEX IF NOT EXISTS idx_agile_issues_assignee ON agile_issues(assignee_id);

CREATE TABLE IF NOT EXISTS agile_labels (
    id         INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name       TEXT NOT NULL COLLATE NOCASE,
    color_key  TEXT NOT NULL DEFAULT 'neutral',
    UNIQUE (project_id, name)
);

CREATE TABLE IF NOT EXISTS agile_issue_labels (
    issue_id INTEGER NOT NULL REFERENCES agile_issues(id) ON DELETE CASCADE,
    label_id INTEGER NOT NULL REFERENCES agile_labels(id) ON DELETE CASCADE,
    PRIMARY KEY (issue_id, label_id)
);

CREATE TABLE IF NOT EXISTS agile_comments (
    id         INTEGER PRIMARY KEY,
    issue_id   INTEGER NOT NULL REFERENCES agile_issues(id) ON DELETE CASCADE,
    author_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    edited_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_agile_comments_issue ON agile_comments(issue_id);

CREATE TABLE IF NOT EXISTS agile_links (
    id         INTEGER PRIMARY KEY,
    source_id  INTEGER NOT NULL REFERENCES agile_issues(id) ON DELETE CASCADE,
    target_id  INTEGER NOT NULL REFERENCES agile_issues(id) ON DELETE CASCADE,
    link_type  TEXT NOT NULL CHECK (link_type IN ('blocks', 'relates', 'duplicates')),
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    UNIQUE (source_id, target_id, link_type)
);

CREATE TABLE IF NOT EXISTS agile_history (
    id        INTEGER PRIMARY KEY,
    issue_id  INTEGER NOT NULL REFERENCES agile_issues(id) ON DELETE CASCADE,
    user_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    ts        TEXT NOT NULL,
    field     TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT
);
CREATE INDEX IF NOT EXISTS idx_agile_history_issue ON agile_history(issue_id);

CREATE VIRTUAL TABLE IF NOT EXISTS agile_issues_fts USING fts5(
    title, description, content='agile_issues', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS agile_issues_ai AFTER INSERT ON agile_issues BEGIN
    INSERT INTO agile_issues_fts(rowid, title, description)
    VALUES (new.id, new.title, new.description);
END;
CREATE TRIGGER IF NOT EXISTS agile_issues_ad AFTER DELETE ON agile_issues BEGIN
    INSERT INTO agile_issues_fts(agile_issues_fts, rowid, title, description)
    VALUES ('delete', old.id, old.title, old.description);
END;
CREATE TRIGGER IF NOT EXISTS agile_issues_au AFTER UPDATE OF title, description ON agile_issues BEGIN
    INSERT INTO agile_issues_fts(agile_issues_fts, rowid, title, description)
    VALUES ('delete', old.id, old.title, old.description);
    INSERT INTO agile_issues_fts(rowid, title, description)
    VALUES (new.id, new.title, new.description);
END;
"""
# (version, sql) -- applied once each by core.db.apply_migrations.
MIGRATIONS = [
    (2, """
        ALTER TABLE agile_issue_types ADD COLUMN is_requirement INTEGER NOT NULL DEFAULT 0;

        ALTER TABLE agile_comments ADD COLUMN parent_comment_id INTEGER
            REFERENCES agile_comments(id) ON DELETE CASCADE;
        ALTER TABLE agile_comments ADD COLUMN external_author TEXT;
        ALTER TABLE agile_comments ADD COLUMN is_question INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE agile_comments ADD COLUMN requirement_ref TEXT NOT NULL DEFAULT '';
        CREATE INDEX IF NOT EXISTS idx_agile_comments_parent
            ON agile_comments(parent_comment_id);

        -- SQLite can't drop a CHECK constraint, so the table is rebuilt
        -- without one; validation of link_type moves to Python
        -- (common.LINK_TYPES), which is where it can actually grow.
        CREATE TABLE agile_links_v2 (
            id         INTEGER PRIMARY KEY,
            source_id  INTEGER NOT NULL REFERENCES agile_issues(id) ON DELETE CASCADE,
            target_id  INTEGER NOT NULL REFERENCES agile_issues(id) ON DELETE CASCADE,
            link_type  TEXT NOT NULL,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            UNIQUE (source_id, target_id, link_type)
        );
        INSERT INTO agile_links_v2 SELECT * FROM agile_links;
        DROP TABLE agile_links;
        ALTER TABLE agile_links_v2 RENAME TO agile_links;
    """),
    (3, """
        -- Goldmine (D-A-032): engineering-requirement fields, one row per
        -- ticket whose type is a requirement type. Codes are validated in
        -- modules/agile/goldmine.py, not by CHECK (lists will evolve).
        CREATE TABLE agile_requirements (
            issue_id            INTEGER PRIMARY KEY REFERENCES agile_issues(id) ON DELETE CASCADE,
            external_id         TEXT NOT NULL DEFAULT '',
            source              TEXT NOT NULL DEFAULT 'client',
            source_doc          TEXT NOT NULL DEFAULT '',
            statement           TEXT NOT NULL DEFAULT '',
            rationale           TEXT NOT NULL DEFAULT '',
            category            TEXT NOT NULL DEFAULT 'functional',
            criticality         TEXT NOT NULL DEFAULT '',
            verification_method TEXT NOT NULL DEFAULT '',
            acceptance_criteria TEXT NOT NULL DEFAULT '',
            allocation          TEXT NOT NULL DEFAULT '',
            verification_ref    TEXT NOT NULL DEFAULT '',
            revision            TEXT NOT NULL DEFAULT 'A',
            received_at         TEXT
        );
        CREATE INDEX idx_agile_requirements_external ON agile_requirements(external_id);
    """),
    (4, """
        -- Client summary (D-B-001): the curated position sent to the client,
        -- separate from the comment thread. History keeps every version.
        ALTER TABLE agile_issues ADD COLUMN client_summary TEXT NOT NULL DEFAULT '';
        ALTER TABLE agile_issues ADD COLUMN client_summary_by INTEGER
            REFERENCES users(id) ON DELETE SET NULL;
        ALTER TABLE agile_issues ADD COLUMN client_summary_at TEXT;
    """),
    (5, """
        -- Goldmine change management (D-B-010): PR, software bugs and ECN
        -- (with ECN sub-tasks) leave the Agile views for Goldmine.
        -- bucket: 'agile' | 'goldmine'; change_role: '' | pr | bug | ecn | ecn_task.
        ALTER TABLE agile_issue_types ADD COLUMN bucket TEXT NOT NULL DEFAULT 'agile';
        ALTER TABLE agile_issue_types ADD COLUMN change_role TEXT NOT NULL DEFAULT '';
        UPDATE agile_issue_types SET bucket = 'goldmine' WHERE is_requirement = 1;

        -- One row per PR / bug / ECN. Codes validated in change_fields.py.
        CREATE TABLE agile_changes (
            issue_id             INTEGER PRIMARY KEY REFERENCES agile_issues(id) ON DELETE CASCADE,
            severity             TEXT NOT NULL DEFAULT '',
            detected_in          TEXT NOT NULL DEFAULT '',
            item_ref             TEXT NOT NULL DEFAULT '',
            found_version        TEXT NOT NULL DEFAULT '',
            containment          TEXT NOT NULL DEFAULT '',
            root_cause           TEXT NOT NULL DEFAULT '',
            change_class         TEXT NOT NULL DEFAULT '',
            reason               TEXT NOT NULL DEFAULT '',
            impact_fff           INTEGER NOT NULL DEFAULT 0,
            impact_certification INTEGER NOT NULL DEFAULT 0,
            impact_safety        INTEGER NOT NULL DEFAULT 0,
            impact_notes         TEXT NOT NULL DEFAULT '',
            effectivity          TEXT NOT NULL DEFAULT '',
            approvers            TEXT NOT NULL DEFAULT '',
            decision_date        TEXT,
            verification_ref     TEXT NOT NULL DEFAULT ''
        );
        -- Items an ECN changes: part, assembly, drawing/document, software.
        CREATE TABLE agile_change_items (
            id          INTEGER PRIMARY KEY,
            issue_id    INTEGER NOT NULL REFERENCES agile_issues(id) ON DELETE CASCADE,
            position    INTEGER NOT NULL DEFAULT 0,
            item_type   TEXT NOT NULL,
            item_number TEXT NOT NULL,
            item_title  TEXT NOT NULL DEFAULT '',
            rev_from    TEXT NOT NULL DEFAULT '',
            rev_to      TEXT NOT NULL DEFAULT '',
            disposition TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX idx_agile_change_items_issue ON agile_change_items(issue_id);
    """),
    (6, """
        -- D-B-011: Goldmine = requirements only (own top tab); PR / bugs / ECN
        -- form Agile's "Change Management". Buckets: agile | goldmine | change.
        UPDATE agile_issue_types SET bucket = 'change' WHERE change_role != '';
    """),
    (7, """
        -- D-B-037: Goldmine question & answer register (full traceability).
        -- direction team = question from the team to the client (answer: client);
        -- direction cust = question / concern of the client (answer: the team).
        -- Every step is also an event; nothing is deleted.
        CREATE TABLE goldmine_qa (
            id             INTEGER PRIMARY KEY,
            issue_id       INTEGER NOT NULL REFERENCES agile_issues(id) ON DELETE CASCADE,
            seq            INTEGER NOT NULL,
            direction      TEXT NOT NULL,
            question       TEXT NOT NULL,
            asked_by       INTEGER REFERENCES users(id) ON DELETE SET NULL,
            asked_name     TEXT NOT NULL DEFAULT '',
            asked_at       TEXT NOT NULL,
            asked_stamp    TEXT NOT NULL,
            answer         TEXT NOT NULL DEFAULT '',
            answered_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
            answered_name  TEXT NOT NULL DEFAULT '',
            answered_at    TEXT,
            answered_stamp TEXT NOT NULL DEFAULT '',
            status         TEXT NOT NULL DEFAULT 'open',
            owner_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
            due_date       TEXT,
            blocking       INTEGER NOT NULL DEFAULT 0,
            req_revision   TEXT NOT NULL DEFAULT '',
            closed_stamp   TEXT NOT NULL DEFAULT '',
            updated_at     TEXT NOT NULL
        );
        CREATE INDEX idx_goldmine_qa_issue ON goldmine_qa(issue_id);
        CREATE INDEX idx_goldmine_qa_status ON goldmine_qa(status);
        CREATE TABLE goldmine_qa_events (
            id      INTEGER PRIMARY KEY,
            qa_id   INTEGER NOT NULL REFERENCES goldmine_qa(id) ON DELETE CASCADE,
            kind    TEXT NOT NULL,
            text    TEXT NOT NULL DEFAULT '',
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            name    TEXT NOT NULL DEFAULT '',
            at      TEXT NOT NULL,
            stamp   TEXT NOT NULL
        );
        CREATE INDEX idx_goldmine_qa_events ON goldmine_qa_events(qa_id);
    """),
    (8, """
        -- D-B-039: requirement types created by « Activer Goldmine » after migration 6
        -- kept the default bucket 'agile' and showed on the Agile board / backlog / list.
        UPDATE agile_issue_types SET bucket = 'goldmine' WHERE is_requirement = 1;
    """),
    (9, """
        -- D-B-055: phase of the product life cycle of a requirement (one code, '' = not classified).
        ALTER TABLE agile_requirements ADD COLUMN lifecycle TEXT NOT NULL DEFAULT '';
    """),
    (11, """
        -- D-B-064: stakeholder needs in Goldmine; a requirement names the needs it derives from.
        ALTER TABLE agile_requirements ADD COLUMN kind TEXT NOT NULL DEFAULT 'requirement';
        ALTER TABLE agile_requirements ADD COLUMN stakeholder TEXT NOT NULL DEFAULT '';
        ALTER TABLE agile_requirements ADD COLUMN derived_from TEXT NOT NULL DEFAULT '';
    """),
    (12, """
        -- D-B-079: « Test Procedure » -- the tests of the Testing base that verify the requirement (IDs, comma-separated).
        ALTER TABLE agile_requirements ADD COLUMN test_ref TEXT NOT NULL DEFAULT '';
    """),
    (13, """
        -- D-B-082: product functions (F-XX, central list of the Testing base) of a requirement.
        ALTER TABLE agile_requirements ADD COLUMN functions TEXT NOT NULL DEFAULT '';
    """),
    (14, """
        -- D-B-086: maturity of a need (Need Status).
        ALTER TABLE agile_requirements ADD COLUMN need_status TEXT NOT NULL DEFAULT '';
    """),
]
