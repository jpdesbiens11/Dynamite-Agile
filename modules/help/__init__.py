"""Help: the user guide, the FAQ and the DEMO learning project (D-B-024).

The guide itself is static content (static/js/help/content_*.js), shown in
the « Help » tab, placed right of Administration (placement "end", core lot
v0.8). This package only creates the DEMO sandbox project at start-up
and lets a user join it.
"""
from . import gtd, headlamp

SCHEMA = ""
MIGRATIONS = []


def on_startup(ctx):
    """Core hook (lot v0.7): DEMO exists from the first launch."""
    headlamp.ensure(ctx)
    from . import demo_example  # 0.60.49 (D-O-058): the Rover, the complete example, inside DEMO (once)
    demo_example.ensure(ctx)
    demo_example.ensure_story(ctx)  # 0.60.52 (D-O-061): the Rover's Storyline in a DEMO loaded before it
    from . import demo_life  # 0.60.54 (D-O-063): the Rover as a project in motion in every module (once)
    demo_life.ensure_life(ctx)
    demo_life.ensure_arranged(ctx)  # 0.60.55 (D-O-064): the Rover is the demo -- its plan first in a DEMO filled before
    gtd.ensure(ctx)  # D-B-033 / D-B-040: « Base de connaissances (BDC) », also for an existing DEMO
    from modules.testing import lists  # D-B-082: the product functions (central list of Testing) as a BDC page
    lists.ensure_bdc_page(ctx)
    from modules.testing import glossary  # D-A-037: Definitions, Acronyms and their French translation
    glossary.ensure_pages(ctx)
    from . import update_guide  # D-A-049: step-by-step guide of Admin → Update
    update_guide.ensure(ctx)
    from . import agile_guide  # D-A-050: the Agile method, step by step with screenshots
    agile_guide.ensure(ctx)
    from . import module_docs_pages  # 0.60.45 (D-O-054): one page per module, with its references, for learning students
    module_docs_pages.ensure(ctx)


ROUTES = [
    ("GET", r"/api/help/headlamp", headlamp.api_status, "user"),
    ("POST", r"/api/help/headlamp/join", headlamp.api_join, "user"),
]
