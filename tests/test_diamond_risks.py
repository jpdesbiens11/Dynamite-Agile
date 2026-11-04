"""0.60.14 (D-O-026): Diamond 💎 -- the project risk register: R-n numbers kept, P x I and levels, residual risk, owner
among the members, link to a function, « À détailler dans le DFMEA », the checks, duplicate / archive, CSV, example."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.diamond import risks as R  # noqa: E402
from tools.api_client import ApiFailure, Client  # noqa: E402


class DiamondRisksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "r.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        mk = lambda key: cls.admin.post("/api/admin/projects", {"key": key, "name": key})["project"]["id"]
        cls.lamp, cls.own = mk("LAMPR"), mk("RISK")
        cls.admin.post("/api/diamond/p/{}/example".format(cls.lamp), {"name": "lampe"})
        cls.base = "/api/diamond/p/{}/risks".format(cls.own)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_01_levels(self):
        self.assertEqual([R.level(s)["key"] for s in (1, 4, 5, 9, 10, 14, 15, 25)],
                         ["faible", "faible", "moyen", "moyen", "eleve", "eleve", "critique", "critique"])

    def test_02_example_with_the_tree(self):
        data = self.admin.get("/api/diamond/p/{}/risks".format(self.lamp))
        self.assertEqual(len(data["risks"]), 9)
        self.assertEqual(len({r["category"] for r in data["risks"]}), len(R.CATEGORIES))  # every category
        heat = next(r for r in data["risks"] if r["title"].startswith("Surchauffe"))
        self.assertEqual((heat["score"], heat["level"]["key"], heat["residual_score"], heat["to_dfmea"]), (16, "critique", 6, 1))
        self.assertEqual(heat["function_text"], "Dissiper la chaleur des DEL")
        self.assertTrue(any("sans action ou sans responsable" in c for c in data["checks"]))  # no owner yet in the example
        with self.assertRaises(ApiFailure):
            self.admin.post("/api/diamond/p/{}/risks/example".format(self.lamp), {})

    def test_03_create_rules_and_numbers(self):
        self.assertTrue(self.admin.get(self.base)["checks"][0].startswith("Aucun risque"))
        data = self.admin.post(self.base, {"title": "Pièce moulée en retard", "category": "fournisseurs", "probability": 4, "impact": 4})
        first = next(r for r in data["risks"] if r["id"] == data["created"])
        self.assertEqual((first["number"], first["score"], first["status"]), (1, 16, "open"))
        for bad in ({"title": ""}, {"title": "x", "probability": 6}, {"title": "x", "category": "météo"},
                    {"title": "x", "due_date": "demain"}, {"title": "x", "owner_id": 9999}):
            with self.assertRaises(ApiFailure) as err:
                self.admin.post(self.base, bad)
            self.assertIn("Correctif", err.exception.message, bad)
        data = self.admin.post(self.base + "/{}/duplicate".format(first["id"]), {})
        copy = next(r for r in data["risks"] if r["id"] == data["created"])
        self.assertEqual((copy["number"], copy["title"]), (2, "Pièce moulée en retard (copie)"))
        self.admin.post(self.base + "/{}/archive".format(copy["id"]), {})
        data = self.admin.post(self.base, {"title": "Fuite d'eau au joint", "probability": 2, "impact": 5})
        self.assertEqual(next(r for r in data["risks"] if r["id"] == data["created"])["number"], 3)  # R-2 is never given again

    def test_04_update_checks_and_export(self):
        data = self.admin.get(self.base)
        r1 = next(r for r in data["risks"] if r["number"] == 1)
        me = self.admin.get("/api/me")["user"]["id"] if "user" in self.admin.get("/api/me") else self.admin.get("/api/me")["id"]
        data = self.admin.patch(self.base + "/{}".format(r1["id"]), {"response": "reduire", "action": "Deuxième mouliste",
                                                                    "owner_id": me, "due_date": "2020-01-01", "residual_p": 5, "residual_i": 5})
        self.assertTrue(any("échéance dépassée" in c for c in data["checks"]))
        self.assertTrue(any("résiduel plus grand" in c for c in data["checks"]))
        data = self.admin.patch(self.base + "/{}".format(r1["id"]), {"residual_p": "", "residual_i": "", "status": "closed"})
        r1 = next(r for r in data["risks"] if r["number"] == 1)
        self.assertEqual((r1["residual_score"], r1["status"]), (None, "closed"))
        raw = self.admin.raw_get(self.base + "/export.csv")
        self.assertEqual(raw[0], 200)
        text = raw[2].decode("utf-8-sig")
        self.assertIn("R-1;Pièce moulée en retard", text)
        self.assertNotIn("(copie)", text)  # archived
        actions = {r["action"] for r in self.sql("SELECT action FROM audit_log WHERE object_type = 'diamond_risks'")}
        self.assertTrue({"diamond_risk_create", "diamond_risk_update", "diamond_risk_duplicate", "diamond_risk_archive"} <= actions)

    def test_05_reader(self):
        made = self.admin.post("/api/admin/users", {"username": "alexis3", "display_name": "Alexis"})
        self.admin.put("/api/admin/projects/{}/members/{}".format(self.lamp, made["user"]["id"]), {"role": "reader"})
        reader = Client(self.url)
        reader.login("alexis3", made["temp_password"], new_password="Lecture-2026!")
        self.assertEqual(len(reader.get("/api/diamond/p/{}/risks".format(self.lamp))["risks"]), 9)
        with self.assertRaises(ApiFailure) as err:
            reader.post("/api/diamond/p/{}/risks".format(self.lamp), {"title": "x"})
        self.assertEqual(err.exception.status, 403)

    def sql(self, query, params=()):
        with db.connect() as conn:
            return [dict(r) for r in conn.execute(query, params)]


if __name__ == "__main__":
    unittest.main()
