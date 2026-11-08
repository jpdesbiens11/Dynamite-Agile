"""« Testing » (D-B-079): the test team's portal, top tab right after Goldmine.

One base of possible tests (testing_tests) for the whole tool: tests of the
standards of a consumer mechatronic product (electrical safety, EMC, IP, drop,
life...), usual industry tests and the team's custom tests, each with its
draft procedure page in the Dynamite space TESTING (catalog.py). Every Goldmine
requirement names its tests in « Test Procedure » (modules/agile/goldmine.py
calls catalog.check_refs), and each test record lists the requirements that
cite it.
"""
from . import bundles, catalog, docx_tests, evidence, lists, plans, results_docx, review, tests_api, verification
from .search import search  # noqa: F401  (core search hook, D-B-076)
from .evidence import on_restore  # noqa: F401  (core lot v0.10 hook; 0.60.94, D-O-100)

SCHEMA = ""

MIGRATIONS = [
    (1, """
        CREATE TABLE testing_tests (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            test_id    TEXT NOT NULL UNIQUE,
            title      TEXT NOT NULL,
            subject    TEXT NOT NULL,
            category   TEXT NOT NULL DEFAULT 'custom',
            standard   TEXT NOT NULL DEFAULT '',
            section    TEXT NOT NULL DEFAULT '',
            level      TEXT NOT NULL DEFAULT '',
            method     TEXT NOT NULL DEFAULT 'T',
            objective  TEXT NOT NULL DEFAULT '',
            acceptance TEXT NOT NULL DEFAULT '',
            means      TEXT NOT NULL DEFAULT '',
            notes      TEXT NOT NULL DEFAULT '',
            status     TEXT NOT NULL DEFAULT 'Draft',
            origin     TEXT NOT NULL DEFAULT 'user',
            edited     INTEGER NOT NULL DEFAULT 0,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE testing_history (
            id          INTEGER PRIMARY KEY,
            test_row_id INTEGER NOT NULL REFERENCES testing_tests(id) ON DELETE CASCADE,
            user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
            field       TEXT NOT NULL,
            old_value   TEXT,
            new_value   TEXT,
            at          TEXT NOT NULL
        );
        CREATE INDEX idx_testing_tests_project ON testing_tests(project_id);
        CREATE INDEX idx_testing_history_test ON testing_history(test_row_id);
    """),
    (2, """
        -- D-B-082: controlled lists (equipment, locations, product functions) and their use on the tests.
        CREATE TABLE testing_lists (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            kind       TEXT NOT NULL,
            code       TEXT NOT NULL,
            label      TEXT NOT NULL,
            category   TEXT NOT NULL DEFAULT '',
            details    TEXT NOT NULL DEFAULT '',
            position   INTEGER NOT NULL DEFAULT 0,
            active     INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (kind, code)
        );
        ALTER TABLE testing_tests ADD COLUMN location TEXT NOT NULL DEFAULT '';
        ALTER TABLE testing_tests ADD COLUMN equipment TEXT NOT NULL DEFAULT '';
        ALTER TABLE testing_tests ADD COLUMN functions TEXT NOT NULL DEFAULT '';
    """),
]


def on_startup(ctx):
    """Core hook (lot v0.7): the TESTING space, its test base and draft procedures exist from the first launch."""
    catalog.ensure(ctx)


T = r"/api/testing/tests/(?P<tid>[A-Za-z0-9-]{2,40})"

MIGRATIONS.append((3, """
    CREATE TABLE testing_plans (
        id           INTEGER PRIMARY KEY,
        project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        code         TEXT NOT NULL UNIQUE,
        title        TEXT NOT NULL,
        location     TEXT NOT NULL,
        tests        TEXT NOT NULL DEFAULT '[]',
        purpose      TEXT NOT NULL DEFAULT '',
        docno        TEXT NOT NULL DEFAULT '',
        rev          TEXT NOT NULL DEFAULT 'A',
        status       TEXT NOT NULL DEFAULT 'draft',
        results_id   INTEGER REFERENCES attachments(id) ON DELETE SET NULL,
        results_name TEXT NOT NULL DEFAULT '',
        created_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at   TEXT NOT NULL,
        updated_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
        updated_at   TEXT NOT NULL,
        sent_at      TEXT,
        closed_at    TEXT,
        closed_by    INTEGER REFERENCES users(id) ON DELETE SET NULL
    );
"""))  # D-A-048: test plans for an external supplier

