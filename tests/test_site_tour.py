"""0.60.70 (D-O-076): the installation page -- the one link shared with partners -- carries its guided tour, the live
demo link and its QR code, in French and in English, with no external resource."""
import re
import unittest
from pathlib import Path

from tools import build_site

BASE = Path(__file__).resolve().parent.parent


class SiteTourTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_site.build()
        cls.pages = {lang: (BASE / "site" / sub / "installation.html").read_text(encoding="utf-8")
                     for lang, sub in (("fr", ""), ("en", "en"))}

    def test_tour_demo_and_qr_on_both_languages(self):
        for lang, page in self.pages.items():
            with self.subTest(lang=lang):
                self.assertIn('data-demo="{}"'.format(build_site.DEMO_URL), page)
                self.assertIn('id="demo"', page)
                self.assertIn('id="demo-qr"', page)
                self.assertIn("data-tour-start", page)
                self.assertIn("da.site.tour.seen", page)      # the tour script
                self.assertIn("qrCanvas", page)                # the QR drawn in the page
                for part in ("tour-pill", "tour-more", "tour-fold", "tour-final"):  # 0.60.72: the phone bar
                    self.assertIn(part, page)
                # 0.60.77 (D-O-083): the phone layout follows the screen (turned phone, step changed while folded)
                self.assertIn('PHONE.addEventListener("change", resized)', page)
                self.assertIn("function fit()", page)
                self.assertEqual(page.count('href="{}"'.format(build_site.DEMO_URL)), 1)

    def test_tour_targets_exist_in_the_page(self):
        js = (BASE / "tools" / "site" / "tour.js").read_text(encoding="utf-8")
        for lang, page in self.pages.items():
            for target in re.findall(r'\{ target: "([^"]+)"', js):
                with self.subTest(lang=lang, target=target):
                    marker = {"header.top nav": '<header class="top">', ".wiz-step[data-step=dest]": 'data-step="dest"',
                              ".progress-bar": 'class="progress-bar"', "#exemple": 'id="exemple"', "#demo": 'id="demo"'}[target]
                    self.assertIn(marker, page)

    def test_no_external_resource(self):
        for page in self.pages.values():
            self.assertNotRegex(page, r'<script[^>]+src=')
            self.assertNotRegex(page, r'<img[^>]+src="https?:')
            self.assertNotRegex(page, r'<link[^>]+rel="stylesheet"')
            self.assertNotRegex(page, r'url\(["\']?https?:')

if __name__ == "__main__":
    unittest.main()
