"""0.60.27 (D-O-036): on a phone, the big screens stay on the computer (a note), Goldmine / Testing / Timesheet become
lists of cards with folded filters, and Dynamite has a quick bar: + Page, ✨ with the AI, Share."""
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


class MobileViewsTest(unittest.TestCase):
    def test_01_script(self):
        js = (BASE_DIR / "static" / "js" / "tools" / "mobile_views.js").read_text("utf-8")
        for needed in ('diamond: "Diamond"', 'exploration:', 'tools:', '["goldmine", "testing", "timesheet"]', "data-label",
                       "navigator.share", "navigator.clipboard", ".dy-ai-btn", "0.60.27-dy-fab", "0.60.27-pc-only", "da-phone"):
            self.assertIn(needed, js, needed)
        self.assertNotIn("innerHTML", js)
        self.assertIn('<script src="/js/tools/mobile_views.js" defer></script>', (BASE_DIR / "static" / "index.html").read_text("utf-8"))

    def test_02_css(self):
        css = (BASE_DIR / "static" / "css" / "mobile.css").read_text("utf-8")
        for needed in ("table.data[data-cards]", "content: attr(data-label)", "html.da-phone.pc-only #main", ".dy-fab",
                       "env(safe-area-inset-bottom", ".ag-filters:not(.filters-open)"):
            self.assertIn(needed, css, needed)


if __name__ == "__main__":
    unittest.main()