MIGRATIONS.append((4, """
    -- D-B-097: one Test Base per Space -- a test ID is unique within its Space, no longer on the whole platform.
    -- The table is rebuilt (same ids, same rows); its history is kept aside then put back (SQLite cannot drop a
    -- UNIQUE constraint, and dropping a table its children reference would cascade).
    CREATE TABLE testing_tests_v4 (
        id         INTEGER PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        test_id    TEXT NOT NULL,
        title      TEXT NOT NULL,
        subject    TEXT NOT NULL,
        category   TEXT NOT NULL DEFAULT 'custom',
        standard   TEXT NOT NULL DEFAULT '',
        section    TEXT NOT NULL DEFAULT '',
        level      TEXT NOT NULL DEFAULT '',
        method     TEXT NOT NULL DEFAULT 'T',
        objective  TEXT NOT NULL DEFAULT '',
        acceptance TEXT NOT NULL DEFAULT '',
        means      TEXT NOT NULL DEFAULT '',
        notes      TEXT NOT NULL DEFAULT '',
        status     TEXT NOT NULL DEFAULT 'Draft',
        origin     TEXT NOT NULL DEFAULT 'user',
        edited     INTEGER NOT NULL DEFAULT 0,
        created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at TEXT NOT NULL,
        updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        updated_at TEXT NOT NULL,
        location   TEXT NOT NULL DEFAULT '',
        equipment  TEXT NOT NULL DEFAULT '',
        functions  TEXT NOT NULL DEFAULT '',
        UNIQUE (project_id, test_id)
    );
    INSERT INTO testing_tests_v4 (id, project_id, test_id, title, subject, category, standard, section, level, method,
        objective, acceptance, means, notes, status, origin, edited, created_by, created_at, updated_by, updated_at,
        location, equipment, functions)
    SELECT id, project_id, test_id, title, subject, category, standard, section, level, method, objective, acceptance,
        means, notes, status, origin, edited, created_by, created_at, updated_by, updated_at, location, equipment, functions
    FROM testing_tests;
    CREATE TABLE testing_history_keep AS SELECT * FROM testing_history;
    DROP TABLE testing_history;
    DROP TABLE testing_tests;
    ALTER TABLE testing_tests_v4 RENAME TO testing_tests;
    CREATE TABLE testing_history (
        id          INTEGER PRIMARY KEY,
        test_row_id INTEGER NOT NULL REFERENCES testing_tests(id) ON DELETE CASCADE,
        user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
        field       TEXT NOT NULL,
        old_value   TEXT,
        new_value   TEXT,
        at          TEXT NOT NULL
    );
    INSERT INTO testing_history SELECT * FROM testing_history_keep;
    DROP TABLE testing_history_keep;
    CREATE INDEX idx_testing_tests_project ON testing_tests(project_id);
    CREATE INDEX idx_testing_history_test ON testing_history(test_row_id);
"""))
MIGRATIONS.append((5, """
    -- 0.60.06 (D-O-019): review of a test proposed by an AI assistant (Project Starter): '' | 'to_verify' | 'verified';
    -- review_checked keeps who confirmed it, when, and the edition of its standard.
    ALTER TABLE testing_tests ADD COLUMN review TEXT NOT NULL DEFAULT '';
    ALTER TABLE testing_tests ADD COLUMN review_checked TEXT NOT NULL DEFAULT '';
"""))

MIGRATIONS.append((6, """
    -- 0.60.90 (D-O-096): one bundle per prototype actually tested, a result per test, evidence files in bulk on the plan.
    CREATE TABLE testing_bundles (
        id         INTEGER PRIMARY KEY,
        plan_id    INTEGER NOT NULL REFERENCES testing_plans(id) ON DELETE CASCADE,
        proto      TEXT NOT NULL,
        serial     TEXT NOT NULL DEFAULT '',
        note       TEXT NOT NULL DEFAULT '',
        created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (plan_id, proto)
    );
    CREATE TABLE testing_evidence (
        id            INTEGER PRIMARY KEY,
        plan_id       INTEGER NOT NULL REFERENCES testing_plans(id) ON DELETE CASCADE,
        attachment_id INTEGER NOT NULL REFERENCES attachments(id),
        name          TEXT NOT NULL,
        note          TEXT NOT NULL DEFAULT '',
        bundle_id     INTEGER REFERENCES testing_bundles(id) ON DELETE SET NULL,
        created_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at    TEXT NOT NULL
    );
    CREATE TABLE testing_results (
        id         INTEGER PRIMARY KEY,
        bundle_id  INTEGER NOT NULL REFERENCES testing_bundles(id) ON DELETE CASCADE,
        test_id    TEXT NOT NULL,
        result     TEXT NOT NULL DEFAULT '',
        note       TEXT NOT NULL DEFAULT '',
        evidence   TEXT NOT NULL DEFAULT '[]',
        updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (bundle_id, test_id)
    );
    CREATE INDEX idx_testing_bundles_plan ON testing_bundles(plan_id);
    CREATE INDEX idx_testing_evidence_plan ON testing_evidence(plan_id);
"""))
MIGRATIONS.append((7, """
    -- 0.60.94 (D-O-100): an evidence is a file on the server (any type, 150 Mo at most) or, beyond that, a reference to
    -- where it lies on the network (kind 'link': no attachment). A newer version from the supplier replaces the file under
    -- the same id, so the results that cite it keep it; the previous versions stay in history (JSON). The table is
    -- rebuilt (SQLite cannot drop NOT NULL on attachment_id); no other table references it.
    CREATE TABLE testing_evidence_v7 (
        id            INTEGER PRIMARY KEY,
        plan_id       INTEGER NOT NULL REFERENCES testing_plans(id) ON DELETE CASCADE,
        attachment_id INTEGER REFERENCES attachments(id),
        name          TEXT NOT NULL,
        note          TEXT NOT NULL DEFAULT '',
        bundle_id     INTEGER REFERENCES testing_bundles(id) ON DELETE SET NULL,
        created_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at    TEXT NOT NULL,
        kind          TEXT NOT NULL DEFAULT 'file',
        link          TEXT NOT NULL DEFAULT '',
        link_size     INTEGER,
        version       INTEGER NOT NULL DEFAULT 1,
        history       TEXT NOT NULL DEFAULT '[]',
        updated_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
        updated_at    TEXT
    );
    INSERT INTO testing_evidence_v7 (id, plan_id, attachment_id, name, note, bundle_id, created_by, created_at)
    SELECT id, plan_id, attachment_id, name, note, bundle_id, created_by, created_at FROM testing_evidence;
    DROP TABLE testing_evidence;
    ALTER TABLE testing_evidence_v7 RENAME TO testing_evidence;
    CREATE INDEX idx_testing_evidence_plan ON testing_evidence(plan_id);
"""))

