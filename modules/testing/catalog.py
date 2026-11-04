"""Testing space and catalogue (D-B-079).

At start-up: the Dynamite space TESTING exists, every test of data_tests.TESTS
is in testing_tests (a catalogue test nobody edited follows the code), and
every draft procedure page exists (one per subject, under a hub page). A page
still in its generated form is refreshed when the catalogue changes; a page
someone edited is never touched. Every active account is an editor of TESTING
(the test team can narrow that in Admin → Spaces).

Goldmine calls check_refs() so that a requirement always names at least one
test of this base (« Test Procedure »).

D-B-097 (0.50.0): one Test Base per Space. The tests of the Space TESTING are the reference catalogue; a Space gets
its own copy of it (same IDs, then edited on its own) the first time its base is needed -- Testing opened on that
Space, a requirement citing a test, a Space copied from another one. A copied catalogue test nobody edited keeps
following the code like the reference. Central lists and the procedure pages (wiki TESTING) stay shared.
"""
import re

from core import admin, db
from core.errors import ApiError

from modules.help.gtd import _b, _ol, _ul
from modules.help.headlamp import _doc, _h, _link, _p, _panel, _table

from .data_procedures import COMMON_RECORDS, COVERS, PROCEDURES
from . import lists
from .data_lists import defaults
from .data_tests import CATEGORIES, SUBJECTS, TESTS

KEY = "TESTING"
NAME = "Testing — Test Base and Test Procedures"
DESCRIPTION = ("Portail de l'équipe de tests : base des tests possibles (sécurité électrique, CEM, IP, chute, durée de vie…, "
               "industry practice, custom tests) et Test Procedures liées aux requirements Goldmine.")
HUB = "Testing — Test Procedures"
GENERATED = "Généré — catalogue Testing"  # version note, kept as is (it identifies generated pages)
OLD_NOTES = ("", "Création", "Modèle de base du projet")
FIELDS = ("title", "subject", "category", "standard", "section", "level", "method", "objective", "acceptance",
          "location", "equipment", "functions")
ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+){1,4}$")


def project_id(conn):
    row = conn.execute("SELECT id FROM projects WHERE key = ?", (KEY,)).fetchone()
    return row["id"] if row else None


def procedure_title(code, subject):
    return "{} — {}".format(code, SUBJECTS.get(subject, subject))


PROCEDURE_OF = {subject: code for code, subject, *_ in PROCEDURES}


# --------------------------------------------------------------------------
# Lookups used by Goldmine (« Test Procedure », D-B-079)
# --------------------------------------------------------------------------
def split_refs(value):
    """'tst-160-08; TST-UN-T1' -> ['TST-160-08', 'TST-UN-T1'] (order kept, no duplicates)."""
    out = []
    for part in re.split(r"[\s,;]+", str(value or "").upper()):
        if part and part not in out:
            out.append(part)
    return out


COPY_COLS = ("test_id", "title", "subject", "category", "standard", "section", "level", "method", "objective",
             "acceptance", "means", "notes", "status", "origin", "edited", "location", "equipment", "functions")


def copy_base(conn, source_pid, target_pid, user_id=None):
    """Copy every test of a Space's base into another Space (the target must have none). Returns the count."""
    now = db.utc_now()
    count = 0
    for r in conn.execute("SELECT * FROM testing_tests WHERE project_id = ? ORDER BY id", (source_pid,)).fetchall():
        conn.execute("INSERT INTO testing_tests (project_id, {cols}, created_by, created_at, updated_by, updated_at) "
                     "VALUES (?, {marks}, ?, ?, ?, ?)".format(cols=", ".join(COPY_COLS), marks=", ".join("?" for _ in COPY_COLS)),
                     (target_pid,) + tuple(r[c] for c in COPY_COLS) + (user_id, now, user_id, now))
        count += 1
    return count


def base(conn, project_id, user_id=None):
    """The Space whose base serves `project_id`: the Space itself, its base copied from the catalogue the first time
    (D-B-097). None project_id -> the reference catalogue."""
    ref = project_id_safe(conn)
    if project_id is None or ref is None or project_id == ref:
        return ref
    try:
        if conn.execute("SELECT 1 FROM testing_tests WHERE project_id = ? LIMIT 1", (project_id,)).fetchone() is None:
            copy_base(conn, ref, project_id, user_id)
    except Exception:  # before the Testing migrations (tests of old lots)
        return None
    return project_id


def project_id_safe(conn):
    try:
        return project_id(conn)
    except Exception:
        return None


