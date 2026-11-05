"""0.60.28 (D-O-037): « Compléter le DFMEA » -- no function skipped (every function can fail), the most relevant key test
of the Test Base on every row, the industry good practices listed in Prevention Controls; « Rien à signaler » only as
the team's explicit, justified choice."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.diamond import dfmea_practices as GP  # noqa: E402
from tools.api_client import Client  # noqa: E402


class PracticesTest(unittest.TestCase):
    def test_01_themes(self):
        self.assertEqual(GP.themes("Isoler les parties sous tension")[0], "elec")
        self.assertIn("therm", GP.themes("Dissiper la chaleur des DEL"))
        self.assertIn("mech", GP.themes("Reposer sur une base lestée"))
        self.assertIn("sw", GP.themes("Mémoriser le dernier réglage"))
        self.assertEqual(GP.themes("xyz"), [])

    def test_02_block(self):
        text = GP.block(["elec"], {"bought"})
        self.assertTrue(text.startswith(GP.MARK))
        self.assertIn("lignes de fuite", text)
        self.assertIn("deuxième source", text)
        for p in GP.GENERAL:
            self.assertIn(p, text)

    def test_03_ras(self):
        for v in ("RAS", "rien à signaler", "Rien a signaler", "N/A"):
            self.assertEqual(GP.ras(v), GP.RAS)
        self.assertEqual(GP.ras("Contact intermittent"), "Contact intermittent")


class CompleteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "c.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.admin = Client("http://127.0.0.1:{}".format(cls.server.server_address[1]))
        cls.admin.login("admin", "admin")
        cls.pid = cls.admin.post("/api/admin/projects", {"key": "CMPL", "name": "Lampe"})["project"]["id"]
        cls.admin.post("/api/diamond/p/{}/example".format(cls.pid), {"name": "lampe"})
        cls.base = "/api/diamond/p/{}/dfmea".format(cls.pid)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_complete(self):
        before = self.admin.get(self.base)
        n_functions = len(before["functions"])
        res = self.admin.post(self.base + "/complete", {})
        rows = res["rows"]
        self.assertEqual({r["function_id"] for r in rows}, {f["id"] for f in res["functions"]})  # none skipped
        self.assertEqual(res["completed"]["added"], n_functions - len({r["function_id"] for r in before["rows"]}))
        self.assertTrue(all(r["test_id"] for r in rows))
        self.assertTrue(all(GP.MARK in r["prevention"] for r in rows))
        self.assertFalse(any("sans ligne" in c or "sans essai" in c for c in res["checks"]))
        heat = next(r for r in rows if r["function_text"] == "Isoler les parties sous tension")
        self.assertIn("lignes de fuite", heat["prevention"])
        again = self.admin.post(self.base + "/complete", {})["completed"]
        self.assertEqual(again, {"added": 0, "tested": 0, "practices": 0})  # idempotent: rows already complete stay

    def test_02_ras(self):
        row = self.admin.get(self.base)["rows"][-1]
        data = self.admin.patch(self.base + "/rows/{}".format(row["id"]), {"failure_mode": "ras", "effect": ""})
        line = next(r for r in data["rows"] if r["id"] == row["id"])
        self.assertEqual(line["failure_mode"], GP.RAS)
        self.assertTrue(any("sans justification" in c for c in data["checks"]))
        data = self.admin.patch(self.base + "/rows/{}".format(row["id"]), {"effect": "Pièce sans fonction mobile ni énergie."})
        self.assertTrue(any("toute fonction peut tomber en panne" in c for c in data["checks"]))
        self.assertFalse(any("sans cotation" in c and str(line["line"]) in c.split(":")[0].split() for c in data["checks"]))


if __name__ == "__main__":
    unittest.main()
