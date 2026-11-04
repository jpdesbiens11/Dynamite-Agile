"""0.45.0: « Terminal R&D » theme (D-B-088, core lot v0.23) -- a choice next to the « Thème par défaut », same
functions; crisp icon set and marks with the same names; prompt line, boot sequence and Ctrl+K palette.

    python -m unittest tests.test_lot_v035 -v
"""
import re
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import prefs  # noqa: E402

STATIC = BASE_DIR / "static"


class LotV035Test(unittest.TestCase):
    def test_01_theme_is_a_choice(self):
        self.assertIn("terminal", prefs.CHOICES["theme"])
        self.assertEqual(prefs.DEFAULTS["theme"], "carnet")  # the Carnet stays the default
        js = (STATIC / "js" / "tools" / "prefs.js").read_text(encoding="utf-8")
        self.assertIn('set("data-term", terminal ? "on" : "", "")', js)
        i18n = (STATIC / "js" / "tools" / "i18n.js").read_text(encoding="utf-8")
        self.assertEqual(i18n.count('"theme.terminal"'), 2)

    def test_02_same_icons_in_both_sets(self):
        ids = lambda name: set(re.findall(r'id="(i-[a-z]+)"', (STATIC / "img" / name).read_text(encoding="utf-8")))  # noqa: E731
        self.assertEqual(ids("icons.svg"), ids("icons-term.svg"))
        self.assertEqual({p.name for p in (STATIC / "img" / "marks").glob("*.svg")},
                         {p.name for p in (STATIC / "img" / "marks-term").glob("*.svg")})

    def test_03_shell_loads_the_theme(self):
        index = (STATIC / "index.html").read_text(encoding="utf-8")
        self.assertLess(index.index("/css/sketch.css"), index.index("/css/terminal.css"))
        for script in ("/js/tools/palette.js", "/js/tools/terminal.js"):
            self.assertLess(index.index(script), index.index("/js/app.js"))
        css = (STATIC / "css" / "terminal.css").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion", css)
        self.assertNotRegex(css, r"url\(\s*['\"]?https?:")  # no external resource
        term = (STATIC / "js" / "tools" / "terminal.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", term)
        palette = (STATIC / "js" / "tools" / "palette.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", palette)
        self.assertIn('"0.45.0-palette"', palette)  # D-A-049: a new function carries its [new] tag
        app = (STATIC / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("DA.bootSequence", app)
        # 0.45.1 (D-B-089): both themes one click away in the account menu
        self.assertIn('themeItem("carnet"', app)
        self.assertIn('themeItem("terminal"', app)
        mentions = (STATIC / "js" / "tools" / "mentions.js").read_text(encoding="utf-8")
        self.assertIn('"/api/mentions" + (sent ? "?box=sent" : done ? "?box=done" : "")', mentions)


if __name__ == "__main__":
    unittest.main(verbosity=2)