def known_tests(conn, project_id=None):
    """{test_id: status} of a Space's base; empty when the Testing base does not exist (no table yet, or empty)."""
    try:
        pid = base(conn, project_id)
        return {r["test_id"]: r["status"] for r in conn.execute("SELECT test_id, status FROM testing_tests WHERE project_id = ?",
                                                                (pid,))}
    except Exception:  # sqlite3.OperationalError before the migration (tests of old lots)
        return {}


def source_of(row):
    """« IEC 60068-2-6, Test Fc — Vibration (sinusoidal) » : the traceability source of a test (D-B-082)."""
    return ", ".join(x for x in (row["standard"], row["section"]) if x)


def sources(conn, project_id=None):
    """{test_id: (title, source)} of every test of a Space's base ({} before the Testing base exists)."""
    try:
        pid = base(conn, project_id)
        return {r["test_id"]: (r["title"], source_of(r)) for r in conn.execute("SELECT * FROM testing_tests WHERE project_id = ?",
                                                                               (pid,))}
    except Exception:
        return {}


def source_text(conn, test_ref, known=None):
    """« TST-VIB-01 Vibration (IEC 60068-2-6, Test Fc) ; … » for a requirement's Test Procedure."""
    known = sources(conn) if known is None else known
    out = []
    for ref in split_refs(test_ref):
        if ref in known:
            out.append("{} {} ({})".format(ref, known[ref][0], known[ref][1]))
    return " ; ".join(out)


def check_refs(conn, kind, value, previous="", project_id=None):
    """Refusal (message, fix) for a requirement's « Test Procedure », or None.
    A requirement must name at least one test of its Space's base; a need is never tested itself."""
    tests = known_tests(conn, project_id)
    if not tests or kind == "need":
        return None
    refs = split_refs(value)
    if not refs:
        return ("« Test Procedure » obligatoire : un Requirement doit toujours être lié à au moins un Test.",
                "Choisissez le Test qui le vérifie dans la liste (par Subject) ; pour un Need particulier, prenez un "
                "« Custom Test » (TST-CUS-…) ou demandez à l'équipe de tests d'en créer un dans Testing.")
    unknown = [r for r in refs if r not in tests]
    if unknown:
        return ("Test(s) inconnu(s) dans « Test Procedure » : {}.".format(", ".join(unknown)),
                "Utilisez les identifiants de la Test Base de ce Space (onglet Testing, ex. TST-160-08), séparés par des "
                "virgules.")
    old = set(split_refs(previous))
    obsolete = [r for r in refs if tests[r] == "Obsolete" and r not in old]
    if obsolete:
        return ("Test(s) obsolète(s) : {}.".format(", ".join(obsolete)),
                "Choisissez le test qui le remplace (voir sa fiche dans Testing).")
    return None


# --------------------------------------------------------------------------
# Start-up
# --------------------------------------------------------------------------
def _seed_tests(ctx, pid):
    now = db.utc_now()
    conn = ctx.conn
    rows = {r["test_id"]: r for r in conn.execute("SELECT * FROM testing_tests WHERE project_id = ?", (pid,))}
    for t in TESTS:
        values = dict(zip(("test_id", "subject", "category", "standard", "section", "level", "method", "title",
                           "objective", "acceptance"), t))
        values["location"], values["equipment"], values["functions"] = defaults(values["test_id"], values["subject"])
        row = rows.get(values["test_id"])
        if row is None:
            status = "Draft" if values["category"] == "custom" else "In Review"
            conn.execute("INSERT INTO testing_tests (project_id, test_id, {cols}, status, origin, created_by, created_at, "
                         "updated_by, updated_at) VALUES (?, ?, {marks}, ?, 'catalog', ?, ?, ?, ?)".format(
                             cols=", ".join(FIELDS), marks=", ".join("?" for _ in FIELDS)),
                         (pid, values["test_id"]) + tuple(values[f] for f in FIELDS) + (status, ctx.user["id"], now,
                                                                                        ctx.user["id"], now))
        elif row["origin"] == "catalog" and not row["edited"] and any(row[f] != values[f] for f in FIELDS):
            conn.execute("UPDATE testing_tests SET {} WHERE id = ?".format(", ".join(f + " = ?" for f in FIELDS)),
                         tuple(values[f] for f in FIELDS) + (row["id"],))
    # D-B-097: the Space copies -- an unedited catalogue test follows the code too
    for values in (dict(zip(("test_id", "subject", "category", "standard", "section", "level", "method", "title",
                             "objective", "acceptance"), t)) for t in TESTS):
        values["location"], values["equipment"], values["functions"] = defaults(values["test_id"], values["subject"])
        conn.execute("UPDATE testing_tests SET {} WHERE project_id != ? AND test_id = ? AND origin = 'catalog' AND edited = 0 "
                     "AND ({})".format(", ".join(f + " = ?" for f in FIELDS), " OR ".join(f + " IS NOT ?" for f in FIELDS)),
                     tuple(values[f] for f in FIELDS) + (pid, values["test_id"]) + tuple(values[f] for f in FIELDS))


