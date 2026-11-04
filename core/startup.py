"""Start-up hooks (core lot v0.7, D-B-022).

Run once when the server starts, after the migrations, in one transaction
per module: a module makes sure the data it needs exists (e.g. Testing
creates the TESTING Space on first launch). Actions
are journalled as the first active administrator.
"""
import logging

from . import db, modules

log = logging.getLogger("dynamite_agile.startup")


class StartupContext:
    """The subset of RequestContext a hook may use."""

    def __init__(self, conn, user, data_dir, config=None):
        self.conn = conn
        self.user = user
        self.data_dir = data_dir
        self.config = config or {}
        self.body = {}
        self.params = {}
        self.query = {}
        self.ip = "startup"


def run(data_dir, config=None):
    try:  # D-B-129: the working copies of the revisions viewed read-only never outlive a start
        from . import baseline_view
        if data_dir:
            baseline_view.drop_copies(data_dir)
    except Exception:
        log.exception("Cleaning of the revision working copies failed")
    for key, hook in modules.startup_hooks():
        try:
            with db.connect() as conn:
                admin = conn.execute("SELECT * FROM users WHERE is_admin = 1 AND is_active = 1 "
                                     "ORDER BY id LIMIT 1").fetchone()
                if admin is None:
                    return
                hook(StartupContext(conn, admin, data_dir, config))
        except Exception:  # a module's start-up must never keep the server down
            log.exception("Start-up hook of module %s failed", key)
    spaces_ready()


def spaces_ready():
    """Core lot v0.34 (D-B-134): every active Space has its structure in every tab (a board and its workflows, the
    requirement type, the wiki home, the plan, the time-sheet settings), whatever its age or how it was made -- so any
    Space chosen as the default opens on a ready, guided empty state everywhere. Each module's ensure_space(ctx, pid)
    is idempotent: it only adds what is missing, never touches content."""
    hooks = modules.space_hooks()
    if not hooks:
        return
    with db.connect() as conn:
        admin = conn.execute("SELECT * FROM users WHERE is_admin = 1 AND is_active = 1 ORDER BY id LIMIT 1").fetchone()
        if admin is None:
            return
        pids = [r["id"] for r in conn.execute("SELECT id FROM projects WHERE is_archived = 0")]
    for pid in pids:
        for key, hook in hooks:
            try:
                with db.connect() as conn:
                    hook(StartupContext(conn, admin, None, None), pid)
            except Exception:
                log.exception("ensure_space of module %s failed for project %s", key, pid)
