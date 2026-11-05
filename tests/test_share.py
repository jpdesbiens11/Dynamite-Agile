"""0.60.29 (D-O-038): « Partager » -- the page's link sent where people already talk (system share sheet, link, courriel,
texto, Messenger, WhatsApp, Teams), from the top bar and, on a phone, beside the ☰ menu; nothing sent from the page."""
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
JS = BASE_DIR / "static" / "js" / "tools"


class ShareTest(unittest.TestCase):
    def test_01_loaded_and_wired(self):
        index = (BASE_DIR / "static" / "index.html").read_text("utf-8")
        self.assertIn('<script src="/js/tools/share.js" defer></script>', index)
        self.assertIn('DA.shareButton("phone")', (JS / "mobile.js").read_text("utf-8"))
        self.assertIn("DA.share({ direct: true })", (JS / "mobile_views.js").read_text("utf-8"))
        self.assertIn('id="i-share"', (BASE_DIR / "static" / "img" / "icons.svg").read_text("utf-8"))
        self.assertIn('id="i-share"', (BASE_DIR / "static" / "img" / "icons-term.svg").read_text("utf-8"))

    def test_02_the_usual_ways(self):
        js = (JS / "share.js").read_text("utf-8")
        for needed in ("navigator.share", "navigator.clipboard", "mailto:", "sms:", "fb-messenger://", "wa.me", "teams.microsoft.com",
                       "Copier le lien", "Autres applications", "0.60.29-share", "DA.topbarTools.push"):
            self.assertIn(needed, js, needed)
        for banned in ("fetch(", "XMLHttpRequest", "innerHTML", "sendBeacon"):  # the person's app sends, never this page
            self.assertNotIn(banned, js, banned)
        self.assertLess(len(js.splitlines()), 500)


if __name__ == "__main__":
    unittest.main()
