"""Goldmine: engineering requirements in their own top tab (D-B-011).

"The requirements are the raw, unrefined ore." Data and API stay in the
Agile module (modules/agile/goldmine.py, agile_requirements, same ticket
numbering and links as the work that implements them); this entry only
gives them their own tab and screen shell (static/js/goldmine/shell.js).
"""
SCHEMA = ""
MIGRATIONS = []
ROUTES = []


def on_project_created(ctx, project_id):
    """Core hook (lot v0.5, D-B-012): requirements ready on every new project.
    Runs after Agile's hook (MODULE_MANIFEST order)."""
    from modules.agile import goldmine  # data lives in the Agile module
    goldmine.enable(ctx, project_id)


def ensure_space(ctx, project_id):
    """Core hook (lot v0.34, D-B-134): the requirement type in any Space with Agile but no Goldmine yet (a conflicting
    « Requirement » type or workflow is left for an administrator: enable() refuses it with its fix)."""
    from core.errors import ApiError
    from modules.agile import goldmine
    if goldmine.requirement_type(ctx.conn, project_id) is None:
        try:
            goldmine.enable(ctx, project_id)
        except ApiError:
            pass
