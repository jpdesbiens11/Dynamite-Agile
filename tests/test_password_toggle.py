"""0.60.96 (D-O-102): an eye button inside every password field of the sign-in, the password change and the reset
pages (static/js/tools/password_toggle.js, DA.passwordToggle). Behaviour checked by tests/js/password_toggle.js.

    python -m unittest tests.test_password_toggle -v
"""
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
JS = BASE_DIR / "static" / "js"


class PasswordToggleTest(unittest.TestCase):
    def test_01_loaded_before_the_screens_that_use_it(self):
        html = (BASE_DIR / "static" / "index.html").read_text("utf-8")
        at = html.index('<script src="/js/tools/password_toggle.js" defer></script>')
        self.assertLess(html.index('<script src="/js/api.js" defer></script>'), at)  # DA.el
        self.assertLess(at, html.index('<script src="/js/account_mail.js" defer></script>'))
        self.assertLess(at, html.index('<script src="/js/app.js" defer></script>'))

    def test_02_every_sign_in_and_new_password_field_has_the_eye(self):
        app = (JS / "app.js").read_text("utf-8")
        for name in ("password", "current", "next", "confirmation"):
            self.assertIn("DA.passwordToggle({})".format(name), app)
        mail = (JS / "account_mail.js").read_text("utf-8")
        for name in ("next", "again"):
            self.assertIn("DA.passwordToggle({})".format(name), mail)

    def test_03_inline_svg_no_html_string_no_resource(self):
        text = (JS / "tools" / "password_toggle.js").read_text("utf-8")
        self.assertNotIn("innerHTML", text)
        self.assertNotIn("http", text.replace("http://www.w3.org/2000/svg", ""))
        self.assertNotIn("autocomplete", text.split("*/", 1)[1])  # never touched
        self.assertIn('type: "button"', text)
        self.assertIn('"data-new": "0.60.96-password-toggle"', text)
        self.assertLess(len(text.splitlines()), 500)

    def test_04_styles_in_every_theme(self):
        css = BASE_DIR / "static" / "css"
        self.assertIn(".pw-toggle:focus-visible", (css / "app.css").read_text("utf-8"))
        self.assertIn("html[data-sketch] .pw-toggle:focus-visible", (css / "sketch.css").read_text("utf-8"))
        self.assertIn("html[data-term] .pw-toggle:focus-visible", (css / "terminal.css").read_text("utf-8"))

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_05_behaviour(self):
        out = subprocess.run(["node", str(BASE_DIR / "tests" / "js" / "password_toggle.js")], capture_output=True, text=True,
                             timeout=60)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("password_toggle OK", out.stdout)


if __name__ == "__main__":
    unittest.main()
