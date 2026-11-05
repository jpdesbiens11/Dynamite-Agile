"""0.60.42 (D-O-051): the default Space is the whole environment -- the Dashboard shows it alone (all=1: every Space),
the search looks there unless asked otherwise (front end), a Space started with « Commencer » becomes the default."""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import Client  # noqa: E402

LAMPE = json.loads((BASE_DIR / "deploy" / "starter_exemples" / "lampe_bureau.json").read_text("utf-8"))


class DefaultSpaceScopeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "s.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_commencer_sets_the_default_and_the_dashboard_follows(self):
        self.admin.post("/api/admin/projects", {"key": "AUTRE", "name": "Autre produit"})
        self.admin.post("/api/starter/apply", {"file": LAMPE})
        self.assertEqual(self.admin.get("/api/me/prefs")["prefs"]["default_space"], "LAMPE")
        dash = self.admin.get("/api/dashboard")
        self.assertEqual(dash["scope"]["space"], "LAMPE")
        self.assertEqual([p["key"] for p in dash["projects"]], ["LAMPE"])
        every = self.admin.get("/api/dashboard?all=1")
        self.assertTrue(every["scope"]["all"])
        self.assertIn("AUTRE", [p["key"] for p in every["projects"]])

    def test_02_front_end_scopes_the_search(self):
        js = (BASE_DIR / "static" / "js" / "tools" / "search.js").read_text("utf-8")
        self.assertIn("defaultKey()", js)
        self.assertIn('params.set("spaces", scope(opts))', js)
        self.assertIn("Chercher dans tous les Spaces", (BASE_DIR / "static" / "js" / "tools" / "search_page.js").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
