"""Agile module: Jira-like tickets, custom workflows, labels, sprints.

Registered in core/modules.py. Every route is declared "user"; each handler
checks the project role itself through modules.agile.common.access().
"""
from .dashboard import dashboard  # noqa: F401  (core lot v0.10 hook)
from .search import search  # noqa: F401  (core lot v0.7 hook)
from . import changes, common, csv_io, goldmine, goldmine_csv, issues, planning, qa, qa_register, qa_xlsx, summary, workflow


def _goldmine_docx(ctx):
    """D-B-083: requirement specification in the Word template (imported late: it uses the Testing module)."""
    from . import goldmine_docx
    return goldmine_docx.api_export(ctx)
from . import pugh, pugh_xlsx
from .schema import MIGRATIONS as _SCHEMA_MIGRATIONS, SCHEMA  # noqa: F401

MIGRATIONS = _SCHEMA_MIGRATIONS + pugh.MIGRATIONS  # D-B-062: Pugh matrices (migration 10)
on_restore = pugh.on_restore  # core lot v0.10 hook

def on_startup(ctx):
    """Core hook (lot v0.7), D-B-085: the former French default names of statuses, transitions, issue types and
    workflows become English (idempotent; names an admin customised are left alone)."""
    from . import vocab
    for statement in vocab.migration_sql().split("\n"):
        ctx.conn.execute(statement)


def on_project_created(ctx, project_id):
    """Core hook (lot v0.5, D-B-012): a new project gets Agile and its
    Change Management ready, no activation click needed."""
    common.enable_project(ctx, project_id)
    changes.enable(ctx, project_id)


def ensure_space(ctx, project_id):
    """Core hook (lot v0.34, D-B-134): Agile and Change Management ready in any Space that lacks them."""
    if not ctx.conn.execute("SELECT 1 FROM agile_settings WHERE project_id = ?", (project_id,)).fetchone():
        common.enable_project(ctx, project_id)
    if "ecn" not in changes.types_by_role(ctx.conn, project_id):
        changes.enable(ctx, project_id)


P = r"/api/agile/p/(?P<pid>\d+)"
I = P + r"/issues/(?P<num>\d+)"

