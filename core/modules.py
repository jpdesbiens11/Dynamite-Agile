"""Registry of business modules pluggable into the platform.

This is the seam that lets Dynamite, Agile, and every future tool (Change
Management, functional analysis, Messenger, File mirror...) share one login, one
project/membership model, and one security layer, without any of them
touching core/ directly.

Each entry in MODULE_MANIFEST describes one business module:
    key      -- short identifier, used in the URL hash (#/<key>) and as a
                table-name prefix (e.g. "changemgmt_request").
    label    -- French label shown in the top navigation.
    phase    -- build step, shown as a "coming soon" hint until ready.
    module   -- None until implemented. Once a module exists, import it
                below and set this to the imported module object.
    scripts  -- browser scripts under static/ (loaded once, in order, after
                login). Each script calls DA.registerModule(key, render).
    styles   -- stylesheets under static/ for the module screens.

A module object is expected to expose, at minimum:
    ROUTES  -- list of (method, url_pattern, handler, access), same shape
               as session_api.ROUTES.
    SCHEMA  -- a string of CREATE TABLE IF NOT EXISTS statements. Every
               table must reference projects(id), directly or through its
               parent table, so access control stays driven by
               core.permissions, and must be additive (never DROP or ALTER
               existing tables from another module).
    MIGRATIONS (optional) -- list of (version, sql) applied once each, for
               changes to tables already in service.

To register a finished module, add its import at the top and change its
manifest entry's "module" value -- nothing else in core/ needs to change.
"""

from modules import agile, codex, dynamite, exploration, goldmine, testing, timesheet, toolbox, training
from modules import help as help_module  # noqa: E402  (top-level package next to core/)
from modules import about  # noqa: E402  D-B-108
from modules import diamond  # noqa: E402  0.60.11, D-O-023

