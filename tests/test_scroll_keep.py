"""0.60.23: a redraw keeps the page where the person was looking (Diamond redraws, the router in the same tab and Space),
and the panel of a sub-system lists the parts of its tertiary functions, as the tags of its box."""
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


class ScrollKeepTest(unittest.TestCase):
    def test_01_wiring(self):
        js = lambda rel: (BASE_DIR / "static" / "js" / rel).read_text("utf-8")  # noqa: E731
        self.assertIn("DA.keepScroll = function", js("tools/scrollkeep.js"))
        self.assertIn('<script src="/js/tools/scrollkeep.js" defer></script>', (BASE_DIR / "static" / "index.html").read_text("utf-8"))
        self.assertIn("DA.keepScroll(fn)", js("diamond/diamond.js"))
        self.assertIn("DA.placeHold(location.hash)", js("app.js"))
        self.assertIn("0.60.23-part-via", js("diamond/structure_parts.js"))


if __name__ == "__main__":
    unittest.main()
