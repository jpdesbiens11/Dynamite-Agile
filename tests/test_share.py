"""0.60.29 (D-O-038): « Partager » -- the page's link sent where people already talk (system share sheet, link, courriel,
texto, Messenger, WhatsApp, Teams), from the top bar and, on a phone, beside the ☰ menu; nothing sent from the page."""
import json
import shutil
import subprocess
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
                       "Copier le lien", "Autres applications", "0.60.29-share", "DA.topbarTools.push",
                       # 0.60.30: solid on a computer -- the link copied first, web versions, the QR code to the phone
                       "mail.google.com", "outlook.office.com", "www.messenger.com", "t.me/share", 'execCommand("copy")',
                       "DA.qrCanvas", "0.60.30-share-qr"):
            self.assertIn(needed, js, needed)
        for banned in ("fetch(", "XMLHttpRequest", "innerHTML", "sendBeacon"):  # the person's app sends, never this page
            self.assertNotIn(banned, js, banned)
        self.assertLess(len(js.splitlines()), 500)

    @unittest.skipUnless(shutil.which("node"), "node absent")
    def test_03_qr_code(self):
        """The QR code made in the page: version by length, the three finder patterns, the dark module, timing lines
        (decoded with an independent reader when 0.60.30 was built: versions 1, 4, 7, 9, 12 and 15)."""
        script = ("const {qr} = require(process.argv[1]); const out = JSON.parse(process.argv[2]).map((t) => { const c = qr(t); "
                  "const m = []; for (let y = 0; y < c.size; y++) { let r = ''; for (let x = 0; x < c.size; x++) r += c.dark(x, y) ? '1' : '0'; "
                  "m.push(r); } return {v: c.version, m}; }); console.log(JSON.stringify(out));")
        texts = ["a", "https://dynamite.example.org/#/goldmine/EQP", "https://example.org/" + "z" * 380]
        out = json.loads(subprocess.check_output(["node", "-e", script, str(JS / "qr.js"), json.dumps(texts)]))
        self.assertEqual([o["v"] for o in out], [1, 4, 15])
        for o in out:
            m, n = o["m"], len(o["m"])
            self.assertEqual(n, o["v"] * 4 + 17)
            for x0, y0 in ((0, 0), (n - 7, 0), (0, n - 7)):
                self.assertEqual(m[y0][x0:x0 + 7], "1111111")
                self.assertEqual(m[y0 + 1][x0:x0 + 7], "1000001")
                self.assertEqual(m[y0 + 3][x0:x0 + 7], "1011101")
            self.assertEqual(m[n - 8][8], "1")  # the dark module
            self.assertEqual(m[6][8:n - 8], "".join("1" if i % 2 == 0 else "0" for i in range(8, n - 8)))


if __name__ == "__main__":
    unittest.main()
