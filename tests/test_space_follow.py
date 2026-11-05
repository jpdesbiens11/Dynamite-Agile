"""0.60.21: the Space one works in follows from tab to tab (sessionStorage, the common Spaces excepted), and a ☆ / ★
beside the Space drop-down of every module makes it the default Space (where the site opens)."""
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


class SpaceFollowTest(unittest.TestCase):
    def test_01_spaces_js(self):
        js = (BASE_DIR / "static" / "js" / "tools" / "spaces.js").read_text("utf-8")
        for needed in ("workKey()", "sessionStorage", '"HEADLAMP", "TOOLS", "TESTING", "TRAINING"', "0.60.21-default-star",
                       "const key = this.workKey();", "return this.defaultKey() || "):  # 0.60.28: the star first
            self.assertIn(needed, js, needed)

    def test_02_every_picker_has_its_star(self):
        for rel in ("agile/agile.js", "dynamite/dynamite.js", "codex/codex.js", "exploration/exploration.js"):
            self.assertIn("DA.spaces.withStar(", (BASE_DIR / "static" / "js" / rel).read_text("utf-8"), rel)
        self.assertIn("DA.spaces.workKey()", (BASE_DIR / "static" / "js" / "toolbox" / "tools.js").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