MODULE_MANIFEST = [
    {"key": "dynamite", "label": "Dynamite", "phase": "3.2", "module": dynamite,
     "scripts": ["/js/dynamite/render.js", "/js/dynamite/mermaid_parse.js", "/js/dynamite/mermaid_layout.js",
                 "/js/dynamite/mermaid_svg.js", "/js/dynamite/mermaid_seq.js", "/js/dynamite/mermaid_png.js", "/js/dynamite/visual_dom.js", "/js/dynamite/visual_cmds.js",
                 "/js/dynamite/visual.js", "/js/dynamite/ai_import.js", "/js/dynamite/ai_modal.js",
                 "/js/dynamite/editor.js", "/js/dynamite/comments.js", "/js/dynamite/page_tools.js",
                 "/js/dynamite/dynamite.js"], "styles": ["/css/dynamite.css"]},
    {"key": "agile", "label": "Agile", "phase": "3.3", "module": agile,
     "scripts": ["/js/agile/agile.js", "/js/agile/summary.js", "/js/agile/issue.js", "/js/agile/board.js",
                 "/js/agile/settings.js", "/js/agile/goldmine.js", "/js/agile/goldmine_tests.js", "/js/agile/goldmine_need.js", "/js/agile/goldmine_import.js", "/js/agile/pugh.js", "/js/agile/qa.js", "/js/agile/qa_io.js",
                 "/js/agile/changes.js", "/js/agile/change_form.js", "/js/agile/transfer.js"],
     "styles": ["/css/agile.css", "/css/qa.css", "/css/pugh.css"]},
    {"key": "goldmine", "label": "Goldmine", "phase": "3.3", "module": goldmine,
     "scripts": ["/js/goldmine/shell.js"], "styles": []},
    # 0.60.11 (D-O-023): functional analysis and design risk, right after the needs and requirements
    {"key": "diamond", "label": "Diamond", "phase": "0.60.11", "module": diamond,
     "scripts": ["/js/diamond/diamond.js", "/js/diamond/export_menu.js", "/js/diamond/story_pictos.js", "/js/diamond/story_stage.js", "/js/diamond/story_ai.js", "/js/diamond/story.js", "/js/diamond/tree_layout.js", "/js/diamond/tree_panel.js", "/js/diamond/tree.js",
                 "/js/diamond/structure_draw.js", "/js/diamond/structure_parts.js", "/js/diamond/structure_panel.js",
                 "/js/diamond/structure.js",
                 "/js/diamond/risks_panel.js", "/js/diamond/risks.js",
                 "/js/diamond/dfmea_table.js", "/js/diamond/dfmea.js", "/js/diamond/dfmea_legend.js",
                 "/js/diamond/costs_tables.js", "/js/diamond/costs_io.js", "/js/diamond/costs.js",
                 "/js/diamond/nuggets_content.js", "/js/diamond/nuggets.js", "/js/diamond/export.js"],
     "styles": ["/css/diamond.css", "/css/diamond_dfmea.css", "/css/diamond_costs.css"]},
    # D-B-079: the test team's portal, right after Goldmine (test base + procedures in the space TESTING)
    {"key": "testing", "label": "Testing", "phase": "3.9", "module": testing,
     "scripts": ["/js/testing/testing.js", "/js/testing/testing_record.js", "/js/testing/testing_lists.js", "/js/testing/testing_evidence.js", "/js/testing/testing_bundles.js", "/js/testing/testing_verify.js", "/js/testing/testing_plans.js"], "styles": ["/css/testing.css"]},
    {"key": "exploration", "label": "Exploration", "phase": "3.4", "module": exploration,
     "scripts": ["/js/exploration/gantt.js", "/js/exploration/exploration.js", "/js/exploration/exploration_io.js"],
     "styles": ["/css/exploration.css"]},
    # D-B-065: « Tools » takes Generator's place in the top bar; Generator lives inside it (placement "tools").
    {"key": "tools", "label": "Tools", "phase": "3.8", "module": toolbox,
     "scripts": ["/js/toolbox/tools.js", "/js/toolbox/ideation.js",
                 "/js/toolbox/brainwriting.js", "/js/toolbox/mindmap.js", "/js/toolbox/kt.js"], "styles": ["/css/toolbox.css"]},
    # D-A-045: Training, right after Tools
    {"key": "training", "label": "Training", "phase": "3.10", "module": training,
     "scripts": ["/js/training/quiz.js", "/js/training/training.js"], "styles": ["/css/training.css"]},
    {"key": "codex", "label": "Generator", "phase": "3.5", "module": codex, "placement": "tools",  # ex-Codex (D-B-022)
     "scripts": ["/js/codex/registry.js", "/js/codex/codex.js"], "styles": ["/css/codex.css"]},
    {"key": "timesheet", "label": "Timesheet", "phase": "3.6", "module": timesheet,
     "scripts": ["/js/timesheet/manage.js", "/js/timesheet/budget_io.js", "/js/timesheet/budget.js", "/js/timesheet/copy.js", "/js/timesheet/timesheet.js"], "styles": ["/css/timesheet.css"]},
    {"key": "help", "label": "Help", "phase": "3.7", "module": help_module, "placement": "end",
     "scripts": ["/js/help/content_path.js", "/js/help/content_path2.js", "/js/help/content_faq.js",
                 "/js/help/help.js"], "styles": ["/css/help.css"]},
    # « About »: who made the tool and how -- right of Help, before the account menu and « ⚙ Admin »
    {"key": "about", "label": "About", "phase": "3.11", "module": about, "placement": "end",
     "scripts": ["/js/about/about.js"], "styles": ["/css/about.css"]},
]


def registered_routes():
    """API routes contributed by every module that is actually built."""
    routes = []
    for entry in MODULE_MANIFEST:
        if entry["module"] is not None:
            routes += entry["module"].ROUTES
    return routes


def project_hooks():
    """on_project_created(ctx, project_id) of every built module, in manifest
    order (core lot v0.5, D-B-012): a new project is ready in every tab."""
    return [(entry["key"], entry["module"].on_project_created) for entry in MODULE_MANIFEST
            if entry["module"] is not None and hasattr(entry["module"], "on_project_created")]