def give_bases(conn):
    """D-B-097, first start-up of 0.50.0: every Space whose requirements cite tests gets its own copy of the base."""
    rows = conn.execute("SELECT DISTINCT i.project_id FROM agile_requirements r JOIN agile_issues i ON i.id = r.issue_id "
                        "WHERE r.test_ref != ''").fetchall()
    return sum(1 for r in rows if base(conn, r[0]) == r[0])


def _generated(ctx, page_id):
    rows = ctx.conn.execute("SELECT author_id, note FROM dynamite_versions WHERE page_id = ?", (page_id,)).fetchall()
    return all(r["author_id"] == ctx.user["id"] and ((r["note"] or "") in OLD_NOTES or (r["note"] or "").startswith(GENERATED))
               for r in rows)


def _tests_by_subject(conn):
    out = {}  # the reference catalogue (the procedure pages describe it)
    for r in conn.execute("SELECT * FROM testing_tests WHERE status != 'Obsolete' AND project_id = ? ORDER BY test_id",
                          (project_id(conn),)):
        out.setdefault(r["subject"], []).append(r)
    return out


def _test_row(t):
    return [_link(t["test_id"], "#/testing/test/" + t["test_id"]), t["title"],
            " · ".join(filter(None, (t["standard"], t["section"]))), t["level"], t["method"], t["status"]]


def covered_tests(tests, subject):
    """The tests a procedure page lists: its subject, then the subjects it covers (COVERS)."""
    out = list(tests.get(subject, []))
    for other, host in COVERS.items():
        if host == subject:
            out += tests.get(other, [])
    return out


def procedure_page(proc, tests):
    code, subject, purpose, means, conditions, steps = proc
    standards = sorted({t["standard"] for t in tests})
    return _doc(
        _panel("warning", _p(_b("Draft"), " — framework test procedure generated from the Testing base. The test team "
                             "completes it (« Modifier »); the test table below is a snapshot: the current list is in ",
                             _link("Testing → " + SUBJECTS[subject], "#/testing/subject/" + subject), ".")),
        {"type": "toc"},
        _h(2, "1. Purpose"), _p(purpose),
        _h(2, "2. Reference Documents"), _p("Cited at a high level only: the text of each standard, in the revision "
                                           "applicable to the program, prevails."), _ul(*standards) if standards else _p("—"),
        _h(2, "3. Tests Covered"),
        _table(["Test", "Title", "Standard · Section", "Level", "Method", "Status"], *[_test_row(t) for t in tests]),
        _h(2, "4. Test Means"), _ul(*means),
        _h(2, "5. General Conditions and Safety"), _ul(*conditions),
        _h(2, "6. Typical Sequence"), _ol(*steps),
        _h(2, "7. Acceptance Criteria"), _p("Those of each test record (Testing tab), taken from the linked Goldmine "
                                           "requirement: any [TBD] value must be set before the test."),
        _h(2, "8. Records"), _ul(*COMMON_RECORDS),
        _h(2, "9. Requirements Verified"), _p("Each test record lists the Goldmine requirements that cite it in "
                                             "« Test Procedure » (every Space you can see)."))


