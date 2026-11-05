"""0.60.40 (D-O-049): the landing page tells the need first (scenes), then the descent into the mine in the order of a
project, deeper at every level, down to the diamonds; HeadLamp keeps its name in every language."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools import site_text as T  # noqa: E402


class LandingStoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(BASE_DIR / "tools" / "build_site.py")], check=True, capture_output=True)

    def test_01_deeper_and_deeper_down_to_the_diamonds(self):
        depths = [d for _k, d, _n, _t in T.MINE]
        self.assertEqual(depths, sorted(depths))
        self.assertEqual(T.MINE[-1][0], "diamond")
        self.assertEqual(len(set(depths)), len(depths))

    def test_02_pages_tell_the_need_then_the_diamonds(self):
        for rel in ("site/index.html", "site/en/index.html"):
            page = (BASE_DIR / rel).read_text("utf-8")
            self.assertIn('id="besoin"', page)
            self.assertEqual(page.count('class="scene reveal"'), len(T.STORY))
            self.assertLess(page.index('id="besoin"'), page.index('id="descente"'))
            self.assertIn('class="diamonds reveal"', page)
            self.assertLess(page.index('data-depth="1000"'), page.index('class="diamonds reveal"'))
            self.assertNotIn("Dynamite | Agile", re.sub(r"<script>.*?</script>", "", page, flags=re.S).split("<main")[1].split("</main>")[0])

    def test_03_headlamp_is_never_translated(self):
        for rel in ("tools/site_text.py", "static/js/help/content_faq.js", "docs/NOMS_DES_MODULES.md"):
            self.assertNotIn("lanterne", (BASE_DIR / rel).read_text("utf-8").lower(), rel)


if __name__ == "__main__":
    unittest.main()
