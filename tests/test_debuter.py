"""0.60.08: « Débuter » -- the project path, landing page after sign-in until it is closed, then a tab."""
import re
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402

JS = BASE_DIR / "static" / "js"


class DebuterPrefsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "d.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_open_until_closed(self):
        self.assertIs(self.admin.get("/api/me/prefs")["prefs"]["debuter_done"], False)
        self.assertIs(self.admin.put("/api/me/prefs", {"debuter_done": True})["prefs"]["debuter_done"], True)
        self.assertIs(self.admin.get("/api/me")["prefs"]["debuter_done"], True)
        with self.assertRaises(ApiFailure):
            self.admin.put("/api/me/prefs", {"debuter_done": "oui"})

    def test_02_landing_choice(self):
        self.assertEqual(self.admin.put("/api/me/prefs", {"landing": "debuter"})["prefs"]["landing"], "debuter")
        self.admin.put("/api/me/prefs", {"landing": "dashboard"})


class DebuterScreenTest(unittest.TestCase):
    def test_03_wired(self):
        index = (BASE_DIR / "static" / "index.html").read_text("utf-8")
        self.assertLess(index.index("/js/tools/debuter_content.js"), index.index("/js/tools/debuter.js"))
        app = (JS / "app.js").read_text("utf-8")
        self.assertIn('prefs.debuter_done === false ? "debuter"', app)
        self.assertIn('"0.60.08-debuter"', app)
        self.assertIn('["debuter", "dashboard", "home"]', (JS / "tools" / "sketch.js").read_text("utf-8"))
        self.assertIn('"nav.debuter": "Débuter"', (JS / "tools" / "i18n.js").read_text("utf-8"))
        self.assertNotIn("innerHTML", (JS / "tools" / "debuter.js").read_text("utf-8"))

    def test_04_links_lead_somewhere(self):
        """Every button of the page opens a module, a core view or an Admin section that exists."""
        content = (JS / "tools" / "debuter_content.js").read_text("utf-8")
        targets = set(re.findall(r'"#/([a-z]+)', content))
        known = {m["key"] for m in modules.MODULE_MANIFEST} | {"admin", "home", "settings", "dashboard", "help"}
        self.assertEqual(targets - known, set())
        admin_js = (JS / "admin.js").read_text("utf-8")
        for section in re.findall(r'"#/admin/([a-z]+)', content):
            self.assertIn('["{}",'.format(section), admin_js, section)
        icons = (BASE_DIR / "static" / "img" / "icons.svg").read_text("utf-8")
        for icon in set(re.findall(r'\[\s*"([a-z]+)", "[A-ZÀ-Ý]', content)):
            self.assertIn('id="i-{}"'.format(icon), icons, icon)

    def test_05_follows_the_pdp(self):
        content = (JS / "tools" / "debuter_content.js").read_text("utf-8")
        order = [content.index('id: "{}"'.format(p)) for p in ("avant", "A", "B", "C", "D", "continu")]
        self.assertEqual(order, sorted(order))
        for deliverable in ("Lean Canvas", "Concept Review", "PDR", "CDR", "Validation Report"):  # 0.60.09 (D-O-021)
            self.assertIn(deliverable, content)
        for retired in ("MIP", "RCS", "RVE", "Pré-étude"):
            self.assertNotIn(retired, content)
        self.assertEqual(content.count('mvp: "MVP '), 4)  # one MVP per phase: the four turns of the tornado

    def test_06_tornado_without_text(self):
        """0.60.09: the spiral is drawn in SVG without any text (FONDATIONS §5); its legend is HTML."""
        tornado = (JS / "tools" / "debuter_tornado.js").read_text("utf-8")
        self.assertNotIn('"text"', tornado)
        self.assertIn("createElementNS", tornado)
        self.assertIn("0.60.09-tornado", tornado)
        index = (BASE_DIR / "static" / "index.html").read_text("utf-8")
        self.assertLess(index.index("/js/tools/debuter_tornado.js"), index.index("/js/tools/debuter.js"))


if __name__ == "__main__":
    unittest.main()
