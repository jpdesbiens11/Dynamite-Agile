"""0.60.26 (D-O-035): a box of several choices (the parts of a function, the columns of the DFMEA) waits: the ticks are
applied together on « Appliquer » or a click outside the box; Escape or « Annuler » puts them back."""
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


class ChoicesTest(unittest.TestCase):
    def test_01_helper_and_uses(self):
        js = lambda rel: (BASE_DIR / "static" / "js" / rel).read_text("utf-8")  # noqa: E731
        helper = js("tools/choices.js")
        for needed in ("DA.choiceBatch = function", "pointerdown", "Escape", "Appliquer", "Annuler", "0.60.26-choices"):
            self.assertIn(needed, helper)
        self.assertIn('<script src="/js/tools/choices.js" defer></script>', (BASE_DIR / "static" / "index.html").read_text("utf-8"))
        parts = js("diamond/structure_parts.js")
        self.assertIn("DA.choiceBatch(box", parts)
        self.assertNotIn('input.addEventListener("change", () => run("/parts/"', parts)  # no write per tick any more
        self.assertIn("state.runMany = async", js("diamond/structure.js"))
        dfmea = js("diamond/dfmea.js")
        self.assertIn("DA.choiceBatch(chooser", dfmea)
        self.assertIn("state.colsOpen", dfmea)


if __name__ == "__main__":
    unittest.main()
