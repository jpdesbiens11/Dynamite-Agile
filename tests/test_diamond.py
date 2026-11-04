"""0.60.11 (D-O-023): Diamond 💎 -- the functional tree of a Space (primary, secondary, tertiary, technique at level 4),
moves (when / how), numbers kept for ever, the original example, rights and journal."""
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


class DiamondTreeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"], cfg["require_initials"] = 0, False
        db.init_db(data_dir / "d.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        cls.pid = cls.admin.post("/api/admin/projects", {"key": "GLUE", "name": "Pistolet"})["project"]["id"]
        cls.ex = cls.admin.post("/api/admin/projects", {"key": "LAMP", "name": "Lampe"})["project"]["id"]
        cls.base = "/api/diamond/p/{}".format(cls.pid)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def add(self, text, **kw):
        data = self.admin.post(self.base + "/functions", dict(kw, text=text))
        return data, max(data["functions"], key=lambda f: f["number"])

    def by_number(self, data):
        return {f["number"]: f for f in data["functions"]}

    def test_01_build_how_when_and_levels(self):
        _, f1 = self.add("Appliquer de la colle chaude", primary=True)
        with self.assertRaises(ApiFailure) as err:
            self.add("Une deuxième primaire", primary=True)
        self.assertEqual(err.exception.status, 409)
        _, f2 = self.add("Stocker les bâtonnets", parent_id=f1["id"])
        _, f3 = self.add("Fondre un bâtonnet", parent_id=f1["id"])
        data, f4 = self.add("Protéger l'utilisateur", parent_id=f1["id"], index=0)  # put first ...
        self.admin.post(self.base + "/functions/{}/move".format(f4["id"]), {"parent_id": f1["id"], "index": 9})  # ... then last
        _, f5 = self.add("Convertir l'électricité en chaleur", parent_id=f3["id"])
        with self.assertRaises(ApiFailure) as err:
            self.add("Trop profond", parent_id=f5["id"])  # level 4 is for a technique function only
        self.assertEqual(err.exception.status, 409)
        data, f6 = self.add("Alimenter une résistance", parent_id=f5["id"], ftype="technique")
        fs = self.by_number(data)
        self.assertEqual([fs[n]["level"] for n in (1, 2, 3, 4, 5, 6)], [1, 2, 2, 2, 3, 4])
        order = sorted((f for f in data["functions"] if f["parent_id"] == f1["id"]), key=lambda f: f["position"])
        self.assertEqual([f["number"] for f in order], [2, 3, 4])  # « quand » : storing, melting, protection last
        self.assertTrue(all(f["in_tree"] for f in data["functions"]))
        with self.assertRaises(ApiFailure) as err:  # a branch under itself
            self.admin.post(self.base + "/functions/{}/move".format(f3["id"]), {"parent_id": f5["id"]})
        self.assertEqual(err.exception.status, 409)

    def test_02_outside_numbers_and_archive(self):
        data = self.admin.get(self.base + "/functions")
        fs = self.by_number(data)
        data, f7 = self.add("Plaire par une allure soignée", ftype="estime")
        self.assertFalse(self.by_number(data)[7]["in_tree"])
        self.assertTrue(any("hors arbre" in c for c in data["checks"]))
        # out of the tree with its « comment »: F5 and F6 leave with F3
        data = self.admin.post(self.base + "/functions/{}/move".format(fs[3]["id"]), {"parent_id": None})
        now = self.by_number(data)
        self.assertEqual([now[n]["in_tree"] for n in (3, 5, 6)], [False, False, False])
        data = self.admin.post(self.base + "/functions/{}/move".format(fs[3]["id"]), {"parent_id": fs[1]["id"], "index": 1})
        # archive F3: F5 takes its place under F1, and F3 is never given again
        data = self.admin.post(self.base + "/functions/{}/archive".format(fs[3]["id"]), {})
        now = self.by_number(data)
        self.assertNotIn(3, now)
        self.assertEqual(now[5]["parent_id"], fs[1]["id"])
        self.assertEqual((now[5]["level"], now[6]["level"]), (2, 3))
        with self.assertRaises(ApiFailure) as err:
            self.admin.patch(self.base + "/functions/{}".format(fs[2]["id"]), {"number": 3})
        self.assertIn("jamais redonné", err.exception.message)
        _, f8 = self.add("Refroidir après usage", parent_id=now[5]["id"])
        self.assertEqual(f8["number"], 8)
        self.assertTrue(any(c.startswith("F6 est une fonction technique") for c in data["checks"]))  # moved up to level 3
        data = self.admin.post(self.base + "/functions/{}/move".format(fs[6]["id"]), {"parent_id": f8["id"]})
        self.assertEqual(self.by_number(data)[6]["level"], 4)
        with self.assertRaises(ApiFailure):  # a technique function at level 4 must stay technique
            self.admin.patch(self.base + "/functions/{}".format(fs[6]["id"]), {"ftype": "usage"})

    def test_03_fields_feedback_and_errors(self):
        fs = self.by_number(self.admin.get(self.base + "/functions"))
        data = self.admin.patch(self.base + "/functions/{}".format(fs[2]["id"]),
                                {"kano": "P", "importance": "indispensable", "critical": True, "feedback_to": fs[5]["id"], "notes": "x"})
        f2 = self.by_number(data)[2]
        self.assertEqual((f2["kano"], f2["importance"], f2["critical"], f2["feedback_to"]), ("P", "indispensable", 1, fs[5]["id"]))
        for bad in ({"kano": "Z"}, {"text": ""}, {"feedback_to": fs[2]["id"]}, {"number": 1000}):
            with self.assertRaises(ApiFailure) as err:
                self.admin.patch(self.base + "/functions/{}".format(fs[2]["id"]), bad)
            self.assertIn("Correctif", err.exception.message, bad)
        actions = {r["action"] for r in self.sql("SELECT action FROM audit_log WHERE object_type = 'diamond_functions'")}
        self.assertTrue({"diamond_function_create", "diamond_function_update", "diamond_function_move",
                         "diamond_function_archive"} <= actions)

    def test_04_example_and_reader(self):
        base = "/api/diamond/p/{}".format(self.ex)
        data = self.admin.post(base + "/example", {"name": "lampe"})
        fs = self.by_number(data)
        self.assertEqual(len(fs), 21)
        self.assertEqual(fs[1]["is_primary"], 1)
        self.assertEqual(fs[16]["level"], 4)  # the technique function under a tertiary
        self.assertFalse(fs[21]["in_tree"])   # the « estime » function waits outside
        self.assertEqual(fs[9]["feedback_to"], fs[14]["id"])
        self.assertEqual(data["checks"], ["1 fonction(s) hors arbre : placez-les ou gardez-les pour le CdCF."])
        with self.assertRaises(ApiFailure) as err:
            self.admin.post(base + "/example", {"name": "lampe"})
        self.assertEqual(err.exception.status, 409)
        made = self.admin.post("/api/admin/users", {"username": "lea", "display_name": "Léa"})
        self.admin.put("/api/admin/projects/{}/members/{}".format(self.ex, made["user"]["id"]), {"role": "reader"})
        reader = Client(self.url)
        reader.login("lea", made["temp_password"], new_password="Lecture-2026!")
        self.assertEqual(len(reader.get(base + "/functions")["functions"]), 21)
        with self.assertRaises(ApiFailure) as err:
            reader.post(base + "/functions", {"text": "Écrire sans droit"})
        self.assertEqual(err.exception.status, 403)

    def sql(self, query, params=()):
        with db.connect() as conn:
            return [dict(r) for r in conn.execute(query, params)]


if __name__ == "__main__":
    unittest.main()
