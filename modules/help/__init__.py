"""Help: the user guide, the FAQ and the HeadLamp learning project (D-B-024).

The guide itself is static content (static/js/help/content_*.js), shown in
the « Help » tab, placed right of Administration (placement "end", core lot
v0.8). This package only creates the HeadLamp sandbox project at start-up
and lets a user join it.
"""
from . import gtd, headlamp

SCHEMA = ""
MIGRATIONS = []


def on_startup(ctx):
    """Core hook (lot v0.7): HeadLamp exists from the first launch."""
    headlamp.ensure(ctx)
    gtd.ensure(ctx)  # D-B-033 / D-B-040: « Base de connaissances (BDC) », also for an existing HEADLAMP
    from modules.testing import lists  # D-B-082: the product functions (central list of Testing) as a BDC page
    lists.ensure_bdc_page(ctx)
    from modules.testing import glossary  # D-A-037: Definitions, Acronyms and their French translation
    glossary.ensure_pages(ctx)
    from . import update_guide  # D-A-049: step-by-step guide of Admin → Update
    update_guide.ensure(ctx)
    from . import agile_guide  # D-A-050: the Agile method, step by step with screenshots
    agile_guide.ensure(ctx)


ROUTES = [
    ("GET", r"/api/help/headlamp", headlamp.api_status, "user"),
    ("POST", r"/api/help/headlamp/join", headlamp.api_join, "user"),
]
