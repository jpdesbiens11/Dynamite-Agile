"""0.60.110 (D-O-123): reading the DFMEA in the browser -- compact rows and their chevron, the scroll bar pinned to the
bottom of the window, the columns kept on the left, full screen, the magnifier, « Essentiel » (static/js/diamond/fm_view.js,
fm_scroll.js, static/css/diamond_fmview.css). Behaviour: tests/js/dfmea_view.js.

    python -m unittest tests.test_dfmea_view -v
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
JS = BASE_DIR / "static" / "js" / "diamond"
CSS = BASE_DIR / "static" / "css" / "diamond_fmview.css"
NEW = ("fm_view.js", "fm_scroll.js")


def read(name):
    return (JS / name).read_text("utf-8")


class DfmeaViewTest(unittest.TestCase):
    def test_01_registered_before_the_screens_that_use_them(self):
        from core.modules import MODULE_MANIFEST
        diamond = next(m for m in MODULE_MANIFEST if m["key"] == "diamond")
        scripts = diamond["scripts"]
        for name in NEW:
            self.assertIn("/js/diamond/" + name, scripts)
            self.assertLess(scripts.index("/js/diamond/" + name), scripts.index("/js/diamond/dfmea.js"))
        self.assertIn("/css/diamond_fmview.css", diamond["styles"])
        self.assertIn("D.fmView(holder, state)", read("dfmea.js"))
        for name in ("pfmea.js", "cplans.js"):  # the pinned scroll bar, shared
            self.assertIn("D.fmScroller(", read(name))

    def test_02_every_new_function_is_tagged(self):
        view = read("fm_view.js")
        for key in ("fm-unfold", "fm-fold", "fm-loupe", "fm-full", "fm-essential"):
            self.assertIn('"0.60.110-' + key + '"', view)
        self.assertIn('"0.60.110-fm-preset"', read("dfmea.js"))
        self.assertIn('["Essentiel", ESSENTIAL', read("dfmea.js"))

    def test_03_safe_dom_browser_only_small_files(self):
        for name in NEW:
            text = read(name)
            self.assertNotIn("innerHTML", text)
            self.assertNotIn("api.", text)  # the view state never goes to the server
            self.assertNotIn('setAttribute("style"', text)
        for name in NEW + ("dfmea.js", "dfmea_table.js", "pfmea.js", "cplans.js"):
            self.assertLess(len(read(name).splitlines()), 500, name)
        self.assertLess(len(CSS.read_text("utf-8").splitlines()), 500)

    def test_04_local_storage_always_in_try_catch(self):
        text = read("fm_view.js")
        lines = [ln for ln in text.splitlines() if "localStorage." in ln]
        self.assertTrue(lines)
        for ln in lines:
            self.assertIn("try {", ln, ln)
            self.assertIn("catch (err)", ln, ln)

    def test_05_themes_and_no_external_resource(self):
        css = CSS.read_text("utf-8")
        for needle in ("html[data-sketch]", "html[data-term]", 'html[data-theme="dark"]', "position: sticky; bottom: 0",
                       ".dm-page.dm-fv-full", "pointer-events: none", "prefers-reduced-motion", "@media print"):
            self.assertIn(needle, css)
        self.assertIsNone(re.search(r"url\(|@import|https?://", css))
        # the full screen stays under the dialogs (z-index 100) and the toasts (200)
        self.assertIn("z-index: 90", css)
        self.assertIn("z-index: 95", css)

    def test_06_translated(self):
        en = {}
        for path in sorted((BASE_DIR / "static" / "i18n").glob("en_*.json")):
            en.update(json.loads(path.read_text("utf-8")))
        for label in ("Tout déplier", "Tout replier", "Loupe", "Plein écran", "Quitter le plein écran", "Essentiel",
                      "Affichage du tableau", "Déplier la ligne ", "Replier la ligne ", "Revenir à la page (Esc)",
                      "Le tableau seul dans la fenêtre ; Esc pour revenir"):
            self.assertIn(label, en)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_07_behaviour(self):
        out = subprocess.run(["node", str(BASE_DIR / "tests" / "js" / "dfmea_view.js")], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("dfmea_view OK", out.stdout)


if __name__ == "__main__":
    unittest.main()
