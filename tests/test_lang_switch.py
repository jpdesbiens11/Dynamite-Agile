"""0.60.48 (D-O-057): FR | EN in the top bar of the platform (no detour through Paramètres); the themes are chosen in
Paramètres only, no longer in the account menu."""
import unittest
from pathlib import Path

from core import prefs

BASE_DIR = Path(__file__).resolve().parent.parent


class LangSwitchTest(unittest.TestCase):
    def test_language_choices_and_button(self):
        self.assertEqual(prefs.CHOICES["language"], ("fr", "en"))
        index = (BASE_DIR / "static" / "index.html").read_text("utf-8")
        self.assertIn('src="/js/tools/langswitch.js"', index)
        js = (BASE_DIR / "static" / "js" / "tools" / "langswitch.js").read_text("utf-8")
        self.assertIn('"data-new": "0.60.48-lang-switch"', js)
        self.assertIn("savePrefs({ language: other })", js)
        self.assertIn("DA.topbarTools.push(button)", js)
        self.assertNotIn("innerHTML", js)

    def test_themes_left_the_account_menu(self):
        app = (BASE_DIR / "static" / "js" / "app.js").read_text("utf-8")
        self.assertNotIn("themeItem(", app)
        self.assertNotIn("0.45.1-theme-menu", app)
        settings = (BASE_DIR / "static" / "js" / "tools" / "prefs.js").read_text("utf-8")
        self.assertIn('select("theme"', settings)  # still in Paramètres


if __name__ == "__main__":
    unittest.main()
