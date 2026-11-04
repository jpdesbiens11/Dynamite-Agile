"""Timesheet: multi-user time sheets per project, exported to Excel (D-B-023).

Weekly sheet per person: time ranges (date, project, time code, hours, short
description) on the projects of the database; the time codes are the steps
of the product development process of the course (catalog.py: A-01 … D-21),
the internal codes and the leave of the INT Space, or the Budget Lines of a
funding program -- exported to Excel and Word for the funding organisms.
Submitted, then approved or returned by the approver (the instructor, a
team lead) or an administrator; each project may map to an organism and a
contract number for the export.

Note on D-A-010: timesheet_weeks belongs to a person, not a project; its
time ranges (timesheet_entries) reference projects(id).
"""
from . import budget, budget_xlsx, catalog, copy, export, leave, manage, report_docx, weeks
from .leave import dashboard  # noqa: F401  (core lot v0.10 hook)

SCHEMA = ""  # tables come from MIGRATIONS

MIGRATIONS = [
    (1, """
        CREATE TABLE timesheet_projects (
            project_id   INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
            organism     TEXT NOT NULL DEFAULT '',
            contract_ref TEXT NOT NULL DEFAULT '',
            task_set     TEXT NOT NULL DEFAULT 'pdp',  -- catalog.DEFAULT_SET
            open_to_all  INTEGER NOT NULL DEFAULT 0,
            enabled      INTEGER NOT NULL DEFAULT 1,
            updated_at   TEXT NOT NULL
        );
        CREATE TABLE timesheet_weeks (
            id           INTEGER PRIMARY KEY,
            user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            week_start   TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'draft',
            note         TEXT NOT NULL DEFAULT '',
            submitted_at TEXT,
            decided_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            decided_at   TEXT,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL,
            UNIQUE (user_id, week_start)
        );
        CREATE TABLE timesheet_entries (
            id          INTEGER PRIMARY KEY,
            week_id     INTEGER NOT NULL REFERENCES timesheet_weeks(id) ON DELETE CASCADE,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            work_date   TEXT NOT NULL,
            task_key    TEXT NOT NULL,
            hours       REAL NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );
        CREATE INDEX idx_timesheet_entries_week ON timesheet_entries(week_id, work_date);
        CREATE INDEX idx_timesheet_entries_project ON timesheet_entries(project_id, work_date);
        CREATE INDEX idx_timesheet_weeks_status ON timesheet_weeks(status, week_start);
    """),
    (2, """
        -- D-B-084: financial spaces (task sets) and budget lines, administered in « Spaces et organismes ».
        CREATE TABLE timesheet_budget_sets (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            key        TEXT NOT NULL UNIQUE,
            label      TEXT NOT NULL,
            position   INTEGER NOT NULL DEFAULT 0,
            active     INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE timesheet_budget_lines (
            id         INTEGER PRIMARY KEY,
            set_id     INTEGER NOT NULL REFERENCES timesheet_budget_sets(id) ON DELETE CASCADE,
            code       TEXT NOT NULL UNIQUE,
            label      TEXT NOT NULL,
            claimable  INTEGER NOT NULL DEFAULT 1,
            position   INTEGER NOT NULL DEFAULT 0,
            active     INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """),
]


def on_project_created(ctx, project_id):
    """Core hook (lot v0.5): every new project is open to time sheets, with the time codes of the PDP. The INT
    Space gets the internal codes and the leave, the « Interne » organism, and is open to everyone."""
    key = ctx.conn.execute("SELECT key FROM projects WHERE id = ?", (project_id,)).fetchone()["key"]
    if key == catalog.INTERNAL_KEY:
        manage.save_settings(ctx.conn, project_id, organism=catalog.INTERNAL_ORGANISM, task_set=catalog.INTERNAL_SET,
                             open_to_all=True)
    else:
        manage.save_settings(ctx.conn, project_id)


def ensure_space(ctx, project_id):
    """Core hook (lot v0.34, D-B-134): every Space is open to time sheets (settings row)."""
    if not ctx.conn.execute("SELECT 1 FROM timesheet_projects WHERE project_id = ?", (project_id,)).fetchone():
        on_project_created(ctx, project_id)


def on_startup(ctx):
    """Core hook (lot v0.7): the INT Space, then the codes of the static catalogue on first launch (D-B-084)."""
    manage.ensure_internal_project(ctx)
    budget.seed(ctx.conn)


W = r"/api/timesheet"

ROUTES = [
    ("GET", W + r"/week", weeks.api_week, "user"),
    ("POST", W + r"/week/submit", weeks.api_submit, "user"),
    ("POST", W + r"/week/recall", weeks.api_recall, "user"),
    ("POST", W + r"/entries", weeks.api_create, "user"),
    ("PATCH", W + r"/entries/(?P<eid>\d+)", weeks.api_update, "user"),
    ("DELETE", W + r"/entries/(?P<eid>\d+)", weeks.api_delete, "user"),
    ("POST", W + r"/copy/days", copy.api_copy_days, "user"),
    ("GET", W + r"/copy/weeks", copy.api_recent, "user"),
    ("POST", W + r"/copy/week", copy.api_copy_week, "user"),
    ("GET", W + r"/approvals", manage.api_approvals, "user"),
    ("GET", W + r"/leave", leave.api_balance, "user"),
    ("POST", W + r"/weeks/(?P<wid>\d+)/decision", manage.api_decide, "user"),
    ("GET", W + r"/projects", manage.api_projects, "user"),
    ("PUT", W + r"/projects/(?P<pid>\d+)", manage.api_save_project, "user"),
    ("GET", W + r"/export\.xlsx", export.api_export, "user"),
    ("GET", W + r"/report\.docx", report_docx.api_report, "user"),  # D-A-042
    ("GET", W + r"/budget", budget.api_budget, "user"),
    ("POST", W + r"/budget/sets", budget.api_create_set, "user"),
    ("PATCH", W + r"/budget/sets/(?P<sid>\d+)", budget.api_update_set, "user"),
    ("POST", W + r"/budget/lines", budget.api_create_line, "user"),
    ("PATCH", W + r"/budget/lines/(?P<lid>\d+)", budget.api_update_line, "user"),
    ("DELETE", W + r"/budget/lines/(?P<lid>\d+)", budget.api_delete_line, "user"),
    ("GET", W + r"/budget/export\.xlsx", budget_xlsx.api_export, "user"),  # D-B-101
    ("GET", W + r"/budget/sets/(?P<sid>\d+)/export\.xlsx", budget_xlsx.api_export, "user"),
    ("POST", W + r"/budget/import", budget_xlsx.api_import, "user"),
    ("POST", W + r"/budget/import/(?P<token>[a-f0-9]{32})", budget_xlsx.api_apply, "user"),
]