def hub_page(tests_by_subject):
    by_standard = {}
    for tests in tests_by_subject.values():
        for t in tests:
            by_standard.setdefault(t["standard"], []).append(t)
    blocks = [
        _panel("info", _p("Test team portal. ", _b("Test base"), ": ", _link("Testing", "#/testing"),
                          " tab (every possible test, filters by subject, standard, category, status). ", _b("Test Procedures"),
                          ": one draft page per subject, below. Every Goldmine requirement picks its tests in the "
                          "« Test Procedure » field (mandatory).")),
        _panel("warning", _p("Standards are cited by title and section only, never reproduced. Sections are to be checked "
                             "against the team's copy of the standard.")),
        {"type": "toc"}, _h(2, "By Subject"),
        _table(["Procedure", "Subject", "Tests"], *[
            [_b(code), SUBJECTS[subject], str(len(tests_by_subject.get(subject, [])))] for code, subject, *_ in PROCEDURES]),
        _h(2, "By Standard"),
    ]
    for standard in sorted(by_standard):
        tests = by_standard[standard]
        blocks.append(_p(_b(standard), " — ", *[x for t in tests for x in (_link(t["test_id"], "#/testing/test/" + t["test_id"]), " ")]))
    blocks += [_h(2, "Categories"), _ul(*["{}: {}".format(label, {
        "standard": "test defined by a cited standard", "industry": "usual practice of the consumer-product industry",
        "custom": "team-specific test (a function or a use case of the product), to be defined and reviewed"}[code])
        for code, label in CATEGORIES.items()]), _h(2, "Pages"), {"type": "children"}]
    return _doc(*blocks)


def _by_code(titles, code):
    """The procedure page of a code, whatever its subject label (FR before D-B-085, EN since)."""
    return next((p for t, p in titles.items() if t.startswith(code + " — ")), None)


def _ensure_pages(ctx, pid):
    import json
    from modules.dynamite import content
    from modules.help.local_api import LocalApi
    api = LocalApi(ctx)
    base = "/api/dynamite/p/{}/pages".format(pid)

    def refresh(page_id, title, body):
        page = api.get(base + "/{}".format(page_id))["page"]
        if (page["title"] == title and page.get("body") == json.loads(content.validate(body))) or not _generated(ctx, page_id):
            return
        api.put(base + "/{}".format(page_id), {"title": title, "body": body, "base_version": page["version"], "note": GENERATED})

    pages = api.get(base)["pages"]
    titles = {p["title"]: p for p in pages}
    tests = _tests_by_subject(ctx.conn)
    hub = titles.get(HUB) or titles.get("Testing — Procedures d'essai")  # D-B-085: renamed hub
    if hub is None:
        home = next((p for p in pages if not p.get("parent_id")), None)
        if home is not None:
            hub = home
        else:
            made = api.post(base, {"title": HUB, "body": hub_page(tests)})
            hub = made.get("page") or made
    refresh(hub["id"], HUB, hub_page(tests))
    for proc in PROCEDURES:
        title = procedure_title(proc[0], proc[1])
        body = procedure_page(proc, covered_tests(tests, proc[1]))
        page = titles.get(title) or _by_code(titles, proc[0])
        if page is None:
            api.post(base, {"title": title, "parent_id": hub["id"], "body": body})
        else:
            refresh(page["id"], title, body)


def ensure(ctx):
    """Create the TESTING space, fill the test base and the draft procedure pages; everyone is an editor."""
    pid = project_id(ctx.conn)
    if pid is None:
        from modules.timesheet import manage as timesheet
        pid = admin.create_project_record(ctx, KEY, NAME, DESCRIPTION)["id"]
        timesheet.save_settings(ctx.conn, pid, organism="Interne", enabled=False)
    lists.seed(ctx.conn, pid)
    from . import legacy
    legacy.upgrade(ctx.conn)  # D-B-085: statuses and default list labels in English
    _seed_tests(ctx, pid)
    give_bases(ctx.conn)
    _ensure_pages(ctx, pid)
    ctx.conn.execute("INSERT OR IGNORE INTO memberships (user_id, project_id, role) "
                     "SELECT id, ?, 'editor' FROM users WHERE is_active = 1 AND is_admin = 0", (pid,))
    return pid


def require_space(conn):
    pid = project_id(conn)
    if pid is None:
        raise ApiError(404, "Le Space TESTING n'existe pas encore. Correctif : redémarrez le serveur.")
    return pid


def procedure_pages(conn, pid):
    """{subject: {id, title}} of the procedure pages that exist (by their generated title)."""
    ids = {r["title"]: r["id"] for r in conn.execute("SELECT id, title FROM dynamite_pages WHERE project_id = ?", (pid,))}
    out = {}
    for code, subject, *_ in PROCEDURES:
        title = procedure_title(code, subject)
        if title in ids:
            out[subject] = {"id": ids[title], "title": title}
        else:  # a page kept under its former title (edited by the team)
            match = next((t for t in ids if t.startswith(code + " — ")), None)
            if match:
                out[subject] = {"id": ids[match], "title": match}
    for other, host in COVERS.items():
        if host in out:
            out.setdefault(other, out[host])
    return out
