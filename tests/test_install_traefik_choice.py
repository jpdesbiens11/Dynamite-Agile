"""0.60.34: the installation command matches the server -- the page asks about Traefik and shows « --traefik <domain> »,
the AI guide confirms the case before giving the command, and install.sh detects Traefik by itself before touching the
firewall; the website presents Diamond and what is new."""
import re
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


class TraefikChoiceTest(unittest.TestCase):
    def test_01_script_detects_before_the_firewall(self):
        sh = (BASE_DIR / "deploy" / "install.sh").read_text("utf-8")
        detect = sh.index("grep -qi traefik")
        self.assertLess(detect, sh.index('exec bash "$APP_DIR/deploy/install_traefik.sh"'))
        self.assertLess(detect, sh.index("ufw allow OpenSSH"))
        self.assertIn("MODE=traefik", sh[detect:detect + 600])

    def test_02_pages_assume_an_empty_server(self):
        """0.60.39 (D-O-048): the 5-step page assumes an empty server; install.sh detects Traefik itself and the AI
        assistant adapts the other cases (the message says so)."""
        for rel in ("tools/site/installation.html", "tools/site/en/installation.html"):
            page = (BASE_DIR / rel).read_text("utf-8")
            self.assertNotIn('id="f-traefik"', page)
            self.assertRegex(page, r'install\.sh \| sudo (DA_LANG=en )?bash -s -- <span data-v="domain">[^\n]*<span data-v="email">')
        js = (BASE_DIR / "tools" / "site" / "install.js").read_text("utf-8")
        self.assertIn("Docker", js)

    def test_03_ai_guide_confirms_the_case(self):
        for rel in ("tools/site/installer.md", "tools/site/en/installer.md"):
            guide = (BASE_DIR / rel).read_text("utf-8")
            self.assertIn("docker ps | grep -i traefik", guide)
            self.assertIn("--traefik", guide)
            self.assertTrue(re.search(r"(Mettre à jour|Update)\*\* later|\*\*Mettre à jour\*\*|\*\*Update\*\*", guide))

    def test_04_website_presents_diamond_and_news(self):
        for rel in ("site/home.html", "site/en/home.html"):
            page = (BASE_DIR / rel).read_text("utf-8")
            self.assertIn("<h3>Diamond</h3>", page)
            self.assertIn('id="nouveautes"', page)
            self.assertIn('<span class="lw-d">Dynamite</span><span class="lw-a">Agile</span>', page)


if __name__ == "__main__":
    unittest.main()