ROUTES = [
    ("POST", P + r"/init", common.api_init, "user"),
    ("GET", P + r"/meta", common.api_meta, "user"),
    ("GET", P + r"/issues", issues.api_list, "user"),
    ("POST", P + r"/issues", issues.api_create, "user"),
    ("GET", I, issues.api_get, "user"),
    ("PATCH", I, issues.api_update, "user"),
    ("DELETE", I, issues.api_delete, "user"),
    ("POST", I + r"/transition", issues.api_transition, "user"),
    ("PUT", I + r"/labels", issues.api_set_labels, "user"),
    ("PUT", I + r"/summary", summary.api_set, "user"),
    ("POST", P + r"/changes/setup", changes.api_setup, "user"),
    ("GET", P + r"/changes", changes.api_list, "user"),
    ("GET", P + r"/export/changes", changes.api_export, "user"),
    ("PUT", I + r"/change", changes.api_update_fields, "user"),
    ("PUT", I + r"/change/items", changes.api_set_items, "user"),
    ("POST", I + r"/derive", changes.api_derive, "user"),
    ("POST", I + r"/comments", issues.api_add_comment, "user"),
    ("DELETE", I + r"/comments/(?P<cid>\d+)", issues.api_delete_comment, "user"),
    ("POST", I + r"/links", issues.api_add_link, "user"),
    ("DELETE", I + r"/links/(?P<lid>\d+)", issues.api_delete_link, "user"),
    ("GET", P + r"/board", planning.api_board, "user"),
    ("GET", P + r"/dependencies", planning.api_dependencies, "user"),
    ("POST", P + r"/goldmine/setup", goldmine.api_setup, "user"),
    ("GET", P + r"/goldmine", goldmine.api_list, "user"),
    ("POST", P + r"/goldmine/requirements", goldmine.api_create, "user"),
    ("GET", P + r"/export/requirements", goldmine_csv.api_export, "user"),
    ("GET", P + r"/export/requirements\.docx", _goldmine_docx, "user"),
    ("POST", P + r"/import/requirements", goldmine_csv.api_import, "user"),
    ("PUT", I + r"/requirement", goldmine.api_update_fields, "user"),
    ("GET", P + r"/pugh", pugh.api_list, "user"),
    ("POST", P + r"/pugh", pugh.api_create, "user"),
    ("GET", P + r"/pugh/(?P<mid>\d+)", pugh.api_get, "user"),
    ("PATCH", P + r"/pugh/(?P<mid>\d+)", pugh.api_update, "user"),
    ("DELETE", P + r"/pugh/(?P<mid>\d+)", pugh.api_delete, "user"),
    ("POST", P + r"/pugh/(?P<mid>\d+)/concepts", pugh.api_concept_add, "user"),
    ("PATCH", P + r"/pugh/(?P<mid>\d+)/concepts/(?P<cid>\d+)", pugh.api_concept_update, "user"),
    ("POST", P + r"/pugh/(?P<mid>\d+)/criteria", pugh.api_criteria_add, "user"),
    ("DELETE", P + r"/pugh/(?P<mid>\d+)/criteria/(?P<kid>\d+)", pugh.api_criterion_delete, "user"),
    ("PUT", P + r"/pugh/(?P<mid>\d+)/score", pugh.api_score, "user"),
    ("POST", P + r"/pugh/(?P<mid>\d+)/round", pugh.api_round, "user"),
    ("GET", P + r"/pugh/(?P<mid>\d+)/export\.xlsx", pugh_xlsx.api_export, "user"),
    ("GET", P + r"/qa", qa.api_list, "user"),
    ("POST", I + r"/qa", qa.api_create, "user"),
    ("POST", P + r"/qa/(?P<qid>\d+)/answer", qa.api_answer, "user"),
    ("POST", P + r"/qa/(?P<qid>\d+)/(?P<action>close|reopen|cancel|revert)", qa.api_status, "user"),
    ("PATCH", P + r"/qa/(?P<qid>\d+)", qa.api_update, "user"),
    ("GET", P + r"/qa/client\.xlsx", qa_xlsx.api_client_package, "user"),
    ("GET", P + r"/qa/register\.xlsx", qa_register.api_register, "user"),
    ("GET", P + r"/qa/archives", qa_register.api_archives, "user"),
    ("GET", P + r"/qa/archives/(?P<name>[A-Za-z0-9_.\-]+)", qa_register.api_archive_file, "user"),
    ("POST", P + r"/qa/import", qa_xlsx.api_import, "user"),
    ("GET", P + r"/export/tickets", csv_io.api_export_tickets, "user"),
    ("POST", P + r"/import/tickets", csv_io.api_import_tickets, "user"),
    ("GET", P + r"/export/questions", csv_io.api_export_questions, "user"),
    ("POST", P + r"/import/questions", csv_io.api_import_questions, "user"),
    ("PATCH", P + r"/backlog/rank", planning.api_move_rank, "user"),
    ("POST", P + r"/sprints", planning.api_create_sprint, "user"),
    ("PATCH", P + r"/sprints/(?P<sid>\d+)", planning.api_update_sprint, "user"),
    ("DELETE", P + r"/sprints/(?P<sid>\d+)", planning.api_delete_sprint, "user"),
    ("POST", P + r"/sprints/(?P<sid>\d+)/start", planning.api_start_sprint, "user"),
    ("POST", P + r"/sprints/(?P<sid>\d+)/close", planning.api_close_sprint, "user"),
    ("POST", P + r"/versions", planning.api_create_version, "user"),
    ("PATCH", P + r"/versions/(?P<vid>\d+)", planning.api_update_version, "user"),
    ("DELETE", P + r"/versions/(?P<vid>\d+)", planning.api_delete_version, "user"),
    ("POST", P + r"/workflows", workflow.api_create_workflow, "user"),
    ("PATCH", P + r"/workflows/(?P<wid>\d+)", workflow.api_rename_workflow, "user"),
    ("POST", P + r"/statuses", workflow.api_create_status, "user"),
    ("PATCH", P + r"/statuses/(?P<sid>\d+)", workflow.api_update_status, "user"),
    ("DELETE", P + r"/statuses/(?P<sid>\d+)", workflow.api_delete_status, "user"),
    ("POST", P + r"/transitions", workflow.api_create_transition, "user"),
    ("DELETE", P + r"/transitions/(?P<tid>\d+)", workflow.api_delete_transition, "user"),
    ("POST", P + r"/types", workflow.api_create_type, "user"),
    ("PATCH", P + r"/types/(?P<tid>\d+)", workflow.api_update_type, "user"),
    ("PATCH", P + r"/labels/(?P<lid>\d+)", workflow.api_update_label, "user"),
    ("DELETE", P + r"/labels/(?P<lid>\d+)", workflow.api_delete_label, "user"),
]
