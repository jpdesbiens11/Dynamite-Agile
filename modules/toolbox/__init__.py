"""« Tools » (D-B-065, sections D-B-073): top tab in place of Generator, in
two sections -- Design (divergent: « Idéation » sessions, ideation.py, with
brainwriting in rotating pairs and a mind map; convergent: Pugh Matrix,
modules/agile/pugh.py, and Kepner-Tregoe, kt.py) and Generator (modules/codex).
Every method has a wiki page and a FAQ in the Dynamite space TOOLS
(catalog.py), created at start-up.
"""
from . import catalog, ideation, kt
from .search import search  # noqa: F401  (core search hook, D-B-076)

SCHEMA = ""

MIGRATIONS = [
    (1, """
        CREATE TABLE tools_ideation (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            title      TEXT NOT NULL,
            method     TEXT NOT NULL DEFAULT 'brainstorming',
            prompt     TEXT NOT NULL DEFAULT '',
            status     TEXT NOT NULL DEFAULT 'open',
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE tools_ideas (
            id              INTEGER PRIMARY KEY,
            session_id      INTEGER NOT NULL REFERENCES tools_ideation(id) ON DELETE CASCADE,
            text            TEXT NOT NULL,
            tag             TEXT NOT NULL DEFAULT '',
            round           INTEGER,
            parent_id       INTEGER REFERENCES tools_ideas(id) ON DELETE SET NULL,
            author_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
            author_initials TEXT NOT NULL DEFAULT '',
            created_at      TEXT NOT NULL
        );
        CREATE TABLE tools_idea_votes (
            idea_id INTEGER NOT NULL REFERENCES tools_ideas(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY (idea_id, user_id)
        );
        CREATE TABLE tools_kt (
            id              INTEGER PRIMARY KEY,
            project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            title           TEXT NOT NULL,
            statement       TEXT NOT NULL DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'draft',
            decision_alt_id INTEGER,
            decision_note   TEXT NOT NULL DEFAULT '',
            created_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at      TEXT NOT NULL,
            updated_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at      TEXT NOT NULL
        );
        CREATE TABLE tools_kt_criteria (
            id       INTEGER PRIMARY KEY,
            kt_id    INTEGER NOT NULL REFERENCES tools_kt(id) ON DELETE CASCADE,
            kind     TEXT NOT NULL CHECK (kind IN ('must', 'want')),
            text     TEXT NOT NULL,
            weight   INTEGER NOT NULL DEFAULT 0,
            issue_id INTEGER REFERENCES agile_issues(id) ON DELETE SET NULL,
            position INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE tools_kt_alts (
            id          INTEGER PRIMARY KEY,
            kt_id       INTEGER NOT NULL REFERENCES tools_kt(id) ON DELETE CASCADE,
            name        TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            position    INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE tools_kt_scores (
            criterion_id INTEGER NOT NULL REFERENCES tools_kt_criteria(id) ON DELETE CASCADE,
            alt_id       INTEGER NOT NULL REFERENCES tools_kt_alts(id) ON DELETE CASCADE,
            value        INTEGER NOT NULL,
            note         TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (criterion_id, alt_id)
        );
        CREATE TABLE tools_kt_risks (
            id          INTEGER PRIMARY KEY,
            kt_id       INTEGER NOT NULL REFERENCES tools_kt(id) ON DELETE CASCADE,
            alt_id      INTEGER NOT NULL REFERENCES tools_kt_alts(id) ON DELETE CASCADE,
            text        TEXT NOT NULL,
            probability INTEGER NOT NULL,
            seriousness INTEGER NOT NULL
        );
        CREATE INDEX idx_tools_ideation_project ON tools_ideation(project_id);
        CREATE INDEX idx_tools_kt_project ON tools_kt(project_id);
    """),
    (2, """
        ALTER TABLE tools_ideation ADD COLUMN round_minutes INTEGER NOT NULL DEFAULT 5;
        ALTER TABLE tools_ideation ADD COLUMN rounds INTEGER NOT NULL DEFAULT 6;
        ALTER TABLE tools_ideation ADD COLUMN ideas_per_round INTEGER NOT NULL DEFAULT 3;
        ALTER TABLE tools_ideation ADD COLUMN phase TEXT NOT NULL DEFAULT 'setup';
        ALTER TABLE tools_ideation ADD COLUMN started_at TEXT;
        ALTER TABLE tools_ideas ADD COLUMN pos_x REAL;
        ALTER TABLE tools_ideas ADD COLUMN pos_y REAL;
        ALTER TABLE tools_ideas ADD COLUMN impact TEXT NOT NULL DEFAULT '';
        ALTER TABLE tools_ideas ADD COLUMN feasibility TEXT NOT NULL DEFAULT '';
        CREATE TABLE tools_ideation_people (
            session_id INTEGER NOT NULL REFERENCES tools_ideation(id) ON DELETE CASCADE,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            position   INTEGER NOT NULL DEFAULT 0,
            joined_at  TEXT NOT NULL,
            PRIMARY KEY (session_id, user_id)
        );
        CREATE TABLE tools_idea_stars (
            idea_id INTEGER NOT NULL REFERENCES tools_ideas(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY (idea_id, user_id)
        );
        CREATE TABLE tools_idea_links (
            id         INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES tools_ideation(id) ON DELETE CASCADE,
            a_id       INTEGER NOT NULL REFERENCES tools_ideas(id) ON DELETE CASCADE,
            b_id       INTEGER REFERENCES tools_ideas(id) ON DELETE CASCADE,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX idx_tools_idea_links_session ON tools_idea_links(session_id);
        INSERT OR IGNORE INTO tools_idea_stars (idea_id, user_id) SELECT idea_id, user_id FROM tools_idea_votes;
        UPDATE tools_ideation SET phase = 'review'
         WHERE method = 'brainwriting' AND EXISTS (SELECT 1 FROM tools_ideas WHERE session_id = tools_ideation.id);
    """),
]


