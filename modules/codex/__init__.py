"""Generator (key « codex »): document references and filing per project (D-B-021).

Names every document of a project the same way: type (a deliverable of the
product development process -- LCV, CRV, CdCF, PDR / CDR, VVR... (D-O-021) -- or general
engineering), step of the PDP, unique Excel serial date-time number,
revision, system code, title -> file name and deliverables folder. Each
reservation is kept in the project's registry (who, when, never reused).
"""
from .search import search  # noqa: F401  (core lot v0.7 hook)
from . import catalog, registry  # noqa: F401  (catalog is used by tests and tools)

SCHEMA = ""  # tables come from MIGRATIONS

MIGRATIONS = [
    (1, """
        CREATE TABLE codex_refs (
            id           INTEGER PRIMARY KEY,
            project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            reference    TEXT NOT NULL,
            date_serial  INTEGER NOT NULL,
            time_serial  INTEGER NOT NULL,
            doc_type     TEXT NOT NULL,
            pdp_step     TEXT NOT NULL,
            pdp_sub      TEXT NOT NULL DEFAULT '00',
            system_code  TEXT NOT NULL DEFAULT '',
            revision     INTEGER NOT NULL DEFAULT 1,
            title        TEXT NOT NULL DEFAULT '',
            file_name    TEXT NOT NULL,
            svn_path     TEXT NOT NULL,
            folder       TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'active',
            void_reason  TEXT NOT NULL DEFAULT '',
            created_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL,
            UNIQUE (date_serial, time_serial)
        );
        CREATE INDEX idx_codex_refs_project ON codex_refs(project_id, date_serial, time_serial);
    """),
]

P = r"/api/codex/p/(?P<pid>\d+)"

ROUTES = [
    ("GET", r"/api/codex/meta", registry.api_meta, "user"),
    ("GET", P + r"/refs", registry.api_list, "user"),
    ("POST", P + r"/refs", registry.api_reserve, "user"),
    ("PATCH", P + r"/refs/(?P<rid>\d+)", registry.api_update, "user"),
    ("GET", P + r"/export\.csv", registry.api_export_csv, "user"),
]