def space_hooks():
    """ensure_space(ctx, project_id) of every built module, in manifest order (core lot v0.34, D-B-134): idempotent,
    adds the structure a Space lacks in that tab (run at start-up for every active Space)."""
    return [(entry["key"], entry["module"].ensure_space) for entry in MODULE_MANIFEST
            if entry["module"] is not None and hasattr(entry["module"], "ensure_space")]


def search_hooks():
    """search(conn, projects, q) of every built module (core lot v0.7, v0.16:
    D-B-022): the top-bar search asks each module for hits in the projects the
    user can see. `projects` maps project id -> key."""
    return [(entry["key"], entry["module"].search) for entry in MODULE_MANIFEST
            if entry["module"] is not None and hasattr(entry["module"], "search")]


def startup_hooks():
    """on_startup(ctx) of every built module, run once per server start after the
    migrations (core lot v0.7): e.g. Testing makes sure the TESTING Space exists."""
    return [(entry["key"], entry["module"].on_startup) for entry in MODULE_MANIFEST
            if entry["module"] is not None and hasattr(entry["module"], "on_startup")]


def restore_hooks():
    """on_restore(conn, maps, old_key, new_key) of every built module (core lot
    v0.10): fix ids or keys stored inside content after a project restore.
    maps[table][old id] = new id."""
    return [(entry["key"], entry["module"].on_restore) for entry in MODULE_MANIFEST
            if entry["module"] is not None and hasattr(entry["module"], "on_restore")]


def dashboard_hooks():
    """dashboard(conn, user, projects) of every built module (core lot v0.10):
    the personal dashboard asks each module for the user's items."""
    return [(entry["key"], entry["module"].dashboard) for entry in MODULE_MANIFEST
            if entry["module"] is not None and hasattr(entry["module"], "dashboard")]


def review_hooks():
    """(module_key, review_items(conn, user_id, year)) -- items a module adds to the annual review (core lot v0.30)."""
    return [(entry["key"], entry["module"].review_items) for entry in MODULE_MANIFEST
            if entry["module"] is not None and hasattr(entry["module"], "review_items")]


def registered_schema():
    """SQL schema contributed by every module that is actually built."""
    parts = [entry["module"].SCHEMA for entry in MODULE_MANIFEST if entry["module"] is not None]
    return "\n".join(parts)


def registered_migrations():
    """(module_key, version, sql) for the core (key "core") and every built module."""
    from . import access_rules, backup, bot, mail, members, mentions, objectives, platform_config, prefs, profile, reviews, tls, ui_audit, uploads  # core tables added after 0.1 live in versioned lots too
    result = [("core", version, sql) for version, sql
              in uploads.MIGRATIONS + access_rules.MIGRATIONS + ui_audit.MIGRATIONS + prefs.MIGRATIONS + members.MIGRATIONS + platform_config.MIGRATIONS
              + objectives.MIGRATIONS + backup.MIGRATIONS + mentions.MIGRATIONS + tls.MIGRATIONS
              + profile.MIGRATIONS + reviews.MIGRATIONS + bot.MIGRATIONS + mail.MIGRATIONS]
    for entry in MODULE_MANIFEST:
        if entry["module"] is not None:
            for version, sql in getattr(entry["module"], "MIGRATIONS", ()):
                result.append((entry["key"], version, sql))
    return result


def nav_manifest():
    """What the browser needs to build the top navigation."""
    return [
        {"key": entry["key"], "label": entry["label"], "phase": entry["phase"],
         "available": entry["module"] is not None,
         "scripts": entry.get("scripts", []) if entry["module"] is not None else [],
         "styles": entry.get("styles", []) if entry["module"] is not None else [],
         "placement": entry.get("placement", "main")}  # "end": right of Administration (core lot v0.8)
        for entry in MODULE_MANIFEST if entry.get("placement") != "none"  # core lot v0.34: a module without any screen
    ]
