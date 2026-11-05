"""0.60.32 (D-O-040): the logo « DynamiteAgile », one word in two colours, Baloo 2 ExtraBold served by the team's server
(only the letters of the logo, SIL OFL licence alongside), in the tool, the showcase page and the website."""
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


class LogoTest(unittest.TestCase):
    def test_01_font_local_and_small(self):
        font = BASE_DIR / "static" / "fonts" / "baloo2-logo.woff2"
        self.assertTrue(font.read_bytes().startswith(b"wOF2"))
        self.assertLess(font.stat().st_size, 8 * 1024)
        self.assertIn("SIL Open Font License", (BASE_DIR / "static" / "fonts" / "OFL-Baloo2.txt").read_text("utf-8-sig"))
        from core import router
        self.assertEqual(router.STATIC_TYPES[".woff2"], "font/woff2")

    def test_02_app(self):
        css = (BASE_DIR / "static" / "css" / "app.css").read_text("utf-8")
        self.assertIn('src: url("/fonts/baloo2-logo.woff2")', css)
        self.assertNotIn("fonts.googleapis", css)
        js = (BASE_DIR / "static" / "js" / "app.js").read_text("utf-8")
        self.assertNotIn('"brand-sep" }, "|"', js)
        self.assertIn('"aria-label": "Dynamite Agile"', js)

    def test_03_vitrine_and_site(self):
        for rel in ("static/apps/vitrine/index.html", "site/index.html", "site/en/index.html"):
            page = (BASE_DIR / rel).read_text("utf-8")
            self.assertIn("data:font/woff2;base64,", page, rel)
            self.assertIn('<span class="lw-d">Dynamite</span><span class="lw-a">Agile</span>', page, rel)


if __name__ == "__main__":
    unittest.main()
