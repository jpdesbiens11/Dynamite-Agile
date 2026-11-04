"""Dynamite: Confluence-like wiki, one space per project (docs/DYNAMITE_ARCHITECTURE.md).

Increment 1: page tree, versions with restore, edit lock, JSON page bodies
(D-A-035) and the live "Ticket Agile" block (D-A-036). Every route is
declared "user"; each handler checks the project role itself.
"""
from .search import search  # noqa: F401  (core lot v0.7 hook)
from . import comments, export, images, pages, templates, transfer
from .restore import on_restore  # noqa: F401  (core lot v0.10 hook)

SCHEMA = ""  # frozen since the placeholder release: tables come from MIGRATIONS (D-A-020)

MIGRATIONS = [
    (1, """
        CREATE TABLE dynamite_pages (
            id              INTEGER PRIMARY KEY,
            project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            parent_id       INTEGER REFERENCES dynamite_pages(id) ON DELETE RESTRICT,
            title           TEXT NOT NULL,
            position        INTEGER NOT NULL DEFAULT 0,
            current_version INTEGER NOT NULL DEFAULT 1,
            created_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at      TEXT NOT NULL,
            updated_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at      TEXT NOT NULL,
            lock_by         INTEGER REFERENCES users(id) ON DELETE SET NULL,
            lock_until      TEXT
        );
        CREATE INDEX idx_dynamite_pages_tree ON dynamite_pages(project_id, parent_id, position);
        CREATE TABLE dynamite_versions (
            id         INTEGER PRIMARY KEY,
            page_id    INTEGER NOT NULL REFERENCES dynamite_pages(id) ON DELETE CASCADE,
            version    INTEGER NOT NULL,
            title      TEXT NOT NULL,
            body       TEXT NOT NULL,
            author_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            note       TEXT NOT NULL DEFAULT '',
            UNIQUE (page_id, version)
        );
    """),
    (2, """
        -- Page comments (D-B-002): threaded, plain text, tied to the page
        -- version they were written against.
        CREATE TABLE dynamite_comments (
            id                INTEGER PRIMARY KEY,
            page_id           INTEGER NOT NULL REFERENCES dynamite_pages(id) ON DELETE CASCADE,
            parent_comment_id INTEGER REFERENCES dynamite_comments(id) ON DELETE CASCADE,
            author_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
            page_version      INTEGER NOT NULL,
            body              TEXT NOT NULL,
            created_at        TEXT NOT NULL
        );
        CREATE INDEX idx_dynamite_comments_page ON dynamite_comments(page_id);
    """),
]

def on_project_created(ctx, project_id):
    """Core hook (lot v0.5, D-B-012): the space opens on a home page named
    after the project, built from the base template."""
    templates.create_home(ctx, project_id)


def ensure_space(ctx, project_id):
    """Core hook (lot v0.34, D-B-134): a Space without any page gets its home page."""
    if not ctx.conn.execute("SELECT 1 FROM dynamite_pages WHERE project_id = ?", (project_id,)).fetchone():
        templates.create_home(ctx, project_id)


P = r"/api/dynamite/p/(?P<pid>\d+)"
PG = P + r"/pages/(?P<page>\d+)"

ROUTES = [
    ("GET", P + r"/pages", pages.api_tree, "user"),
    ("POST", P + r"/pages", pages.api_create, "user"),
    ("GET", PG, pages.api_get, "user"),
    ("PUT", PG, pages.api_save, "user"),
    ("DELETE", PG, pages.api_delete, "user"),
    ("PATCH", PG + r"/move", pages.api_move, "user"),
    ("POST", PG + r"/transfer", transfer.api_transfer, "user"),
    ("GET", PG + r"/export\.(?P<fmt>docx|pdf)", export.api_export, "user"),
    ("POST", PG + r"/lock", pages.api_lock, "user"),
    ("DELETE", PG + r"/lock", pages.api_unlock, "user"),
    ("GET", PG + r"/versions", pages.api_versions, "user"),
    ("GET", PG + r"/versions/(?P<ver>\d+)", pages.api_version, "user"),
    ("POST", PG + r"/versions/(?P<ver>\d+)/restore", pages.api_restore, "user"),
    ("GET", PG + r"/comments", comments.api_list, "user"),
    ("POST", PG + r"/comments", comments.api_add, "user"),
    ("DELETE", PG + r"/comments/(?P<cid>\d+)", comments.api_delete, "user"),
    ("POST", P + r"/images", images.api_upload, "user"),
    ("GET", r"/api/dynamite/image/(?P<id>\d+)", images.api_get, "user"),
    ("GET", r"/api/dynamite/ticket/(?P<key>[A-Za-z0-9-]{3,30})", pages.api_ticket, "user"),
]
