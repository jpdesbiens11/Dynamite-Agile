"""The Rover example inside DEMO (0.60.49, D-O-058): DEMO holds the guided tour of every tool, the reference library and
the training documents, and also the complete academic example of a product -- the Rover, an autonomous robot on an
all-terrain RC car (deploy/spaces_exemples/rover.json, tools/make_rover_example.py), every module filled from MVP 0 to
MVP 3. Loaded once, at start-up, through the same code as « Commencer » (same checks, same journal), but into the DEMO
Space and without the example accounts: no account is created on an installation that did not ask for one; the
assignees, owners and team of the file stay as text in its pages.
"""
import json
from pathlib import Path

from core import audit, starter

from .headlamp import KEY, project_id

FILE = Path(__file__).resolve().parent.parent.parent / "deploy" / "spaces_exemples" / "rover.json"
DONE = "demo_example_loaded"
AI_NOTE = set(starter.AI_DRAFT_NOTE.values())


def _without_accounts(raw):
    """The file without its team: assignees and owners removed, everything else as it is."""
    raw = dict(raw, team=[])
    raw["backlog"] = [{k: v for k, v in b.items() if k != "assignee"} for b in raw.get("backlog", [])]
    diamond = dict(raw.get("diamond") or {})
    for name in ("risks", "dfmea"):
        diamond[name] = [{k: v for k, v in r.items() if k != "owner"} for r in diamond.get(name, [])]
    raw["diamond"] = diamond
    return raw


def _plain_pages(clean):
    """The pages of DEMO are reviewed content, not an AI draft: the « Brouillon IA » panel is left out."""
    for p in clean["pages"]:
        p["body"]["content"] = [b for b in p["body"]["content"]
                                if not (b.get("type") == "panel" and b.get("kind") == "note"
                                        and any(t.get("text") in AI_NOTE for c in b.get("content", []) for t in c.get("content", [])))]
        p["ai_draft"] = False


def ensure(ctx):
    """Load the Rover into DEMO once. Returns the counts, or None when already done (or no DEMO, or no file)."""
    pid = project_id(ctx.conn)
    if pid is None or not FILE.exists():
        return None
    if ctx.conn.execute("SELECT 1 FROM audit_log WHERE action = ? AND object_id = ?", (DONE, str(pid))).fetchone():
        return None
    from core import starter_apply as A, starter_diamond, starter_more
    from modules.exploration import reference
    clean, _warnings = starter.parse(json.dumps(_without_accounts(json.loads(FILE.read_text("utf-8")))))
    _plain_pages(clean)
    test_ids, _placeholder = A._tests(ctx, pid, clean)
    # the Rover's tests stay in DEMO: never copied into a new product's Test Base (testing.catalog.copy_base)
    ctx.conn.executemany("UPDATE testing_tests SET origin = 'example' WHERE project_id = ? AND test_id = ?",
                         [(pid, code) for code in test_ids.values()])
    req_keys = A._requirements(ctx, pid, KEY, clean, test_ids)
    pages = _pages_beside(ctx, pid, clean)  # the Rover pages beside the DEMO home, never replacing it
    rows = {r["test_id"]: r["id"] for r in ctx.conn.execute("SELECT id, test_id FROM testing_tests WHERE project_id = ?", (pid,))}
    made = starter_diamond.apply(ctx.conn, ctx.user["id"], pid, clean["diamond"], {ref: rows.get(code) for ref, code in test_ids.items()})
    more = starter_more.apply(ctx, pid, KEY, clean["more"], lambda p, body, func: A._as(ctx, p, body, func), req_keys)
    plan = reference.apply(ctx, pid, reference.parse_start(clean["project"]["start_date"]), clean["project"]["weeks"], [ctx.user["id"]])
    counts = {"requirements": len(req_keys), "tests": len(test_ids), "pages": len(pages), "plan_tasks": plan,
              **{"diamond_" + k: n for k, n in made.items()}, **more}
    audit.log_action(ctx.conn, ctx.user["id"], DONE, "project", pid, counts, None)
    return counts


def _pages_beside(ctx, pid, clean):
    """Create every page of the file in DEMO: its top pages at the root, next to the DEMO home."""
    from core import starter_apply as A
    from modules.dynamite import pages
    ids = {}
    for p in clean["pages"]:
        parent = ids[p["parent"]] if p["parent"] else None
        ids[p["ref"]] = A._as(ctx, pid, {"title": p["title"], "parent_id": parent, "body": p["body"]}, pages.api_create)["id"]
    return ids