TP = r"/api/testing/plans/(?P<code>TP-\d{3,})"
ROUTES = [
    ("GET", r"/api/testing/plans", plans.api_list, "user"),
    ("POST", r"/api/testing/plans", plans.api_create, "user"),
    ("GET", TP, plans.api_get, "user"),
    ("PATCH", TP, plans.api_update, "user"),
    ("POST", TP + r"/status", plans.api_status, "user"),
    ("POST", TP + r"/results", plans.api_results, "user"),
    ("GET", TP + r"/results\.pdf", plans.api_results_file, "user"),
    ("GET", TP + r"/plan\.docx", plans.api_docx, "user"),
    ("GET", TP + r"/results-summary\.docx", results_docx.api_results_docx, "user"),  # 0.60.92 (D-O-098)
    ("POST", TP + r"/bundles", bundles.api_bundle_create, "user"),  # 0.60.90 (D-O-096)
    ("PATCH", TP + r"/bundles/(?P<bid>\d+)", bundles.api_bundle_update, "user"),
    ("DELETE", TP + r"/bundles/(?P<bid>\d+)", bundles.api_bundle_delete, "user"),
    ("PUT", TP + r"/bundles/(?P<bid>\d+)/results/(?P<tid>[A-Za-z0-9-]{2,40})", bundles.api_result, "user"),
    ("POST", TP + r"/evidence", evidence.api_add, "user"),
    ("PATCH", TP + r"/evidence/(?P<eid>\d+)", evidence.api_update, "user"),
    ("DELETE", TP + r"/evidence/(?P<eid>\d+)", evidence.api_delete, "user"),
    ("POST", TP + r"/evidence/link", evidence.api_link_add, "user"),  # 0.60.94 (D-O-100)
    ("POST", TP + r"/evidence/(?P<eid>\d+)/replace", evidence.api_replace, "user"),
    ("POST", TP + r"/evidence/(?P<eid>\d+)/link", evidence.api_link_replace, "user"),
    ("GET", TP + r"/evidence/(?P<eid>\d+)/file", evidence.api_file, "user"),
    ("GET", r"/api/testing/verification", verification.api_verification, "user"),  # 0.60.91 (D-O-097)
    ("GET", r"/api/testing/tests", tests_api.api_list, "user"),
    ("GET", r"/api/testing/options", tests_api.api_options, "user"),
    ("GET", r"/api/testing/export\.csv", tests_api.api_export, "user"),
    ("GET", r"/api/testing/export\.docx", docx_tests.api_export, "user"),
    ("GET", r"/api/testing/lists", lists.api_lists, "user"),
    ("POST", r"/api/testing/lists", lists.api_create, "user"),
    ("PATCH", r"/api/testing/lists/(?P<lid>\d+)", lists.api_update, "user"),
    ("POST", r"/api/testing/import", tests_api.api_import, "user"),
    ("POST", r"/api/testing/tests", tests_api.api_create, "user"),
    ("GET", T, tests_api.api_get, "user"),
    ("PATCH", T, tests_api.api_update, "user"),
    ("POST", T + r"/review", review.api_review, "user"),  # 0.60.07 (D-O-019)
]
