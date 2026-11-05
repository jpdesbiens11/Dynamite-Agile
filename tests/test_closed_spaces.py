"""0.60.41 (D-O-050): a fresh installation is empty but for HeadLamp, which also holds the reference content (Test Base,
procedures, lists, Tools methods, Training topics, time-code sets); every new Space is a closed environment: its own
Test Base (copied once), the leave codes in its timesheet, the DFMEA offers only its own tests."""
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


class ClosedSpacesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "c.db", modules.registered_schema(), modules.registered_migrations())
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

    def keys(self):
        return {p["key"]: p["id"] for p in self.admin.get("/api/admin/projects")["projects"]}

    def test_01_only_headlamp_with_the_reference_content(self):
        keys = self.keys()
        self.assertEqual(set(keys), {"HEADLAMP"})
        hl = keys["HEADLAMP"]
        with db.connect() as conn:
            count = lambda sql: conn.execute(sql, (hl,)).fetchone()[0]  # noqa: E731
            self.assertGreater(count("SELECT COUNT(*) FROM testing_tests WHERE project_id = ?"), 20)
            self.assertGreater(count("SELECT COUNT(*) FROM training_topics WHERE project_id = ?"), 10)
            self.assertEqual(count("SELECT COUNT(*) FROM timesheet_budget_sets WHERE project_id = ?"), 2)
        titles = [p["title"] for p in self.admin.get("/api/dynamite/p/{}/pages".format(hl))["pages"]]
        for title in ("Testing — Test Procedures", "Tools — Boîte à outils", "Politique de l'équipe — vacances et congés"):
            self.assertIn(title, titles)
        roots = [p for p in self.admin.get("/api/dynamite/p/{}/pages".format(hl))["pages"] if not p.get("parent_id")]
        self.assertEqual(len(roots), 1)
        self.assertIn("HeadLamp", roots[0]["title"])  # the sandbox keeps its home; the hubs hang under it
        self.assertEqual(self.admin.get("/api/testing/tests")["space"], "HEADLAMP")

    def test_02_a_new_space_lives_on_its_own(self):
        pid = self.admin.post("/api/admin/projects", {"key": "SON", "name": "Sonnette"})["project"]["id"]
        tests = self.admin.get("/api/testing/tests?space=SON")
        self.assertEqual(tests["space"], "SON")
        self.assertFalse(tests["reference"])
        self.assertGreater(len(tests["tests"]), 20)  # copied once from the reference catalogue
        offered = self.admin.get("/api/diamond/p/{}/dfmea".format(pid))["tests"]
        self.assertTrue(offered and {t["space"] for t in offered} == {"SON"})
        week = self.admin.get("/api/timesheet/week")
        self.assertEqual([t["key"] for t in week["meta"]["leave"]], ["INT-VAC", "INT-SAN"])
        import datetime as dt
        monday = (dt.date.today() - dt.timedelta(days=dt.date.today().weekday())).isoformat()
        made = self.admin.post("/api/timesheet/entries", {"work_date": monday, "project_id": pid, "task_key": "INT-VAC",
                                                          "hours": 2, "description": "Vacances"})
        self.assertEqual(json.dumps(made).count("INT-VAC") > 0, True)


if __name__ == "__main__":
    unittest.main()
