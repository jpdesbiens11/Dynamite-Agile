"""Core lot v0.37 (0.60.103, D-O-111): « Modules et fonctions » -- every part on by default; an administrator turns off
Timesheet, the reviews, or a part of Diamond: menus, routes (404 with the way back), dashboard and search follow; the
data is kept; a part that needs another one follows it; only administrators change it; every change is journalled."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class FeaturesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "f.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        made = cls.admin.post("/api/admin/users", {"username": "etudiant", "display_name": "Étudiant"})
        cls.user = Client(cls.url)
        cls.user.login("etudiant", made["temp_password"], new_password="Baccalaureat-2026!")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fails(self, status, fn, *args):
        with self.assertRaises(ApiFailure) as caught:
            fn(*args)
        self.assertEqual(caught.exception.status, status, caught.exception)
        return str(caught.exception)

    def test_01_all_on_by_default(self):
        data = self.admin.get("/api/admin/features")["features"]
        self.assertEqual({f["key"] for f in data}, {"timesheet", "reviews", "diamond_process", "diamond_pfmea", "diamond_cplans"})
        self.assertTrue(all(f["on"] for f in data))
        me = self.user.get("/api/me")
        self.assertTrue(all(me["features"].values()))
        self.assertIn("timesheet", [m["key"] for m in me["modules"]])
        self.fails(403, self.user.put, "/api/admin/features", {"features": {"timesheet": False}})

    def test_02_turn_off_and_back(self):
        self.assertIn("inconnue", self.fails(400, self.admin.put, "/api/admin/features", {"features": {"magic": False}}))
        res = self.admin.put("/api/admin/features", {"features": {"timesheet": False, "reviews": False, "diamond_process": False}})
        on = {f["key"]: f["on"] for f in res["features"]}
        self.assertEqual((on["timesheet"], on["reviews"], on["diamond_process"], on["diamond_pfmea"], on["diamond_cplans"]),
                         (False, False, False, False, False))  # PFMEA and control plans need the assembly lines
        me = self.user.get("/api/me")
        self.assertNotIn("timesheet", [m["key"] for m in me["modules"]])
        self.assertFalse(me["features"]["reviews"])
        message = self.fails(404, self.user.get, "/api/timesheet/week")
        self.assertIn("Modules et fonctions", message)
        self.fails(404, self.user.get, "/api/objectives/people")
        self.fails(404, self.user.get, "/api/team")
        self.fails(404, self.user.get, "/api/diamond/p/1/process")
        self.admin.get("/api/diamond/p/1/dfmea")  # the rest of Diamond still answers
        dash = self.user.get("/api/dashboard")
        self.assertFalse(any(s.get("module") == "timesheet" for s in dash.get("sections", [])))
        self.admin.get("/api/admin/features")  # the admin routes stay open
        res = self.admin.put("/api/admin/features", {"features": {"timesheet": True, "reviews": True, "diamond_process": True}})
        self.assertTrue(all(f["on"] for f in res["features"]))
        self.user.get("/api/objectives/people")
        with db.connect() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'features_changed'").fetchone()[0], 2)

    def test_03_screens(self):
        js = (BASE_DIR / "static" / "js" / "admin_features.js").read_text("utf-8")
        self.assertNotIn("innerHTML", js)
        self.assertIn('"0.60.103-features"', js)
        self.assertIn('<script src="/js/admin_features.js"', (BASE_DIR / "static" / "index.html").read_text("utf-8"))
        self.assertIn('["features", "Modules et fonctions"]', (BASE_DIR / "static" / "js" / "admin.js").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
