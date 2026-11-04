"""Exploration: multi-month planning of the ore extraction (D-B-019).

A simple, abstract Gantt per project -- phases, tasks, predecessors,
durations in weeks, status, owner among the project's members -- prepared
and reviewed in Excel (often with an AI agent), loaded here, then followed
up by the owners. Deliberately not linked to Agile tickets.
"""
from .dashboard import dashboard  # noqa: F401  (core lot v0.10 hook)
from .search import search  # noqa: F401  (core lot v0.7 hook)
from . import plan, transfer

SCHEMA = ""  # tables come from MIGRATIONS

MIGRATIONS = [
    (1, """
        CREATE TABLE exploration_plans (
            project_id INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
            start_date TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE exploration_tasks (
            id             INTEGER PRIMARY KEY,
            project_id     INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            code           TEXT NOT NULL,
            position       INTEGER NOT NULL DEFAULT 0,
            phase          TEXT NOT NULL DEFAULT '',
            title          TEXT NOT NULL,
            description    TEXT NOT NULL DEFAULT '',
            owner_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
            duration_weeks REAL NOT NULL DEFAULT 1,
            start_date     TEXT,
            predecessors   TEXT NOT NULL DEFAULT '',
            status         TEXT NOT NULL DEFAULT 'todo',
            progress       INTEGER NOT NULL DEFAULT 0,
            note           TEXT NOT NULL DEFAULT '',
            updated_by     INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at     TEXT NOT NULL,
            UNIQUE (project_id, code)
        );
        CREATE INDEX idx_exploration_tasks_project ON exploration_tasks(project_id, position);
    """),
    (2, """
        -- D-B-061: automatic task codes (T1, T2...) are never given twice, even after a deletion.
        CREATE TABLE exploration_counters (
            project_id INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
            next_task  INTEGER NOT NULL DEFAULT 1
        );
    """),
]


def on_project_created(ctx, project_id):
    """Core hook (lot v0.5, D-B-012): the plan starts next Monday with a
    kick-off milestone named after the project."""
    name = ctx.conn.execute("SELECT name FROM projects WHERE id = ?", (project_id,)).fetchone()["name"]
    plan.set_start(ctx.conn, project_id, plan.next_monday())
    plan.insert(ctx, project_id, {"code": "J0", "phase": "Lancement", "title": "Lancement — " + name,
                                  "description": "Milestone de départ du plan d'exploration : remplacez ce plan en "
                                                 "important un fichier Excel (voir « Importer »).",
                                  "owner_id": None, "duration_weeks": 0, "start_date": None, "predecessors": "",
                                  "status": "todo", "progress": 0, "note": ""}, 0)


def ensure_space(ctx, project_id):
    """Core hook (lot v0.34, D-B-134): a Space without a plan gets its start date and kick-off milestone."""
    if not ctx.conn.execute("SELECT 1 FROM exploration_plans WHERE project_id = ?", (project_id,)).fetchone() and \
            not ctx.conn.execute("SELECT 1 FROM exploration_tasks WHERE project_id = ?", (project_id,)).fetchone():
        on_project_created(ctx, project_id)


P = r"/api/exploration/p/(?P<pid>\d+)"

ROUTES = [
    ("GET", P + r"/plan", plan.api_plan, "user"),
    ("PUT", P + r"/plan", plan.api_set_start, "user"),
    ("PUT", P + r"/plan/order", plan.api_reorder, "user"),  # D-A-041: edit mode
    ("POST", P + r"/tasks", plan.api_create, "user"),
    ("PATCH", P + r"/tasks/(?P<tid>\d+)", plan.api_update, "user"),
    ("DELETE", P + r"/tasks/(?P<tid>\d+)", plan.api_delete, "user"),
    ("GET", P + r"/export\.xlsx", transfer.api_export_xlsx, "user"),
    ("GET", P + r"/export\.csv", transfer.api_export_csv, "user"),
    ("POST", P + r"/import", transfer.api_import, "user"),
]
