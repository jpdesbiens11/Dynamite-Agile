"""The reference Space (0.60.41, D-O-050): every Space is a closed product environment ("vase clos"); the only common
Space is DEMO -- the sandbox, which is also the library of reference content (the generic Test Base, its procedures
and central lists, the design-method pages of Tools, the Training topics, the time-code sets). A Space copies what it
needs from there once, then lives on its own.

An installation made before 0.60.41 keeps its Spaces TESTING, TOOLS, TRAINING and INT (nothing is deleted): while such a
Space exists, its content stays where it is. A fresh installation creates none of them -- only DEMO.
"""
KEY = "DEMO"


def _pid(conn, key):
    try:
        row = conn.execute("SELECT id FROM projects WHERE key = ?", (key,)).fetchone()
    except Exception:  # before the core tables (tests of old lots)
        return None
    return row["id"] if row else None


def space(conn, legacy_key=None):
    """The Space that holds this reference content: the legacy Space when the installation still has it, else DEMO."""
    if legacy_key:
        pid = _pid(conn, legacy_key)
        if pid is not None:
            return pid
    return _pid(conn, KEY) or _pid(conn, "HEADLAMP")  # 0.60.49 (D-O-058): HEADLAMP until the start-up renames it


def ensure(ctx, legacy_key=None):
    """Same, creating DEMO (with its sandbox content) when it does not exist yet."""
    pid = space(ctx.conn, legacy_key)
    if pid is None:
        from . import headlamp
        pid = headlamp.ensure_space(ctx)
    return pid


def is_reference(conn, project_id):
    return project_id is not None and project_id == space(conn)
