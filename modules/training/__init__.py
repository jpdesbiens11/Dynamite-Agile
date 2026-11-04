"""« Training » (D-A-045): training topics (content, reference in the wiki / Help, multiple-choice test in Markdown),
individual training plans by year, workflow with different rights for the employee and his manager (editable by the
administrators), tests graded on the server. Top-bar tab right after Tools; also reached from « Mes objectifs » and
the account menu. Topics live in the TRAINING Space (D-A-010).
"""
from . import catalog, plan

SCHEMA = ""

MIGRATIONS = [
    (1, """
        CREATE TABLE training_topics (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            parent_id  INTEGER REFERENCES training_topics(id) ON DELETE SET NULL,
            code       TEXT NOT NULL DEFAULT '',
            title      TEXT NOT NULL,
            content    TEXT NOT NULL DEFAULT '',
            reference  TEXT NOT NULL DEFAULT '',
            ref_label  TEXT NOT NULL DEFAULT '',
            quiz_md    TEXT NOT NULL DEFAULT '',
            position   INTEGER NOT NULL DEFAULT 0,
            active     INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE training_items (
            id            INTEGER PRIMARY KEY,
            topic_id      INTEGER NOT NULL REFERENCES training_topics(id) ON DELETE CASCADE,
            user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            year          INTEGER NOT NULL,
            status        TEXT NOT NULL DEFAULT 'todo',
            due_date      TEXT,
            note          TEXT NOT NULL DEFAULT '',
            manager_eval  TEXT NOT NULL DEFAULT '',
            quiz_score    INTEGER,
            quiz_passed   INTEGER NOT NULL DEFAULT 0,
            quiz_attempts INTEGER NOT NULL DEFAULT 0,
            completed_at  TEXT,
            achieved_at   TEXT,
            achieved_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL,
            UNIQUE (topic_id, user_id, year)
        );
        CREATE TABLE training_attempts (
            id          INTEGER PRIMARY KEY,
            item_id     INTEGER NOT NULL REFERENCES training_items(id) ON DELETE CASCADE,
            score       INTEGER NOT NULL,
            right_count INTEGER NOT NULL,
            total       INTEGER NOT NULL,
            answers     TEXT NOT NULL DEFAULT '{}',
            created_at  TEXT NOT NULL
        );
        CREATE INDEX idx_training_items_user ON training_items(user_id, year);
    """),
    # 0.50.10 (D-B-128): circle-back of the missed questions; additive only.
    (2, """
        ALTER TABLE training_items ADD COLUMN quiz_pending TEXT NOT NULL DEFAULT '';
        ALTER TABLE training_attempts ADD COLUMN round INTEGER NOT NULL DEFAULT 0;
    """),
]

T = r"/api/training"
ROUTES = [
    ("GET", T + r"/topics", plan.api_topics, "user"),
    ("POST", T + r"/topics", plan.api_create_topic, "user"),
    ("PATCH", T + r"/topics/(?P<tid>\d+)", plan.api_update_topic, "user"),
    ("POST", T + r"/quiz-check", plan.api_check_quiz, "user"),
    ("GET", T + r"/workflow", plan.api_workflow, "user"),
    ("PUT", T + r"/workflow", plan.api_save_workflow, "user"),
    ("GET", T + r"/people", plan.api_people, "user"),
    ("GET", T + r"/plan/(?P<uid>\d+)", plan.api_plan, "user"),
    ("POST", T + r"/plan/(?P<uid>\d+)/items", plan.api_add, "user"),
    ("PATCH", T + r"/items/(?P<iid>\d+)", plan.api_update, "user"),
    ("DELETE", T + r"/items/(?P<iid>\d+)", plan.api_delete, "user"),
    ("GET", T + r"/items/(?P<iid>\d+)/quiz", plan.api_quiz, "user"),
    ("POST", T + r"/items/(?P<iid>\d+)/quiz", plan.api_answer, "user"),
]


def on_startup(ctx):
    catalog.ensure(ctx)


def review_items(conn, user_id, year):
    """Core lot v0.30 (D-B-111): the training plan of the year joins the annual review, item by item."""
    rows = conn.execute("SELECT i.id, i.status, t.code, t.title FROM training_items i JOIN training_topics t ON t.id = i.topic_id "
                        "WHERE i.user_id = ? AND i.year = ? ORDER BY t.position, i.id", (user_id, year)).fetchall()
    return [{"id": r["id"], "title": ((r["code"] + " — ") if r["code"] else "") + r["title"],
             "status": catalog.STATUSES.get(r["status"], r["status"])} for r in rows]
