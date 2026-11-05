"""0.60.47 (D-O-056): « Partager » in the top bar of every page of the website, in both languages -- the page being read,
anchor included; the phone's share sheet or a small menu of plain links (nothing loaded from other sites)."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class SiteShareTest(unittest.TestCase):
    def test_share_button_on_every_page(self):
        subprocess.run([sys.executable, str(BASE_DIR / "tools" / "build_site.py")], check=True, capture_output=True)
        for lang, word in (("", "Partager"), ("en/", "Share")):
            for name in ("index.html", "installation.html", "guide.html", "modules.html", "versions.html"):
                page = (BASE_DIR / "site" / (lang + name)).read_text("utf-8")
                top = page[page.index('<header class="top">'):page.index("</header>")]
                self.assertIn('data-new="0.60.47-site-share"', top, lang + name)
                self.assertIn("<span>{}</span>".format(word), top, lang + name)
                self.assertIn("navigator.share", page)
                self.assertIn("location.href", page)
                # plain links only: no script, frame or image from a social network
                self.assertIsNone(re.search(r'<(script|iframe|img)[^>]+(facebook|linkedin|wa\.me|x\.com)', page), lang + name)


if __name__ == "__main__":
    unittest.main()
