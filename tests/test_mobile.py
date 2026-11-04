"""0.60.25 (D-O-034): phones -- a compact app bar with a navigation drawer, one column, wide tables scrolling in their
own box, 44 px touch targets, slightly smaller text; the desktop top bar is never touched."""
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


class MobileTest(unittest.TestCase):
    def test_01_wiring(self):
        html = (BASE_DIR / "static" / "index.html").read_text("utf-8")
        self.assertIn('<link rel="stylesheet" href="/css/mobile.css">', html)
        self.assertIn('<script src="/js/tools/mobile.js" defer></script>', html)
        self.assertLess(html.index("/css/terminal.css"), html.index("/css/mobile.css"))  # after the themes
        self.assertIn('name="viewport" content="width=device-width, initial-scale=1"', html)

    def test_02_drawer(self):
        js = (BASE_DIR / "static" / "js" / "tools" / "mobile.js").read_text("utf-8")
        for needed in ('matchMedia("(max-width: 760px)")', "nav-drawer", "aria-expanded", "Escape", "0.60.25-phone-menu"):
            self.assertIn(needed, js)
        self.assertNotIn("innerHTML", js)
        css = (BASE_DIR / "static" / "css" / "mobile.css").read_text("utf-8")
        for needed in ("@media (max-width: 760px)", "min-height: 44px", "overflow-x: auto", "prefers-reduced-motion"):
            self.assertIn(needed, css)
        self.assertNotRegex(css, r"url\(['\"]?https?://")


if __name__ == "__main__":
    unittest.main()