def on_startup(ctx):
    """Core hook (lot v0.7): the TOOLS wiki space and its method pages exist from the first launch."""
    catalog.ensure(ctx)


def on_restore(conn, maps, old_key, new_key):
    """The KT decision points to an alternative by id (not a foreign key)."""
    alts = maps.get("tools_kt_alts", {})
    for new_id in maps.get("tools_kt", {}).values():
        row = conn.execute("SELECT decision_alt_id FROM tools_kt WHERE id = ?", (new_id,)).fetchone()
        if row and row["decision_alt_id"]:
            conn.execute("UPDATE tools_kt SET decision_alt_id = ? WHERE id = ?", (alts.get(row["decision_alt_id"]), new_id))


P = r"/api/tools/p/(?P<pid>\d+)"
S = P + r"/ideation/(?P<sid>\d+)"
K = P + r"/kt/(?P<kid>\d+)"

ROUTES = [
    ("GET", r"/api/tools/catalog", catalog.api_catalog, "user"),
    ("GET", P + r"/ideation", ideation.api_list, "user"),
    ("POST", P + r"/ideation", ideation.api_create, "user"),
    ("GET", S, ideation.api_get, "user"),
    ("PATCH", S, ideation.api_update, "user"),
    ("POST", S + r"/ideas", ideation.api_add_idea, "user"),
    ("PATCH", S + r"/ideas/(?P<iid>\d+)", ideation.api_update_idea, "user"),
    ("POST", S + r"/ideas/(?P<iid>\d+)/star", ideation.api_star, "user"),
    ("POST", S + r"/brainwriting", ideation.api_brainwriting, "user"),
    ("POST", S + r"/links", ideation.api_link, "user"),
    ("DELETE", S + r"/links/(?P<lid>\d+)", ideation.api_unlink, "user"),
    ("GET", S + r"/export\.csv", ideation.api_export, "user"),
    ("GET", P + r"/kt", kt.api_list, "user"),
    ("POST", P + r"/kt", kt.api_create, "user"),
    ("GET", K, kt.api_get, "user"),
    ("PATCH", K, kt.api_update, "user"),
    ("POST", K + r"/criteria", kt.api_criterion, "user"),
    ("PATCH", K + r"/criteria/(?P<cid>\d+)", kt.api_criterion, "user"),
    ("POST", K + r"/alts", kt.api_alt, "user"),
    ("PATCH", K + r"/alts/(?P<aid>\d+)", kt.api_alt, "user"),
    ("PUT", K + r"/score", kt.api_score, "user"),
    ("POST", K + r"/risks", kt.api_risk, "user"),
    ("PATCH", K + r"/risks/(?P<rid>\d+)", kt.api_risk, "user"),
]
